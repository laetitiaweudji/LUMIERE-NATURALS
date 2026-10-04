# Lumière Naturals — Business Intelligence Project

*Nourish · Shine · Grow*

Lumière Naturals is a fictional natural hair oil brand. This project is a complete,
cloud-connected BI system for it:

```
 data/generate_data.py ──► CSV files + database/seed.sql
                                   │
                                   ▼  (setup_database.py)
                    ┌──────────────────────────────┐
                    │  Supabase PostgreSQL (cloud) │
                    │  star schema, 258 records    │
                    └──────────────────────────────┘
                     ▲                          ▲
           SQL over  │                          │  SQL over the internet
           internet  │                          │
           ┌─────────┴─────────┐       ┌────────┴─────────┐
           │ Flask API         │       │ Power BI Desktop │
           │ backend/app.py    │       │ (admin report)   │
           └─────────▲─────────┘       └──────────────────┘
                     │ fetch() (JSON)
           ┌─────────┴─────────┐
           │ Consumer dashboard│
           │ frontend/         │
           └───────────────────┘
```

No customer data is written into the web page or the API code. Everything shown is
read from the cloud database at the moment someone logs in.

## What's in the folder

| Path | What it does |
|---|---|
| `data/generate_data.py` | Creates the fake dataset. Uses a fixed random seed, so it produces the same data every time. |
| `data/*.csv` | The dataset: 100 customers, 10 products, 5 channels, 130 orders and 13 inventory batches (258 records). |
| `database/schema.sql` | Creates the 5 star-schema tables, with primary and foreign keys. |
| `database/seed.sql` | Inserts the 258 records. Passwords are stored as secure hashes. |
| `database/setup_database.py` | Runs both SQL files against your Supabase database and counts the rows. |
| `backend/app.py` | Flask API with `/health` and `/login`. It also serves the dashboard. |
| `frontend/` | Consumer dashboard (HTML/CSS/JS) in the forest green and gold theme. |
| `docs/POWER_BI.md` | How to connect Power BI Desktop to the same database. |
| `.env.example` | Template for your secret connection string. The real `.env` is never committed. |

## The star schema

```
               dim_customer (100)
                     │ customer_id
                     │
 dim_channel (5) ── fact_orders (130) ── dim_product (10) ── dim_inventory (13)
     channel_id                            product_id          product_id
```

- **fact_orders** is the *fact* table. It has one row per order and holds the numbers you
  analyse: quantity, revenue and rating.
- The **dim_** tables are *dimensions*. They describe each order: who bought it
  (customer), what was bought (product) and where it was bought (channel).
  **dim_inventory** links to products and tracks stock and expiry dates.

PostgreSQL turns unquoted names into lower case, so the tables use snake_case:
`DimCustomer` → `dim_customer`, `FactOrders` → `fact_orders`, and so on.

---

## Step-by-step setup (Windows)

### 1. Install the Python packages (one time)

Open a terminal in this folder:

```powershell
py -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

`.venv` is a private folder of packages for this project only.

### 2. Create the Supabase database

1. Go to <https://supabase.com>, sign in, and click **New project**.
2. Choose a name (for example `lumiere-naturals`), **set a database password and write it down**,
   and pick the region closest to you (for example *South Asia (Mumbai)*).
3. Wait about 2 minutes for the project to start.
4. Click **Connect** in the top bar of the project. In the *Connection string* tab, choose
   **Type: URI** and **Method: Session pooler**. Copy the string. It looks like this:

   ```
   postgresql://postgres.abcdefghijklmnop:[YOUR-PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:5432/postgres
   ```

   > Why "Session pooler"? The "Direct connection" address only works on IPv6
   > networks, which most home and college Wi-Fi is not. The session pooler works everywhere.

### 3. Put the connection string in `.env`

```powershell
copy .env.example .env
notepad .env
```

Replace the example `DATABASE_URL` with your string, and replace `[YOUR-PASSWORD]`
with your real database password (remove the square brackets too).

> If your password contains special characters such as `@ # / : ?`, they must be encoded:
> `@` → `%40`, `#` → `%23`, `/` → `%2F`, `:` → `%3A`, `?` → `%3F`.
> The simplest fix is to reset the database password to letters and numbers only
> (Project Settings → Database → Reset database password).

`.env` is listed in `.gitignore`, so your password never goes to GitHub.

### 4. Load the data into the cloud

```powershell
.venv\Scripts\python database\setup_database.py
```

Expected output:

```
Connected to 'postgres' at ... (PostgreSQL 17...)
Running schema.sql...
Running seed.sql...

Rows now in the database:
  dim_customer    100
  dim_product      10
  dim_channel       5
  dim_inventory    13
  fact_orders     130
  TOTAL           258
```

To check, open Supabase → **Table Editor**. All 5 tables are there with their data.

*(Another way to load the data without Python: open Supabase → **SQL Editor**, paste all of
`database/schema.sql` and click Run, then do the same with `database/seed.sql`.)*

### 5. Start the backend and open the dashboard

```powershell
.venv\Scripts\python backend\app.py
```

Then open **<http://127.0.0.1:5000>** in your browser. The small status line under the
Log In button should show a green dot: *"Live login server connected · database online"*.

Demo login:

| Email | Password |
|---|---|
| `priya.sharma@example.com` | `Lumiere@2026` |

Every customer can log in. Their emails and passwords are in `data/customers.csv`
(for example `deepika.venkatesh@example.com` / `Deepika@4920`).

Press `Ctrl + C` in the terminal to stop the server.

---

## The API

| Method | URL | Body | Returns |
|---|---|---|---|
| GET | `/health` | none | `{"status":"ok","database":"connected","customers":100}`. Returns 503 if the database cannot be reached. |
| POST | `/login` | `{"email": "...", "password": "..."}` | `{customer, orders[], summary}`. Returns 401 for a wrong email or password, and 400 if a field is missing. |

How `/login` works:
1. It looks up the email in `dim_customer`.
2. It checks the password against the stored hash. The real password is never stored.
3. It joins `fact_orders` with `dim_product` and `dim_channel` to get that customer's orders.
4. It calculates total spent and loyalty points (1 point for every ₹10 spent) from those orders.

## Power BI

See **[docs/POWER_BI.md](docs/POWER_BI.md)**. Power BI Desktop connects straight to the same
Supabase database, so the admin report and the consumer dashboard always show the same data.

## Changing the data

1. Edit `data/generate_data.py`, for example to change `NUM_CUSTOMERS`.
2. Run `.venv\Scripts\python data\generate_data.py`.
3. Run `.venv\Scripts\python database\setup_database.py`. This replaces the tables in Supabase.

## Troubleshooting

| Message | Fix |
|---|---|
| `DATABASE_URL is missing` | You haven't created `.env` yet. See step 3. |
| `password authentication failed` | Wrong password in `.env`, or the special characters aren't encoded. |
| `could not translate host name` / timeout | You're using the *Direct connection* string. Use the **Session pooler** one. |
| `Tenant or user not found` | The username must be `postgres.<project-ref>`, exactly as Supabase shows it. |
| Red dot: "Login server offline" | The backend isn't running. Start it with step 5. |
| `py` is not recognised | Install Python from python.org and tick "Add to PATH". |
