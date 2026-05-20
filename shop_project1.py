# shop_web_app.py - Complete Supermarket Management System
# Deployable to Render, PythonAnywhere, or any Flask hosting

from flask import Flask, request, redirect, url_for, flash, render_template_string, jsonify, make_response, send_file
from datetime import datetime, timedelta
from functools import wraps
from collections import defaultdict
import json
import os
import hashlib
import secrets
import re

# Import reportlab with error handling
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("Note: ReportLab not installed. PDF receipt generation will be disabled.")

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# ==================== SECURE USER MANAGEMENT ====================
USERS_FILE = "users.json"

def init_admin():
    """Initialize admin user if not exists"""
    if not os.path.exists(USERS_FILE):
        admin_password = hashlib.sha256("admin123".encode()).hexdigest()
        users_data = {
            "admin": {
                "password": admin_password,
                "role": "admin",
                "name": "Isaac Manager",
                "email": "isaac@supermarket.com",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "last_login_ip": "",
                "last_login_time": ""
            }
        }
        with open(USERS_FILE, "w") as file:
            json.dump(users_data, file, indent=2)
        return users_data
    else:
        with open(USERS_FILE, "r") as file:
            return json.load(file)

def save_users(users_data):
    with open(USERS_FILE, "w") as file:
        json.dump(users_data, file, indent=2)

def get_users():
    return init_admin()

users = get_users()
current_session = {}

def get_client_ip():
    """Get client IP address"""
    if request.headers.get('X-Forwarded-For'):
        ip = request.headers.get('X-Forwarded-For').split(',')[0]
    else:
        ip = request.remote_addr
    return ip

def login_required(role=None):
    def decorator(func):
        @wraps(func)
        def decorated_function(*args, **kwargs):
            if not current_session.get('logged_in'):
                flash('Please login first!', 'danger')
                return redirect(url_for('login'))
            if role and current_session.get('role') != role and current_session.get('role') != 'admin':
                flash('Access denied! Insufficient permissions.', 'danger')
                return redirect(url_for('index'))
            return func(*args, **kwargs)
        return decorated_function
    return decorator

# ==================== PRODUCTS DATABASE ====================
products = {
    "🛢️ Cooking Oil": {"price": 250, "quantity": 45, "quality": "high", "category": "cooking", "cost_price": 180, "min_stock": 8, "popularity": 95},
    "🌽 Maize Flour": {"price": 120, "quantity": 65, "quality": "medium", "category": "cooking", "cost_price": 85, "min_stock": 15, "popularity": 98},
    "🌾 Wheat Flour": {"price": 110, "quantity": 58, "quality": "high", "category": "cooking", "cost_price": 75, "min_stock": 12, "popularity": 97},
    "🍚 Rice": {"price": 600, "quantity": 32, "quality": "premium", "category": "cooking", "cost_price": 450, "min_stock": 5, "popularity": 96},
    "🍝 Pasta": {"price": 80, "quantity": 48, "quality": "medium", "category": "cooking", "cost_price": 50, "min_stock": 10, "popularity": 85},
    "🧂 Salt": {"price": 20, "quantity": 105, "quality": "low", "category": "cooking", "cost_price": 10, "min_stock": 20, "popularity": 99},
    "🍬 Sugar": {"price": 140, "quantity": 55, "quality": "medium", "category": "cooking", "cost_price": 100, "min_stock": 12, "popularity": 98},
    "🍎 Apple": {"price": 30, "quantity": 55, "quality": "high", "category": "fruits", "cost_price": 20, "min_stock": 10, "popularity": 95},
    "🍌 Banana": {"price": 20, "quantity": 105, "quality": "medium", "category": "fruits", "cost_price": 12, "min_stock": 15, "popularity": 98},
    "🍊 Orange": {"price": 25, "quantity": 48, "quality": "high", "category": "fruits", "cost_price": 15, "min_stock": 10, "popularity": 92},
    "🥭 Mango": {"price": 45, "quantity": 38, "quality": "high", "category": "fruits", "cost_price": 28, "min_stock": 8, "popularity": 91},
    "🍅 Tomato": {"price": 40, "quantity": 65, "quality": "medium", "category": "vegetables", "cost_price": 25, "min_stock": 12, "popularity": 96},
    "🥕 Carrot": {"price": 25, "quantity": 85, "quality": "high", "category": "vegetables", "cost_price": 15, "min_stock": 15, "popularity": 94},
    "🥔 Potato": {"price": 20, "quantity": 125, "quality": "low", "category": "vegetables", "cost_price": 12, "min_stock": 20, "popularity": 97},
    "🧅 Onion": {"price": 25, "quantity": 95, "quality": "medium", "category": "vegetables", "cost_price": 15, "min_stock": 15, "popularity": 98},
    "🥛 Milk": {"price": 50, "quantity": 25, "quality": "high", "category": "dairy", "cost_price": 35, "min_stock": 5, "popularity": 96},
    "🧀 Cheese": {"price": 120, "quantity": 18, "quality": "premium", "category": "dairy", "cost_price": 85, "min_stock": 3, "popularity": 89},
    "🥚 Eggs": {"price": 300, "quantity": 45, "quality": "medium", "category": "dairy", "cost_price": 220, "min_stock": 8, "popularity": 94},
    "🍞 Bread": {"price": 40, "quantity": 20, "quality": "low", "category": "bakery", "cost_price": 25, "min_stock": 5, "popularity": 98},
    "🍪 Cookies": {"price": 35, "quantity": 55, "quality": "medium", "category": "bakery", "cost_price": 20, "min_stock": 10, "popularity": 93},
    "☕ Coffee": {"price": 150, "quantity": 35, "quality": "premium", "category": "beverages", "cost_price": 90, "min_stock": 8, "popularity": 94},
    "🍵 Tea": {"price": 80, "quantity": 45, "quality": "high", "category": "beverages", "cost_price": 50, "min_stock": 10, "popularity": 96},
    "🥤 Soda": {"price": 40, "quantity": 105, "quality": "low", "category": "beverages", "cost_price": 25, "min_stock": 20, "popularity": 97},
    "🍫 Chocolate": {"price": 75, "quantity": 55, "quality": "high", "category": "snacks", "cost_price": 45, "min_stock": 12, "popularity": 95},
    "🍬 Candy": {"price": 10, "quantity": 310, "quality": "low", "category": "snacks", "cost_price": 5, "min_stock": 50, "popularity": 98},
    "🧼 Detergent": {"price": 180, "quantity": 35, "quality": "high", "category": "household", "cost_price": 120, "min_stock": 8, "popularity": 94}
}

daily_sales = []
sales_transactions = []
activity_log = []
customers = {}

def save_data():
    data_to_save = {
        "products": products,
        "daily_sales": daily_sales,
        "sales_transactions": sales_transactions,
        "activity_log": activity_log,
        "customers": customers
    }
    with open("shop_data.json", "w", encoding='utf-8') as file:
        json.dump(data_to_save, file, indent=2, ensure_ascii=False)

def load_data():
    global products, daily_sales, sales_transactions, activity_log, customers
    try:
        with open("shop_data.json", "r", encoding='utf-8') as file:
            data_loaded = json.load(file)
            products = data_loaded.get("products", products)
            daily_sales = data_loaded.get("daily_sales", daily_sales)
            sales_transactions = data_loaded.get("sales_transactions", sales_transactions)
            activity_log = data_loaded.get("activity_log", activity_log)
            customers = data_loaded.get("customers", customers)
    except FileNotFoundError:
        pass
    except Exception as error:
        print(f"Error loading data: {error}")

load_data()

def log_activity(action_message, user=None):
    activity_log.append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user": user or current_session.get('username', 'system'),
        "action": action_message,
        "ip": get_client_ip()
    })
    save_data()

def get_total_stock():
    return sum(product["quantity"] for product in products.values())

def get_total_sales():
    return sum(daily_sales)

def get_total_profit():
    total_profit_value = 0
    for transaction in sales_transactions:
        transaction_profit = transaction['total']
        for item in transaction['items']:
            if item['name'] in products:
                cost_price_value = products[item['name']].get('cost_price', products[item['name']]['price'] - 10)
                transaction_profit -= cost_price_value * item['quantity']
        total_profit_value += transaction_profit
    return int(total_profit_value)

def get_daily_sales_last_7_days():
    sales_by_day = defaultdict(float)
    today_date = datetime.now()
    for i in range(7):
        date_str = (today_date - timedelta(days=i)).strftime("%Y-%m-%d")
        sales_by_day[date_str] = 0
    for transaction in sales_transactions:
        transaction_date = transaction['timestamp'][:10]
        if transaction_date in sales_by_day:
            sales_by_day[transaction_date] += transaction['total']
    return dict(sorted(sales_by_day.items()))

# ==================== HTML TEMPLATES ====================
LOGIN_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Login - Isaac Supermarket</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%);
            min-height: 100vh; 
            display: flex; 
            justify-content: center; 
            align-items: center; 
        }
        .login-container { 
            background: rgba(255,255,255,0.95); 
            padding: 40px; 
            border-radius: 20px; 
            width: 380px; 
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            animation: slideUp 0.5s ease;
        }
        @keyframes slideUp {
            from { transform: translateY(50px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
        h1 { text-align: center; margin-bottom: 30px; color: #1e3a8a; }
        .company-name { text-align: center; font-size: 14px; color: #2563eb; margin-bottom: 20px; letter-spacing: 2px; }
        input { width: 100%; padding: 12px; margin: 10px 0; border: 2px solid #e0e0e0; border-radius: 10px; }
        input:focus { border-color: #2563eb; outline: none; box-shadow: 0 0 10px rgba(37,99,235,0.3); }
        button { width: 100%; padding: 12px; background: #2563eb; color: white; border: none; border-radius: 10px; cursor: pointer; font-size: 16px; }
        button:hover { background: #1d4ed8; }
        .flash { background: #dc2626; color: white; padding: 10px; border-radius: 10px; margin-bottom: 20px; text-align: center; }
        .register-link { text-align: center; margin-top: 20px; }
        .register-link a { color: #2563eb; text-decoration: none; }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="company-name">🏪 ISAAC SUPERMARKET COMPANY</div>
        <h1>🏪 Shop Login</h1>
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="flash">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        <form method="POST">
            <input type="text" name="username" placeholder="Username" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Login</button>
        </form>
        <div class="register-link">
            New user? <a href="/register">Create an account</a>
        </div>
        <div class="register-link">
            Default Admin: admin / admin123
        </div>
    </div>
</body>
</html>
'''

REGISTER_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Register - Isaac Supermarket</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', sans-serif; background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center; }
        .register-container { background: rgba(255,255,255,0.95); padding: 40px; border-radius: 20px; width: 400px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); }
        h1 { text-align: center; margin-bottom: 30px; color: #1e3a8a; }
        .company-name { text-align: center; font-size: 14px; color: #2563eb; margin-bottom: 20px; }
        input { width: 100%; padding: 12px; margin: 10px 0; border: 2px solid #e0e0e0; border-radius: 10px; }
        button { width: 100%; padding: 12px; background: #2563eb; color: white; border: none; border-radius: 10px; cursor: pointer; font-size: 16px; }
        .flash { background: #dc2626; color: white; padding: 10px; border-radius: 10px; margin-bottom: 20px; text-align: center; }
        .login-link { text-align: center; margin-top: 20px; }
        .login-link a { color: #2563eb; text-decoration: none; }
    </style>
</head>
<body>
    <div class="register-container">
        <div class="company-name">🏪 ISAAC SUPERMARKET COMPANY</div>
        <h1>📝 Create Account</h1>
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="flash">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        <form method="POST">
            <input type="text" name="username" placeholder="Username" required>
            <input type="email" name="email" placeholder="Email" required>
            <input type="text" name="fullname" placeholder="Full Name" required>
            <input type="password" name="password" placeholder="Password" required>
            <input type="password" name="confirm_password" placeholder="Confirm Password" required>
            <button type="submit">Register</button>
        </form>
        <div class="login-link">Already have an account? <a href="/login">Login here</a></div>
    </div>
</body>
</html>
'''

INDEX_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Isaac Supermarket - Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', sans-serif; background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%); min-height: 100vh; }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        .header { background: rgba(255,255,255,0.95); padding: 20px; border-radius: 20px; margin-bottom: 20px; border-bottom: 4px solid #2563eb; }
        .company-header { text-align: center; margin-bottom: 15px; padding-bottom: 15px; border-bottom: 2px solid #e0e7ff; }
        .company-name { font-size: 28px; font-weight: bold; color: #1e3a8a; letter-spacing: 3px; display: inline-block; }
        .user-info { float: right; text-align: right; margin-top: -50px; }
        .nav { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 15px; clear: both; }
        .nav a { background: #2563eb; color: white; padding: 10px 20px; text-decoration: none; border-radius: 10px; transition: all 0.3s; }
        .nav a:hover { transform: translateY(-2px); background: #1d4ed8; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px; }
        .stat-card { background: rgba(255,255,255,0.95); padding: 20px; border-radius: 15px; text-align: center; cursor: pointer; transition: all 0.3s; }
        .stat-card:hover { transform: translateY(-5px); box-shadow: 0 10px 30px rgba(0,0,0,0.2); }
        .stat-card .value { font-size: 2em; font-weight: bold; color: #1e3a8a; }
        .chart-container { background: rgba(255,255,255,0.95); padding: 20px; border-radius: 15px; margin-bottom: 20px; }
        table { width: 100%; background: rgba(255,255,255,0.95); border-collapse: collapse; border-radius: 15px; overflow: hidden; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #e5e7eb; }
        th { background: #2563eb; color: white; }
        .low-stock { color: #dc2626; font-weight: bold; }
        .flash { position: fixed; top: 20px; right: 20px; padding: 15px; border-radius: 10px; animation: slideIn 0.3s; z-index: 1000; }
        .flash.success { background: #10b981; color: white; }
        .flash.danger { background: #dc2626; color: white; }
        @keyframes slideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
        .search-box { margin-bottom: 20px; }
        .search-box input { width: 100%; padding: 12px; border: 2px solid #e0e0e0; border-radius: 10px; font-size: 16px; }
        @media (max-width: 768px) { .stats { grid-template-columns: 1fr; } .nav a { font-size: 12px; padding: 8px 12px; } .user-info { float: none; text-align: center; margin-top: 10px; } }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="company-header">
                <div class="company-name">🏪 ISAAC SUPERMARKET COMPANY</div>
                <div class="company-tagline" style="font-size:12px;color:#2563eb;">Quality Products | Best Prices</div>
            </div>
            <div class="user-info">
                <span>👤 {{ session_name }}</span> ({{ session_role }})<br>
                <a href="/change_password" style="color:#2563eb;">🔐 Change Password</a> | 
                <a href="/logout" style="color:#dc2626;">🚪 Logout</a>
            </div>
            <div class="nav">
                <a href="/">📊 Dashboard</a>
                <a href="/products">📦 Products</a>
                <a href="/add_product">➕ Add Product</a>
                <a href="/sale">🛒 Record Sale</a>
                <a href="/report">📈 Report</a>
                <a href="/low_stock">⚠️ Low Stock</a>
                <a href="/best_sellers">🏆 Best Sellers</a>
                <a href="/customers">👥 Customers</a>
                <a href="/activity">📋 Activity Log</a>
            </div>
        </div>
        <div class="stats">
            <div class="stat-card" onclick="location.href='/products'"><div class="value">{{ total_products }}</div><div>📦 Products</div></div>
            <div class="stat-card" onclick="location.href='/low_stock'"><div class="value">{{ total_stock }}</div><div>📊 Stock</div></div>
            <div class="stat-card" onclick="location.href='/low_stock'"><div class="value">{{ low_stock_count }}</div><div>⚠️ Low Stock</div></div>
            <div class="stat-card" onclick="location.href='/report'"><div class="value">{{ total_sales }} KES</div><div>💰 Total Sales</div></div>
            <div class="stat-card"><div class="value">{{ total_profit }} KES</div><div>💵 Profit</div></div>
            <div class="stat-card" onclick="location.href='/report'"><div class="value">{{ transaction_count }}</div><div>🔄 Transactions</div></div>
        </div>
        <div class="chart-container"><canvas id="salesChart" style="max-height:300px;"></canvas></div>
        <div class="search-box"><input type="text" id="searchInput" placeholder="🔍 Search products..." onkeyup="searchProducts()"></div>
        <div id="productsTable">
            <table>
                <thead><tr><th>🛍️ Product</th><th>💰 Price</th><th>📦 Quantity</th><th>⭐ Quality</th><th>📂 Category</th></tr></thead>
                <tbody>
                    {% for name, details in products.items() %}
                    <tr class="product-row">
                        <td>{{ name }}</td>
                        <td>{{ details.price }} KES</td>
                        <td class="{% if details.quantity < details.get('min_stock', 5) %}low-stock{% endif %}">{{ details.quantity }}</td>
                        <td>{{ details.quality|capitalize }}</td>
                        <td>{{ details.category|capitalize }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
                <div class="flash {{ category }}">{{ message }}</div>
            {% endfor %}
        {% endif %}
    {% endwith %}
    <script>
        setTimeout(function() { document.querySelectorAll('.flash').forEach(f => f.remove()); }, 3000);
        function searchProducts() {
            var input = document.getElementById('searchInput').value.toLowerCase();
            var rows = document.getElementsByClassName('product-row');
            for (var i = 0; i < rows.length; i++) {
                rows[i].style.display = rows[i].textContent.toLowerCase().includes(input) ? '' : 'none';
            }
        }
        var ctx = document.getElementById('salesChart').getContext('2d');
        new Chart(ctx, {
            type: 'line',
            data: { labels: {{ chart_labels|tojson }}, datasets: [{ label: 'Daily Sales (KES)', data: {{ chart_data|tojson }}, borderColor: '#2563eb', backgroundColor: 'rgba(37,99,235,0.1)', tension: 0.4, fill: true }] },
            options: { responsive: true, maintainAspectRatio: true }
        });
    </script>
</body>
</html>
'''

CHANGE_PASSWORD_HTML = '''
<!DOCTYPE html>
<html>
<head><title>Change Password</title><style>
body{font-family:'Segoe UI';background:linear-gradient(135deg,#1e3a8a 0%,#2563eb 100%);display:flex;justify-content:center;align-items:center;min-height:100vh;}
.container{background:white;padding:40px;border-radius:20px;width:400px;}
input{width:100%;padding:12px;margin:10px 0;border:2px solid #e0e0e0;border-radius:10px;}
button{width:100%;padding:12px;background:#2563eb;color:white;border:none;border-radius:10px;cursor:pointer;}
.flash{background:#dc2626;color:white;padding:10px;border-radius:10px;margin-bottom:20px;}
</style></head>
<body>
<div class="container"><h1>🔐 Change Password</h1>
{% with messages = get_flashed_messages(with_categories=true) %}{% if messages %}{% for category, message in messages %}<div class="flash">{{ message }}</div>{% endfor %}{% endif %}{% endwith %}
<form method="POST"><input type="password" name="current_password" placeholder="Current Password" required><input type="password" name="new_password" placeholder="New Password" required><input type="password" name="confirm_password" placeholder="Confirm Password" required><button type="submit">Change Password</button></form>
<a href="/">← Back</a></div></body></html>
'''

# ==================== ROUTES ====================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip().lower()
        email = request.form['email'].strip()
        fullname = request.form['fullname'].strip()
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        if not all([username, email, fullname, password]):
            flash('All fields are required!', 'danger')
            return redirect(url_for('register'))
        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('register'))
        if len(password) < 4:
            flash('Password must be at least 4 characters!', 'danger')
            return redirect(url_for('register'))
        users_data = get_users()
        if username in users_data:
            flash('Username already exists!', 'danger')
            return redirect(url_for('register'))
        users_data[username] = {
            "password": hashlib.sha256(password.encode()).hexdigest(),
            "role": "staff",
            "name": fullname,
            "email": email,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "last_login_ip": "",
            "last_login_time": ""
        }
        save_users(users_data)
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template_string(REGISTER_HTML)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip().lower()
        password = hashlib.sha256(request.form['password'].encode()).hexdigest()
        client_ip = get_client_ip()
        users_data = get_users()
        if username in users_data and users_data[username]['password'] == password:
            users_data[username]['last_login_ip'] = client_ip
            users_data[username]['last_login_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_users(users_data)
            current_session['logged_in'] = True
            current_session['username'] = username
            current_session['role'] = users_data[username]['role']
            current_session['name'] = users_data[username]['name']
            log_activity(f"User logged in from IP: {client_ip}", username)
            flash(f'Welcome back, {users_data[username]["name"]}!', 'success')
            return redirect(url_for('index'))
        flash('Invalid credentials!', 'danger')
    return render_template_string(LOGIN_HTML)

@app.route('/change_password', methods=['GET', 'POST'])
@login_required()
def change_password():
    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        username = current_session.get('username')
        users_data = get_users()
        current_hash = hashlib.sha256(current_password.encode()).hexdigest()
        if users_data[username]['password'] != current_hash:
            flash('Current password is incorrect!', 'danger')
            return redirect(url_for('change_password'))
        if new_password != confirm_password:
            flash('New passwords do not match!', 'danger')
            return redirect(url_for('change_password'))
        if len(new_password) < 4:
            flash('Password must be at least 4 characters!', 'danger')
            return redirect(url_for('change_password'))
        users_data[username]['password'] = hashlib.sha256(new_password.encode()).hexdigest()
        save_users(users_data)
        flash('Password changed! Please login again.', 'success')
        current_session.clear()
        return redirect(url_for('login'))
    return render_template_string(CHANGE_PASSWORD_HTML)

@app.route('/logout')
def logout():
    log_activity(f"User logged out")
    current_session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))

@app.route('/')
@login_required()
def index():
    daily_sales_data = get_daily_sales_last_7_days()
    return render_template_string(INDEX_HTML,
        total_products=len(products),
        total_stock=get_total_stock(),
        low_stock_count=sum(1 for p in products.values() if p["quantity"] < p.get("min_stock", 5)),
        total_sales=get_total_sales(),
        total_profit=get_total_profit(),
        transaction_count=len(sales_transactions),
        products=products,
        session_name=current_session.get('name', 'User'),
        session_role=current_session.get('role', 'staff'),
        chart_labels=list(daily_sales_data.keys()),
        chart_data=list(daily_sales_data.values()))

@app.route('/products')
@login_required()
def view_products():
    PRODUCTS_HTML = '''
    <!DOCTYPE html>
    <html>
    <head><title>Products</title><style>
    body{font-family:'Segoe UI';background:linear-gradient(135deg,#1e3a8a 0%,#2563eb 100%);padding:20px;}
    .container{max-width:1400px;margin:0 auto;}
    .header{background:white;padding:20px;border-radius:20px;margin-bottom:20px;}
    .nav a{background:#2563eb;color:white;padding:10px 20px;text-decoration:none;border-radius:10px;display:inline-block;margin:5px;}
    table{width:100%;background:white;border-collapse:collapse;border-radius:15px;overflow:hidden;}
    th,td{padding:12px;border-bottom:1px solid #e5e7eb;}
    th{background:#2563eb;color:white;}
    .btn-edit{background:#2563eb;color:white;padding:5px 10px;border-radius:5px;text-decoration:none;}
    .btn-delete{background:#dc2626;color:white;padding:5px 10px;border-radius:5px;text-decoration:none;}
    .low-stock{color:#dc2626;font-weight:bold;}
    </style></head>
    <body><div class="container"><div class="header"><h1>📦 Products ({{ products|length }} items)</h1><div class="nav"><a href="/">Dashboard</a><a href="/add_product">Add Product</a></div></div>
    <table><thead><tr><th>Product</th><th>Price</th><th>Quantity</th><th>Quality</th><th>Category</th><th>Actions</th></tr></thead><tbody>
    {% for name,details in products.items() %}
    <tr><td>{{ name }}</td><td>{{ details.price }} KES</td><td class="{% if details.quantity < details.get('min_stock',5) %}low-stock{% endif %}">{{ details.quantity }}</td><td>{{ details.quality }}</td><td>{{ details.category }}</td>
    <td><a href="/edit_product/{{ name }}" class="btn-edit">Edit</a> <a href="/delete_product/{{ name }}" class="btn-delete">Delete</a>
    <form action="/restock/{{ name }}" method="POST" style="display:inline;"><input type="number" name="quantity" placeholder="Qty" style="width:60px;"><button type="submit" style="background:#10b981;color:white;border:none;padding:5px 10px;">Restock</button></form>
    </td></tr>
    {% endfor %}
    </tbody></table></div></body></html>
    '''
    return render_template_string(PRODUCTS_HTML, products=products)

@app.route('/add_product', methods=['GET', 'POST'])
@login_required(role='admin')
def add_product():
    if request.method == 'POST':
        name = request.form['name'].strip()
        if name in products:
            flash('Product exists!', 'danger')
            return redirect(url_for('add_product'))
        qty = int(request.form['quantity'])
        if qty <= 0:
            flash('Quantity must be > 0!', 'danger')
            return redirect(url_for('add_product'))
        products[name] = {
            "price": int(request.form['price']),
            "quantity": qty,
            "quality": request.form['quality'],
            "category": request.form['category'],
            "cost_price": int(request.form['cost_price']),
            "min_stock": int(request.form['min_stock']),
            "popularity": 80
        }
        save_data()
        flash('Product added!', 'success')
        return redirect(url_for('view_products'))
    ADD_FORM = '''
    <!DOCTYPE html>
    <html>
    <head><title>Add Product</title><style>
    body{font-family:Arial;background:linear-gradient(135deg,#1e3a8a 0%,#2563eb 100%);padding:20px;}
    .container{max-width:500px;margin:0 auto;background:white;padding:30px;border-radius:20px;}
    input,select{width:100%;padding:10px;margin:10px 0;border:2px solid #e0e0e0;border-radius:5px;}
    button{background:#2563eb;color:white;padding:12px;border:none;border-radius:10px;cursor:pointer;width:100%;}
    </style></head>
    <body><div class="container"><h1>Add Product</h1>
    <form method="POST"><input type="text" name="name" placeholder="Name" required>
    <input type="number" name="price" placeholder="Price" required>
    <input type="number" name="cost_price" placeholder="Cost Price" required>
    <input type="number" name="quantity" placeholder="Quantity (>0)" required min="1">
    <input type="number" name="min_stock" placeholder="Min Stock" value="5">
    <select name="quality"><option>low</option><option>medium</option><option>high</option><option>premium</option></select>
    <select name="category"><option>cooking</option><option>fruits</option><option>vegetables</option><option>dairy</option><option>bakery</option><option>beverages</option><option>snacks</option><option>household</option></select>
    <button type="submit">Add Product</button></form></div></body></html>
    '''
    return render_template_string(ADD_FORM)

@app.route('/edit_product/<name>', methods=['GET', 'POST'])
@login_required(role='admin')
def edit_product(name):
    if request.method == 'POST':
        qty = int(request.form['quantity'])
        if qty <= 0:
            flash('Quantity must be > 0!', 'danger')
            return redirect(url_for('edit_product', name=name))
        products[name] = {
            "price": int(request.form['price']),
            "quantity": qty,
            "quality": request.form['quality'],
            "category": request.form['category'],
            "cost_price": int(request.form['cost_price']),
            "min_stock": int(request.form['min_stock']),
            "popularity": products[name].get('popularity', 80)
        }
        save_data()
        flash('Product updated!', 'success')
        return redirect(url_for('view_products'))
    edit_form = f'''
    <!DOCTYPE html>
    <html>
    <head><title>Edit Product</title><style>
    body{{font-family:Arial;background:linear-gradient(135deg,#1e3a8a 0%,#2563eb 100%);padding:20px;}}
    .container{{max-width:500px;margin:0 auto;background:white;padding:30px;border-radius:20px;}}
    input,select{{width:100%;padding:10px;margin:10px 0;border:2px solid #e0e0e0;border-radius:5px;}}
    button{{background:#2563eb;color:white;padding:12px;border:none;border-radius:10px;cursor:pointer;width:100%;}}
    </style></head>
    <body><div class="container"><h1>Edit {name}</h1>
    <form method="POST">
    <input type="number" name="price" value="{products[name]['price']}" required>
    <input type="number" name="cost_price" value="{products[name].get('cost_price', products[name]['price'] - 10)}" required>
    <input type="number" name="quantity" value="{products[name]['quantity']}" required min="1">
    <input type="number" name="min_stock" value="{products[name].get('min_stock', 5)}" required>
    <select name="quality"><option {"selected" if products[name]['quality'] == 'low' else ""}>low</option><option {"selected" if products[name]['quality'] == 'medium' else ""}>medium</option><option {"selected" if products[name]['quality'] == 'high' else ""}>high</option><option {"selected" if products[name]['quality'] == 'premium' else ""}>premium</option></select>
    <select name="category"><option {"selected" if products[name]['category'] == 'cooking' else ""}>cooking</option><option {"selected" if products[name]['category'] == 'fruits' else ""}>fruits</option><option {"selected" if products[name]['category'] == 'vegetables' else ""}>vegetables</option><option {"selected" if products[name]['category'] == 'dairy' else ""}>dairy</option><option {"selected" if products[name]['category'] == 'bakery' else ""}>bakery</option><option {"selected" if products[name]['category'] == 'beverages' else ""}>beverages</option><option {"selected" if products[name]['category'] == 'snacks' else ""}>snacks</option><option {"selected" if products[name]['category'] == 'household' else ""}>household</option></select>
    <button type="submit">Update Product</button></form></div></body></html>
    '''
    return render_template_string(edit_form)

@app.route('/delete_product/<name>')
@login_required(role='admin')
def delete_product(name):
    if name in products:
        del products[name]
        save_data()
        flash('Product deleted!', 'success')
    return redirect(url_for('view_products'))

@app.route('/restock/<name>', methods=['POST'])
@login_required()
def restock_product(name):
    if name in products:
        qty = int(request.form['quantity'])
        if qty > 0:
            products[name]["quantity"] += qty
            save_data()
            flash(f'Restocked {qty} units of {name}!', 'success')
        else:
            flash('Quantity must be positive!', 'danger')
    return redirect(request.referrer or url_for('view_products'))

@app.route('/sale', methods=['GET', 'POST'])
@login_required()
def record_sale():
    if request.method == 'POST':
        cart = []
        total = 0
        items = request.form.getlist('cart_items[]')
        quantities = request.form.getlist('quantities[]')
        customer_phone = request.form.get('customer_phone', '')
        customer_name = request.form.get('customer_name', '')
        customer_email = request.form.get('customer_email', '')
        if customer_phone and customer_phone not in customers:
            customers[customer_phone] = {'name': customer_name or 'Unknown', 'email': customer_email or '', 'total_spent': 0, 'visits': 0, 'last_purchase': '', 'registered_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 'registered_ip': get_client_ip()}
        for i, name in enumerate(items):
            if name and name in products:
                qty = int(quantities[i]) if quantities[i] else 0
                if qty > 0 and qty <= products[name]["quantity"]:
                    cost = products[name]["price"] * qty
                    cart.append({'name': name, 'quantity': qty, 'cost': cost})
                    total += cost
                    products[name]["quantity"] -= qty
        if cart:
            daily_sales.append(total)
            transaction_id = f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            transaction = {'id': transaction_id, 'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 'items': cart, 'total': total, 'customer_phone': customer_phone, 'customer_name': customer_name, 'customer_email': customer_email, 'ip_address': get_client_ip()}
            sales_transactions.append(transaction)
            if customer_phone and customer_phone in customers:
                customers[customer_phone]['total_spent'] += total
                customers[customer_phone]['visits'] += 1
                customers[customer_phone]['last_purchase'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_data()
            log_activity(f"Sale: {len(cart)} items, total {total} KES")
            RECEIPT_HTML = '''
            <!DOCTYPE html>
            <html><head><title>Receipt</title><style>
            body{font-family:Arial;background:linear-gradient(135deg,#1e3a8a 0%,#2563eb 100%);display:flex;justify-content:center;align-items:center;min-height:100vh;}
            .receipt{background:white;max-width:500px;padding:30px;border-radius:20px;border-top:5px solid #2563eb;}
            .item{display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #ddd;}
            .total{font-size:24px;font-weight:bold;margin-top:20px;padding-top:20px;border-top:2px solid #2563eb;color:#2563eb;}
            button{background:#2563eb;color:white;padding:10px;border:none;border-radius:10px;cursor:pointer;width:100%;margin-top:10px;}
            </style></head>
            <body><div class="receipt"><div class="company-name" style="text-align:center;font-size:18px;font-weight:bold;">🏪 ISAAC SUPERMARKET</div>
            <h1>🧾 RECEIPT</h1><p>{{ timestamp }}</p>
            {% for item in cart %}<div class="item"><span>{{ item.quantity }} x {{ item.name }}</span><span>{{ item.cost }} KES</span></div>{% endfor %}
            <div class="total">TOTAL: {{ total }} KES</div>
            <button onclick="window.print()">Print Receipt</button>
            <a href="/" style="display:inline-block;margin-top:20px;color:#2563eb;">Back to Dashboard</a>
            </div></body></html>
            '''
            return render_template_string(RECEIPT_HTML, cart=cart, total=total, timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        else:
            flash('No valid items selected or insufficient stock!', 'danger')
    SALE_HTML = '''
    <!DOCTYPE html>
    <html><head><title>Record Sale</title><style>
    body{font-family:Arial;background:linear-gradient(135deg,#1e3a8a 0%,#2563eb 100%);padding:20px;}
    .container{max-width:800px;margin:0 auto;}
    .product-item{background:white;padding:15px;margin-bottom:10px;border-radius:10px;display:flex;justify-content:space-between;}
    .quantity-input{width:80px;padding:5px;}
    button{background:#2563eb;color:white;padding:10px;border:none;border-radius:10px;cursor:pointer;width:100%;margin-top:20px;}
    .customer-input{background:white;padding:20px;border-radius:10px;margin-bottom:20px;}
    input{width:100%;padding:10px;margin:5px 0;}
    </style></head>
    <body><div class="container">
    <div class="customer-input"><h3>👤 Customer Information</h3>
    <input type="text" id="customerPhone" placeholder="Phone Number">
    <input type="text" id="customerName" placeholder="Customer Name">
    <input type="email" id="customerEmail" placeholder="Email Address"></div>
    <form method="POST" id="saleForm">
    <input type="hidden" name="customer_phone" id="customerPhoneInput">
    <input type="hidden" name="customer_name" id="customerNameInput">
    <input type="hidden" name="customer_email" id="customerEmailInput">
    {% for name,details in products.items() %}
    <div class="product-item"><div><strong>{{ name }}</strong><br>{{ details.price }} KES | Stock: {{ details.quantity }}</div>
    <div><input type="number" name="quantities[]" class="quantity-input" placeholder="Qty" min="0" max="{{ details.quantity }}" value="0"><input type="hidden" name="cart_items[]" value="{{ name }}"></div></div>
    {% endfor %}
    <button type="submit">💳 Complete Purchase</button></form>
    </div>
    <script>document.getElementById('saleForm').onsubmit=function(){document.getElementById('customerPhoneInput').value=document.getElementById('customerPhone').value;document.getElementById('customerNameInput').value=document.getElementById('customerName').value;document.getElementById('customerEmailInput').value=document.getElementById('customerEmail').value;};</script>
    </body></html>
    '''
    return render_template_string(SALE_HTML, products=products)

@app.route('/report')
@login_required()
def daily_report():
    if daily_sales:
        stats = {'total_transactions': len(daily_sales), 'total_sales': sum(daily_sales), 'average_sale': sum(daily_sales) / len(daily_sales)}
    else:
        stats = {'total_transactions': 0, 'total_sales': 0, 'average_sale': 0}
    REPORT_HTML = '''
    <!DOCTYPE html>
    <html><head><title>Sales Report</title><style>
    body{font-family:Arial;background:linear-gradient(135deg,#1e3a8a 0%,#2563eb 100%);padding:20px;}
    .stat-card{background:white;padding:20px;border-radius:10px;display:inline-block;width:200px;margin:10px;text-align:center;}
    .transaction{background:white;padding:15px;margin-bottom:10px;border-radius:10px;}
    </style></head>
    <body><div style="max-width:1000px;margin:0 auto;"><h1 style="color:white;">📊 Sales Report</h1>
    <div><div class="stat-card"><h3>Transactions</h3><div style="font-size:2em;color:#2563eb;">{{ stats.total_transactions }}</div></div>
    <div class="stat-card"><h3>Total Sales</h3><div style="font-size:2em;color:#2563eb;">{{ stats.total_sales }} KES</div></div>
    <div class="stat-card"><h3>Average</h3><div style="font-size:2em;color:#2563eb;">{{ "%.2f"|format(stats.average_sale) }} KES</div></div></div>
    {% for trans in transactions|reverse %}<div class="transaction"><strong>{{ trans.timestamp }}</strong><br>{% for item in trans['items'] %}{{ item.quantity }} x {{ item.name }} = {{ item.cost }} KES<br>{% endfor %}<strong>Total: {{ trans.total }} KES</strong></div>{% endfor %}
    </div></body></html>
    '''
    return render_template_string(REPORT_HTML, stats=stats, transactions=sales_transactions)

@app.route('/low_stock')
@login_required()
def low_stock_alert():
    low_stock_items = {name: details for name, details in products.items() if details["quantity"] < details.get("min_stock", 5)}
    LOW_HTML = '''
    <!DOCTYPE html>
    <html><head><title>Low Stock Alert</title><style>
    body{font-family:Arial;background:linear-gradient(135deg,#1e3a8a 0%,#2563eb 100%);padding:20px;}
    .alert-item{background:#fff3cd;border-left:4px solid #dc2626;padding:15px;margin-bottom:15px;border-radius:10px;}
    </style></head>
    <body><h1 style="color:white;">⚠️ Low Stock ({{ low_stock_items|length }})</h1>
    {% if low_stock_items %}{% for name,details in low_stock_items.items() %}
    <div class="alert-item"><h3>{{ name }}</h3><p>Stock: {{ details.quantity }} | Min: {{ details.get('min_stock',5) }}</p>
    <form action="/restock/{{ name }}" method="POST"><input type="number" name="quantity" placeholder="Add qty" required><button type="submit" style="background:#2563eb;color:white;border:none;padding:5px 15px;">Restock</button></form></div>
    {% endfor %}{% else %}<div style="background:white;padding:40px;text-align:center;">✅ All stock levels are healthy!</div>{% endif %}
    </body></html>
    '''
    return render_template_string(LOW_HTML, low_stock_items=low_stock_items)

@app.route('/best_sellers')
@login_required()
def best_sellers():
    sales_count = defaultdict(int)
    for transaction in sales_transactions:
        for item in transaction['items']:
            sales_count[item['name']] += item['quantity']
    best_sellers_list = sorted(sales_count.items(), key=lambda x: x[1], reverse=True)[:10]
    revenue = defaultdict(float)
    for transaction in sales_transactions:
        for item in transaction['items']:
            revenue[item['name']] += item['cost']
    top_revenue = sorted(revenue.items(), key=lambda x: x[1], reverse=True)[:10]
    BEST_HTML = '''
    <!DOCTYPE html>
    <html><head><title>Best Sellers</title><style>
    body{font-family:Arial;background:linear-gradient(135deg,#1e3a8a 0%,#2563eb 100%);padding:20px;}
    .best-seller{background:white;padding:20px;margin-bottom:10px;border-radius:10px;border-left:4px solid #f59e0b;}
    </style></head>
    <body><h1 style="color:white;">🏆 Best Sellers</h1>
    <h2 style="color:white;">📊 By Quantity</h2>
    {% for name,qty in best_sellers %}<div class="best-seller"><strong>{{ name }}</strong> - {{ qty }} units</div>{% endfor %}
    <h2 style="color:white;">💰 By Revenue</h2>
    {% for name,rev in top_revenue %}<div class="best-seller"><strong>{{ name }}</strong> - {{ rev }} KES</div>{% endfor %}
    </body></html>
    '''
    return render_template_string(BEST_HTML, best_sellers=best_sellers_list, top_revenue=top_revenue)

@app.route('/customers')
@login_required()
def view_customers():
    total_revenue = sum(c['total_spent'] for c in customers.values())
    total_visits = sum(c['visits'] for c in customers.values())
    CUST_HTML = '''
    <!DOCTYPE html>
    <html><head><title>Customers</title><style>
    body{font-family:Arial;background:linear-gradient(135deg,#1e3a8a 0%,#2563eb 100%);padding:20px;}
    .customer-card{background:white;padding:20px;margin-bottom:10px;border-radius:10px;border-left:4px solid #2563eb;}
    </style></head>
    <body><h1 style="color:white;">👥 Customers ({{ customers|length }})</h1>
    <div style="background:white;padding:20px;border-radius:10px;margin-bottom:20px;display:flex;justify-content:space-around;">
    <div>💰 Total Revenue: {{ total_revenue }} KES</div><div>🔄 Total Visits: {{ total_visits }}</div></div>
    {% for phone,info in customers.items() %}
    <div class="customer-card"><strong>👤 {{ info.name }}</strong><br>📞 {{ phone }}<br>💰 Spent: {{ info.total_spent }} KES<br>🔄 Visits: {{ info.visits }}<br>📅 Last: {{ info.last_purchase }}</div>
    {% endfor %}</body></html>
    '''
    return render_template_string(CUST_HTML, customers=customers, total_revenue=total_revenue, total_visits=total_visits)

@app.route('/activity')
@login_required(role='admin')
def view_activity():
    ACT_HTML = '''
    <!DOCTYPE html>
    <html><head><title>Activity Log</title><style>
    body{font-family:Arial;background:linear-gradient(135deg,#1e3a8a 0%,#2563eb 100%);padding:20px;}
    .log-entry{background:white;padding:10px;margin-bottom:5px;border-radius:10px;border-left:3px solid #2563eb;}
    </style></head>
    <body><h1 style="color:white;">📋 Activity Log</h1>
    {% for log in activity_log|reverse %}<div class="log-entry"><strong>{{ log.timestamp }}</strong> | 👤 {{ log.user }}: {{ log.action }}<br><span style="color:#666;">🌐 IP: {{ log.get('ip', 'Unknown') }}</span></div>{% endfor %}
    </body></html>
    '''
    return render_template_string(ACT_HTML, activity_log=activity_log[-100:])

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("\n" + "=" * 70)
    print("🏪 ISAAC SUPERMARKET MANAGEMENT SYSTEM")
    print("=" * 70)
    print(f"✅ Loaded {len(products)} products")
    print(f"📊 Total Stock: {get_total_stock()} units")
    print("\n🔐 LOGIN CREDENTIALS:")
    print("   • Admin: username 'admin', password 'admin123'")
    print("\n🌐 SERVER RUNNING AT:")
    print(f"   🔗 http://localhost:{po
    rt}")
    print("=" * 70 + "\n")
    app.run(debug=False, host='0.0.0.0', port=port)