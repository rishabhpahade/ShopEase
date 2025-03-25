"""
models.py — Data-access functions for the E-Commerce application.

Every function accepts a database connection (from get_db()) and uses
parameterised queries to prevent SQL injection.  No ORM is used — this
keeps the code transparent and easy to follow for learners.

Sections:
  1. User functions
  2. Category functions
  3. Product functions
  4. Cart functions
  5. Order functions
"""

from werkzeug.security import generate_password_hash, check_password_hash
import uuid
from datetime import datetime


# ==========================================================================
# 1. USER FUNCTIONS
# ==========================================================================

def create_user(db, username, email, password, full_name):
    """Register a new customer account.  Returns the new user's ID."""
    password_hash = generate_password_hash(password)
    cursor = db.execute(
        """INSERT INTO users (username, email, password_hash, full_name)
           VALUES (?, ?, ?, ?)""",
        (username, email, password_hash, full_name)
    )
    db.commit()
    return cursor.lastrowid


def get_user_by_id(db, user_id):
    """Fetch a single user by primary key."""
    return db.execute(
        "SELECT * FROM users WHERE id = ?", (user_id,)
    ).fetchone()


def get_user_by_username(db, username):
    """Fetch a single user by username (for login)."""
    return db.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()


def get_user_by_email(db, email):
    """Fetch a single user by email (for duplicate checks)."""
    return db.execute(
        "SELECT * FROM users WHERE email = ?", (email,)
    ).fetchone()


def verify_password(user_row, password):
    """Check a plain-text password against the stored hash."""
    return check_password_hash(user_row['password_hash'], password)


def update_user_profile(db, user_id, full_name, phone, address, city, state, pincode):
    """Update a customer's delivery information."""
    db.execute(
        """UPDATE users
           SET full_name = ?, phone = ?, address = ?, city = ?, state = ?, pincode = ?
           WHERE id = ?""",
        (full_name, phone, address, city, state, pincode, user_id)
    )
    db.commit()


# ==========================================================================
# 2. CATEGORY FUNCTIONS
# ==========================================================================

def get_all_categories(db):
    """Return every category, ordered by name."""
    return db.execute(
        "SELECT * FROM categories ORDER BY name"
    ).fetchall()


def get_category_by_id(db, category_id):
    """Fetch a single category by primary key."""
    return db.execute(
        "SELECT * FROM categories WHERE id = ?", (category_id,)
    ).fetchone()


def get_category_by_slug(db, slug):
    """Fetch a single category by its URL-friendly slug."""
    return db.execute(
        "SELECT * FROM categories WHERE slug = ?", (slug,)
    ).fetchone()


# ==========================================================================
# 3. PRODUCT FUNCTIONS
# ==========================================================================

def get_all_products(db):
    """Return all products joined with their category name."""
    return db.execute(
        """SELECT p.*, c.name AS category_name
           FROM products p
           JOIN categories c ON p.category_id = c.id
           ORDER BY p.created_at DESC"""
    ).fetchall()


def get_product_by_id(db, product_id):
    """Fetch a single product by ID, including its category name."""
    return db.execute(
        """SELECT p.*, c.name AS category_name
           FROM products p
           JOIN categories c ON p.category_id = c.id
           WHERE p.id = ?""",
        (product_id,)
    ).fetchone()


def get_products_by_category(db, category_id):
    """Return all products belonging to a given category."""
    return db.execute(
        """SELECT p.*, c.name AS category_name
           FROM products p
           JOIN categories c ON p.category_id = c.id
           WHERE p.category_id = ?
           ORDER BY p.name""",
        (category_id,)
    ).fetchall()


def search_products(db, query):
    """Search products by name or description (case-insensitive LIKE)."""
    like_query = f'%{query}%'
    return db.execute(
        """SELECT p.*, c.name AS category_name
           FROM products p
           JOIN categories c ON p.category_id = c.id
           WHERE p.name LIKE ? OR p.description LIKE ?
           ORDER BY p.name""",
        (like_query, like_query)
    ).fetchall()


def filter_products(db, category_id=None, min_price=None, max_price=None, search_query=None):
    """
    Flexible product filter that combines category, price range and keyword.
    Only non-None parameters are applied.
    """
    sql = """SELECT p.*, c.name AS category_name
             FROM products p
             JOIN categories c ON p.category_id = c.id
             WHERE 1 = 1"""
    params = []

    if category_id:
        sql += " AND p.category_id = ?"
        params.append(category_id)

    if min_price is not None:
        sql += " AND p.price >= ?"
        params.append(min_price)

    if max_price is not None:
        sql += " AND p.price <= ?"
        params.append(max_price)

    if search_query:
        sql += " AND (p.name LIKE ? OR p.description LIKE ?)"
        like_q = f'%{search_query}%'
        params.extend([like_q, like_q])

    sql += " ORDER BY p.name"
    return db.execute(sql, params).fetchall()


def get_featured_products(db, limit=6):
    """Return a handful of products for the home-page showcase."""
    return db.execute(
        """SELECT p.*, c.name AS category_name
           FROM products p
           JOIN categories c ON p.category_id = c.id
           ORDER BY p.created_at DESC
           LIMIT ?""",
        (limit,)
    ).fetchall()


def create_product(db, name, category_id, description, price, stock, image_filename='default.png'):
    """Insert a new product (admin action)."""
    cursor = db.execute(
        """INSERT INTO products (name, category_id, description, price, stock, image_filename)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (name, category_id, description, price, stock, image_filename)
    )
    db.commit()
    return cursor.lastrowid


def update_product(db, product_id, name, category_id, description, price, stock, image_filename=None):
    """Update an existing product.  Image is only changed if a new filename is provided."""
    if image_filename:
        db.execute(
            """UPDATE products
               SET name = ?, category_id = ?, description = ?, price = ?, stock = ?, image_filename = ?
               WHERE id = ?""",
            (name, category_id, description, price, stock, image_filename, product_id)
        )
    else:
        db.execute(
            """UPDATE products
               SET name = ?, category_id = ?, description = ?, price = ?, stock = ?
               WHERE id = ?""",
            (name, category_id, description, price, stock, product_id)
        )
    db.commit()


def delete_product(db, product_id):
    """Remove a product from the catalogue (admin action)."""
    db.execute("DELETE FROM cart_items WHERE product_id = ?", (product_id,))
    db.execute("DELETE FROM products WHERE id = ?", (product_id,))
    db.commit()


def update_stock(db, product_id, new_stock):
    """Set the stock level for a product."""
    db.execute(
        "UPDATE products SET stock = ? WHERE id = ?",
        (new_stock, product_id)
    )
    db.commit()


# ==========================================================================
# 4. CART FUNCTIONS
# ==========================================================================

def get_cart_items(db, user_id):
    """
    Return all items in a user's cart, joined with product details.
    Each row includes a calculated 'subtotal' column.
    """
    return db.execute(
        """SELECT ci.*, p.name, p.price, p.stock, p.image_filename,
                  (ci.quantity * p.price) AS subtotal
           FROM cart_items ci
           JOIN products p ON ci.product_id = p.id
           WHERE ci.user_id = ?""",
        (user_id,)
    ).fetchall()


def get_cart_count(db, user_id):
    """Return the total number of distinct items in the user's cart."""
    row = db.execute(
        "SELECT COUNT(*) FROM cart_items WHERE user_id = ?", (user_id,)
    ).fetchone()
    return row[0] if row else 0


def add_to_cart(db, user_id, product_id, quantity=1):
    """
    Add a product to the cart.  If the product is already in the cart,
    increment the quantity instead of creating a duplicate row.
    Returns (success: bool, message: str).
    """
    # Check product exists and has stock
    product = db.execute(
        "SELECT * FROM products WHERE id = ?", (product_id,)
    ).fetchone()

    if not product:
        return False, "Product not found."

    if product['stock'] <= 0:
        return False, "This product is currently out of stock."

    # Check if already in cart
    existing = db.execute(
        "SELECT * FROM cart_items WHERE user_id = ? AND product_id = ?",
        (user_id, product_id)
    ).fetchone()

    if existing:
        new_qty = existing['quantity'] + quantity
        if new_qty > product['stock']:
            return False, f"Only {product['stock']} items available in stock."
        db.execute(
            "UPDATE cart_items SET quantity = ? WHERE id = ?",
            (new_qty, existing['id'])
        )
    else:
        if quantity > product['stock']:
            return False, f"Only {product['stock']} items available in stock."
        db.execute(
            "INSERT INTO cart_items (user_id, product_id, quantity) VALUES (?, ?, ?)",
            (user_id, product_id, quantity)
        )

    db.commit()
    return True, "Product added to cart."


def update_cart_quantity(db, user_id, product_id, quantity):
    """
    Set the quantity of a cart item.
    Returns (success: bool, message: str).
    """
    if quantity <= 0:
        return remove_from_cart(db, user_id, product_id)

    product = db.execute(
        "SELECT stock FROM products WHERE id = ?", (product_id,)
    ).fetchone()

    if not product:
        return False, "Product not found."

    if quantity > product['stock']:
        return False, f"Only {product['stock']} items available in stock."

    db.execute(
        "UPDATE cart_items SET quantity = ? WHERE user_id = ? AND product_id = ?",
        (quantity, user_id, product_id)
    )
    db.commit()
    return True, "Cart updated."


def remove_from_cart(db, user_id, product_id):
    """Remove a single product from the user's cart."""
    db.execute(
        "DELETE FROM cart_items WHERE user_id = ? AND product_id = ?",
        (user_id, product_id)
    )
    db.commit()
    return True, "Item removed from cart."


def clear_cart(db, user_id):
    """Remove all items from the user's cart (e.g. after checkout)."""
    db.execute("DELETE FROM cart_items WHERE user_id = ?", (user_id,))
    db.commit()


def get_cart_total(db, user_id):
    """Calculate the grand total of all items in the user's cart."""
    row = db.execute(
        """SELECT SUM(ci.quantity * p.price) AS total
           FROM cart_items ci
           JOIN products p ON ci.product_id = p.id
           WHERE ci.user_id = ?""",
        (user_id,)
    ).fetchone()
    return row['total'] if row and row['total'] else 0.0


# ==========================================================================
# 5. ORDER FUNCTIONS
# ==========================================================================

def generate_order_number():
    """
    Create a unique, human-readable order number.
    Format: ORD-YYYYMMDD-XXXX  (XXXX = short UUID segment)
    """
    date_part = datetime.now().strftime('%Y%m%d')
    unique_part = uuid.uuid4().hex[:6].upper()
    return f"ORD-{date_part}-{unique_part}"


def create_order(db, user_id, full_name, email, phone, address, city, state, pincode,
                 payment_method='Cash on Delivery'):
    """
    Place an order:
      1. Generate order number
      2. Snapshot current cart items into order_items
      3. Deduct stock for each product
      4. Clear the cart
    Returns (order_id, order_number) on success or (None, error_message) on failure.
    """
    # Get the user's cart
    cart_items = get_cart_items(db, user_id)
    if not cart_items:
        return None, "Your cart is empty."

    # Validate stock for every item
    for item in cart_items:
        product = db.execute(
            "SELECT stock FROM products WHERE id = ?", (item['product_id'],)
        ).fetchone()
        if not product or item['quantity'] > product['stock']:
            return None, f"Insufficient stock for '{item['name']}'."

    # Calculate total
    total = sum(item['subtotal'] for item in cart_items)
    order_number = generate_order_number()

    # Insert order header
    cursor = db.execute(
        """INSERT INTO orders
           (order_number, user_id, full_name, email, phone,
            address, city, state, pincode, payment_method, total_amount)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (order_number, user_id, full_name, email, phone,
         address, city, state, pincode, payment_method, total)
    )
    order_id = cursor.lastrowid

    # Insert order items and deduct stock
    for item in cart_items:
        subtotal = item['quantity'] * item['price']
        db.execute(
            """INSERT INTO order_items
               (order_id, product_id, product_name, product_price, quantity, subtotal)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (order_id, item['product_id'], item['name'], item['price'],
             item['quantity'], subtotal)
        )
        # Deduct stock
        db.execute(
            "UPDATE products SET stock = stock - ? WHERE id = ?",
            (item['quantity'], item['product_id'])
        )

    # Clear the cart
    clear_cart(db, user_id)
    db.commit()

    return order_id, order_number


def get_user_orders(db, user_id):
    """Return all orders placed by a customer, newest first."""
    return db.execute(
        "SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    ).fetchall()


def get_order_by_id(db, order_id):
    """Fetch a single order header."""
    return db.execute(
        "SELECT * FROM orders WHERE id = ?", (order_id,)
    ).fetchone()


def get_order_by_number(db, order_number):
    """Fetch a single order by its human-readable order number."""
    return db.execute(
        "SELECT * FROM orders WHERE order_number = ?", (order_number,)
    ).fetchone()


def get_order_items(db, order_id):
    """Return all line items for a given order."""
    return db.execute(
        "SELECT * FROM order_items WHERE order_id = ?", (order_id,)
    ).fetchall()


def get_all_orders(db):
    """Return every order in the system (admin view), newest first."""
    return db.execute(
        """SELECT o.*, u.username
           FROM orders o
           JOIN users u ON o.user_id = u.id
           ORDER BY o.created_at DESC"""
    ).fetchall()


def update_order_status(db, order_id, new_status):
    """Change an order's status (admin action)."""
    valid_statuses = ['Placed', 'Processing', 'Shipped', 'Delivered']
    if new_status not in valid_statuses:
        return False, f"Invalid status. Choose from: {', '.join(valid_statuses)}"

    db.execute(
        "UPDATE orders SET status = ? WHERE id = ?",
        (new_status, order_id)
    )
    db.commit()
    return True, f"Order status updated to '{new_status}'."


def get_admin_stats(db):
    """Return summary statistics for the admin dashboard."""
    stats = {}
    stats['total_products'] = db.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    stats['total_orders'] = db.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    stats['total_users'] = db.execute("SELECT COUNT(*) FROM users WHERE is_admin = 0").fetchone()[0]
    revenue_row = db.execute("SELECT SUM(total_amount) FROM orders").fetchone()
    stats['total_revenue'] = revenue_row[0] if revenue_row[0] else 0.0
    stats['recent_orders'] = db.execute(
        """SELECT o.*, u.username
           FROM orders o
           JOIN users u ON o.user_id = u.id
           ORDER BY o.created_at DESC
           LIMIT 5"""
    ).fetchall()
    return stats
