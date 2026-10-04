-- =====================================================================
-- Lumière Naturals - star schema (PostgreSQL / Supabase)
--
--                     dim_customer
--                          |
--   dim_channel --- fact_orders --- dim_product --- dim_inventory
--
-- fact_orders is the fact table: one row per order, holding the numbers
-- we analyse (quantity, revenue, rating). The dim_* tables describe the
-- who / what / where of each order.
--
-- PostgreSQL folds unquoted names to lower case, so the tables are named
-- in snake_case:  DimCustomer -> dim_customer, FactOrders -> fact_orders.
--
-- WARNING: running this file deletes the tables and all their data.
-- Run it, then run seed.sql to load the data again.
-- =====================================================================

DROP TABLE IF EXISTS fact_orders, dim_inventory, dim_customer, dim_product, dim_channel CASCADE;

CREATE TABLE dim_customer (
    customer_id    VARCHAR(10)  PRIMARY KEY,                 -- e.g. C001
    name           VARCHAR(100) NOT NULL,
    gender         VARCHAR(20)  NOT NULL CHECK (gender IN ('Female', 'Male', 'Undisclosed')),
    age            SMALLINT     NOT NULL CHECK (age BETWEEN 13 AND 100),
    age_group      VARCHAR(10)  NOT NULL CHECK (age_group IN ('18-24', '25-34', '35-44', '45+')),
    email          VARCHAR(150) NOT NULL UNIQUE,
    password_hash  VARCHAR(255) NOT NULL,                    -- hashed, never plain text
    country        VARCHAR(60)  NOT NULL,
    city           VARCHAR(60)  NOT NULL
);

CREATE TABLE dim_product (
    product_id     VARCHAR(10)   PRIMARY KEY,                -- e.g. LN-B01
    product_name   VARCHAR(100)  NOT NULL,
    size           VARCHAR(10)   NOT NULL,
    price          NUMERIC(10,2) NOT NULL CHECK (price > 0)  -- INR
);

CREATE TABLE dim_channel (
    channel_id     VARCHAR(10)  PRIMARY KEY,                 -- e.g. CH01
    channel_name   VARCHAR(50)  NOT NULL UNIQUE
);

CREATE TABLE dim_inventory (
    batch_id       VARCHAR(20)  PRIMARY KEY,                 -- e.g. BATCH-01
    product_id     VARCHAR(10)  NOT NULL REFERENCES dim_product (product_id),
    stock_units    INTEGER      NOT NULL CHECK (stock_units >= 0),
    expiry_date    DATE         NOT NULL
);

CREATE TABLE fact_orders (
    order_id       VARCHAR(12)   PRIMARY KEY,                -- e.g. ORD-0001
    customer_id    VARCHAR(10)   NOT NULL REFERENCES dim_customer (customer_id),
    product_id     VARCHAR(10)   NOT NULL REFERENCES dim_product (product_id),
    channel_id     VARCHAR(10)   NOT NULL REFERENCES dim_channel (channel_id),
    order_date     DATE          NOT NULL,
    quantity       INTEGER       NOT NULL CHECK (quantity > 0),
    revenue        NUMERIC(10,2) NOT NULL CHECK (revenue >= 0),   -- INR
    rating         SMALLINT      CHECK (rating BETWEEN 1 AND 5)   -- NULL = not rated yet
);

-- Speeds up "all orders for this customer" (the login page) and report filters.
CREATE INDEX idx_fact_orders_customer ON fact_orders (customer_id);
CREATE INDEX idx_fact_orders_date     ON fact_orders (order_date);
CREATE INDEX idx_dim_inventory_product ON dim_inventory (product_id);

-- Supabase also publishes every table in the "public" schema through its
-- web Data API. Turning on Row Level Security with no policies closes that
-- door, so nobody can read customer data with the public API key. Our Flask
-- backend and Power BI log in as the database owner, which is not affected.
ALTER TABLE dim_customer  ENABLE ROW LEVEL SECURITY;
ALTER TABLE dim_product   ENABLE ROW LEVEL SECURITY;
ALTER TABLE dim_channel   ENABLE ROW LEVEL SECURITY;
ALTER TABLE dim_inventory ENABLE ROW LEVEL SECURITY;
ALTER TABLE fact_orders   ENABLE ROW LEVEL SECURITY;
