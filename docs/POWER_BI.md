# Connecting Power BI Desktop to Supabase

Power BI connects **directly** to the same Supabase PostgreSQL database as the Flask
backend. It doesn't use the CSV files. When you click **Refresh**, Power BI downloads the
latest data from the cloud.

## Why this schema already works with Power BI

- It's a **star schema**: one fact table (`fact_orders`) and dimension tables around it,
  which is the layout Power BI is designed for.
- Every table has a **primary key**, and every link is a **foreign key**. When you load the
  tables, Power BI can create the relationships for you.
- The data types are clean (`DATE`, `NUMERIC`, `INTEGER`), so dates, sums and averages
  work without any conversion.

## 1. Get your connection details

Supabase → your project → **Connect** → *Connection string* → **Session pooler** → choose
"View parameters" (or read them from the URI):

| Setting | Example |
|---|---|
| Host | `aws-0-ap-south-1.pooler.supabase.com` |
| Port | `5432` |
| Database | `postgres` |
| User | `postgres.abcdefghijklmnop` (your project ref after the dot) |
| Password | your database password |

## 2. Trust Supabase's SSL certificate (one time, important)

Power BI only accepts encrypted connections it can verify. Supabase signs its certificate
with its own authority, so you need to install that certificate on Windows once. If you skip
this step, Power BI shows *"The remote certificate is invalid according to the validation procedure."*

1. Supabase → **Project Settings → Database → SSL Configuration → Download certificate**
   (the file is named something like `prod-ca-2021.crt`).
2. Double-click the file → **Install Certificate…** → *Current User* → Next.
3. Choose **Place all certificates in the following store** → Browse → **Trusted Root
   Certification Authorities** → OK → Next → Finish → Yes.
4. Close and reopen Power BI Desktop.

## 3. Connect

1. Power BI Desktop → **Home → Get data → More… → PostgreSQL database** → Connect.
2. **Server:** `aws-0-ap-south-1.pooler.supabase.com:5432` (your host + `:5432`)
   **Database:** `postgres`
   **Data connectivity mode:** **Import**
3. In the credentials window, choose the **Database** tab (not Windows). Enter your user
   (`postgres.<project-ref>`) and password. Click Connect.
4. In the Navigator, tick:
   `public.dim_customer`, `public.dim_product`, `public.dim_channel`,
   `public.dim_inventory`, `public.fact_orders`.
5. Click **Transform Data** (not Load) and make two small changes:
   - Select `dim_customer`, right-click the **password_hash** column and choose **Remove**.
     Hashes don't belong in a report.
   - Optional: rename the tables to `DimCustomer`, `DimProduct`, `DimChannel`, `DimInventory`
     and `FactOrders` so they match your report.
6. **Close & Apply.**

## 4. Check the relationships (Model view)

Click the **Model view** icon on the left. You should see the following relationships.
If any line is missing, drag the column from one table onto the matching column in the other.

| From (many) | To (one) | Column |
|---|---|---|
| fact_orders | dim_customer | customer_id |
| fact_orders | dim_product | product_id |
| fact_orders | dim_channel | channel_id |
| dim_inventory | dim_product | product_id |

Keep the cross-filter direction set to **Single**.

## 5. Add a date table and measures

**Modeling → New table:**

```DAX
Calendar =
ADDCOLUMNS (
    CALENDAR ( DATE ( 2026, 5, 1 ), DATE ( 2026, 12, 31 ) ),
    "Month", FORMAT ( [Date], "MMM yyyy" ),
    "MonthNo", YEAR ( [Date] ) * 100 + MONTH ( [Date] )
)
```

Then link `Calendar[Date]` to `fact_orders[order_date]`. In Table view, set
`Calendar[Month]` → *Sort by column* → `MonthNo`.

**Modeling → New measure** (one at a time, on `fact_orders`):

```DAX
Total Revenue = SUM ( fact_orders[revenue] )
Total Orders = COUNTROWS ( fact_orders )
Total Customers = DISTINCTCOUNT ( fact_orders[customer_id] )
Avg Order Value = DIVIDE ( [Total Revenue], [Total Orders] )
Avg Rating = AVERAGE ( fact_orders[rating] )
Repeat Purchase Rate =
    VAR buyers = VALUES ( fact_orders[customer_id] )
    VAR repeaters = FILTER ( buyers, CALCULATE ( COUNTROWS ( fact_orders ) ) > 1 )
    RETURN DIVIDE ( COUNTROWS ( repeaters ), COUNTROWS ( buyers ) )
Stock Units = SUM ( dim_inventory[stock_units] )
```

## 6. Suggested visuals (matches the admin report design)

| Visual | Fields |
|---|---|
| Cards | Total Customers, Total Revenue, Repeat Purchase Rate, Avg Order Value |
| Line + clustered column | X: Calendar[Month]; columns: Total Customers; line: Total Revenue |
| Bar chart | dim_customer[country] by Total Orders |
| Donut | dim_customer[gender] by Total Orders |
| Column chart | dim_customer[age_group] by Total Orders |
| Table | dim_channel[channel_name], Total Orders, Total Revenue |
| Table | dim_inventory[batch_id], dim_product[product_name], dim_product[size], Stock Units, dim_inventory[expiry_date] (conditional formatting: red below 20) |
| Slicers | Calendar[Month], dim_customer[country], dim_customer[gender], dim_customer[age_group] |

## 7. Prove it's live (good for your demo)

1. In Supabase → **SQL Editor**, run:
   ```sql
   UPDATE dim_inventory SET stock_units = 5 WHERE batch_id = 'BATCH-08';
   ```
2. In Power BI, click **Home → Refresh**. The inventory table now shows 5 units.
   The data came from the cloud, not from a file.

## Common errors

| Error | Fix |
|---|---|
| *The remote certificate is invalid…* | Do step 2 (install the Supabase certificate), then restart Power BI. |
| *Tenant or user not found* | The user must be `postgres.<project-ref>`, not just `postgres`. |
| *password authentication failed* | Re-enter credentials: File → Options and settings → Data source settings → select the source → Edit Permissions. |
| Connection times out | Use the **pooler** host (`…pooler.supabase.com`), not `db.<ref>.supabase.co`. |
| The free project went to sleep | Free Supabase projects pause after a week with no activity. Open the dashboard and click **Restore project**. |
