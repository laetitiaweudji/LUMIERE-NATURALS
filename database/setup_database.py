"""
Create the tables and load the data into the database named in .env (DATABASE_URL).

Run from the project folder:  .venv\\Scripts\\python database\\setup_database.py

It runs schema.sql (drops + recreates the tables) and then seed.sql (inserts the
rows), then counts the rows in every table so you can see the data arrived.
"""
import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

TABLES = ["dim_customer", "dim_product", "dim_channel", "dim_inventory", "fact_orders"]


def connect():
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url or "[YOUR-PASSWORD]" in url:
        sys.exit("DATABASE_URL is missing. Copy .env.example to .env and paste your Supabase connection string.")
    # Supabase only accepts encrypted connections.
    extra = {} if "sslmode=" in url else {"sslmode": "require"}
    return psycopg2.connect(url, connect_timeout=15, **extra)


def main():
    print("Connecting to the database...")
    conn = connect()
    with conn, conn.cursor() as cur:
        cur.execute("SELECT current_database(), inet_server_addr(), version()")
        db, host, version = cur.fetchone()
        print(f"Connected to '{db}' at {host} ({version.split(',')[0]})")

        for name in ("schema.sql", "seed.sql"):
            print(f"Running {name}...")
            cur.execute((ROOT / "database" / name).read_text(encoding="utf-8"))

        print("\nRows now in the database:")
        total = 0
        for table in TABLES:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            n = cur.fetchone()[0]
            total += n
            print(f"  {table:<14} {n:>4}")
        print(f"  {'TOTAL':<14} {total:>4}")
    conn.close()
    print("\nDone - the data is live in the database.")


if __name__ == "__main__":
    main()
