"""
app.py — Main Flask application for the E-Commerce web application.

This file contains:
  • Application factory and configuration
  • Authentication decorators (login_required, admin_required)
  • Public routes     — home, products, search, login, register
  • Customer routes   — cart, checkout, orders, profile
  • Admin routes      — dashboard, product CRUD, order management
  • Error handlers    — 404, 500
  • Template context  — cart count injected globally

Run with:
    python app.py
"""

import os
import sqlite3
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, g, abort
)
from werkzeug.utils import secure_filename

import config
from database import get_db, close_db, init_db
import models


# ==========================================================================
# APPLICATION SETUP
# ==========================================================================

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH

# Register the teardown hook so DB connections close after each request
app.teardown_appcontext(close_db)

# Initialise database (creates tables + seeds data on first run)
init_db(app)


# ==========================================================================
# HELPER UTILITIES
# ==========================================================================

def allowed_file(filename):
    """Check if an uploaded filename has a permitted extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS


# --------------------------------------------------------------------------
# Authentication decorators
# --------------------------------------------------------------------------

def login_required(f):
    """Redirect to the login page if the user is not authenticated."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Return 403 Forbidden if the current user is not an admin."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        db = get_db()
        user = models.get_user_by_id(db, session['user_id'])
        if not user or not user['is_admin']:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


# --------------------------------------------------------------------------
# Context processor — inject cart count and user info into every template
# --------------------------------------------------------------------------

@app.context_processor
def inject_globals():
    """Make cart_count and current_user available in all templates."""
    cart_count = 0
    current_user = None
    if 'user_id' in session:
        db = get_db()
        cart_count = models.get_cart_count(db, session['user_id'])
        current_user = models.get_user_by_id(db, session['user_id'])
    return dict(cart_count=cart_count, current_user=current_user)


# ==========================================================================
# PUBLIC ROUTES
# ==========================================================================

@app.route('/')
def home():
    """Home page — hero banner + featured products + category links."""
    db = get_db()
    featured = models.get_featured_products(db, limit=6)
    categories = models.get_all_categories(db)
    return render_template('index.html', products=featured, categories=categories)


@app.route('/products')
def products():
    """Product catalogue with search, category filter and price filter."""
    db = get_db()
    categories = models.get_all_categories(db)

    # Read filter parameters from the query string
    search_query = request.args.get('q', '').strip()
    category_id = request.args.get('category', type=int)
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)

    product_list = models.filter_products(
        db,
        category_id=category_id,
        min_price=min_price,
        max_price=max_price,
        search_query=search_query if search_query else None
    )

    return render_template(
        'products.html',
        products=product_list,
        categories=categories,
        search_query=search_query,
        selected_category=category_id,
        min_price=min_price,
        max_price=max_price
    )


@app.route('/product/<int:product_id>')
def product_detail(product_id):
    """Individual product detail page."""
    db = get_db()
    product = models.get_product_by_id(db, product_id)
    if not product:
        abort(404)
    return render_template('product_detail.html', product=product)


# --------------------------------------------------------------------------
# Authentication routes
# --------------------------------------------------------------------------

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Customer registration form."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        full_name = request.form.get('full_name', '').strip()

        # --- Validation ---
        errors = []
        if not username or not email or not password or not full_name:
            errors.append('All fields are required.')
        if len(username) < 3:
            errors.append('Username must be at least 3 characters.')
        if len(password) < 6:
            errors.append('Password must be at least 6 characters.')
        if password != confirm_password:
            errors.append('Passwords do not match.')

        db = get_db()
        if models.get_user_by_username(db, username):
            errors.append('Username is already taken.')
        if models.get_user_by_email(db, email):
            errors.append('Email is already registered.')

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('register.html')

        # --- Create account ---
        try:
            user_id = models.create_user(db, username, email, password, full_name)
        except sqlite3.IntegrityError:
            flash('Username or email is already taken. Please try different credentials.', 'danger')
            return render_template('register.html')

        session['user_id'] = user_id
        flash('Account created successfully! Welcome!', 'success')
        return redirect(url_for('home'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login form."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash('Please enter both username and password.', 'danger')
            return render_template('login.html')

        db = get_db()
        user = models.get_user_by_username(db, username)

        if user and models.verify_password(user, password):
            session['user_id'] = user['id']
            flash(f'Welcome back, {user["full_name"]}!', 'success')

            # Redirect to the page they were trying to visit, or home.
            # Skip POST-only endpoints (e.g. /cart/add/) that would cause
            # a 405 Method Not Allowed on a GET redirect.
            next_page = request.args.get('next') or request.form.get('next')
            if next_page and ('/cart/add/' in next_page or
                              '/cart/update/' in next_page or
                              '/cart/remove/' in next_page or
                              '/admin/products/delete/' in next_page):
                next_page = None
            return redirect(next_page or url_for('home'))
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('login.html')


@app.route('/logout')
def logout():
    """Clear the session and log out."""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))


# ==========================================================================
# CUSTOMER ROUTES (login required)
# ==========================================================================

# --------------------------------------------------------------------------
# Shopping Cart
# --------------------------------------------------------------------------

@app.route('/cart')
@login_required
def cart():
    """Display the user's shopping cart."""
    db = get_db()
    items = models.get_cart_items(db, session['user_id'])
    total = models.get_cart_total(db, session['user_id'])
    return render_template('cart.html', items=items, total=total)


@app.route('/cart/add/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    """Add a product to the cart."""
    db = get_db()
    quantity = request.form.get('quantity', 1, type=int)

    if quantity <= 0:
        flash('Quantity must be at least 1.', 'danger')
        return redirect(url_for('product_detail', product_id=product_id))

    success, message = models.add_to_cart(db, session['user_id'], product_id, quantity)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('cart'))


@app.route('/cart/update/<int:product_id>', methods=['POST'])
@login_required
def update_cart(product_id):
    """Update the quantity of a cart item."""
    db = get_db()
    quantity = request.form.get('quantity', 1, type=int)
    success, message = models.update_cart_quantity(db, session['user_id'], product_id, quantity)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('cart'))


@app.route('/cart/remove/<int:product_id>', methods=['POST'])
@login_required
def remove_from_cart(product_id):
    """Remove a product from the cart."""
    db = get_db()
    models.remove_from_cart(db, session['user_id'], product_id)
    flash('Item removed from cart.', 'info')
    return redirect(url_for('cart'))


# --------------------------------------------------------------------------
# Checkout & Orders
# --------------------------------------------------------------------------

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    """Checkout page — collect delivery details and place the order."""
    db = get_db()
    items = models.get_cart_items(db, session['user_id'])
    total = models.get_cart_total(db, session['user_id'])

    if not items:
        flash('Your cart is empty. Add some products first!', 'warning')
        return redirect(url_for('products'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        city = request.form.get('city', '').strip()
        state = request.form.get('state', '').strip()
        pincode = request.form.get('pincode', '').strip()

        # --- Validation ---
        errors = []
        if not all([full_name, email, phone, address, city, state, pincode]):
            errors.append('All delivery fields are required.')
        if phone and (not phone.isdigit() or len(phone) < 10):
            errors.append('Please enter a valid phone number (at least 10 digits).')
        if pincode and (not pincode.isdigit() or len(pincode) != 6):
            errors.append('Please enter a valid 6-digit pincode.')

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('checkout.html', items=items, total=total)

        # --- Place order ---
        order_id, result = models.create_order(
            db, session['user_id'],
            full_name, email, phone, address, city, state, pincode
        )

        if order_id is None:
            flash(result, 'danger')
            return redirect(url_for('cart'))

        flash('Order placed successfully!', 'success')
        return redirect(url_for('order_confirmation', order_number=result))

    # Pre-fill form with profile data
    user = models.get_user_by_id(db, session['user_id'])
    return render_template('checkout.html', items=items, total=total, user=user)


@app.route('/order-confirmation/<order_number>')
@login_required
def order_confirmation(order_number):
    """Display order confirmation after successful checkout."""
    db = get_db()
    order = models.get_order_by_number(db, order_number)
    if not order or order['user_id'] != session['user_id']:
        abort(404)
    order_items = models.get_order_items(db, order['id'])
    return render_template('order_confirmation.html', order=order, items=order_items)


@app.route('/orders')
@login_required
def orders():
    """Customer order history."""
    db = get_db()
    user_orders = models.get_user_orders(db, session['user_id'])
    return render_template('orders.html', orders=user_orders)


@app.route('/order/<int:order_id>')
@login_required
def order_detail(order_id):
    """Customer view of a single order."""
    db = get_db()
    order = models.get_order_by_id(db, order_id)
    if not order or order['user_id'] != session['user_id']:
        abort(404)
    order_items = models.get_order_items(db, order['id'])
    return render_template('order_detail.html', order=order, items=order_items)


# --------------------------------------------------------------------------
# Profile
# --------------------------------------------------------------------------

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """View and edit the customer profile and delivery address."""
    db = get_db()
    user = models.get_user_by_id(db, session['user_id'])

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        city = request.form.get('city', '').strip()
        state = request.form.get('state', '').strip()
        pincode = request.form.get('pincode', '').strip()

        if not full_name:
            flash('Full name is required.', 'danger')
            return render_template('profile.html', user=user)

        models.update_user_profile(
            db, session['user_id'],
            full_name, phone, address, city, state, pincode
        )
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))

    return render_template('profile.html', user=user)


# ==========================================================================
# ADMIN ROUTES (admin required)
# ==========================================================================

@app.route('/admin')
@admin_required
def admin_dashboard():
    """Admin dashboard with summary statistics."""
    db = get_db()
    stats = models.get_admin_stats(db)
    return render_template('admin/dashboard.html', stats=stats)


@app.route('/admin/products')
@admin_required
def admin_products():
    """Admin product management — list all products."""
    db = get_db()
    all_products = models.get_all_products(db)
    return render_template('admin/products.html', products=all_products)


@app.route('/admin/products/add', methods=['GET', 'POST'])
@admin_required
def admin_add_product():
    """Add a new product to the catalogue."""
    db = get_db()
    categories = models.get_all_categories(db)

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        category_id = request.form.get('category_id', type=int)
        description = request.form.get('description', '').strip()
        price = request.form.get('price', type=float)
        stock = request.form.get('stock', type=int)

        # Validation
        errors = []
        if not name:
            errors.append('Product name is required.')
        if not category_id:
            errors.append('Please select a category.')
        if price is None or price < 0:
            errors.append('Price must be a non-negative number.')
        if stock is None or stock < 0:
            errors.append('Stock must be a non-negative number.')

        # Handle image upload
        image_filename = 'default.png'
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                image_filename = secure_filename(file.filename)
                file.save(os.path.join(config.UPLOAD_FOLDER, image_filename))

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('admin/product_form.html',
                                   categories=categories, action='Add')

        models.create_product(db, name, category_id, description, price, stock, image_filename)
        flash('Product added successfully!', 'success')
        return redirect(url_for('admin_products'))

    return render_template('admin/product_form.html',
                           categories=categories, action='Add')


@app.route('/admin/products/edit/<int:product_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_product(product_id):
    """Edit an existing product."""
    db = get_db()
    product = models.get_product_by_id(db, product_id)
    if not product:
        abort(404)

    categories = models.get_all_categories(db)

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        category_id = request.form.get('category_id', type=int)
        description = request.form.get('description', '').strip()
        price = request.form.get('price', type=float)
        stock = request.form.get('stock', type=int)

        errors = []
        if not name:
            errors.append('Product name is required.')
        if price is None or price < 0:
            errors.append('Price must be a non-negative number.')
        if stock is None or stock < 0:
            errors.append('Stock must be a non-negative number.')

        # Handle optional image update
        image_filename = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                image_filename = secure_filename(file.filename)
                file.save(os.path.join(config.UPLOAD_FOLDER, image_filename))

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('admin/product_form.html',
                                   product=product, categories=categories, action='Edit')

        models.update_product(db, product_id, name, category_id, description,
                              price, stock, image_filename)
        flash('Product updated successfully!', 'success')
        return redirect(url_for('admin_products'))

    return render_template('admin/product_form.html',
                           product=product, categories=categories, action='Edit')


@app.route('/admin/products/delete/<int:product_id>', methods=['POST'])
@admin_required
def admin_delete_product(product_id):
    """Delete a product from the catalogue."""
    db = get_db()
    product = models.get_product_by_id(db, product_id)
    if not product:
        abort(404)
    models.delete_product(db, product_id)
    flash('Product deleted.', 'info')
    return redirect(url_for('admin_products'))


@app.route('/admin/orders')
@admin_required
def admin_orders():
    """Admin view — all orders."""
    db = get_db()
    all_orders = models.get_all_orders(db)
    return render_template('admin/orders.html', orders=all_orders)


@app.route('/admin/orders/<int:order_id>', methods=['GET', 'POST'])
@admin_required
def admin_order_detail(order_id):
    """Admin view — single order with status update."""
    db = get_db()
    order = models.get_order_by_id(db, order_id)
    if not order:
        abort(404)

    if request.method == 'POST':
        new_status = request.form.get('status', '').strip()
        success, message = models.update_order_status(db, order_id, new_status)
        flash(message, 'success' if success else 'danger')
        return redirect(url_for('admin_order_detail', order_id=order_id))

    order_items = models.get_order_items(db, order['id'])
    # Get the customer who placed the order
    customer = models.get_user_by_id(db, order['user_id'])
    return render_template('admin/order_detail.html',
                           order=order, items=order_items, customer=customer)


# ==========================================================================
# ERROR HANDLERS
# ==========================================================================

@app.errorhandler(403)
def forbidden(e):
    return render_template('404.html',
                           error_code=403,
                           error_message='Access Denied — You do not have permission to view this page.'), 403


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html',
                           error_code=404,
                           error_message='Page Not Found — The page you are looking for does not exist.'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500


# ==========================================================================
# ENTRY POINT
# ==========================================================================

if __name__ == '__main__':
    # Ensure the image upload directory exists
    os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=config.DEBUG, port=5000)
