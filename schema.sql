-- ============================================================================
-- E-Commerce Application Database Schema
-- Database: SQLite
-- Description: Creates all tables required for the e-commerce application
-- ============================================================================

-- --------------------------------------------------------------------------
-- Users table — stores customer and admin accounts
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    username    TEXT    NOT NULL UNIQUE,
    email       TEXT    NOT NULL UNIQUE,
    password_hash TEXT  NOT NULL,
    full_name   TEXT    NOT NULL,
    phone       TEXT    DEFAULT '',
    address     TEXT    DEFAULT '',
    city        TEXT    DEFAULT '',
    state       TEXT    DEFAULT '',
    pincode     TEXT    DEFAULT '',
    is_admin    INTEGER DEFAULT 0,          -- 0 = customer, 1 = admin
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- --------------------------------------------------------------------------
-- Categories table — product categories for filtering
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS categories (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    slug TEXT NOT NULL UNIQUE
);

-- --------------------------------------------------------------------------
-- Products table — the product catalogue
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS products (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL,
    category_id     INTEGER NOT NULL,
    description     TEXT    DEFAULT '',
    price           REAL    NOT NULL CHECK(price >= 0),
    stock           INTEGER NOT NULL DEFAULT 0 CHECK(stock >= 0),
    image_filename  TEXT    DEFAULT 'default.png',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

-- --------------------------------------------------------------------------
-- Cart items — per-user shopping cart (database-backed, not session-only)
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cart_items (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity   INTEGER NOT NULL DEFAULT 1 CHECK(quantity > 0),
    FOREIGN KEY (user_id)    REFERENCES users(id),
    FOREIGN KEY (product_id) REFERENCES products(id),
    UNIQUE(user_id, product_id)   -- one row per product per user
);

-- --------------------------------------------------------------------------
-- Orders — confirmed customer orders
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS orders (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    order_number   TEXT    NOT NULL UNIQUE,
    user_id        INTEGER NOT NULL,
    full_name      TEXT    NOT NULL,
    email          TEXT    NOT NULL,
    phone          TEXT    NOT NULL,
    address        TEXT    NOT NULL,
    city           TEXT    NOT NULL,
    state          TEXT    NOT NULL,
    pincode        TEXT    NOT NULL,
    payment_method TEXT    NOT NULL DEFAULT 'Cash on Delivery',
    total_amount   REAL    NOT NULL CHECK(total_amount >= 0),
    status         TEXT    NOT NULL DEFAULT 'Placed',  -- Placed | Processing | Shipped | Delivered
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- --------------------------------------------------------------------------
-- Order items — snapshot of products at the moment the order was placed
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS order_items (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id      INTEGER NOT NULL,
    product_id    INTEGER NOT NULL,
    product_name  TEXT    NOT NULL,
    product_price REAL    NOT NULL,
    quantity      INTEGER NOT NULL CHECK(quantity > 0),
    subtotal      REAL    NOT NULL CHECK(subtotal >= 0),
    FOREIGN KEY (order_id)   REFERENCES orders(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);
