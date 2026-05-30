"""
ISAAC SUPERMARKET COMPANY - Complete Point of Sale & Inventory System
Flask Web Application with Customer Registration and Login
Including Admin Receipt Printing and Purchase Details
"""

import os
import sqlite3
import json
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
import webbrowser
import functools
import hashlib
import re

# ============================================================
# DATABASE MODULE
# ============================================================

DB_PATH = "isaac_supermarket.db"

app = Flask(__name__)
app.secret_key = os.urandom(24)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as db:
        db.execute('''CREATE TABLE IF NOT EXISTS admin_users
                      (
                          id
                          INTEGER
                          PRIMARY
                          KEY
                          AUTOINCREMENT,
                          username
                          TEXT
                          UNIQUE
                          NOT
                          NULL,
                          password
                          TEXT
                          NOT
                          NULL,
                          role
                          TEXT
                          DEFAULT
                          'admin'
                      )''')
        db.execute('''CREATE TABLE IF NOT EXISTS customers
                      (
                          id
                          INTEGER
                          PRIMARY
                          KEY
                          AUTOINCREMENT,
                          full_name
                          TEXT
                          NOT
                          NULL,
                          email
                          TEXT
                          UNIQUE
                          NOT
                          NULL,
                          phone
                          TEXT
                          NOT
                          NULL,
                          password
                          TEXT
                          NOT
                          NULL,
                          address
                          TEXT,
                          city
                          TEXT,
                          created_at
                          TIMESTAMP
                          DEFAULT
                          CURRENT_TIMESTAMP,
                          total_purchases
                          REAL
                          DEFAULT
                          0,
                          loyalty_points
                          INTEGER
                          DEFAULT
                          0
                      )''')
        db.execute('''CREATE TABLE IF NOT EXISTS products
                      (
                          id
                          INTEGER
                          PRIMARY
                          KEY
                          AUTOINCREMENT,
                          sku
                          TEXT
                          UNIQUE
                          NOT
                          NULL,
                          name
                          TEXT
                          NOT
                          NULL,
                          category
                          TEXT
                          NOT
                          NULL,
                          price
                          REAL
                          NOT
                          NULL,
                          stock
                          INTEGER
                          NOT
                          NULL
                          DEFAULT
                          0,
                          image_url
                          TEXT,
                          unit
                          TEXT
                          DEFAULT
                          'pcs',
                          description
                          TEXT
                      )''')
        db.execute('''CREATE TABLE IF NOT EXISTS sales
        (
            id
            INTEGER
            PRIMARY
            KEY
            AUTOINCREMENT,
            receipt_no
            TEXT
            UNIQUE
            NOT
            NULL,
            customer_id
            INTEGER,
            customer_name
            TEXT,
            customer_phone
            TEXT,
            items
            TEXT
            NOT
            NULL,
            subtotal
            REAL
            NOT
            NULL,
            tax
            REAL
            NOT
            NULL,
            total
            REAL
            NOT
            NULL,
            payment_method
            TEXT,
            mpesa_code
            TEXT,
            loyalty_points_used
            INTEGER
            DEFAULT
            0,
            loyalty_points_earned
            INTEGER
            DEFAULT
            0,
            created_at
            TIMESTAMP
            DEFAULT
            CURRENT_TIMESTAMP,
            FOREIGN
            KEY
                      (
            customer_id
                      ) REFERENCES customers
                      (
                          id
                      ))''')
        db.execute('''CREATE TABLE IF NOT EXISTS inventory_log
        (
            id
            INTEGER
            PRIMARY
            KEY
            AUTOINCREMENT,
            product_id
            INTEGER,
            quantity_change
            INTEGER,
            reason
            TEXT,
            timestamp
            TIMESTAMP
            DEFAULT
            CURRENT_TIMESTAMP,
            FOREIGN
            KEY
                      (
            product_id
                      ) REFERENCES products
                      (
                          id
                      ))''')
        db.commit()
    with get_db() as db:
        count = db.execute('SELECT COUNT(*) FROM products').fetchone()[0]
        if count == 0:
            seed_products()
            create_default_admin()


def create_default_admin():
    hashed_password = hashlib.sha256("admin123".encode()).hexdigest()
    with get_db() as db:
        db.execute('INSERT OR IGNORE INTO admin_users (username, password, role) VALUES (?, ?, ?)',
                   ('admin', hashed_password, 'admin'))
        db.commit()


def seed_products():
    products = [
        ("FR001", "Fresh Red Apples", "Fruits", 120, 150,
         "https://images.unsplash.com/photo-1570913149827-d2ac84ab3f9a?w=200", "kg", "Crisp and sweet apples"),
        ("FR002", "Organic Bananas", "Fruits", 90, 200,
         "https://images.unsplash.com/photo-1603833665858-e61d17a86224?w=200", "kg", "Rich in potassium"),
        ("FR003", "Seedless Grapes", "Fruits", 250, 100,
         "https://images.unsplash.com/photo-1537640538966-79f369143f8f?w=200", "kg", "Sweet green grapes"),
        ("FR004", "Juicy Oranges", "Fruits", 110, 180,
         "https://images.unsplash.com/photo-1580052614034-c55e20ab19cb?w=200", "kg", "Fresh navel oranges"),
        ("FR005", "Fresh Strawberries", "Fruits", 300, 80,
         "https://images.unsplash.com/photo-1464965911861-746a04b4bca5?w=200", "pack", "Organic strawberries"),
        ("FR006", "Sweet Mangoes", "Fruits", 180, 120,
         "https://images.unsplash.com/photo-1553279768-865429fa0078?w=200", "kg", "Alphonso mangoes"),
        ("FR007", "Pineapple", "Fruits", 220, 60, "https://images.unsplash.com/photo-1550258987-190a2d41a8ba?w=200",
         "piece", "Ripe and juicy"),
        ("FR008", "Hass Avocados", "Fruits", 150, 140,
         "https://images.unsplash.com/photo-1523049673857-eb18f1d7b578?w=200", "piece", "Creamy avocados"),
        ("FR009", "Fresh Lemons", "Fruits", 60, 250,
         "https://images.unsplash.com/photo-1587393855524-087f83d95bc9?w=200", "kg", "Fresh lemons"),
        ("FR010", "Watermelon", "Fruits", 400, 40,
         "https://images.unsplash.com/photo-1563114773-84221bd62daa?w=200", "piece", "Sweet red watermelon"),
        ("VG001", "Fresh Tomatoes", "Vegetables", 80, 170,
         "https://images.unsplash.com/photo-1592924357228-91a4daadcfea?w=200", "kg", "Roma tomatoes"),
        ("VG002", "Red Onions", "Vegetables", 70, 200,
         "https://images.unsplash.com/photo-1508747703725-719777637510?w=200", "kg", "Fresh red onions"),
        ("VG003", "Irish Potatoes", "Vegetables", 65, 220,
         "https://images.unsplash.com/photo-1518977676601-b53f82aba655?w=200", "kg", "Russet potatoes"),
        ("VG004", "Fresh Carrots", "Vegetables", 60, 180,
         "https://images.unsplash.com/photo-1598170845058-32b9d6a5da37?w=200", "kg", "Organic carrots"),
        ("VG005", "Broccoli", "Vegetables", 150, 90,
         "https://images.unsplash.com/photo-1584270354949-c26b0d5b4a0c?w=200", "piece", "Fresh broccoli heads"),
        ("VG006", "Baby Spinach", "Vegetables", 120, 70,
         "https://images.unsplash.com/photo-1570913149827-d2ac84ab3f9a?w=200", "pack", "Fresh baby spinach"),
        ("VG007", "Cucumber", "Vegetables", 50, 160,
         "https://images.unsplash.com/photo-1604977042946-1eecc30f269e?w=200", "piece", "English cucumber"),
        ("VG008", "Bell Peppers", "Vegetables", 140, 110,
         "https://images.unsplash.com/photo-1563565375-f3fdfdbefa83?w=200", "kg", "Mixed colors"),
        ("DY001", "Fresh Milk 1L", "Dairy & Eggs", 110, 120,
         "https://images.unsplash.com/photo-1563636619-e9143da7973b?w=200", "pack", "Pasteurized whole milk"),
        ("DY002", "Greek Yogurt", "Dairy & Eggs", 180, 90,
         "https://images.unsplash.com/photo-1488477181946-6428a0291777?w=200", "cup", "Strained yogurt"),
        ("DY003", "Cheddar Cheese", "Dairy & Eggs", 350, 70,
         "https://images.unsplash.com/photo-1615937657715-bc7b4b7962c1?w=200", "kg", "Aged cheddar"),
        ("DY004", "Butter 250g", "Dairy & Eggs", 220, 100,
         "https://images.unsplash.com/photo-1589985270826-4b7bb135bc9d?w=200", "pack", "Salted butter"),
        ("DY005", "Free-Range Eggs", "Dairy & Eggs", 250, 150,
         "https://images.unsplash.com/photo-1498654077810-12c21d4d6dc3?w=200", "tray", "Pack of 6"),
        ("MT001", "Chicken Breast", "Meat & Seafood", 550, 100,
         "https://images.unsplash.com/photo-1604503468506-a8da13d82791?w=200", "kg", "Boneless skinless"),
        ("MT002", "Ground Beef", "Meat & Seafood", 600, 90,
         "https://images.unsplash.com/photo-1588168333986-5078d3ae3976?w=200", "kg", "Lean 85/15"),
        ("MT003", "Pork Chops", "Meat & Seafood", 500, 80,
         "https://images.unsplash.com/photo-1604503468506-a8da13d82791?w=200", "kg", "Center cut"),
        ("MT004", "Salmon Fillet", "Meat & Seafood", 1200, 40,
         "https://images.unsplash.com/photo-1594787318286-3d835c1d207f?w=200", "kg", "Atlantic salmon"),
        ("MT005", "Shrimp", "Meat & Seafood", 900, 60,
         "https://images.unsplash.com/photo-1565680018433-b513d5e5c6f7?w=200", "kg", "Raw peeled"),
        ("BK001", "White Bread", "Bakery & Snacks", 85, 150,
         "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=200", "loaf", "Fresh white bread"),
        ("BK002", "Croissant", "Bakery & Snacks", 120, 80,
         "https://images.unsplash.com/photo-1555507036-ab1f4038024a?w=200", "piece", "Butter croissant"),
        ("BK003", "Potato Chips", "Bakery & Snacks", 180, 200,
         "https://images.unsplash.com/photo-1566478989037-eec170784d0b?w=200", "pack", "Salted chips"),
        ("BK004", "Chocolate Bar", "Bakery & Snacks", 120, 250,
         "https://images.unsplash.com/photo-1548907040-4baa42d10919?w=200", "piece", "Milk chocolate"),
        ("BV001", "Cola Soda 2L", "Beverages", 180, 150,
         "https://images.unsplash.com/photo-1629203851122-3726ecdf080e?w=200", "bottle", "Chilled cola"),
        ("BV002", "Orange Juice", "Beverages", 300, 90,
         "https://images.unsplash.com/photo-1600271886742-f049cd451bba?w=200", "pack", "Fresh squeezed"),
        ("BV003", "Mineral Water", "Beverages", 80, 250,
         "https://images.unsplash.com/photo-1616118132534-38157a1c297a?w=200", "bottle", "Sparkling water"),
        ("BV004", "Energy Drink", "Beverages", 220, 100,
         "https://images.unsplash.com/photo-1616118132534-38157a1c297a?w=200", "can", "Caffeinated"),
        ("BV005", "Apple Juice", "Beverages", 280, 75,
         "https://images.unsplash.com/photo-1600271886742-f049cd451bba?w=200", "pack", "Clear apple juice"),
        ("PA001", "White Rice 2kg", "Pantry", 300, 200,
         "https://images.unsplash.com/photo-1586201375761-83865001e8ac?w=200", "pack", "Premium long grain"),
        ("PA002", "Pasta Spaghetti", "Pantry", 150, 180,
         "https://images.unsplash.com/photo-1551462147-37885b3edd6d?w=200", "pack", "Italian pasta"),
        ("PA003", "Olive Oil", "Pantry", 600, 70,
         "https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?w=200", "bottle", "Extra virgin"),
        ("PA004", "Tomato Ketchup", "Pantry", 220, 130,
         "https://images.unsplash.com/photo-1589924691995-400dc9ecc119?w=200", "bottle", "Tomato ketchup"),
        ("PA005", "Mayonnaise", "Pantry", 250, 120,
         "https://images.unsplash.com/photo-1589924691995-400dc9ecc119?w=200", "jar", "Creamy mayo"),
        ("HH001", "Toilet Paper", "Household", 500, 120,
         "https://images.unsplash.com/photo-1585680878066-6cacb2d7d0fe?w=200", "pack", "12 rolls"),
        ("HH002", "Laundry Detergent", "Household", 700, 80,
         "https://images.unsplash.com/photo-1604335877083-6c0d0e5e8af9?w=200", "bottle", "Liquid detergent"),
        ("HH003", "Dish Soap", "Household", 200, 150,
         "https://images.unsplash.com/photo-1604335877083-6c0d0e5e8af9?w=200", "bottle", "Lemon scent"),
        ("HH004", "Paper Towels", "Household", 350, 100,
         "https://images.unsplash.com/photo-1585680878066-6cacb2d7d0fe?w=200", "roll", "2-ply"),
        ("PC001", "Shampoo", "Personal Care", 400, 90,
         "https://images.unsplash.com/photo-1556228578-8c89e6adf883?w=200", "bottle", "Moisturizing"),
        ("PC002", "Toothpaste", "Personal Care", 250, 120,
         "https://images.unsplash.com/photo-1556228578-8c89e6adf883?w=200", "tube", "Whitening"),
        ("PC003", "Body Lotion", "Personal Care", 350, 80,
         "https://images.unsplash.com/photo-1556228578-8c89e6adf883?w=200", "bottle", "Shea butter"),
        ("PC004", "Bar Soap", "Personal Care", 80, 200,
         "https://images.unsplash.com/photo-1556228578-8c89e6adf883?w=200", "piece", "Gentle cleansing"),
    ]
    with get_db() as db:
        for p in products:
            db.execute('''INSERT
            OR IGNORE INTO products (sku, name, category, price, stock, image_url, unit, description) VALUES (?,?,?,?,?,?,?,?)''',
                       p)
        db.commit()


def list_products(search="", category="All"):
    with get_db() as db:
        query = "SELECT * FROM products WHERE 1=1"
        params = []
        if search:
            query += " AND name LIKE ?"
            params.append(f"%{search}%")
        if category and category != "All":
            query += " AND category = ?"
            params.append(category)
        query += " ORDER BY name"
        return [dict(row) for row in db.execute(query, params).fetchall()]


def categories():
    with get_db() as db:
        return [row["category"] for row in db.execute("SELECT DISTINCT category FROM products ORDER BY category")]


def update_stock(product_id, quantity_change, reason="Manual adjustment"):
    with get_db() as db:
        db.execute("UPDATE products SET stock = stock + ? WHERE id = ?", (quantity_change, product_id))
        db.execute("INSERT INTO inventory_log (product_id, quantity_change, reason) VALUES (?,?,?)",
                   (product_id, quantity_change, reason))
        db.commit()


def save_sale(customer_id, customer_name, customer_phone, cart_items, payment_method, mpesa_code=None,
              loyalty_points_used=0):
    receipt_no = f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    subtotal = sum(item["qty"] * item["unit_price"] for item in cart_items)
    tax = subtotal * 0.08
    total = subtotal + tax
    loyalty_points_earned = int(total / 100)
    items_json = json.dumps(cart_items)
    with get_db() as db:
        db.execute(
            '''INSERT INTO sales (receipt_no, customer_id, customer_name, customer_phone, items, subtotal, tax,
                                  total, payment_method, mpesa_code, loyalty_points_used, loyalty_points_earned)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (receipt_no, customer_id, customer_name, customer_phone, items_json, subtotal, tax, total, payment_method,
             mpesa_code, loyalty_points_used, loyalty_points_earned))
        if customer_id:
            db.execute('''UPDATE customers
                          SET total_purchases = total_purchases + ?,
                              loyalty_points  = loyalty_points - ? + ?
                          WHERE id = ?''', (total, loyalty_points_used, loyalty_points_earned, customer_id))
        for item in cart_items:
            db.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (item["qty"], item["product_id"]))
            db.execute("INSERT INTO inventory_log (product_id, quantity_change, reason) VALUES (?,?,?)",
                       (item["product_id"], -item["qty"], f"Sale - {receipt_no}"))
        db.commit()
    return receipt_no, total, loyalty_points_earned


def daily_sales(date_str):
    with get_db() as db:
        rows = db.execute('''SELECT *
                             FROM sales
                             WHERE DATE (created_at) = ?
                             ORDER BY created_at DESC''', (date_str,)).fetchall()
        total = db.execute('''SELECT COALESCE(SUM(total), 0)
                              FROM sales
                              WHERE DATE (created_at) = ?''', (date_str,)).fetchone()[0]
        return [dict(row) for row in rows], total


def register_customer(full_name, email, phone, password, address="", city=""):
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    with get_db() as db:
        try:
            db.execute('''INSERT INTO customers (full_name, email, phone, password, address, city)
                          VALUES (?, ?, ?, ?, ?, ?)''', (full_name, email, phone, hashed_password, address, city))
            db.commit()
            return True
        except sqlite3.IntegrityError:
            return False


def validate_customer_login(email, password):
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    with get_db() as db:
        customer = db.execute('SELECT * FROM customers WHERE email = ? AND password = ?',
                              (email, hashed_password)).fetchone()
        return dict(customer) if customer else None


def get_customer_by_id(customer_id):
    with get_db() as db:
        customer = db.execute('SELECT * FROM customers WHERE id = ?', (customer_id,)).fetchone()
        return dict(customer) if customer else None


# ============================================================
# DECORATORS
# ============================================================

def login_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)

    return decorated_function


def customer_login_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'customer_id' not in session:
            return redirect(url_for('customer_login'))
        return f(*args, **kwargs)

    return decorated_function


# ============================================================
# FLASK ROUTES
# ============================================================

@app.route('/')
def index():
    return render_template('landing.html')


@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        hashed = hashlib.sha256(password.encode()).hexdigest()
        with get_db() as db:
            admin = db.execute('SELECT * FROM admin_users WHERE username = ? AND password = ?',
                               (username, hashed)).fetchone()
            if admin:
                session['admin_id'] = admin['id']
                session['admin_username'] = admin['username']
                return redirect(url_for('admin_dashboard'))
        return render_template('admin_login.html', error='Invalid username or password')
    return render_template('admin_login.html')


@app.route('/admin-dashboard')
@login_required
def admin_dashboard():
    return render_template('admin_dashboard.html', username=session.get('admin_username'))


@app.route('/customer-login', methods=['GET', 'POST'])
def customer_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        customer = validate_customer_login(email, password)
        if customer:
            session['customer_id'] = customer['id']
            session['customer_name'] = customer['full_name']
            session['customer_email'] = customer['email']
            session['customer_points'] = customer['loyalty_points']
            return redirect(url_for('pos'))
        return render_template('customer_login.html', error='Invalid email or password')
    return render_template('customer_login.html')


@app.route('/customer-register', methods=['GET', 'POST'])
def customer_register():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        if not all([full_name, email, phone, password]):
            return render_template('customer_register.html', error='All fields are required')
        if password != confirm_password:
            return render_template('customer_register.html', error='Passwords do not match')
        if len(password) < 6:
            return render_template('customer_register.html', error='Password must be at least 6 characters')
        if register_customer(full_name, email, phone, password):
            return redirect(url_for('customer_login'))
        else:
            return render_template('customer_register.html', error='Email already registered')
    return render_template('customer_register.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route('/pos')
@customer_login_required
def pos():
    return render_template('pos.html', customer_name=session.get('customer_name'),
                           loyalty_points=session.get('customer_points', 0))


@app.route('/receipts')
@login_required
def receipts():
    return render_template('receipts.html', username=session.get('admin_username'),
                           today=datetime.now().strftime('%Y-%m-%d'))


@app.route('/change-password', methods=['GET', 'POST'])
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        if new_password != confirm_password:
            return render_template('change_password.html', error='Passwords do not match')
        if len(new_password) < 6:
            return render_template('change_password.html', error='Password must be at least 6 characters')
        hashed_current = hashlib.sha256(current_password.encode()).hexdigest()
        hashed_new = hashlib.sha256(new_password.encode()).hexdigest()
        if 'admin_id' in session:
            with get_db() as db:
                admin = db.execute('SELECT * FROM admin_users WHERE id = ? AND password = ?',
                                   (session['admin_id'], hashed_current)).fetchone()
                if admin:
                    db.execute('UPDATE admin_users SET password = ? WHERE id = ?', (hashed_new, session['admin_id']))
                    db.commit()
                    return render_template('change_password.html', success='Password changed successfully!')
                else:
                    return render_template('change_password.html', error='Current password is incorrect')
        elif 'customer_id' in session:
            with get_db() as db:
                customer = db.execute('SELECT * FROM customers WHERE id = ? AND password = ?',
                                      (session['customer_id'], hashed_current)).fetchone()
                if customer:
                    db.execute('UPDATE customers SET password = ? WHERE id = ?', (hashed_new, session['customer_id']))
                    db.commit()
                    return render_template('change_password.html', success='Password changed successfully!')
                else:
                    return render_template('change_password.html', error='Current password is incorrect')
        else:
            return redirect(url_for('index'))
    return render_template('change_password.html')


@app.route('/api/products')
def api_products():
    search = request.args.get('search', '')
    category = request.args.get('category', 'All')
    return jsonify(list_products(search, category))


@app.route('/api/categories')
def api_categories():
    return jsonify(categories())


@app.route('/api/daily_sales')
def api_daily_sales():
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    sales, total = daily_sales(date)
    return jsonify({'sales': sales, 'total': total})


@app.route('/api/all_sales')
def api_all_sales():
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    with get_db() as db:
        sales = db.execute('''SELECT *
                              FROM sales
                              WHERE DATE (created_at) = ?
                              ORDER BY created_at DESC''', (date,)).fetchall()
        return jsonify({'sales': [dict(s) for s in sales]})


@app.route('/api/inventory')
def api_inventory():
    return jsonify(list_products())


@app.route('/api/customers')
def api_customers():
    with get_db() as db:
        customers = db.execute(
            'SELECT id, full_name, email, phone, total_purchases, loyalty_points, created_at FROM customers ORDER BY total_purchases DESC').fetchall()
        return jsonify([dict(c) for c in customers])


@app.route('/api/checkout', methods=['POST'])
@customer_login_required
def api_checkout():
    try:
        data = request.json
        cart = data.get('cart', [])
        payment_method = data.get('payment_method', 'CASH')
        mpesa_code = data.get('mpesa_code')
        customer_id = session.get('customer_id')
        customer = get_customer_by_id(customer_id)
        if not cart:
            return jsonify({'success': False, 'error': 'Cart is empty'}), 400
        subtotal = sum(item["qty"] * item["unit_price"] for item in cart)
        tax = subtotal * 0.08
        final_total = subtotal + tax
        with get_db() as db:
            for item in cart:
                product = db.execute('SELECT stock, name FROM products WHERE id = ?', (item['product_id'],)).fetchone()
                if not product:
                    return jsonify({'success': False, 'error': f"Product {item['name']} not found"}), 400
                if product['stock'] < item['qty']:
                    return jsonify({'success': False, 'error': f"Insufficient stock for {item['name']}"}), 400
        receipt_no, saved_total, points_earned = save_sale(customer_id, customer['full_name'] if customer else '',
                                                           customer['phone'] if customer else '', cart, payment_method,
                                                           mpesa_code)
        if customer:
            new_points = customer['loyalty_points'] + points_earned
            session['customer_points'] = new_points
        return jsonify({
            'success': True, 'message': 'Products Purchased Successfully!', 'receipt_no': receipt_no,
            'subtotal': subtotal, 'tax': tax, 'total': final_total, 'points_earned': points_earned,
            'new_points_balance': session.get('customer_points', 0), 'payment_method': payment_method,
            'mpesa_code': mpesa_code, 'items': cart,
            'customer_name': customer['full_name'] if customer else 'Walk-in Customer',
            'customer_phone': customer['phone'] if customer else '',
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        print(f"Checkout error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/restock', methods=['POST'])
@login_required
def api_restock():
    data = request.json
    update_stock(data.get('product_id'), data.get('quantity', 0))
    return jsonify({'success': True})


@app.route('/inventory')
@login_required
def inventory():
    return render_template('inventory.html', username=session.get('admin_username'))


@app.route('/sales')
@login_required
def sales():
    return render_template('sales.html', username=session.get('admin_username'))


@app.route('/customers')
@login_required
def customers():
    return render_template('customers.html', username=session.get('admin_username'))


# ============================================================
# CREATE HTML TEMPLATES
# ============================================================

def create_templates():
    os.makedirs('templates', exist_ok=True)

    with open('templates/landing.html', 'w', encoding='utf-8') as f:
        f.write(
            '''<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>ISAAC SUPERMARKET</title><style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:'Segoe UI',sans-serif;background:linear-gradient(135deg,#0B6E4F,#085239);min-height:100vh}.container{max-width:1200px;margin:0 auto;padding:40px 20px}.header{text-align:center;color:#fff;margin-bottom:60px}.header h1{font-size:48px;margin-bottom:10px}.options{display:flex;justify-content:center;gap:30px;flex-wrap:wrap}.card{background:#fff;border-radius:20px;padding:40px;width:350px;text-align:center;transition:transform .3s}.card:hover{transform:translateY(-10px);box-shadow:0 20px 40px rgba(0,0,0,.2)}.card-icon{font-size:64px;margin-bottom:20px}.card h2{color:#0B6E4F;margin-bottom:15px}.card p{color:#6B7280;margin-bottom:25px}.btn{display:inline-block;padding:12px 30px;border-radius:25px;text-decoration:none;font-weight:700}.btn-primary{background:#0B6E4F;color:#fff}.btn-primary:hover{background:#085239}.btn-secondary{background:#F1C40F;color:#1F2937}.btn-secondary:hover{background:#D4AC0D}.footer{text-align:center;color:#fff;margin-top:60px;opacity:.8}</style></head><body><div class="container"><div class="header"><h1>ISAAC SUPERMARKET</h1><p>Quality * Value * Service</p></div><div class="options"><div class="card"><div class="card-icon">👤</div><h2>Customer Login</h2><p>Login to shop and earn points!</p><a href="/customer-login" class="btn btn-primary">Login</a></div><div class="card"><div class="card-icon">📝</div><h2>Register</h2><p>New customer? Create an account.</p><a href="/customer-register" class="btn btn-secondary">Register</a></div><div class="card"><div class="card-icon">🔐</div><h2>Admin Login</h2><p>Store administrators only.</p><a href="/admin-login" class="btn btn-primary">Admin Access</a></div></div><div class="footer"><p>&copy; 2024 ISAAC SUPERMARKET</p></div></div></body></html>''')

    with open('templates/admin_login.html', 'w', encoding='utf-8') as f:
        f.write(
            '''<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Admin Login</title><style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:'Segoe UI',sans-serif;background:linear-gradient(135deg,#0B6E4F,#085239);height:100vh;display:flex;align-items:center;justify-content:center}.login-container{background:#fff;border-radius:20px;box-shadow:0 20px 40px rgba(0,0,0,.2);width:400px;padding:40px}.logo{text-align:center;margin-bottom:30px}.logo h1{color:#0B6E4F;font-size:28px}.form-group{margin-bottom:20px}label{display:block;margin-bottom:8px;font-weight:500}input{width:100%;padding:12px;border:1px solid #E5E7EB;border-radius:10px;font-size:14px}input:focus{outline:none;border-color:#0B6E4F}button{width:100%;padding:12px;background:#0B6E4F;color:#fff;border:none;border-radius:10px;font-size:16px;font-weight:700;cursor:pointer}button:hover{background:#085239}.error{background:#FEE2E2;color:#DC2626;padding:10px;border-radius:8px;margin-bottom:20px;text-align:center}.back-link{display:block;text-align:center;margin-top:20px;color:#6B7280;text-decoration:none}</style></head><body><div class="login-container"><div class="logo"><h1>Admin Portal</h1><p>ISAAC SUPERMARKET</p></div>{% if error %}<div class="error">{{ error }}</div>{% endif %}<form method="POST"><div class="form-group"><label>Username</label><input type="text" name="username" required></div><div class="form-group"><label>Password</label><input type="password" name="password" required></div><button type="submit">Login</button></form><a href="/" class="back-link">← Back to Home</a><p style="text-align:center;margin-top:15px;font-size:12px;color:#6B7280">admin / admin123</p></div></body></html>''')

    with open('templates/customer_login.html', 'w', encoding='utf-8') as f:
        f.write(
            '''<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Customer Login</title><style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:'Segoe UI',sans-serif;background:linear-gradient(135deg,#0B6E4F,#085239);height:100vh;display:flex;align-items:center;justify-content:center}.login-container{background:#fff;border-radius:20px;box-shadow:0 20px 40px rgba(0,0,0,.2);width:400px;padding:40px}.logo{text-align:center;margin-bottom:30px}.logo h1{color:#0B6E4F;font-size:28px}.form-group{margin-bottom:20px}label{display:block;margin-bottom:8px;font-weight:500}input{width:100%;padding:12px;border:1px solid #E5E7EB;border-radius:10px;font-size:14px}input:focus{outline:none;border-color:#0B6E4F}button{width:100%;padding:12px;background:#0B6E4F;color:#fff;border:none;border-radius:10px;font-size:16px;font-weight:700;cursor:pointer}button:hover{background:#085239}.error{background:#FEE2E2;color:#DC2626;padding:10px;border-radius:8px;margin-bottom:20px;text-align:center}.back-link{display:block;text-align:center;margin-top:20px;color:#6B7280;text-decoration:none}.register-link{text-align:center;margin-top:15px;font-size:14px}.register-link a{color:#0B6E4F;font-weight:700;text-decoration:none}</style></head><body><div class="login-container"><div class="logo"><h1>Customer Login</h1><p>Welcome back!</p></div>{% if error %}<div class="error">{{ error }}</div>{% endif %}<form method="POST"><div class="form-group"><label>Email</label><input type="email" name="email" required></div><div class="form-group"><label>Password</label><input type="password" name="password" required></div><button type="submit">Login</button></form><div class="register-link">No account? <a href="/customer-register">Register</a></div><a href="/" class="back-link">← Back to Home</a></div></body></html>''')

    with open('templates/customer_register.html', 'w', encoding='utf-8') as f:
        f.write(
            '''<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Register</title><style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:'Segoe UI',sans-serif;background:linear-gradient(135deg,#0B6E4F,#085239);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}.register-container{background:#fff;border-radius:20px;box-shadow:0 20px 40px rgba(0,0,0,.2);width:500px;padding:40px}.logo{text-align:center;margin-bottom:30px}.logo h1{color:#0B6E4F;font-size:28px}.form-group{margin-bottom:15px}label{display:block;margin-bottom:5px;font-weight:500;font-size:14px}input{width:100%;padding:10px;border:1px solid #E5E7EB;border-radius:8px;font-size:14px}input:focus{outline:none;border-color:#0B6E4F}button{width:100%;padding:12px;background:#0B6E4F;color:#fff;border:none;border-radius:10px;font-size:16px;font-weight:700;cursor:pointer;margin-top:10px}button:hover{background:#085239}.error{background:#FEE2E2;color:#DC2626;padding:10px;border-radius:8px;margin-bottom:20px;text-align:center}.back-link{display:block;text-align:center;margin-top:20px;color:#6B7280;text-decoration:none}</style></head><body><div class="register-container"><div class="logo"><h1>Create Account</h1><p>Join ISAAC SUPERMARKET!</p></div>{% if error %}<div class="error">{{ error }}</div>{% endif %}<form method="POST"><div class="form-group"><label>Full Name *</label><input type="text" name="full_name" required></div><div class="form-group"><label>Email *</label><input type="email" name="email" required></div><div class="form-group"><label>Phone *</label><input type="tel" name="phone" required></div><div class="form-group"><label>Password * (min 6 chars)</label><input type="password" name="password" required minlength="6"></div><div class="form-group"><label>Confirm Password *</label><input type="password" name="confirm_password" required></div><button type="submit">Register</button></form><div style="text-align:center;margin-top:15px">Have account? <a href="/customer-login" style="color:#0B6E4F;font-weight:700">Login</a></div><a href="/" class="back-link">← Back to Home</a></div></body></html>''')

    with open('templates/admin_base.html', 'w', encoding='utf-8') as f:
        f.write(
            '''<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>ISAAC SUPERMARKET - {% block title %}Admin{% endblock %}</title><style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:'Segoe UI',sans-serif;background:#F5F7F6}.header{background:#0B6E4F;color:#fff;padding:15px 30px;display:flex;justify-content:space-between;align-items:center}.logo h2{font-size:20px}.logo p{font-size:12px;color:#F1C40F}.user-info{display:flex;align-items:center;gap:20px}.logout-btn{background:#F1C40F;color:#1F2937;padding:8px 16px;border-radius:8px;text-decoration:none;font-weight:700}.nav{background:#fff;padding:0 30px;display:flex;gap:5px;box-shadow:0 1px 3px rgba(0,0,0,.1);flex-wrap:wrap}.nav a{padding:15px 20px;text-decoration:none;color:#6B7280;font-weight:500;border-bottom:3px solid transparent}.nav a:hover,.nav a.active{color:#0B6E4F;border-bottom-color:#0B6E4F}.container{padding:20px 30px}.status-badge{display:inline-block;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:700}.status-low{background:#FEE2E2;color:#DC2626}.status-normal{background:#D1FAE5;color:#10B981}button{cursor:pointer}{% block extra_css %}{% endblock %}</style></head><body><div class="header"><div class="logo"><h2>ISAAC SUPERMARKET - Admin</h2><p>Management System</p></div><div class="user-info"><a href="/change-password" style="color:white;text-decoration:none;margin-right:15px;font-size:13px">🔒 Change Password</a><span>{{ username }}</span><a href="/logout" class="logout-btn">Logout</a></div></div><div class="nav"><a href="/admin-dashboard" class="{% if request.endpoint == 'admin_dashboard' %}active{% endif %}">Dashboard</a><a href="/inventory" class="{% if request.endpoint == 'inventory' %}active{% endif %}">Inventory</a><a href="/sales" class="{% if request.endpoint == 'sales' %}active{% endif %}">Sales</a><a href="/receipts" class="{% if request.endpoint == 'receipts' %}active{% endif %}">Receipts</a><a href="/customers" class="{% if request.endpoint == 'customers' %}active{% endif %}">Customers</a></div><div class="container">{% block content %}{% endblock %}</div><script>function formatNumber(n){return new Intl.NumberFormat('en-KE',{minimumFractionDigits:2,maximumFractionDigits:2}).format(n);}</script>{% block extra_js %}{% endblock %}</body></html>''')

    with open('templates/admin_dashboard.html', 'w', encoding='utf-8') as f:
        f.write(
            '''{% extends "admin_base.html" %}{% block title %}Dashboard{% endblock %}{% block content %}<h2>Welcome, {{ username }}!</h2><div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:20px;margin-top:20px"><div style="background:linear-gradient(135deg,#0B6E4F,#085239);color:#fff;padding:20px;border-radius:12px"><h3>📦 Inventory</h3><p style="font-size:32px;margin:10px 0" id="productCount">-</p><p>Products</p></div><div style="background:linear-gradient(135deg,#F1C40F,#D4AC0D);color:#1F2937;padding:20px;border-radius:12px"><h3>💰 Today's Sales</h3><p style="font-size:32px;margin:10px 0" id="todaySales">-</p><p>Revenue</p></div><div style="background:linear-gradient(135deg,#3B82F6,#2563EB);color:#fff;padding:20px;border-radius:12px"><h3>👥 Customers</h3><p style="font-size:32px;margin:10px 0" id="customerCount">-</p><p>Registered</p></div><div style="background:linear-gradient(135deg,#EF4444,#DC2626);color:#fff;padding:20px;border-radius:12px"><h3>⚠️ Low Stock</h3><p style="font-size:32px;margin:10px 0" id="lowStockCount">-</p><p>Below 10 units</p></div><div style="background:linear-gradient(135deg,#8B5CF6,#6D28D9);color:#fff;padding:20px;border-radius:12px"><h3>🧾 Receipts</h3><p style="font-size:32px;margin:10px 0">📄</p><p>View & print</p><a href="/receipts" style="color:#fff;text-decoration:none;font-weight:700">View →</a></div></div><script>fetch('/api/inventory').then(r=>r.json()).then(p=>{document.getElementById('productCount').textContent=p.length;document.getElementById('lowStockCount').textContent=p.filter(x=>x.stock<10).length;}).catch(e=>console.error(e));fetch('/api/daily_sales?date='+new Date().toISOString().split('T')[0]).then(r=>r.json()).then(d=>{document.getElementById('todaySales').textContent='KES '+formatNumber(d.total);}).catch(e=>console.error(e));fetch('/api/customers').then(r=>r.json()).then(c=>{document.getElementById('customerCount').textContent=c.length;}).catch(e=>console.error(e));</script>{% endblock %}''')

    with open('templates/base.html', 'w', encoding='utf-8') as f:
        f.write(
            '''<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>ISAAC SUPERMARKET - {% block title %}POS{% endblock %}</title><style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:'Segoe UI',sans-serif;background:#F5F7F6}.header{background:#0B6E4F;color:#fff;padding:15px 30px;display:flex;justify-content:space-between;align-items:center}.logo h2{font-size:20px}.logo p{font-size:12px;color:#F1C40F}.user-info{display:flex;align-items:center;gap:20px}.logout-btn{background:#F1C40F;color:#1F2937;padding:8px 16px;border-radius:8px;text-decoration:none;font-weight:700}.container{padding:20px 30px}button{cursor:pointer}{% block extra_css %}{% endblock %}</style></head><body><div class="header"><div class="logo"><h2>ISAAC SUPERMARKET</h2><p>Quality * Value * Service</p></div><div class="user-info"><a href="/change-password" style="color:white;text-decoration:none;margin-right:15px;font-size:13px">🔒 Change Password</a><span>Welcome, {{ customer_name }}</span><a href="/logout" class="logout-btn">Logout</a></div></div><div class="container">{% block content %}{% endblock %}</div><script>function formatNumber(n){return new Intl.NumberFormat('en-KE',{minimumFractionDigits:2,maximumFractionDigits:2}).format(n);}</script>{% block extra_js %}{% endblock %}</body></html>''')

    with open('templates/pos.html', 'w', encoding='utf-8') as f:
        f.write(
            '''{% extends "base.html" %}{% block title %}Point of Sale{% endblock %}{% block extra_css %}<style>.pos-container{display:flex;gap:20px}.products-panel{flex:2;background:#fff;border-radius:12px;padding:20px;box-shadow:0 1px 3px rgba(0,0,0,.1)}.cart-panel{flex:1;background:#fff;border-radius:12px;padding:20px;box-shadow:0 1px 3px rgba(0,0,0,.1);position:sticky;top:20px;height:fit-content}.search-bar{display:flex;gap:10px;margin-bottom:20px}.search-bar input,.search-bar select{padding:10px;border:1px solid #E5E7EB;border-radius:8px;font-size:14px}.search-bar input{flex:1}.category-tabs{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:15px}.category-tab{padding:8px 16px;border:1px solid #E5E7EB;border-radius:20px;cursor:pointer;font-size:13px;background:#fff;transition:all .3s}.category-tab:hover,.category-tab.active{background:#0B6E4F;color:#fff;border-color:#0B6E4F}.category-section{margin-bottom:25px}.category-title{font-size:18px;font-weight:700;color:#0B6E4F;margin-bottom:10px;padding-bottom:8px;border-bottom:2px solid #E5E7EB}.products-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:12px}.product-card{border:1px solid #E5E7EB;border-radius:10px;padding:10px;text-align:center;transition:all .3s;cursor:pointer}.product-card:hover{box-shadow:0 4px 12px rgba(0,0,0,.1);transform:translateY(-2px);border-color:#0B6E4F}.product-emoji{font-size:32px;margin-bottom:5px}.product-name{font-weight:700;font-size:13px;margin:5px 0}.product-price{color:#0B6E4F;font-weight:700;font-size:15px}.product-stock{font-size:11px;color:#6B7280}.product-stock.low{color:#DC2626;font-weight:700}.add-btn{background:#F1C40F;border:none;padding:5px 10px;border-radius:6px;cursor:pointer;margin-top:6px;font-weight:700;font-size:12px}.add-btn:hover{background:#D4AC0D}.cart-table{width:100%;border-collapse:collapse;margin:15px 0}.cart-table th,.cart-table td{padding:10px;text-align:left;border-bottom:1px solid #E5E7EB}.cart-table th{background:#F9FAFB}.quantity-input{width:55px;padding:5px;border:1px solid #E5E7EB;border-radius:4px;text-align:center}.remove-btn{background:#DC2626;color:#fff;border:none;padding:4px 8px;border-radius:4px;cursor:pointer;font-size:12px}.total-row{font-size:24px;font-weight:700;color:#0B6E4F;text-align:right;padding:15px;border-top:2px solid #E5E7EB}.checkout-btn{width:100%;padding:12px;margin:8px 0;border:none;border-radius:8px;font-weight:700;cursor:pointer}.cash-btn{background:#0B6E4F;color:#fff}.mpesa-btn{background:#F1C40F;color:#1F2937}.modal{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.5);justify-content:center;align-items:center;z-index:1000}.modal-content{background:#fff;border-radius:12px;padding:30px;max-width:550px;width:95%;max-height:85vh;overflow-y:auto}.success-header{text-align:center;margin-bottom:20px}.success-header h2{color:#059669;font-size:24px}.receipt-details{background:#F9FAFB;border-radius:8px;padding:15px;margin:15px 0}.receipt-row{display:flex;justify-content:space-between;padding:5px 0;font-size:14px}.items-list table{width:100%;border-collapse:collapse}.items-list th{background:#0B6E4F;color:#fff;padding:6px;font-size:12px}.items-list td{padding:5px 6px;border-bottom:1px solid #E5E7EB;font-size:13px}.btn-group{display:flex;gap:10px;margin-top:20px;flex-wrap:wrap}.btn-group button{flex:1;padding:12px;border:none;border-radius:8px;font-weight:700;cursor:pointer;min-width:100px}.btn-close{background:#6B7280;color:#fff}.btn-new-sale{background:#0B6E4F;color:#fff}</style>{% endblock %}{% block content %}<div class="pos-container"><div class="products-panel"><div class="search-bar"><input type="text" id="searchInput" placeholder="Search products..." onkeyup="filterProducts()"><select id="categoryFilter" onchange="filterProducts()"><option value="All">All Categories</option></select></div><div class="category-tabs" id="categoryTabs"></div><div id="productsContainer"></div></div><div class="cart-panel"><h3>🛒 Current Sale</h3><p style="font-size:14px;color:#6B7280">Welcome, <strong>{{ customer_name }}</strong></p><table class="cart-table"><thead><tr><th>Item</th><th>Qty</th><th>Price</th><th>Total</th><th></th></tr></thead><tbody id="cartBody"></tbody></table><div class="total-row" id="totalAmount">KES 0.00</div><div style="background:linear-gradient(135deg,#FEF3C7,#FDE68A);padding:10px 15px;border-radius:8px;margin:10px 0;display:flex;justify-content:space-between;align-items:center"><span style="font-weight:700">🏆 Loyalty Points</span><strong id="loyaltyPointsDisplay" style="font-size:20px;color:#0B6E4F">{{ loyalty_points }}</strong></div><button class="checkout-btn cash-btn" onclick="checkout('CASH')">💰 CASH CHECKOUT</button><button class="checkout-btn mpesa-btn" onclick="checkout('MPESA')">📱 M-PESA CHECKOUT</button><button onclick="clearCart()" style="width:100%;padding:8px;margin-top:8px">Clear Cart</button></div></div><div id="receiptModal" class="modal"><div class="modal-content" id="receiptContent"></div></div><script>let cart=[],allProducts=[],customerPoints={{loyalty_points}};function formatNumber(n){return new Intl.NumberFormat('en-KE',{minimumFractionDigits:2,maximumFractionDigits:2}).format(n);}function loadProducts(){fetch('/api/products').then(r=>r.json()).then(p=>{allProducts=p;loadCategories();displayProducts(p);});}function loadCategories(){fetch('/api/categories').then(r=>r.json()).then(cats=>{const f=document.getElementById('categoryFilter'),t=document.getElementById('categoryTabs');t.innerHTML='<button class="category-tab active" onclick="filterByCategory(\\'All\\')">All</button>';cats.forEach(c=>{f.innerHTML+=`<option value="${c}">${c}</option>`;t.innerHTML+=`<button class="category-tab" onclick="filterByCategory(\\'${c}\\')">${c}</button>`;});});}function filterByCategory(c){document.getElementById('categoryFilter').value=c;document.querySelectorAll('.category-tab').forEach(t=>t.classList.remove('active'));event.target.classList.add('active');filterProducts();}function filterProducts(){const s=document.getElementById('searchInput').value.toLowerCase(),c=document.getElementById('categoryFilter').value;let f=allProducts;if(s)f=f.filter(p=>p.name.toLowerCase().includes(s));if(c!=='All')f=f.filter(p=>p.category===c);displayProducts(f);}function displayProducts(products){const c=document.getElementById('productsContainer');if(products.length===0){c.innerHTML='<p style="text-align:center;color:#6B7280;padding:40px">No products found</p>';return;}const cats=[...new Set(products.map(p=>p.category))];c.innerHTML=cats.map(cat=>{const cp=products.filter(p=>p.category===cat);return`<div class="category-section"><div class="category-title">📦 ${cat} (${cp.length})</div><div class="products-grid">${cp.map(p=>`<div class="product-card" onclick="addToCart(${p.id},'${p.name.replace(/'/g,"\\\\'")}',${p.price},${p.stock})"><div class="product-emoji">${p.image_url||'📦'}</div><div class="product-name">${p.name}</div><div class="product-price">KES ${formatNumber(p.price)}/${p.unit}</div><div class="product-stock ${p.stock<10?'low':''}">Stock: ${p.stock}</div><button class="add-btn">+ Add</button></div>`).join('')}</div></div>`;}).join('');}function addToCart(id,name,price,stock){const e=cart.find(i=>i.product_id===id);if(e){if(e.qty+1>stock){alert('Max stock: '+stock);return;}e.qty++;}else{if(stock<1){alert('Out of stock!');return;}cart.push({product_id:id,name:name,qty:1,unit_price:price});}updateCart();}function updateCart(){const t=document.getElementById('cartBody');let total=0;if(cart.length===0){t.innerHTML='<tr><td colspan="5" style="text-align:center;padding:20px">Cart is empty</td></tr>';}else{t.innerHTML=cart.map((i,idx)=>{const st=i.qty*i.unit_price;total+=st;return`<tr><td>${i.name}</td><td><input type="number" class="quantity-input" value="${i.qty}" min="1" onchange="updateQty(${idx},this.value)"></td><td>KES ${formatNumber(i.unit_price)}</td><td>KES ${formatNumber(st)}</td><td><button class="remove-btn" onclick="removeItem(${idx})">✕</button></td></tr>`;}).join('');}document.getElementById('totalAmount').innerHTML='KES '+formatNumber(total);}function updateQty(i,q){q=parseInt(q);if(q>0){cart[i].qty=q;updateCart();}}function removeItem(i){cart.splice(i,1);updateCart();}function clearCart(){if(cart.length&&confirm('Clear cart?')){cart=[];updateCart();}}function checkout(method){if(cart.length===0){alert('Cart is empty!');return;}let code=null;if(method==='MPESA'){code=prompt('M-Pesa code:');if(!code||!code.trim()){alert('Code required!');return;}}fetch('/api/checkout',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({cart:cart,payment_method:method,mpesa_code:code})}).then(r=>r.json()).then(d=>{if(d.success){const items=d.items.map((i,idx)=>`<tr><td>${idx+1}</td><td>${i.name}</td><td>${i.qty}</td><td>KES ${formatNumber(i.unit_price)}</td><td>KES ${formatNumber(i.qty*i.unit_price)}</td></tr>`).join('');document.getElementById('receiptContent').innerHTML=`<div class="success-header"><span style="font-size:64px">✅</span><h2>Products Purchased Successfully!</h2></div><div class="receipt-details"><div class="receipt-row"><span>Receipt:</span><strong>${d.receipt_no}</strong></div><div class="receipt-row"><span>Customer:</span><strong>${d.customer_name}</strong></div><div class="receipt-row"><span>Payment:</span><strong>${d.payment_method}</strong></div><div class="receipt-row"><span>Date:</span><strong>${d.date}</strong></div></div><div class="items-list"><h4>📋 Items (${d.items.length})</h4><table><thead><tr><th>#</th><th>Item</th><th>Qty</th><th>Price</th><th>Total</th></tr></thead><tbody>${items}</tbody></table></div><div style="margin-top:15px;border-top:2px solid #0B6E4F;padding-top:10px"><div class="receipt-row"><span>Subtotal:</span><span>KES ${formatNumber(d.subtotal)}</span></div><div class="receipt-row"><span>Tax (8%):</span><span>KES ${formatNumber(d.tax)}</span></div><div class="receipt-row" style="font-size:18px;font-weight:700;color:#0B6E4F"><span>TOTAL:</span><span>KES ${formatNumber(d.total)}</span></div></div>${d.points_earned>0?`<div style="background:#FEF3C7;padding:10px;border-radius:8px;margin-top:10px;text-align:center"><strong>🏆 Points Earned: ${d.points_earned} | Balance: ${d.new_points_balance}</strong></div>`:''}<div class="btn-group"><button class="btn-new-sale" onclick="newSale()">🆕 New Sale</button><button class="btn-close" onclick="closeModal()">✕ Close</button></div>`;document.getElementById('receiptModal').style.display='flex';if(d.new_points_balance!==undefined){customerPoints=d.new_points_balance;document.getElementById('loyaltyPointsDisplay').innerHTML=customerPoints;}cart=[];updateCart();loadProducts();}else{alert('❌ '+(d.error||'Failed'));}}).catch(e=>{alert('❌ Network error');console.error(e);});}function newSale(){document.getElementById('receiptModal').style.display='none';cart=[];updateCart();}function closeModal(){document.getElementById('receiptModal').style.display='none';}document.getElementById('receiptModal').addEventListener('click',function(e){if(e.target===this)this.style.display='none';});loadProducts();</script>{% endblock %}''')

    with open('templates/change_password.html', 'w', encoding='utf-8') as f:
        f.write(
            '''<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Change Password</title><style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:'Segoe UI',sans-serif;background:linear-gradient(135deg,#0B6E4F,#085239);height:100vh;display:flex;align-items:center;justify-content:center}.container{background:#fff;border-radius:20px;box-shadow:0 20px 40px rgba(0,0,0,.2);width:450px;padding:40px}.logo{text-align:center;margin-bottom:30px}.logo h1{color:#0B6E4F;font-size:24px}.form-group{margin-bottom:20px}label{display:block;margin-bottom:8px;font-weight:500}input{width:100%;padding:12px;border:1px solid #E5E7EB;border-radius:10px;font-size:14px}input:focus{outline:none;border-color:#0B6E4F}button{width:100%;padding:12px;background:#0B6E4F;color:#fff;border:none;border-radius:10px;font-size:16px;font-weight:700;cursor:pointer}button:hover{background:#085239}.error{background:#FEE2E2;color:#DC2626;padding:10px;border-radius:8px;margin-bottom:20px;text-align:center}.success{background:#D1FAE5;color:#059669;padding:10px;border-radius:8px;margin-bottom:20px;text-align:center}.back-link{display:block;text-align:center;margin-top:20px;color:#6B7280;text-decoration:none}</style></head><body><div class="container"><div class="logo"><h1>🔒 Change Password</h1></div>{% if error %}<div class="error">{{ error }}</div>{% endif %}{% if success %}<div class="success">{{ success }}</div>{% endif %}<form method="POST"><div class="form-group"><label>Current Password</label><input type="password" name="current_password" required></div><div class="form-group"><label>New Password (min 6 chars)</label><input type="password" name="new_password" required minlength="6"></div><div class="form-group"><label>Confirm New Password</label><input type="password" name="confirm_password" required></div><button type="submit">Change Password</button></form>{% if session.admin_id %}<a href="/admin-dashboard" class="back-link">← Back to Dashboard</a>{% elif session.customer_id %}<a href="/pos" class="back-link">← Back to POS</a>{% else %}<a href="/" class="back-link">← Back to Home</a>{% endif %}</div></body></html>''')

    with open('templates/receipts.html', 'w', encoding='utf-8') as f:
        f.write(
            '''{% extends "admin_base.html" %}{% block title %}Receipts{% endblock %}{% block extra_css %}<style>.search-section{background:#fff;padding:20px;border-radius:12px;margin-bottom:20px;box-shadow:0 1px 3px rgba(0,0,0,.1)}.search-row{display:flex;gap:15px;align-items:center;flex-wrap:wrap}.search-input{padding:10px;border:1px solid #E5E7EB;border-radius:8px;font-size:14px}.search-btn{padding:10px 20px;background:#0B6E4F;color:#fff;border:none;border-radius:8px;cursor:pointer;font-weight:700}.receipts-table{width:100%;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.1);margin-bottom:20px}.receipts-table th,.receipts-table td{padding:12px;text-align:left;border-bottom:1px solid #E5E7EB}.receipts-table th{background:#F9FAFB;font-weight:600}.receipts-table tr:hover{background:#F9FAFB}.view-btn{background:#3B82F6;color:#fff;border:none;padding:6px 12px;border-radius:4px;cursor:pointer;font-size:12px}.print-btn{background:#F59E0B;color:#fff;border:none;padding:6px 12px;border-radius:4px;cursor:pointer;font-size:12px;margin-left:5px}.modal{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.5);justify-content:center;align-items:center;z-index:1000}.modal-content{background:#fff;border-radius:12px;padding:30px;max-width:700px;width:95%;max-height:80vh;overflow-y:auto}.receipt-header{text-align:center;margin-bottom:20px}.receipt-header h2{color:#0B6E4F}.receipt-info{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:20px}.items-table{width:100%;border-collapse:collapse;margin-bottom:20px}.items-table th,.items-table td{padding:8px;border:1px solid #E5E7EB;text-align:left}.items-table th{background:#F9FAFB}.total-section{text-align:right;font-size:16px;margin-top:15px}.total-row{font-weight:700;font-size:18px;color:#0B6E4F}@media print{body *{visibility:hidden}.modal-content,.modal-content *{visibility:visible}.modal-content{position:absolute;left:0;top:0;width:100%;max-width:100%;padding:20px}.no-print{display:none!important}}.no-print{margin-top:20px}</style>{% endblock %}{% block content %}<h2>🧾 Receipts & Purchase Details</h2><p style="margin-bottom:20px">View and print customer receipts</p><div class="search-section"><div class="search-row"><input type="date" id="dateFilter" class="search-input" value="{{ today }}"><input type="text" id="receiptSearch" class="search-input" placeholder="Receipt #..." style="flex:1" onkeyup="loadReceipts()"><button class="search-btn" onclick="loadReceipts()">🔍 Search</button></div></div><table class="receipts-table"><thead><tr><th>Receipt #</th><th>Date</th><th>Customer</th><th>Items</th><th>Total</th><th>Payment</th><th>Actions</th></tr></thead><tbody id="receiptsBody"></tbody></table><div id="receiptModal" class="modal"><div class="modal-content" id="receiptContent"></div></div><script>let allReceipts=[];function loadReceipts(){const date=document.getElementById('dateFilter').value,search=document.getElementById('receiptSearch').value.toLowerCase();fetch('/api/all_sales?date='+date).then(r=>r.json()).then(d=>{allReceipts=d.sales||[];let filtered=allReceipts;if(search)filtered=filtered.filter(r=>r.receipt_no.toLowerCase().includes(search));const tbody=document.getElementById('receiptsBody');if(!filtered.length){tbody.innerHTML='<tr><td colspan="7" style="text-align:center;padding:20px">No receipts found</td></tr>';return;}tbody.innerHTML=filtered.map(r=>{let items=[];try{items=typeof r.items==='string'?JSON.parse(r.items):r.items;}catch(e){}return`<tr><td><strong>${r.receipt_no}</strong></td><td>${new Date(r.created_at).toLocaleString()}</td><td>${r.customer_name||'Walk-in'}</td><td>${items.length} item(s)</td><td><strong>KES ${formatNumber(r.total)}</strong></td><td>${r.payment_method||'N/A'}</td><td><button class="view-btn" onclick="viewReceipt(${r.id})">👁 View</button><button class="print-btn" onclick="printReceipt(${r.id})">🖨 Print</button></td></tr>`;}).join('');});}function viewReceipt(id){const r=allReceipts.find(x=>x.id===id);if(!r)return;let items=[];try{items=typeof r.items==='string'?JSON.parse(r.items):r.items;}catch(e){}const subtotal=items.reduce((s,i)=>s+(i.qty*i.unit_price),0),tax=subtotal*0.08;document.getElementById('receiptContent').innerHTML=`<div class="receipt-header"><h2>ISAAC SUPERMARKET</h2><p>Quality * Value * Service</p><hr><p><strong>RECEIPT #: ${r.receipt_no}</strong></p><p>Date: ${new Date(r.created_at).toLocaleString()}</p></div><div class="receipt-info"><div><strong>Customer:</strong> ${r.customer_name||'Walk-in'}</div><div><strong>Phone:</strong> ${r.customer_phone||'N/A'}</div><div><strong>Payment:</strong> ${r.payment_method} ${r.mpesa_code?'| M-Pesa: '+r.mpesa_code:''}</div></div><p><strong>Items (${items.length}):</strong></p><table class="items-table"><thead><tr><th>#</th><th>Item</th><th>Qty</th><th>Price</th><th>Total</th></tr></thead><tbody>${items.map((i,idx)=>`<tr><td>${idx+1}</td><td>${i.name}</td><td>${i.qty}</td><td>KES ${formatNumber(i.unit_price)}</td><td>KES ${formatNumber(i.qty*i.unit_price)}</td></tr>`).join('')}</tbody></table><div class="total-section"><p>Subtotal: KES ${formatNumber(subtotal)}</p><p>Tax (8%): KES ${formatNumber(tax)}</p><p class="total-row">TOTAL: KES ${formatNumber(r.total)}</p></div><p style="text-align:center;color:#059669;font-weight:700">✅ Products Purchased Successfully!</p><div class="no-print" style="text-align:center;margin-top:20px"><button onclick="window.print()" style="padding:10px 20px;background:#0B6E4F;color:#fff;border:none;border-radius:8px;cursor:pointer;margin:5px">🖨 Print Receipt</button><button onclick="document.getElementById('receiptModal').style.display='none'" style="padding:10px 20px;background:#6B7280;color:#fff;border:none;border-radius:8px;cursor:pointer;margin:5px">✕ Close</button></div>`;document.getElementById('receiptModal').style.display='flex';}function printReceipt(id){viewReceipt(id);setTimeout(()=>window.print(),500);}document.getElementById('receiptModal').addEventListener('click',function(e){if(e.target===this)this.style.display='none';});document.getElementById('dateFilter').value=new Date().toISOString().split('T')[0];loadReceipts();</script>{% endblock %}''')

    with open('templates/inventory.html', 'w', encoding='utf-8') as f:
        f.write(
            '''{% extends "admin_base.html" %}{% block title %}Inventory{% endblock %}{% block extra_css %}<style>.search-section{margin-bottom:20px}.search-section input,.search-section select{padding:10px;border:1px solid #E5E7EB;border-radius:8px;margin-right:10px}.inventory-table{width:100%;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.1)}.inventory-table th,.inventory-table td{padding:10px;text-align:left;border-bottom:1px solid #E5E7EB;font-size:14px}.inventory-table th{background:#F9FAFB;font-weight:600}.inventory-table tr:hover{background:#F9FAFB}.restock-input{width:60px;padding:5px;border:1px solid #E5E7EB;border-radius:4px}.restock-btn{background:#3B82F6;color:#fff;border:none;padding:5px 10px;border-radius:4px;cursor:pointer}</style>{% endblock %}{% block content %}<h2>📦 Inventory Management</h2><div class="search-section"><input type="text" id="searchInventory" placeholder="Search..." onkeyup="loadInventory()"><select id="categoryFilter" onchange="loadInventory()"><option value="All">All</option></select></div><table class="inventory-table"><thead><tr><th>SKU</th><th>Product</th><th>Category</th><th>Price</th><th>Stock</th><th>Unit</th><th>Status</th><th>Restock</th></tr></thead><tbody id="inventoryBody"></tbody></table><script>fetch('/api/categories').then(r=>r.json()).then(cats=>{const s=document.getElementById('categoryFilter');cats.forEach(c=>{s.innerHTML+=`<option value="${c}">${c}</option>`;});});function loadInventory(){const search=document.getElementById('searchInventory').value.toLowerCase(),cat=document.getElementById('categoryFilter').value;fetch('/api/inventory').then(r=>r.json()).then(p=>{let f=p;if(search)f=f.filter(x=>x.name.toLowerCase().includes(search));if(cat!=='All')f=f.filter(x=>x.category===cat);document.getElementById('inventoryBody').innerHTML=f.map(x=>`<tr><td>${x.sku}</td><td>${x.image_url||''} ${x.name}</td><td>${x.category}</td><td>KES ${formatNumber(x.price)}</td><td>${x.stock}</td><td>${x.unit}</td><td><span class="status-badge ${x.stock<10?'status-low':'status-normal'}">${x.stock<10?'Low':'OK'}</span></td><td><input type="number" class="restock-input" id="r_${x.id}" value="10" min="1"><button class="restock-btn" onclick="restock(${x.id})">+</button></td></tr>`).join('');});}function restock(id){const q=parseInt(document.getElementById('r_'+id).value);fetch('/api/restock',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({product_id:id,quantity:q})}).then(r=>r.json()).then(d=>{if(d.success){loadInventory();alert('Updated!');}});}loadInventory();</script>{% endblock %}''')

    with open('templates/sales.html', 'w', encoding='utf-8') as f:
        f.write(
            '''{% extends "admin_base.html" %}{% block title %}Sales{% endblock %}{% block content %}<h2>Daily Sales</h2><div style="background:linear-gradient(135deg,#0B6E4F,#085239);color:#fff;padding:20px;border-radius:12px;margin-bottom:20px"><h3>Total: <span id="totalRevenue">KES 0.00</span></h3></div><input type="date" id="dateFilter" onchange="loadSales()" style="padding:10px;border:1px solid #E5E7EB;border-radius:8px;margin-bottom:20px"><table style="width:100%;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.1)"><thead><tr style="background:#F9FAFB"><th>Receipt</th><th>Customer</th><th>Items</th><th>Total</th><th>Payment</th><th>Time</th></tr></thead><tbody id="salesBody"></tbody></table><script>function loadSales(){const d=document.getElementById('dateFilter').value||new Date().toISOString().split('T')[0];fetch('/api/daily_sales?date='+d).then(r=>r.json()).then(data=>{document.getElementById('totalRevenue').textContent='KES '+formatNumber(data.total);document.getElementById('salesBody').innerHTML=data.sales.map(s=>{let items=[];try{items=JSON.parse(s.items);}catch(e){}return`<tr><td>${s.receipt_no}</td><td>${s.customer_name||'Walk-in'}</td><td>${items.length} item(s)</td><td>KES ${formatNumber(s.total)}</td><td>${s.payment_method}</td><td>${new Date(s.created_at).toLocaleTimeString()}</td></tr>`;}).join('');});}document.getElementById('dateFilter').value=new Date().toISOString().split('T')[0];loadSales();</script>{% endblock %}''')

    with open('templates/customers.html', 'w', encoding='utf-8') as f:
        f.write(
            '''{% extends "admin_base.html" %}{% block title %}Customers{% endblock %}{% block content %}<h2>Customers</h2><table style="width:100%;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.1)"><thead><tr style="background:#F9FAFB"><th>ID</th><th>Name</th><th>Email</th><th>Phone</th><th>Purchases</th><th>Points</th><th>Member Since</th></tr></thead><tbody id="customersBody"></tbody></table><script>fetch('/api/customers').then(r=>r.json()).then(c=>{document.getElementById('customersBody').innerHTML=c.map(x=>`<tr><td>${x.id}</td><td>${x.full_name}</td><td>${x.email}</td><td>${x.phone}</td><td>KES ${formatNumber(x.total_purchases||0)}</td><td>${x.loyalty_points||0}</td><td>${x.created_at?new Date(x.created_at).toLocaleDateString():'N/A'}</td></tr>`).join('');});</script>{% endblock %}''')


# ============================================================
# MAIN ENTRY POINT - Runs on both local and Render
# ============================================================

# Initialize on startup (required for gunicorn/Render)
init_db()
create_templates()
if not os.path.exists("receipts"):
    os.makedirs("receipts")

if __name__ == "__main__":
    print("=" * 60)
    print("ISAAC SUPERMARKET POS SYSTEM")
    print("=" * 60)
    print("Server running at: http://127.0.0.1:5000")
    print("\nAdmin Login: admin / admin123")
    print("Customer: Register first, then login")
    print("=" * 60)
    webbrowser.open("http://127.0.0.1:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)