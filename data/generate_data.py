"""
Generate the synthetic Lumière Naturals dataset.

Outputs (all regenerated on every run):
  data/customers.csv, products.csv, channels.csv, orders.csv, inventory.csv
  database/seed.sql   -> INSERT statements that load the same data into PostgreSQL

The random seed is fixed, so the people, products and orders are the same every
time. Passwords are stored in the CSV in plain text (they are fake demo logins)
but only a secure hash of each password goes into seed.sql / the database.

Run:  .venv\\Scripts\\python data\\generate_data.py
"""
import csv
import random
from datetime import date, timedelta
from pathlib import Path

from werkzeug.security import generate_password_hash

random.seed(2026)

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
SEED_SQL = ROOT / "database" / "seed.sql"

NUM_CUSTOMERS = 100
NUM_REPEAT_ORDERS = 30            # 100 first orders + 30 repeat orders = 130 orders
START_DATE = date(2026, 5, 1)
END_DATE = date(2026, 9, 30)

# ---------------------------------------------------------------- reference data
PRODUCTS = [
    # product_id, product_name, size, price (INR), popularity weight
    ("LN-B01", "Growth & Shine Hair Oil", "100ml", 299, 22),
    ("LN-B02", "Growth & Shine Hair Oil", "200ml", 499, 16),
    ("LN-B03", "Rosemary Boost Oil", "100ml", 349, 12),
    ("LN-B04", "Rosemary Boost Oil", "200ml", 579, 7),
    ("LN-B05", "Argan Silk Repair Oil", "100ml", 399, 9),
    ("LN-B06", "Argan Silk Repair Oil", "200ml", 649, 5),
    ("LN-B07", "Castor Thick & Strong Oil", "100ml", 329, 10),
    ("LN-B08", "Castor Thick & Strong Oil", "200ml", 549, 6),
    ("LN-B09", "Coconut Classic Daily Oil", "100ml", 249, 8),
    ("LN-B10", "Coconut Classic Daily Oil", "200ml", 429, 5),
]

CHANNELS = [
    ("CH01", "Website"),
    ("CH02", "Instagram"),
    ("CH03", "Retail Store"),
    ("CH04", "WhatsApp"),
    ("CH05", "Amazon"),
]
# Customers in India can buy anywhere; customers abroad buy online only.
CHANNEL_WEIGHTS_INDIA = {"CH01": 20, "CH02": 30, "CH03": 15, "CH04": 20, "CH05": 15}
CHANNEL_WEIGHTS_ABROAD = {"CH01": 35, "CH02": 35, "CH04": 30}

# Exact counts so the dataset matches the pilot report (72% India, 82% female, ...)
COUNTRY_COUNTS = {"India": 72, "Cameroon": 14, "Nigeria": 6, "Ghana": 4, "Kenya": 4}
GENDER_COUNTS = {"Female": 82, "Male": 15, "Undisclosed": 3}
AGE_GROUP_COUNTS = {"18-24": 58, "25-34": 31, "35-44": 8, "45+": 3}
AGE_RANGES = {"18-24": (18, 24), "25-34": (25, 34), "35-44": (35, 44), "45+": (45, 58)}

CITIES = {
    "India": [("Coimbatore", 40), ("Chennai", 10), ("Bengaluru", 9), ("Kochi", 5),
              ("Hyderabad", 5), ("Mumbai", 3)],
    "Cameroon": [("Yaoundé", 8), ("Douala", 6)],
    "Nigeria": [("Lagos", 4), ("Abuja", 2)],
    "Ghana": [("Accra", 4)],
    "Kenya": [("Nairobi", 4)],
}

FIRST_NAMES = {
    ("India", "Female"): ["Priya", "Divya", "Kavya", "Ananya", "Meera", "Harini", "Sneha",
                          "Lakshmi", "Nandhini", "Aishwarya", "Swathi", "Keerthana", "Pooja",
                          "Deepika", "Janani", "Shruti", "Riya", "Varsha", "Sowmya", "Gayathri",
                          "Ishita", "Nithya", "Bhavana", "Revathi", "Sanjana", "Aarthi"],
    ("India", "Male"): ["Arjun", "Karthik", "Rahul", "Vignesh", "Surya", "Aditya", "Pranav",
                        "Rohan", "Hari", "Naveen"],
    ("Cameroon", "Female"): ["Laure", "Brenda", "Christelle", "Nadège", "Estelle", "Murielle",
                             "Carine", "Sandrine", "Vanessa", "Ornella"],
    ("Cameroon", "Male"): ["Junior", "Franck", "Arnaud", "Boris"],
    ("Nigeria", "Female"): ["Chiamaka", "Adaeze", "Funmilayo", "Ngozi", "Temitope", "Amara"],
    ("Nigeria", "Male"): ["Chinedu", "Emeka", "Tunde"],
    ("Ghana", "Female"): ["Abena", "Akosua", "Efua", "Ama"],
    ("Ghana", "Male"): ["Kwame", "Kofi"],
    ("Kenya", "Female"): ["Wanjiru", "Achieng", "Njeri", "Akinyi"],
    ("Kenya", "Male"): ["Otieno", "Kamau"],
}
LAST_NAMES = {
    "India": ["Sharma", "Iyer", "Raman", "Krishnan", "Nair", "Reddy", "Menon", "Subramanian",
              "Rajan", "Pillai", "Kumar", "Srinivasan", "Venkatesh", "Balaji", "Murthy",
              "Patel", "Gupta", "Shankar", "Mohan", "Prakash"],
    "Cameroon": ["Mbarga", "Nkemdirim", "Tchoumi", "Fotso", "Ngono", "Essomba", "Kamga",
                 "Njoya", "Atangana", "Biya"],
    "Nigeria": ["Okafor", "Adeyemi", "Eze", "Balogun", "Nwosu", "Okonkwo"],
    "Ghana": ["Mensah", "Owusu", "Boateng", "Asante"],
    "Kenya": ["Mwangi", "Odhiambo", "Wambui", "Kiprono"],
}


def expand(counts):
    """{'A': 2, 'B': 1} -> shuffled ['A', 'B', 'A']"""
    items = [key for key, n in counts.items() for _ in range(n)]
    random.shuffle(items)
    return items


def ascii_slug(text):
    """Strip accents so emails stay plain ASCII (Nadège -> nadege)."""
    table = str.maketrans("éèêëàâäïîôöùûüçÉÈ", "eeeeaaaiioouuucEE")
    return text.translate(table).lower().replace(" ", "")


def random_date(start, end, weights_by_month):
    """Pick a date between start and end, favouring later months (sales were growing)."""
    days = [start + timedelta(d) for d in range((end - start).days + 1)]
    weights = [weights_by_month.get(d.month, 1) for d in days]
    return random.choices(days, weights)[0]


# ------------------------------------------------------------------- customers
def build_customers():
    countries = expand(COUNTRY_COUNTS)
    genders = expand(GENDER_COUNTS)
    age_groups = expand(AGE_GROUP_COUNTS)
    city_pool = {c: expand(dict(cities)) for c, cities in CITIES.items()}
    # Customer C001 is a memorable demo login: an 18-24 female student in Coimbatore.
    for values, wanted in ((countries, "India"), (genders, "Female"), (age_groups, "18-24")):
        k = values.index(wanted)
        values[0], values[k] = values[k], values[0]
    city_pool["India"].remove("Coimbatore")

    customers, used_emails = [], set()
    for i in range(NUM_CUSTOMERS):
        country, gender, age_group = countries[i], genders[i], age_groups[i]
        name_gender = "Female" if gender == "Undisclosed" else gender
        first = random.choice(FIRST_NAMES[(country, name_gender)])
        last = random.choice(LAST_NAMES[country])
        if i == 0:
            first, last = "Priya", "Sharma"
        email = f"{ascii_slug(first)}.{ascii_slug(last)}@example.com"
        n = 2
        while email in used_emails:
            email = f"{ascii_slug(first)}.{ascii_slug(last)}{n}@example.com"
            n += 1
        used_emails.add(email)

        customers.append({
            "CustomerID": f"C{i + 1:03d}",
            "Name": f"{first} {last}",
            "Gender": gender,
            "Age": random.randint(*AGE_RANGES[age_group]),
            "AgeGroup": age_group,
            "Email": email,
            "Password": "Lumiere@2026" if i == 0 else f"{first}@{random.randint(1000, 9999)}",
            "Country": country,
            "City": "Coimbatore" if i == 0 else city_pool[country].pop(),
        })
    return customers


# ---------------------------------------------------------------------- orders
def build_orders(customers):
    product_ids = [p[0] for p in PRODUCTS]
    product_weights = [p[4] for p in PRODUCTS]
    prices = {p[0]: p[3] for p in PRODUCTS}
    month_weights = {5: 1.0, 6: 1.5, 7: 2.0, 8: 2.3, 9: 2.6}

    def make_order(customer, order_date):
        weights = CHANNEL_WEIGHTS_INDIA if customer["Country"] == "India" else CHANNEL_WEIGHTS_ABROAD
        product_id = random.choices(product_ids, product_weights)[0]
        quantity = random.choices([1, 2, 3], [80, 17, 3])[0]
        return {
            "CustomerID": customer["CustomerID"],
            "ProductID": product_id,
            "ChannelID": random.choices(list(weights), list(weights.values()))[0],
            "OrderDate": order_date,
            "Quantity": quantity,
            "Revenue": quantity * prices[product_id],
            "Rating": random.choices([5, 4, 3, 2, 1], [45, 35, 12, 5, 3])[0],
        }

    orders, first_dates = [], {}
    for c in customers:
        d = random_date(START_DATE, END_DATE, month_weights)
        first_dates[c["CustomerID"]] = d
        orders.append(make_order(c, d))

    # Repeat buyers: only customers whose first order leaves room for a second one.
    eligible = [c for c in customers if first_dates[c["CustomerID"]] <= END_DATE - timedelta(21)]
    eligible.remove(customers[0])
    repeaters = [customers[0]] + random.sample(eligible, 21)   # demo customer always has history
    for i in range(NUM_REPEAT_ORDERS):
        c = repeaters[i % len(repeaters)]
        last = max(o["OrderDate"] for o in orders if o["CustomerID"] == c["CustomerID"])
        d = min(last + timedelta(random.randint(18, 45)), END_DATE)
        orders.append(make_order(c, d))

    orders.sort(key=lambda o: (o["OrderDate"], o["CustomerID"]))
    for i, o in enumerate(orders, start=1):
        o["OrderID"] = f"ORD-{i:04d}"
        o["OrderDate"] = o["OrderDate"].isoformat()
    cols = ["OrderID", "CustomerID", "ProductID", "ChannelID", "OrderDate", "Quantity", "Revenue", "Rating"]
    return [{k: o[k] for k in cols} for o in orders]


# ------------------------------------------------------------------- inventory
def build_inventory():
    # Two batches for best sellers, one for the rest. LN-B07 and LN-B10 run low,
    # matching the "low stock" alert in the admin report.
    stock = {"LN-B01": [120, 85], "LN-B02": [90, 60], "LN-B03": [70, 45], "LN-B04": [52],
             "LN-B05": [64], "LN-B06": [38], "LN-B07": [18], "LN-B08": [64], "LN-B09": [41],
             "LN-B10": [9]}
    rows, n = [], 1
    for product_id, units in stock.items():
        for k, u in enumerate(units):
            expiry = date(2027, 3, 31) + timedelta(days=60 * k + random.randint(0, 120))
            rows.append({"BatchID": f"BATCH-{n:02d}", "ProductID": product_id,
                         "StockUnits": u, "ExpiryDate": expiry.isoformat()})
            n += 1
    return rows


# --------------------------------------------------------------------- writers
def write_csv(name, rows):
    path = DATA_DIR / name
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"  {path.relative_to(ROOT)}: {len(rows)} rows")


def sql_value(v):
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def insert_block(table, columns, rows):
    lines = [f"INSERT INTO {table} ({', '.join(columns)}) VALUES"]
    lines += [f"  ({', '.join(sql_value(v) for v in row)})," for row in rows]
    lines[-1] = lines[-1][:-1] + ";"
    return "\n".join(lines) + "\n\n"


def write_seed_sql(customers, orders, inventory):
    sql = [
        "-- Lumière Naturals seed data (generated by data/generate_data.py - do not edit by hand)\n",
        "-- Run AFTER schema.sql. Passwords are stored as one-way hashes, never as plain text.\n\n",
        insert_block("dim_product", ["product_id", "product_name", "size", "price"],
                     [p[:4] for p in PRODUCTS]),
        insert_block("dim_channel", ["channel_id", "channel_name"], CHANNELS),
        insert_block("dim_customer",
                     ["customer_id", "name", "gender", "age", "age_group", "email",
                      "password_hash", "country", "city"],
                     [(c["CustomerID"], c["Name"], c["Gender"], c["Age"], c["AgeGroup"], c["Email"],
                       generate_password_hash(c["Password"]), c["Country"], c["City"])
                      for c in customers]),
        insert_block("dim_inventory", ["batch_id", "product_id", "stock_units", "expiry_date"],
                     [tuple(r.values()) for r in inventory]),
        insert_block("fact_orders",
                     ["order_id", "customer_id", "product_id", "channel_id", "order_date",
                      "quantity", "revenue", "rating"],
                     [tuple(o.values()) for o in orders]),
    ]
    SEED_SQL.write_text("".join(sql), encoding="utf-8")
    print(f"  {SEED_SQL.relative_to(ROOT)}")


def main():
    customers = build_customers()
    orders = build_orders(customers)
    inventory = build_inventory()
    products = [{"ProductID": p[0], "ProductName": p[1], "Size": p[2], "Price": p[3]} for p in PRODUCTS]
    channels = [{"ChannelID": c[0], "ChannelName": c[1]} for c in CHANNELS]

    print("Writing dataset:")
    write_csv("customers.csv", customers)
    write_csv("products.csv", products)
    write_csv("channels.csv", channels)
    write_csv("orders.csv", orders)
    write_csv("inventory.csv", inventory)
    write_seed_sql(customers, orders, inventory)

    total = len(customers) + len(products) + len(channels) + len(orders) + len(inventory)
    print(f"Total records: {total}")
    print(f"Demo login: {customers[0]['Email']} / {customers[0]['Password']}")


if __name__ == "__main__":
    main()
