"""
Lumière Naturals API - a small Flask server between the web page and Supabase.

  GET  /health  -> is the server up, and can it reach the database?
  POST /login   -> {"email", "password"}; returns the customer's profile and
                   their order history, read live from the database.
  GET  /        -> serves the consumer dashboard (frontend/index.html).

Run from the project folder:  .venv\\Scripts\\python backend\\app.py
"""
import os
from datetime import date
from decimal import Decimal
from pathlib import Path

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from werkzeug.security import check_password_hash

ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT / "frontend"
load_dotenv(ROOT / ".env")

RUPEES_PER_POINT = 10   # loyalty programme: 1 point for every ₹10 spent

app = Flask(__name__, static_folder=None)
CORS(app)   # lets the page call the API even when opened straight from disk


def get_connection():
    """Open a new connection to the database in DATABASE_URL (Supabase)."""
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url or "[YOUR-PASSWORD]" in url:
        raise RuntimeError("DATABASE_URL is not set - copy .env.example to .env and fill it in")
    extra = {} if "sslmode=" in url else {"sslmode": "require"}
    return psycopg2.connect(url, connect_timeout=10,
                            cursor_factory=psycopg2.extras.RealDictCursor, **extra)


def to_json(row):
    """Database values -> JSON-friendly values (Decimal -> number, date -> 'YYYY-MM-DD')."""
    out = {}
    for key, value in row.items():
        if isinstance(value, Decimal):
            value = float(value)
        elif isinstance(value, date):
            value = value.isoformat()
        out[key] = value
    return out


@app.get("/health")
def health():
    try:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS customers FROM dim_customer")
                customers = cur.fetchone()["customers"]
        finally:
            conn.close()
    except Exception as exc:
        app.logger.error("Health check failed: %s", exc)
        return jsonify(status="ok", database="unreachable", error=str(exc).strip()), 503
    return jsonify(status="ok", database="connected", customers=customers)


@app.post("/login")
def login():
    body = request.get_json(silent=True) or {}
    email = str(body.get("email", "")).strip().lower()
    password = str(body.get("password", ""))
    if not email or not password:
        return jsonify(error="Please enter your email and password."), 400

    try:
        conn = get_connection()
    except Exception as exc:
        app.logger.error("Database connection failed: %s", exc)
        return jsonify(error="Cannot reach the database right now. Please try again."), 503

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT customer_id, name, gender, age, age_group, email,
                       password_hash, country, city
                FROM dim_customer
                WHERE lower(email) = %s
                """,
                (email,),
            )
            customer = cur.fetchone()
            # Same message for "no such email" and "wrong password", so the
            # page does not reveal which emails are registered.
            if customer is None or not check_password_hash(customer.pop("password_hash"), password):
                return jsonify(error="Incorrect email or password."), 401

            cur.execute(
                """
                SELECT o.order_id, o.order_date, o.quantity, o.revenue, o.rating,
                       p.product_id, p.product_name, p.size, p.price,
                       c.channel_name
                FROM fact_orders o
                JOIN dim_product p ON p.product_id = o.product_id
                JOIN dim_channel c ON c.channel_id = o.channel_id
                WHERE o.customer_id = %s
                ORDER BY o.order_date DESC, o.order_id DESC
                """,
                (customer["customer_id"],),
            )
            orders = [to_json(row) for row in cur.fetchall()]
    finally:
        conn.close()

    total_spent = sum(o["revenue"] for o in orders)
    summary = {
        "total_orders": len(orders),
        "total_spent": total_spent,
        "loyalty_points": int(total_spent // RUPEES_PER_POINT),
        "first_order_date": orders[-1]["order_date"] if orders else None,
    }
    return jsonify(customer=to_json(customer), orders=orders, summary=summary)


# ------------------------------------------------------------ dashboard files
@app.get("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.get("/<path:filename>")
def frontend_files(filename):
    return send_from_directory(FRONTEND_DIR, filename)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Lumière Naturals API running - open http://127.0.0.1:{port} in your browser")
    app.run(host="127.0.0.1", port=port, debug=os.environ.get("FLASK_DEBUG") == "1")
