"""
database.py — Database connection management, initialisation and seeding.

Provides helper functions to:
  • get_db()   — obtain a per-request SQLite connection
  • close_db() — close the connection at request teardown
  • init_db()  — create tables from schema.sql
  • seed_data()— populate the database with sample data
"""

import sqlite3
import os
from flask import g
from werkzeug.security import generate_password_hash
import config


# --------------------------------------------------------------------------
# Connection helpers
# --------------------------------------------------------------------------

def get_db():
    """
    Return a SQLite connection bound to the current Flask request.
    The connection is created once per request and reused if called again.
    Row factory is set so rows behave like dictionaries.
    """
    if 'db' not in g:
        g.db = sqlite3.connect(config.DATABASE_PATH)
        g.db.row_factory = sqlite3.Row      # access columns by name
        g.db.execute("PRAGMA foreign_keys = ON")  # enforce FK constraints
    return g.db


def close_db(exception=None):
    """Close the database connection at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


# --------------------------------------------------------------------------
# Initialisation
# --------------------------------------------------------------------------

def init_db(app):
    """
    Create all tables defined in schema.sql and seed sample data.
    Called once when the application starts for the first time.
    """
    with app.app_context():
        db = get_db()

        # Read and execute the schema file
        schema_path = os.path.join(config.BASE_DIR, 'schema.sql')
        with open(schema_path, 'r') as f:
            db.executescript(f.read())

        # Only seed if the database is empty (first run)
        count = db.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
        if count == 0:
            seed_data(db)

        db.commit()
        close_db()


# --------------------------------------------------------------------------
# Sample data
# --------------------------------------------------------------------------

def seed_data(db):
    """
    Insert sample categories, products and an admin account into the database.
    This runs only once — on the very first application start.
    """

    # ── Admin account ────────────────────────────────────────────────────
    admin_hash = generate_password_hash('admin123')
    db.execute(
        """INSERT INTO users (username, email, password_hash, full_name, is_admin)
           VALUES (?, ?, ?, ?, ?)""",
        ('admin', 'admin@ecommerce.com', admin_hash, 'Admin User', 1)
    )

    # ── Categories ───────────────────────────────────────────────────────
    categories = [
        ('Electronics', 'electronics'),
        ('Clothing', 'clothing'),
        ('Books', 'books'),
        ('Home & Kitchen', 'home-kitchen'),
        ('Sports', 'sports'),
    ]
    for name, slug in categories:
        db.execute(
            "INSERT INTO categories (name, slug) VALUES (?, ?)",
            (name, slug)
        )

    # ── Products ─────────────────────────────────────────────────────────
    # (name, category_id, description, price, stock, image_filename)
    products = [
        # Electronics (category_id = 1)
        ('Wireless Bluetooth Headphones', 1,
         'Premium over-ear headphones with active noise cancellation, '
         '30-hour battery life and deep bass. Perfect for music lovers and commuters.',
         2499.00, 25, 'headphones.png'),

        ('Smartphone Pro Max', 1,
         'Latest flagship smartphone with 6.7-inch AMOLED display, '
         '108 MP camera, 5G connectivity and 5000 mAh battery.',
         54999.00, 15, 'smartphone.png'),

        ('Laptop UltraSlim 14', 1,
         '14-inch ultra-thin laptop with Intel i7 processor, 16 GB RAM, '
         '512 GB SSD and all-day battery life. Ideal for students and professionals.',
         62999.00, 10, 'laptop.png'),

        ('Smartwatch Fitness Tracker', 1,
         'Water-resistant smartwatch with heart-rate monitor, GPS tracking, '
         'sleep analysis and 7-day battery life.',
         3999.00, 40, 'smartwatch.png'),

        # Clothing (category_id = 2)
        ('Classic Cotton T-Shirt', 2,
         'Comfortable 100 % cotton crew-neck t-shirt available in multiple colours. '
         'Pre-shrunk fabric for a lasting fit.',
         599.00, 100, 'tshirt.png'),

        ('Denim Jacket', 2,
         'Stylish medium-wash denim jacket with button closure and '
         'chest pockets. A wardrobe essential for every season.',
         2199.00, 30, 'jacket.png'),

        ('Running Sneakers', 2,
         'Lightweight mesh running shoes with cushioned sole and '
         'breathable upper. Engineered for comfort on long runs.',
         3499.00, 45, 'sneakers.png'),

        ('Summer Floral Dress', 2,
         'Elegant A-line floral print dress with adjustable waist tie. '
         'Perfect for brunches, parties and casual outings.',
         1299.00, 35, 'dress.png'),

        # Books (category_id = 3)
        ('The Great Adventure Novel', 3,
         'A bestselling fiction novel that takes you on an epic journey '
         'across continents. Over 2 million copies sold worldwide.',
         399.00, 60, 'fiction_book.png'),

        ('Python Programming Mastery', 3,
         'Comprehensive guide to Python programming — from basics to '
         'advanced topics including web development, data science and automation.',
         749.00, 50, 'programming_book.png'),

        ('Gourmet Cookbook Collection', 3,
         'Over 200 chef-curated recipes with step-by-step instructions '
         'and beautiful food photography. Covers Indian, Italian and Asian cuisines.',
         899.00, 40, 'cookbook.png'),

        # Home & Kitchen (category_id = 4)
        ('High-Speed Blender', 4,
         'Powerful 1000-watt blender with 5 speed settings, pulse function '
         'and BPA-free jar. Makes smoothies, soups and sauces in seconds.',
         2799.00, 20, 'blender.png'),

        ('Modern Desk Lamp', 4,
         'Sleek LED desk lamp with adjustable brightness, colour temperature '
         'control and USB charging port. Minimalist design.',
         1499.00, 35, 'lamp.png'),

        ('Luxury Pillow Set (Pack of 2)', 4,
         'Premium memory-foam pillows with breathable bamboo covers. '
         'Provides excellent neck support for a restful sleep.',
         1199.00, 55, 'pillow.png'),

        # Sports (category_id = 5)
        ('Premium Yoga Mat', 5,
         'Extra-thick 6 mm non-slip yoga mat with alignment lines. '
         'Made from eco-friendly TPE material. Includes carry strap.',
         999.00, 70, 'yoga_mat.png'),

        ('Stainless Steel Water Bottle', 5,
         'Double-wall vacuum insulated bottle that keeps drinks cold 24 hours '
         'or hot 12 hours. 750 ml capacity, leak-proof lid.',
         699.00, 80, 'water_bottle.png'),

        ('Adjustable Dumbbell Set', 5,
         'Space-saving adjustable dumbbells ranging from 2.5 kg to 15 kg. '
         'Quick-lock mechanism for fast weight changes during workouts.',
         4999.00, 18, 'dumbbell.png'),
    ]

    for name, cat_id, desc, price, stock, image in products:
        db.execute(
            """INSERT INTO products
               (name, category_id, description, price, stock, image_filename)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (name, cat_id, desc, price, stock, image)
        )
