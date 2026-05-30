"""
ISAAC SUPERMARKET COMPANY - Complete Point of Sale & Inventory System
Flask Web Application with Customer Registration and Login
Including Admin Receipt Printing and Purchase Details
"""

import os
import io
import sqlite3
import json
import threading
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
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database with all tables."""
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
        ("FR010", "Watermelon", "Fruits", 400, 40, "https://images.unsplash.com/photo-1563114773-84221bd62daa?w=200",
         "piece", "Sweet red watermelon"),
        ("FR011", "Fresh Pears", "Fruits", 130, 90,
         "https://images.unsplash.com/photo-1514428933627-528f1a259e38?w=200", "kg", "Sweet Bartlett pears"),
        ("FR012", "Plums", "Fruits", 160, 75, "https://images.unsplash.com/photo-1520748487103-dbc553f84c2f?w=200",
         "kg", "Juicy red plums"),
        ("FR013", "Kiwi Fruit", "Fruits", 200, 85, "https://images.unsplash.com/photo-1585059895524-72359e06133a?w=200",
         "kg", "Zespri kiwis"),
        ("FR014", "Papaya", "Fruits", 180, 55, "https://images.unsplash.com/photo-1517282009859-a000a0f9d559?w=200",
         "piece", "Ripe papaya"),
        ("FR015", "Dragon Fruit", "Fruits", 350, 45,
         "https://images.unsplash.com/photo-1527325678964-54921661f888?w=200", "piece", "White flesh dragon fruit"),
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
        ("VG009", "Cauliflower", "Vegetables", 130, 85,
         "https://images.unsplash.com/photo-1568584711075-3d021a7c3ca3?w=200", "piece", "White cauliflower"),
        ("VG010", "Zucchini", "Vegetables", 110, 95,
         "https://images.unsplash.com/photo-1587280501635-68a0e82cd5ff?w=200", "kg", "Fresh zucchini"),
        ("VG011", "Cabbage", "Vegetables", 55, 150,
         "https://images.unsplash.com/photo-1568584711075-3d021a7c3ca3?w=200", "piece", "Green cabbage"),
        ("VG012", "Garlic", "Vegetables", 200, 120,
         "https://images.unsplash.com/photo-1540148426945-6cf22a6b2383?w=200", "kg", "Fresh garlic bulbs"),
        ("VG013", "Ginger", "Vegetables", 180, 100,
         "https://images.unsplash.com/photo-1589032191511-8d529e1a6d1c?w=200", "kg", "Fresh ginger root"),
        ("VG014", "Celery", "Vegetables", 90, 80, "https://images.unsplash.com/photo-1589032191511-8d529e1a6d1c?w=200",
         "bunch", "Crisp celery stalks"),
        ("VG015", "Lettuce", "Vegetables", 85, 70, "https://images.unsplash.com/photo-1568584711075-3d021a7c3ca3?w=200",
         "piece", "Iceberg lettuce"),
        ("DY001", "Fresh Milk 1L", "Dairy", 110, 120, "https://images.unsplash.com/photo-1563636619-e9143da7973b?w=200",
         "pack", "Pasteurized whole milk"),
        ("DY002", "Greek Yogurt", "Dairy", 180, 90,
         "https://images.unsplash.com/photo-1488477181946-6428a0291777?w=200", "cup", "Strained yogurt"),
        ("DY003", "Cheddar Cheese", "Dairy", 350, 70,
         "https://images.unsplash.com/photo-1615937657715-bc7b4b7962c1?w=200", "kg", "Aged cheddar"),
        ("DY004", "Butter 250g", "Dairy", 220, 100,
         "https://images.unsplash.com/photo-1589985270826-4b7bb135bc9d?w=200", "pack", "Salted butter"),
        ("DY005", "Free-Range Eggs", "Dairy", 250, 150,
         "https://images.unsplash.com/photo-1498654077810-12c21d4d6dc3?w=200", "tray", "Pack of 6"),
        ("DY006", "Cream Cheese", "Dairy", 200, 80,
         "https://images.unsplash.com/photo-1626808642875-0aa61e6374c7?w=200", "pack", "Spreadable"),
        ("DY007", "Parmesan Cheese", "Dairy", 400, 50,
         "https://images.unsplash.com/photo-1615937657715-bc7b4b7962c1?w=200", "kg", "Grated parmesan"),
        ("DY008", "Sour Cream", "Dairy", 150, 75, "https://images.unsplash.com/photo-1626808642875-0aa61e6374c7?w=200",
         "cup", "Cultured sour cream"),
        ("DY009", "Cottage Cheese", "Dairy", 230, 60,
         "https://images.unsplash.com/photo-1626808642875-0aa61e6374c7?w=200", "pack", "Low fat"),
        ("DY010", "Almond Milk", "Dairy", 280, 45, "https://images.unsplash.com/photo-1563636619-e9143da7973b?w=200",
         "pack", "Unsweetened"),
        ("DY011", "Condensed Milk", "Dairy", 190, 110,
         "https://images.unsplash.com/photo-1563636619-e9143da7973b?w=200", "tin", "Sweetened"),
        ("DY012", "Whipping Cream", "Dairy", 240, 55,
         "https://images.unsplash.com/photo-1626808642875-0aa61e6374c7?w=200", "pack", "Heavy cream"),
        ("MT001", "Chicken Breast", "Meat", 550, 100,
         "https://images.unsplash.com/photo-1604503468506-a8da13d82791?w=200", "kg", "Boneless skinless"),
        ("MT002", "Ground Beef", "Meat", 600, 90, "https://images.unsplash.com/photo-1588168333986-5078d3ae3976?w=200",
         "kg", "Lean 85/15"),
        ("MT003", "Pork Chops", "Meat", 500, 80, "https://images.unsplash.com/photo-1604503468506-a8da13d82791?w=200",
         "kg", "Center cut"),
        ("MT004", "Salmon Fillet", "Seafood", 1200, 40,
         "https://images.unsplash.com/photo-1594787318286-3d835c1d207f?w=200", "kg", "Atlantic salmon"),
        ("MT005", "Shrimp", "Seafood", 900, 60, "https://images.unsplash.com/photo-1565680018433-b513d5e5c6f7?w=200",
         "kg", "Raw peeled"),
        ("MT006", "Beef Steak", "Meat", 1100, 50, "https://images.unsplash.com/photo-1604503468506-a8da13d82791?w=200",
         "kg", "Ribeye"),
        ("MT007", "Turkey Breast", "Meat", 480, 45,
         "https://images.unsplash.com/photo-1604503468506-a8da13d82791?w=200", "kg", "Sliced"),
        ("MT008", "Lamb Chops", "Meat", 1300, 30, "https://images.unsplash.com/photo-1604503468506-a8da13d82791?w=200",
         "kg", "Premium cuts"),
        ("MT009", "Tuna Steak", "Seafood", 1000, 35,
         "https://images.unsplash.com/photo-1594787318286-3d835c1d207f?w=200", "kg", "Yellowfin"),
        ("MT010", "Bacon", "Meat", 450, 110, "https://images.unsplash.com/photo-1588168333986-5078d3ae3976?w=200",
         "pack", "Smoked bacon"),
        ("MT011", "Sausages", "Meat", 380, 120, "https://images.unsplash.com/photo-1588168333986-5078d3ae3976?w=200",
         "pack", "Italian style"),
        ("MT012", "Chicken Thighs", "Meat", 420, 95,
         "https://images.unsplash.com/photo-1604503468506-a8da13d82791?w=200", "kg", "Bone-in"),
        ("PA001", "White Rice 2kg", "Pantry", 300, 200,
         "https://images.unsplash.com/photo-1586201375761-83865001e8ac?w=200", "pack", "Premium long grain"),
        ("PA002", "Pasta Spaghetti", "Pantry", 150, 180,
         "https://images.unsplash.com/photo-1551462147-37885b3edd6d?w=200", "pack", "Italian pasta"),
        ("PA003", "Olive Oil", "Pantry", 600, 70, "https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?w=200",
         "bottle", "Extra virgin"),
        ("PA004", "Tomato Ketchup", "Pantry", 220, 130,
         "https://images.unsplash.com/photo-1589924691995-400dc9ecc119?w=200", "bottle", "Tomato ketchup"),
        ("PA005", "Mayonnaise", "Pantry", 250, 120,
         "https://images.unsplash.com/photo-1589924691995-400dc9ecc119?w=200", "jar", "Creamy"),
        ("PA006", "Peanut Butter", "Pantry", 300, 100,
         "https://images.unsplash.com/photo-1590779033100-9f60a05a013d?w=200", "jar", "Smooth"),
        ("PA007", "Strawberry Jam", "Pantry", 280, 90,
         "https://images.unsplash.com/photo-1590779033100-9f60a05a013d?w=200", "jar", "Fruit spread"),
        ("PA008", "Raw Honey", "Pantry", 450, 60, "https://images.unsplash.com/photo-1587049352847-4a222e784d38?w=200",
         "jar", "Pure honey"),
        ("PA009", "Canned Beans", "Pantry", 120, 150,
         "https://images.unsplash.com/photo-1586201375761-83865001e8ac?w=200", "tin", "Kidney beans"),
        ("PA010", "Tomato Sauce", "Pantry", 100, 170,
         "https://images.unsplash.com/photo-1589924691995-400dc9ecc119?w=200", "tin", "400g can"),
        ("PA011", "Corn Flakes", "Snacks", 350, 110,
         "https://images.unsplash.com/photo-1599490656163-0a6e0b5cc7af?w=200", "box", "Breakfast cereal"),
        ("PA012", "Potato Chips", "Snacks", 180, 200,
         "https://images.unsplash.com/photo-1566478989037-eec170784d0b?w=200", "pack", "Salted"),
        ("PA013", "Chocolate Bar", "Snacks", 120, 250,
         "https://images.unsplash.com/photo-1548907040-4baa42d10919?w=200", "piece", "Milk chocolate"),
        ("PA014", "Chocolate Chip Cookies", "Snacks", 250, 130,
         "https://images.unsplash.com/photo-1499636136210-6f4ee915583e?w=200", "pack", "Fresh baked"),
        ("PA015", "Vanilla Ice Cream", "Snacks", 400, 80,
         "https://images.unsplash.com/photo-1501443762994-82bd5dace89a?w=200", "tub", "Premium vanilla"),
        ("BV001", "Cola Soda 2L", "Beverages", 180, 150,
         "https://images.unsplash.com/photo-1629203851122-3726ecdf080e?w=200", "bottle", "Chilled"),
        ("BV002", "Orange Juice", "Beverages", 300, 90,
         "https://images.unsplash.com/photo-1600271886742-f049cd451bba?w=200", "pack", "Fresh squeezed"),
        ("BV003", "Mineral Water", "Beverages", 80, 250,
         "https://images.unsplash.com/photo-1616118132534-38157a1c297a?w=200", "bottle", "Sparkling"),
        ("BV004", "Energy Drink", "Beverages", 220, 100,
         "https://images.unsplash.com/photo-1616118132534-38157a1c297a?w=200", "can", "Caffeinated"),
        ("BV005", "Coconut Water", "Beverages", 250, 80,
         "https://images.unsplash.com/photo-1600271886742-f049cd451bba?w=200", "pack", "100% natural"),
        ("BV006", "Apple Juice", "Beverages", 280, 75,
         "https://images.unsplash.com/photo-1600271886742-f049cd451bba?w=200", "pack", "Clear apple"),
        ("BV007", "Iced Tea", "Beverages", 150, 120,
         "https://images.unsplash.com/photo-1629203851122-3726ecdf080e?w=200", "bottle", "Lemon flavored"),
        ("BV008", "Coffee Grounds", "Beverages", 450, 60,
         "https://images.unsplash.com/photo-1442512595331-e89e73853f31?w=200", "pack", "Medium roast"),
        ("BV009", "Black Tea", "Beverages", 200, 90,
         "https://images.unsplash.com/photo-1442512595331-e89e73853f31?w=200", "pack", "Ceylon tea"),
        ("BV010", "Hot Chocolate", "Beverages", 350, 55,
         "https://images.unsplash.com/photo-1442512595331-e89e73853f31?w=200", "jar", "Rich cocoa"),
        ("HH001", "Toilet Paper", "Household", 500, 120,
         "https://images.unsplash.com/photo-1585680878066-6cacb2d7d0fe?w=200", "pack", "12 rolls"),
        ("HH002", "Laundry Detergent", "Household", 700, 80,
         "https://images.unsplash.com/photo-1604335877083-6c0d0e5e8af9?w=200", "bottle", "Liquid"),
        ("HH003", "Dish Soap", "Household", 200, 150,
         "https://images.unsplash.com/photo-1604335877083-6c0d0e5e8af9?w=200", "bottle", "Lemon scent"),
        ("HH004", "Paper Towels", "Household", 350, 100,
         "https://images.unsplash.com/photo-1585680878066-6cacb2d7d0fe?w=200", "roll", "2-ply"),
        ("HH005", "Trash Bags", "Household", 280, 110,
         "https://images.unsplash.com/photo-1604335877083-6c0d0e5e8af9?w=200", "box", "Drawstring"),
        ("HH006", "Scrub Sponges", "Household", 150, 130,
         "https://images.unsplash.com/photo-1604335877083-6c0d0e5e8af9?w=200", "pack", "Durable"),
        ("HH007", "Hand Soap", "Household", 180, 140,
         "https://images.unsplash.com/photo-1604335877083-6c0d0e5e8af9?w=200", "bottle", "Antibacterial"),
        ("HH008", "All-Purpose Cleaner", "Household", 320, 95,
         "https://images.unsplash.com/photo-1604335877083-6c0d0e5e8af9?w=200", "bottle", "Spray"),
        ("PC001", "Moisturizing Shampoo", "Personal Care", 400, 90,
         "https://images.unsplash.com/photo-1556228578-8c89e6adf883?w=200", "bottle", "For dry hair"),
        ("PC002", "Whitening Toothpaste", "Personal Care", 250, 120,
         "https://images.unsplash.com/photo-1556228578-8c89e6adf883?w=200", "tube", "With fluoride"),
        ("PC003", "Shea Butter Lotion", "Personal Care", 350, 80,
         "https://images.unsplash.com/photo-1556228578-8c89e6adf883?w=200", "bottle", "Moisturizing"),
        ("PC004", "Bar Soap", "Personal Care", 80, 200,
         "https://images.unsplash.com/photo-1556228578-8c89e6adf883?w=200", "piece", "Gentle cleansing"),
    ]

    with get_db() as db:
        for p in products:
            db.execute('''INSERT
            OR IGNORE INTO products 
                       (sku, name, category, price, stock, image_url, unit, description)
                       VALUES (?,?,?,?,?,?,?,?)''', p)
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


def add_product(sku, name, category, price, stock, image_url, unit, description=""):
    with get_db() as db:
        db.execute('''INSERT INTO products (sku, name, category, price, stock, image_url, unit, description)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                   (sku, name, category, price, stock, image_url, unit, description))
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
        db.execute('''INSERT INTO sales
                      (receipt_no, customer_id, customer_name, customer_phone, items, subtotal, tax, total,
                       payment_method, mpesa_code, loyalty_points_used, loyalty_points_earned)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                   (receipt_no, customer_id, customer_name, customer_phone, items_json, subtotal, tax, total,
                    payment_method, mpesa_code, loyalty_points_used, loyalty_points_earned))

        if customer_id:
            db.execute('''UPDATE customers
                          SET total_purchases = total_purchases + ?,
                              loyalty_points  = loyalty_points - ? + ?
                          WHERE id = ?''',
                       (total, loyalty_points_used, loyalty_points_earned, customer_id))

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
                             ORDER BY created_at DESC''',
                          (date_str,)).fetchall()
        total = db.execute('''SELECT COALESCE(SUM(total), 0)
                              FROM sales
                              WHERE DATE (created_at) = ?''',
                           (date_str,)).fetchone()[0]
        return [dict(row) for row in rows], total


def sales_summary(days=14):
    with get_db() as db:
        rows = db.execute('''SELECT DATE (created_at) as d, COUNT (*) as n, SUM (total) as t
                             FROM sales
                             WHERE created_at >= date ('now', ?)
                             GROUP BY DATE (created_at)
                             ORDER BY d DESC''',
                          (f'-{days} days',)).fetchall()
        return [dict(row) for row in rows]


def get_customer_by_email(email):
    with get_db() as db:
        return db.execute('SELECT * FROM customers WHERE email = ?', (email,)).fetchone()


def register_customer(full_name, email, phone, password, address="", city=""):
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    with get_db() as db:
        try:
            db.execute('''INSERT INTO customers (full_name, email, phone, password, address, city)
                          VALUES (?, ?, ?, ?, ?, ?)''',
                       (full_name, email, phone, hashed_password, address, city))
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
# RECEIPT MODULE
# ============================================================

def format_text_receipt(receipt_no, customer_name, customer_phone, items, total, payment_method, mpesa_code,
                        loyalty_points_earned=0, loyalty_points_used=0):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    subtotal = sum(i["qty"] * i["unit_price"] for i in items)
    tax = subtotal * 0.08

    lines = [
        "=" * 52,
        "              ISAAC SUPERMARKET",
        "          Quality & Freshness Guaranteed",
        "        Nairobi, Kenya | Tel: +254 700 000000",
        "=" * 52,
        f"Receipt No: {receipt_no}",
        f"Date: {now}",
        f"Customer: {customer_name or 'Walk-in Customer'}",
        f"Phone: {customer_phone or 'N/A'}",
        "-" * 52,
        f"{'Item':<28} {'Qty':>5} {'Price':>9} {'Total':>9}",
        "-" * 52,
    ]
    for item in items:
        total_item = item["qty"] * item["unit_price"]
        lines.append(f"{item['name'][:27]:<28} {item['qty']:>5} {item['unit_price']:>9,.0f} {total_item:>9,.0f}")

    lines.extend([
        "-" * 52,
        f"{'Subtotal:':>42} {subtotal:>9,.2f}",
        f"{'Tax (8% VAT):':>42} {tax:>9,.2f}",
        "-" * 52,
        f"{'TOTAL:':>42} {total:>9,.2f}",
        "-" * 52,
        f"Payment Method: {payment_method}",
        f"M-Pesa Code: {mpesa_code or 'N/A'}",
    ])

    if loyalty_points_used > 0:
        lines.append(f"Loyalty Points Used: {loyalty_points_used}")
    if loyalty_points_earned > 0:
        lines.append(f"Loyalty Points Earned: {loyalty_points_earned}")

    lines.extend([
        "=" * 52,
        "     ✅ PRODUCTS PURCHASED SUCCESSFULLY!",
        "        Thank you for shopping with us!",
        "           Visit again soon.",
        "=" * 52,
    ])
    return "\n".join(lines)


def save_receipt_pdf(receipt_no, customer_name, customer_phone, items, total, payment_method, mpesa_code,
                     loyalty_points_earned=0):
    filename = f"receipt_{receipt_no}.pdf"
    doc = SimpleDocTemplate(filename, pagesize=A4, rightMargin=20 * mm, leftMargin=20 * mm, topMargin=20 * mm,
                            bottomMargin=20 * mm)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('TitleStyle', parent=styles['Title'], fontSize=14, alignment=1,
                                 textColor=colors.darkgreen)
    normal_style = ParagraphStyle('NormalStyle', parent=styles['Normal'], fontSize=10)

    story = []
    story.append(Paragraph("ISAAC SUPERMARKET", title_style))
    story.append(Paragraph("Quality & Freshness Guaranteed", normal_style))
    story.append(Spacer(1, 10))

    info = [
        [f"Receipt No: {receipt_no}", f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"],
        [f"Customer: {customer_name or 'Walk-in Customer'}", f"Phone: {customer_phone or 'N/A'}"],
    ]
    info_table = Table(info, colWidths=[220, 220])
    info_table.setStyle(TableStyle([('FONTNAME', (0, 0), (-1, -1), 'Helvetica'), ('FONTSIZE', (0, 0), (-1, -1), 10)]))
    story.append(info_table)
    story.append(Spacer(1, 10))

    data = [["Item", "Qty", "Unit Price", "Total"]]
    subtotal = 0
    for item in items:
        item_total = item["qty"] * item["unit_price"]
        subtotal += item_total
        data.append([item["name"][:30], str(item["qty"]), f"KES {item['unit_price']:,.2f}", f"KES {item_total:,.2f}"])

    tax = subtotal * 0.08
    final_total = subtotal + tax

    item_table = Table(data, colWidths=[220, 50, 80, 80])
    item_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -2), 0.5, colors.grey),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
    ]))
    story.append(item_table)
    story.append(Spacer(1, 10))

    totals_data = [
        ["Subtotal:", f"KES {subtotal:,.2f}"],
        ["Tax (8% VAT):", f"KES {tax:,.2f}"],
        ["TOTAL:", f"KES {final_total:,.2f}"],
        ["Payment:", payment_method],
        ["M-Pesa Code:", mpesa_code or "N/A"],
        ["Loyalty Points Earned:", str(loyalty_points_earned)],
    ]
    totals_table = Table(totals_data, colWidths=[150, 150])
    totals_table.setStyle(TableStyle([('FONTNAME', (0, 0), (-1, -1), 'Helvetica'), ('FONTSIZE', (0, 0), (-1, -1), 11)]))
    story.append(totals_table)
    story.append(Spacer(1, 20))
    story.append(Paragraph("✅ PRODUCTS PURCHASED SUCCESSFULLY!", normal_style))
    story.append(Paragraph("Thank you for shopping with us!", normal_style))

    doc.build(story)
    return filename


def save_invoice_pdf(receipt_no, customer_name, customer_phone, items, total, mpesa_code, status):
    filename = f"invoice_{receipt_no}.pdf"
    doc = SimpleDocTemplate(filename, pagesize=A4)
    styles = getSampleStyleSheet()

    story = []
    story.append(Paragraph("TAX INVOICE", styles['Title']))
    story.append(Paragraph(f"Invoice No: {receipt_no}", styles['Normal']))
    story.append(Paragraph(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    story.append(Paragraph(f"Customer: {customer_name or 'Walk-in Customer'}", styles['Normal']))
    story.append(Spacer(1, 10))

    data = [["Description", "Quantity", "Unit Price (KES)", "Total (KES)"]]
    for item in items:
        data.append(
            [item["name"], str(item["qty"]), f"{item['unit_price']:,.2f}", f"{item['qty'] * item['unit_price']:,.2f}"])

    table = Table(data)
    table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                               ('GRID', (0, 0), (-1, -1), 0.5, colors.black)]))
    story.append(table)
    story.append(Spacer(1, 10))
    story.append(Paragraph(f"Total Amount: KES {total:,.2f}", styles['Normal']))
    story.append(Paragraph(f"Payment Status: {status}", styles['Normal']))
    story.append(Paragraph(f"M-Pesa Transaction: {mpesa_code or 'Pending'}", styles['Normal']))

    doc.build(story)
    return filename


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
                session['role'] = 'admin'
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
        address = request.form.get('address', '')
        city = request.form.get('city', '')

        if not full_name or not email or not phone or not password:
            return render_template('customer_register.html', error='All fields are required')
        if password != confirm_password:
            return render_template('customer_register.html', error='Passwords do not match')
        if len(password) < 6:
            return render_template('customer_register.html', error='Password must be at least 6 characters')
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            return render_template('customer_register.html', error='Invalid email format')

        if register_customer(full_name, email, phone, password, address, city):
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
    return render_template('pos.html',
                           customer_name=session.get('customer_name'),
                           customer_id=session.get('customer_id'),
                           loyalty_points=session.get('customer_points', 0))


@app.route('/receipts')
@login_required
def receipts():
    return render_template('receipts.html', username=session.get('admin_username'),
                           today=datetime.now().strftime('%Y-%m-%d'))


@app.route('/change-password', methods=['GET', 'POST'])
def change_password():
    """Change password for both admin and customers."""
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
                    db.execute('UPDATE admin_users SET password = ? WHERE id = ?',
                               (hashed_new, session['admin_id']))
                    db.commit()
                    return render_template('change_password.html', success='Password changed successfully!')
                else:
                    return render_template('change_password.html', error='Current password is incorrect')

        elif 'customer_id' in session:
            with get_db() as db:
                customer = db.execute('SELECT * FROM customers WHERE id = ? AND password = ?',
                                      (session['customer_id'], hashed_current)).fetchone()
                if customer:
                    db.execute('UPDATE customers SET password = ? WHERE id = ?',
                               (hashed_new, session['customer_id']))
                    db.commit()
                    return render_template('change_password.html', success='Password changed successfully!')
                else:
                    return render_template('change_password.html', error='Current password is incorrect')
        else:
            return redirect(url_for('index'))

    return render_template('change_password.html')


@app.route('/api/customer/profile')
@customer_login_required
def api_customer_profile():
    customer = get_customer_by_id(session['customer_id'])
    return jsonify(customer)


@app.route('/api/products')
def api_products():
    search = request.args.get('search', '')
    category = request.args.get('category', 'All')
    products = list_products(search, category)
    return jsonify(products)


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
                              ORDER BY created_at DESC''',
                           (date,)).fetchall()
        return jsonify({'sales': [dict(s) for s in sales]})


@app.route('/api/sales_summary')
def api_sales_summary():
    days = int(request.args.get('days', 14))
    summary = sales_summary(days)
    return jsonify(summary)


@app.route('/api/inventory')
def api_inventory():
    products = list_products()
    return jsonify(products)


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
        use_loyalty_points = data.get('use_loyalty_points', False)

        customer_id = session.get('customer_id')
        customer = get_customer_by_id(customer_id)

        if not cart:
            return jsonify({'success': False, 'error': 'Cart is empty'}), 400

        subtotal = sum(item["qty"] * item["unit_price"] for item in cart)
        tax = subtotal * 0.08
        total_before_discount = subtotal + tax

        loyalty_points_used = 0
        discount = 0
        if use_loyalty_points and customer and customer['loyalty_points'] > 0:
            max_discount = total_before_discount * 0.20
            points_value = customer['loyalty_points']
            discount = min(points_value, max_discount, total_before_discount)
            loyalty_points_used = int(discount)
            final_total = total_before_discount - discount
        else:
            final_total = total_before_discount

        with get_db() as db:
            for item in cart:
                product = db.execute('SELECT stock, name FROM products WHERE id = ?',
                                     (item['product_id'],)).fetchone()
                if not product:
                    return jsonify({'success': False, 'error': f"Product {item['name']} not found"}), 400
                if product['stock'] < item['qty']:
                    return jsonify({'success': False,
                                    'error': f"Insufficient stock for {item['name']}. Available: {product['stock']}"}), 400

        receipt_no, saved_total, points_earned = save_sale(
            customer_id,
            customer['full_name'] if customer else '',
            customer['phone'] if customer else '',
            cart, payment_method, mpesa_code, loyalty_points_used
        )

        if customer:
            new_points = customer['loyalty_points'] - loyalty_points_used + points_earned
            session['customer_points'] = new_points

        return jsonify({
            'success': True,
            'message': '✅ Products Purchased Successfully!',
            'receipt_no': receipt_no,
            'subtotal': subtotal,
            'tax': tax,
            'discount': discount,
            'total': final_total,
            'points_used': loyalty_points_used,
            'points_earned': points_earned,
            'new_points_balance': session.get('customer_points', 0),
            'payment_method': payment_method,
            'mpesa_code': mpesa_code,
            'items': cart,
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
    product_id = data.get('product_id')
    quantity = data.get('quantity', 0)
    if not product_id:
        return jsonify({'error': 'Product ID required'}), 400
    update_stock(product_id, quantity)
    return jsonify({'success': True})


@app.route('/api/add_product', methods=['POST'])
@login_required
def api_add_product():
    data = request.json
    try:
        add_product(
            data.get('sku'), data.get('name'), data.get('category'),
            float(data.get('price', 0)), int(data.get('stock', 0)),
            data.get('image_url', ''), data.get('unit', 'pcs'),
            data.get('description', '')
        )
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/download/<filename>')
def download_file(filename):
    if os.path.exists(filename):
        return send_file(filename, as_attachment=True)
    return jsonify({'error': 'File not found'}), 404


@app.route('/inventory')
@login_required
def inventory():
    return render_template('inventory.html', username=session.get('admin_username'))


@app.route('/sales')
@login_required
def sales():
    return render_template('sales.html', username=session.get('admin_username'))


@app.route('/reports')
@login_required
def reports():
    return render_template('reports.html', username=session.get('admin_username'))


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
        f.write('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ISAAC SUPERMARKET - Welcome</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;background:linear-gradient(135deg,#0B6E4F 0%,#085239 100%);min-height:100vh}
        .container{max-width:1200px;margin:0 auto;padding:40px 20px}
        .header{text-align:center;color:white;margin-bottom:60px}
        .header h1{font-size:48px;margin-bottom:10px}
        .header p{font-size:20px;opacity:0.9}
        .options{display:flex;justify-content:center;gap:30px;flex-wrap:wrap}
        .card{background:white;border-radius:20px;padding:40px;width:350px;text-align:center;transition:transform 0.3s,box-shadow 0.3s;cursor:pointer}
        .card:hover{transform:translateY(-10px);box-shadow:0 20px 40px rgba(0,0,0,0.2)}
        .card-icon{font-size:64px;margin-bottom:20px}
        .card h2{color:#0B6E4F;margin-bottom:15px}
        .card p{color:#6B7280;margin-bottom:25px}
        .btn{display:inline-block;padding:12px 30px;border-radius:25px;text-decoration:none;font-weight:bold;transition:all 0.3s}
        .btn-primary{background:#0B6E4F;color:white}.btn-primary:hover{background:#085239}
        .btn-secondary{background:#F1C40F;color:#1F2937}.btn-secondary:hover{background:#D4AC0D}
        .footer{text-align:center;color:white;margin-top:60px;opacity:0.8}
    </style>
</head>
<body>
    <div class="container">
        <div class="header"><h1>Shopping Cart ISAAC SUPERMARKET</h1><p>Quality * Value * Service</p></div>
        <div class="options">
            <div class="card"><div class="card-icon">👤</div><h2>Customer Login</h2><p>Already have an account? Login to start shopping and earn loyalty points!</p><a href="/customer-login" class="btn btn-primary">Login as Customer</a></div>
            <div class="card"><div class="card-icon">📝</div><h2>Register Account</h2><p>New customer? Create an account to enjoy loyalty points and track your orders.</p><a href="/customer-register" class="btn btn-secondary">Register Now</a></div>
            <div class="card"><div class="card-icon">🔐</div><h2>Admin Login</h2><p>For store administrators only. Manage inventory, view sales, and generate reports.</p><a href="/admin-login" class="btn btn-primary">Admin Access</a></div>
        </div>
        <div class="footer"><p>&copy; 2024 ISAAC SUPERMARKET. All rights reserved.</p></div>
    </div>
</body>
</html>''')

    with open('templates/admin_login.html', 'w', encoding='utf-8') as f:
        f.write('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Login - ISAAC SUPERMARKET</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;background:linear-gradient(135deg,#0B6E4F 0%,#085239 100%);height:100vh;display:flex;align-items:center;justify-content:center}
        .login-container{background:white;border-radius:20px;box-shadow:0 20px 40px rgba(0,0,0,0.2);width:400px;padding:40px}
        .logo{text-align:center;margin-bottom:30px}.logo h1{color:#0B6E4F;font-size:28px}.logo p{color:#6B7280;font-size:14px}
        .form-group{margin-bottom:20px}label{display:block;margin-bottom:8px;color:#1F2937;font-weight:500}
        input{width:100%;padding:12px;border:1px solid #E5E7EB;border-radius:10px;font-size:14px;transition:all 0.3s}
        input:focus{outline:none;border-color:#0B6E4F;box-shadow:0 0 0 3px rgba(11,110,79,0.1)}
        button{width:100%;padding:12px;background:#0B6E4F;color:white;border:none;border-radius:10px;font-size:16px;font-weight:bold;cursor:pointer;transition:background 0.3s}
        button:hover{background:#085239}
        .error{background:#FEE2E2;color:#DC2626;padding:10px;border-radius:8px;margin-bottom:20px;font-size:14px;text-align:center}
        .back-link{display:block;text-align:center;margin-top:20px;color:#6B7280;text-decoration:none}.back-link:hover{color:#0B6E4F}
    </style>
</head>
<body>
    <div class="login-container">
        <div class="logo"><h1>Admin Portal</h1><p>ISAAC SUPERMARKET Management System</p></div>
        {% if error %}<div class="error">{{ error }}</div>{% endif %}
        <form method="POST">
            <div class="form-group"><label>Username</label><input type="text" name="username" required autofocus></div>
            <div class="form-group"><label>Password</label><input type="password" name="password" required></div>
            <button type="submit">Login as Admin</button>
        </form>
        <a href="/" class="back-link">← Back to Home</a>
        <p style="text-align:center;margin-top:15px;font-size:12px;color:#6B7280;">Demo: admin / admin123</p>
    </div>
</body>
</html>''')

    with open('templates/customer_login.html', 'w', encoding='utf-8') as f:
        f.write('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Customer Login - ISAAC SUPERMARKET</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;background:linear-gradient(135deg,#0B6E4F 0%,#085239 100%);height:100vh;display:flex;align-items:center;justify-content:center}
        .login-container{background:white;border-radius:20px;box-shadow:0 20px 40px rgba(0,0,0,0.2);width:400px;padding:40px}
        .logo{text-align:center;margin-bottom:30px}.logo h1{color:#0B6E4F;font-size:28px}.logo p{color:#6B7280;font-size:14px}
        .form-group{margin-bottom:20px}label{display:block;margin-bottom:8px;color:#1F2937;font-weight:500}
        input{width:100%;padding:12px;border:1px solid #E5E7EB;border-radius:10px;font-size:14px;transition:all 0.3s}
        input:focus{outline:none;border-color:#0B6E4F;box-shadow:0 0 0 3px rgba(11,110,79,0.1)}
        button{width:100%;padding:12px;background:#0B6E4F;color:white;border:none;border-radius:10px;font-size:16px;font-weight:bold;cursor:pointer;transition:background 0.3s}
        button:hover{background:#085239}
        .error{background:#FEE2E2;color:#DC2626;padding:10px;border-radius:8px;margin-bottom:20px;font-size:14px;text-align:center}
        .back-link{display:block;text-align:center;margin-top:20px;color:#6B7280;text-decoration:none}.back-link:hover{color:#0B6E4F}
        .register-link{text-align:center;margin-top:15px;font-size:14px}.register-link a{color:#0B6E4F;text-decoration:none;font-weight:bold}
    </style>
</head>
<body>
    <div class="login-container">
        <div class="logo"><h1>Customer Login</h1><p>Welcome back! Login to continue shopping</p></div>
        {% if error %}<div class="error">{{ error }}</div>{% endif %}
        <form method="POST">
            <div class="form-group"><label>Email Address</label><input type="email" name="email" required autofocus></div>
            <div class="form-group"><label>Password</label><input type="password" name="password" required></div>
            <button type="submit">Login</button>
        </form>
        <div class="register-link">Don't have an account? <a href="/customer-register">Register here</a></div>
        <a href="/" class="back-link">← Back to Home</a>
    </div>
</body>
</html>''')

    with open('templates/customer_register.html', 'w', encoding='utf-8') as f:
        f.write('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Register - ISAAC SUPERMARKET</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;background:linear-gradient(135deg,#0B6E4F 0%,#085239 100%);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:40px 20px}
        .register-container{background:white;border-radius:20px;box-shadow:0 20px 40px rgba(0,0,0,0.2);width:500px;padding:40px}
        .logo{text-align:center;margin-bottom:30px}.logo h1{color:#0B6E4F;font-size:28px}.logo p{color:#6B7280;font-size:14px}
        .form-group{margin-bottom:15px}label{display:block;margin-bottom:5px;color:#1F2937;font-weight:500;font-size:14px}
        input,textarea{width:100%;padding:10px;border:1px solid #E5E7EB;border-radius:8px;font-size:14px;transition:all 0.3s}
        input:focus,textarea:focus{outline:none;border-color:#0B6E4F;box-shadow:0 0 0 3px rgba(11,110,79,0.1)}
        textarea{resize:vertical;min-height:60px}
        button{width:100%;padding:12px;background:#0B6E4F;color:white;border:none;border-radius:10px;font-size:16px;font-weight:bold;cursor:pointer;transition:background 0.3s;margin-top:10px}
        button:hover{background:#085239}
        .error{background:#FEE2E2;color:#DC2626;padding:10px;border-radius:8px;margin-bottom:20px;font-size:14px;text-align:center}
        .back-link{display:block;text-align:center;margin-top:20px;color:#6B7280;text-decoration:none}.back-link:hover{color:#0B6E4F}
        .row{display:flex;gap:15px}.row .form-group{flex:1}
    </style>
</head>
<body>
    <div class="register-container">
        <div class="logo"><h1>Create Account</h1><p>Join ISAAC SUPERMARKET and earn loyalty points!</p></div>
        {% if error %}<div class="error">{{ error }}</div>{% endif %}
        <form method="POST">
            <div class="form-group"><label>Full Name *</label><input type="text" name="full_name" required></div>
            <div class="form-group"><label>Email Address *</label><input type="email" name="email" required></div>
            <div class="form-group"><label>Phone Number *</label><input type="tel" name="phone" required></div>
            <div class="row">
                <div class="form-group"><label>Password *</label><input type="password" name="password" required minlength="6"></div>
                <div class="form-group"><label>Confirm Password *</label><input type="password" name="confirm_password" required></div>
            </div>
            <div class="form-group"><label>Address</label><textarea name="address" rows="2"></textarea></div>
            <div class="form-group"><label>City</label><input type="text" name="city"></div>
            <button type="submit">Register Account</button>
        </form>
        <div style="text-align:center;margin-top:15px;font-size:14px;">Already have an account? <a href="/customer-login" style="color:#0B6E4F;">Login here</a></div>
        <a href="/" class="back-link">← Back to Home</a>
    </div>
</body>
</html>''')

    with open('templates/admin_base.html', 'w', encoding='utf-8') as f:
        f.write('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ISAAC SUPERMARKET - {% block title %}Admin Panel{% endblock %}</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;background:#F5F7F6}
        .header{background:#0B6E4F;color:white;padding:15px 30px;display:flex;justify-content:space-between;align-items:center}
        .logo h2{font-size:20px}.logo p{font-size:12px;color:#F1C40F}
        .user-info{display:flex;align-items:center;gap:20px}
        .logout-btn{background:#F1C40F;color:#1F2937;padding:8px 16px;border-radius:8px;text-decoration:none;font-weight:bold}
        .nav{background:white;padding:0 30px;display:flex;gap:5px;box-shadow:0 1px 3px rgba(0,0,0,0.1)}
        .nav a{padding:15px 20px;text-decoration:none;color:#6B7280;font-weight:500;transition:all 0.3s;border-bottom:3px solid transparent}
        .nav a:hover,.nav a.active{color:#0B6E4F;border-bottom-color:#0B6E4F}
        .container{padding:20px 30px}
        .status-badge{display:inline-block;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:bold}
        .status-low{background:#FEE2E2;color:#DC2626}
        button{cursor:pointer}
        {% block extra_css %}{% endblock %}
    </style>
</head>
<body>
    <div class="header"><div class="logo"><h2>ISAAC SUPERMARKET - Admin Portal</h2><p>Management System</p></div><div class="user-info"><a href="/change-password" style="color:white;text-decoration:none;margin-right:15px;font-size:13px">🔒 Change Password</a><span>Admin: {{ username }}</span><a href="/logout" class="logout-btn">Logout</a></div></div>
    <div class="nav">
        <a href="/admin-dashboard" class="{% if request.endpoint == 'admin_dashboard' %}active{% endif %}">Dashboard</a>
        <a href="/inventory" class="{% if request.endpoint == 'inventory' %}active{% endif %}">Inventory</a>
        <a href="/sales" class="{% if request.endpoint == 'sales' %}active{% endif %}">Daily Sales</a>
        <a href="/reports" class="{% if request.endpoint == 'reports' %}active{% endif %}">Reports</a>
        <a href="/customers" class="{% if request.endpoint == 'customers' %}active{% endif %}">Customers</a>
        <a href="/receipts" class="{% if request.endpoint == 'receipts' %}active{% endif %}">Receipts</a>
    </div>
    <div class="container">{% block content %}{% endblock %}</div>
    <script>function formatNumber(num){return new Intl.NumberFormat('en-KE',{minimumFractionDigits:2,maximumFractionDigits:2}).format(num);}</script>
    {% block extra_js %}{% endblock %}
</body>
</html>''')

    with open('templates/admin_dashboard.html', 'w', encoding='utf-8') as f:
        f.write('''{% extends "admin_base.html" %}
{% block title %}Admin Dashboard{% endblock %}
{% block content %}
<h2>Welcome, {{ username }}!</h2>
<p style="margin-bottom:30px">Manage your supermarket operations from this dashboard.</p>
<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:20px">
    <div style="background:linear-gradient(135deg,#0B6E4F 0%,#085239 100%);color:white;padding:20px;border-radius:12px"><h3>Inventory</h3><p style="font-size:32px;margin:10px 0" id="productCount">-</p><p>Products in stock</p><a href="/inventory" style="color:white;text-decoration:none">Manage →</a></div>
    <div style="background:linear-gradient(135deg,#F1C40F 0%,#D4AC0D 100%);color:#1F2937;padding:20px;border-radius:12px"><h3>Today's Sales</h3><p style="font-size:32px;margin:10px 0" id="todaySales">-</p><p>Total revenue</p><a href="/sales" style="color:#1F2937;text-decoration:none">View →</a></div>
    <div style="background:linear-gradient(135deg,#3B82F6 0%,#2563EB 100%);color:white;padding:20px;border-radius:12px"><h3>Customers</h3><p style="font-size:32px;margin:10px 0" id="customerCount">-</p><p>Registered customers</p><a href="/customers" style="color:white;text-decoration:none">View →</a></div>
    <div style="background:linear-gradient(135deg,#EF4444 0%,#DC2626 100%);color:white;padding:20px;border-radius:12px"><h3>Low Stock</h3><p style="font-size:32px;margin:10px 0" id="lowStockCount">-</p><p>Items below 10 units</p><a href="/inventory" style="color:white;text-decoration:none">Restock →</a></div>
    <div style="background:linear-gradient(135deg,#8B5CF6 0%,#6D28D9 100%);color:white;padding:20px;border-radius:12px"><h3>Receipts</h3><p style="font-size:32px;margin:10px 0">📄</p><p>View & print receipts</p><a href="/receipts" style="color:white;text-decoration:none">View Receipts →</a></div>
</div>
<script>
fetch('/api/inventory').then(res=>res.json()).then(products=>{document.getElementById('productCount').textContent=products.length;const lowStock=products.filter(p=>p.stock<10).length;document.getElementById('lowStockCount').textContent=lowStock;});
fetch('/api/daily_sales?date='+new Date().toISOString().split('T')[0]).then(res=>res.json()).then(data=>{document.getElementById('todaySales').textContent='KES '+formatNumber(data.total);});
fetch('/api/customers').then(res=>res.json()).then(customers=>{document.getElementById('customerCount').textContent=customers.length;});
</script>
{% endblock %}''')

    with open('templates/base.html', 'w', encoding='utf-8') as f:
        f.write('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ISAAC SUPERMARKET - {% block title %}POS System{% endblock %}</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;background:#F5F7F6}
        .header{background:#0B6E4F;color:white;padding:15px 30px;display:flex;justify-content:space-between;align-items:center;box-shadow:0 2px 10px rgba(0,0,0,0.1)}
        .logo h2{font-size:20px}.logo p{font-size:12px;color:#F1C40F}
        .user-info{display:flex;align-items:center;gap:20px}
        .logout-btn{background:#F1C40F;color:#1F2937;padding:8px 16px;border-radius:8px;text-decoration:none;font-weight:bold;transition:background 0.3s}
        .logout-btn:hover{background:#D4AC0D}
        .nav{background:white;padding:0 30px;display:flex;gap:5px;box-shadow:0 1px 3px rgba(0,0,0,0.1)}
        .nav a{padding:15px 20px;text-decoration:none;color:#6B7280;font-weight:500;transition:all 0.3s;border-bottom:3px solid transparent}
        .nav a:hover,.nav a.active{color:#0B6E4F;border-bottom-color:#0B6E4F}
        .container{padding:20px 30px}
        .status-badge{display:inline-block;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:bold}
        .status-low{background:#FEE2E2;color:#DC2626}.status-normal{background:#D1FAE5;color:#10B981}
        button{cursor:pointer}
        {% block extra_css %}{% endblock %}
    </style>
</head>
<body>
    <div class="header"><div class="logo"><h2>ISAAC SUPERMARKET</h2><p>Quality * Value * Service</p></div><div class="user-info"><a href="/change-password" style="color:white;text-decoration:none;margin-right:15px;font-size:13px">🔒 Change Password</a><span>Welcome, {{ customer_name }}</span><a href="/logout" class="logout-btn">Logout</a></div></div>
    <div class="nav"><a href="/pos" class="{% if request.endpoint == 'pos' %}active{% endif %}">Point of Sale</a></div>
    <div class="container">{% block content %}{% endblock %}</div>
    <script>function formatNumber(num){return new Intl.NumberFormat('en-KE',{minimumFractionDigits:2,maximumFractionDigits:2}).format(num);}</script>
    {% block extra_js %}{% endblock %}
</body>
</html>''')

    with open('templates/pos.html', 'w', encoding='utf-8') as f:
        f.write('''{% extends "base.html" %}
{% block title %}Point of Sale{% endblock %}
{% block extra_css %}
<style>
    .pos-container{display:flex;gap:20px}
    .products-panel{flex:2;background:white;border-radius:12px;padding:20px;box-shadow:0 1px 3px rgba(0,0,0,0.1)}
    .cart-panel{flex:1;background:white;border-radius:12px;padding:20px;box-shadow:0 1px 3px rgba(0,0,0,0.1);position:sticky;top:20px;height:fit-content}
    .search-bar{display:flex;gap:10px;margin-bottom:20px}
    .search-bar input,.search-bar select{padding:10px;border:1px solid #E5E7EB;border-radius:8px;font-size:14px}
    .search-bar input{flex:1}
    .products-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:15px;max-height:500px;overflow-y:auto}
    .product-card{border:1px solid #E5E7EB;border-radius:10px;padding:12px;text-align:center;transition:all 0.3s;cursor:pointer}
    .product-card:hover{box-shadow:0 4px 12px rgba(0,0,0,0.1);transform:translateY(-2px)}
    .product-name{font-weight:bold;margin:8px 0;font-size:14px}
    .product-price{color:#0B6E4F;font-weight:bold;font-size:16px}
    .product-stock{font-size:12px;color:#6B7280;margin:5px 0}
    .add-btn{background:#F1C40F;border:none;padding:6px 12px;border-radius:6px;cursor:pointer;margin-top:8px;font-weight:bold}
    .add-btn:hover{background:#D4AC0D}
    .cart-table{width:100%;border-collapse:collapse;margin:15px 0}
    .cart-table th,.cart-table td{padding:10px;text-align:left;border-bottom:1px solid #E5E7EB}
    .cart-table th{background:#F9FAFB}
    .quantity-input{width:60px;padding:5px;border:1px solid #E5E7EB;border-radius:4px;text-align:center}
    .remove-btn{background:#DC2626;color:white;border:none;padding:4px 8px;border-radius:4px;cursor:pointer;font-size:12px}
    .total-row{font-size:24px;font-weight:bold;color:#0B6E4F;text-align:right;padding:15px;border-top:2px solid #E5E7EB}
    .checkout-btn{width:100%;padding:12px;margin:8px 0;border:none;border-radius:8px;font-weight:bold;cursor:pointer}
    .cash-btn{background:#0B6E4F;color:white}.mpesa-btn{background:#F1C40F;color:#1F2937}
    .modal{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);justify-content:center;align-items:center;z-index:1000}
    .modal-content{background:white;border-radius:12px;padding:30px;max-width:550px;width:95%;max-height:85vh;overflow-y:auto}
    .success-header{text-align:center;margin-bottom:20px}.success-icon{font-size:64px;display:block;margin-bottom:10px}
    .success-header h2{color:#059669;font-size:24px;margin-bottom:5px}
    .receipt-details{background:#F9FAFB;border-radius:8px;padding:15px;margin:15px 0}
    .receipt-row{display:flex;justify-content:space-between;padding:5px 0;font-size:14px}
    .items-list{margin:15px 0}.items-list table{width:100%;border-collapse:collapse}
    .items-list th{background:#0B6E4F;color:white;padding:8px;font-size:12px;text-align:left}
    .items-list td{padding:6px 8px;border-bottom:1px solid #E5E7EB;font-size:13px}
    .total-summary{margin-top:15px;border-top:2px solid #0B6E4F;padding-top:10px}
    .total-summary .receipt-row{font-size:16px;font-weight:bold;color:#0B6E4F}
    .btn-group{display:flex;gap:10px;margin-top:20px;flex-wrap:wrap}
    .btn-group button{flex:1;padding:12px;border:none;border-radius:8px;font-weight:bold;cursor:pointer;font-size:14px;min-width:120px}
    .btn-close{background:#6B7280;color:white}.btn-new-sale{background:#0B6E4F;color:white}
    .loading-overlay{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.7);justify-content:center;align-items:center;z-index:2000}
    .loading-spinner{background:white;padding:30px;border-radius:12px;text-align:center}
    .spinner{border:4px solid #E5E7EB;border-top:4px solid #0B6E4F;border-radius:50%;width:50px;height:50px;animation:spin 1s linear infinite;margin:0 auto 15px}
    @keyframes spin{0%{transform:rotate(0deg)}100%{transform:rotate(360deg)}}
</style>
{% endblock %}
{% block content %}
<div class="loading-overlay" id="loadingOverlay"><div class="loading-spinner"><div class="spinner"></div><p>Processing your order...</p></div></div>
<div class="pos-container">
    <div class="products-panel">
        <div class="search-bar"><input type="text" id="searchInput" placeholder="Search products..." onkeyup="loadProducts()"><select id="categorySelect" onchange="loadProducts()"><option value="All">All Categories</option></select></div>
        <div class="products-grid" id="productsGrid"><div>Loading products...</div></div>
    </div>
    <div class="cart-panel">
        <h3>🛒 Current Sale</h3><div style="font-size:14px;color:#6B7280;margin-bottom:10px">Welcome, <strong>{{ customer_name }}</strong></div>
        <div style="margin:10px 0;display:flex;align-items:center;gap:10px"><input type="checkbox" id="useLoyaltyPoints"><label for="useLoyaltyPoints">Use loyalty points (1 point = 1 KES, max 20% off)</label></div>
        <table class="cart-table"><thead><tr><th>Item</th><th>Qty</th><th>Price</th><th>Total</th><th></th></tr></thead><tbody id="cartBody"></tbody></table>
        <div class="total-row" id="totalAmount">KES 0.00</div>
        <div id="discountInfo" style="font-size:12px;color:#6B7280;text-align:right"></div>
        <div style="background:linear-gradient(135deg,#FEF3C7,#FDE68A);padding:10px 15px;border-radius:8px;margin:10px 0;display:flex;justify-content:space-between;align-items:center">
            <span style="font-weight:bold">🏆 Loyalty Points</span>
            <strong id="loyaltyPointsDisplay" style="font-size:20px;color:#0B6E4F">{{ loyalty_points }}</strong>
        </div>
        <button class="checkout-btn cash-btn" onclick="checkout('CASH')">💰 CASH CHECKOUT</button>
        <button class="checkout-btn mpesa-btn" onclick="checkout('MPESA')">📱 M-PESA CHECKOUT</button>
        <button onclick="clearCart()" style="width:100%;padding:8px;margin-top:8px">Clear Cart</button>
    </div>
</div>
<div id="receiptModal" class="modal"><div class="modal-content" id="receiptContent"></div></div>
<script>
let cart=[],lastReceipt=null,customerPoints={{loyalty_points}};
function loadProducts(){const search=document.getElementById('searchInput').value,category=document.getElementById('categorySelect').value;fetch(`/api/products?search=${encodeURIComponent(search)}&category=${encodeURIComponent(category)}`).then(res=>res.json()).then(products=>{const grid=document.getElementById('productsGrid');grid.innerHTML=products.map(p=>`<div class="product-card" onclick="addToCart(${p.id},'${p.name.replace(/'/g,"\\\\'")}',${p.price},${p.stock})"><div class="product-name">${p.name}</div><div class="product-price">KES ${formatNumber(p.price)}</div><div class="product-stock">Stock: ${p.stock} ${p.unit}</div><button class="add-btn">+ Add to Cart</button></div>`).join('');});}
function loadCategories(){fetch('/api/categories').then(res=>res.json()).then(cats=>{const select=document.getElementById('categorySelect');cats.forEach(cat=>{const option=document.createElement('option');option.value=cat;option.textContent=cat;select.appendChild(option);});});}
function addToCart(id,name,price,stock){const existing=cart.find(item=>item.product_id===id);if(existing){if(existing.qty+1>stock){alert('❌ Cannot exceed available stock! Available: '+stock);return;}existing.qty++;}else{if(stock<1){alert('❌ Product out of stock!');return;}cart.push({product_id:id,name:name,qty:1,unit_price:price});}updateCartDisplay();}
function updateCartDisplay(){const tbody=document.getElementById('cartBody');let total=0;if(cart.length===0){tbody.innerHTML='<tr><td colspan="5" style="text-align:center;color:#6B7280;padding:20px">Cart is empty</td></tr>';}else{tbody.innerHTML=cart.map((item,idx)=>{const subtotal=item.qty*item.unit_price;total+=subtotal;return`<tr><td>${item.name}</td><td><input type="number" class="quantity-input" value="${item.qty}" min="1" onchange="updateQuantity(${idx},this.value)"></td><td>KES ${formatNumber(item.unit_price)}</td><td>KES ${formatNumber(subtotal)}</td><td><button class="remove-btn" onclick="removeFromCart(${idx})">✕</button></td></tr>`;}).join('');}document.getElementById('totalAmount').innerHTML=`KES ${formatNumber(total)}`;const usePoints=document.getElementById('useLoyaltyPoints').checked;if(usePoints&&customerPoints>0&&total>0){const maxDiscount=total*0.20;const discount=Math.min(customerPoints,maxDiscount,total);const finalTotal=total-discount;document.getElementById('discountInfo').innerHTML=`🏆 Points discount: -KES ${formatNumber(discount)}<br><strong>Final total: KES ${formatNumber(finalTotal)}</strong>`;}else{document.getElementById('discountInfo').innerHTML='';}}
function updateQuantity(index,qty){qty=parseInt(qty);if(qty>0){cart[index].qty=qty;updateCartDisplay();}}
function removeFromCart(index){cart.splice(index,1);updateCartDisplay();}
function clearCart(){if(cart.length>0&&!confirm('Are you sure you want to clear the cart?'))return;cart=[];updateCartDisplay();}
function checkout(method){if(cart.length===0){alert('❌ Cart is empty! Please add items before checkout.');return;}let mpesaCode=null;if(method==='MPESA'){mpesaCode=prompt('📱 Enter M-Pesa confirmation code:');if(!mpesaCode||mpesaCode.trim()===''){alert('❌ M-Pesa code is required!');return;}}const usePoints=document.getElementById('useLoyaltyPoints').checked;document.getElementById('loadingOverlay').style.display='flex';fetch('/api/checkout',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({cart:cart,payment_method:method,mpesa_code:mpesaCode,use_loyalty_points:usePoints})}).then(res=>res.json()).then(data=>{document.getElementById('loadingOverlay').style.display='none';if(data.success){lastReceipt=data;displaySuccessModal(data);if(data.new_points_balance!==undefined){customerPoints=data.new_points_balance;document.getElementById('loyaltyPointsDisplay').innerHTML=customerPoints;}cart=[];updateCartDisplay();loadProducts();}else{alert('❌ '+(data.error||'Checkout failed. Please try again.'));}}).catch(err=>{document.getElementById('loadingOverlay').style.display='none';alert('❌ Network error. Please check your connection and try again.');console.error('Checkout error:',err);});}
function displaySuccessModal(data){const modal=document.getElementById('receiptModal');const content=document.getElementById('receiptContent');const itemsRows=data.items.map((item,idx)=>`<tr><td>${idx+1}</td><td>${item.name}</td><td>${item.qty}</td><td>KES ${formatNumber(item.unit_price)}</td><td>KES ${formatNumber(item.qty*item.unit_price)}</td></tr>`).join('');content.innerHTML=`<div class="success-header"><span class="success-icon">✅</span><h2>Products Purchased Successfully!</h2><p>Your order has been processed successfully</p></div><div class="receipt-details"><div class="receipt-row"><span>Receipt Number:</span><strong>${data.receipt_no}</strong></div><div class="receipt-row"><span>Customer:</span><strong>${data.customer_name}</strong></div><div class="receipt-row"><span>Phone:</span><strong>${data.customer_phone||'N/A'}</strong></div><div class="receipt-row"><span>Payment Method:</span><strong>${data.payment_method}</strong></div>${data.mpesa_code?`<div class="receipt-row"><span>M-Pesa Code:</span><strong>${data.mpesa_code}</strong></div>`:''}<div class="receipt-row"><span>Date:</span><strong>${new Date().toLocaleString()}</strong></div></div><div class="items-list"><h4 style="margin-bottom:10px">📋 Purchased Items (${data.items.length})</h4><table><thead><tr><th>#</th><th>Item</th><th>Qty</th><th>Unit Price</th><th>Total</th></tr></thead><tbody>${itemsRows}</tbody></table></div><div class="total-summary"><div class="receipt-row"><span>Subtotal:</span><span>KES ${formatNumber(data.subtotal)}</span></div><div class="receipt-row"><span>Tax (8% VAT):</span><span>KES ${formatNumber(data.tax)}</span></div>${data.discount>0?`<div class="receipt-row" style="color:#DC2626"><span>Points Discount:</span><span>-KES ${formatNumber(data.discount)}</span></div>`:''}<div class="receipt-row" style="font-size:18px;font-weight:bold;color:#0B6E4F;margin-top:10px;padding-top:10px;border-top:2px solid #0B6E4F"><span>TOTAL PAID:</span><span>KES ${formatNumber(data.total)}</span></div></div>${data.points_earned>0||data.points_used>0?`<div style="background:#FEF3C7;padding:10px;border-radius:8px;margin-top:15px;text-align:center"><strong>🏆 Loyalty Points Summary</strong><br>${data.points_used>0?`Points Used: ${data.points_used}<br>`:''}Points Earned: ${data.points_earned}<br><strong>New Balance: ${data.new_points_balance} points</strong></div>`:''}<div class="btn-group"><button class="btn-new-sale" onclick="startNewSale()">🆕 Start New Sale</button><button class="btn-close" onclick="closeModal()">✕ Close</button></div>`;modal.style.display='flex';}
function startNewSale(){document.getElementById('receiptModal').style.display='none';cart=[];updateCartDisplay();document.getElementById('searchInput').value='';document.getElementById('categorySelect').value='All';loadProducts();window.scrollTo({top:0,behavior:'smooth'});}
function closeModal(){document.getElementById('receiptModal').style.display='none';lastReceipt=null;}
document.getElementById('receiptModal').addEventListener('click',function(e){if(e.target===this){this.style.display='none';}});
document.getElementById('useLoyaltyPoints').addEventListener('change',function(){updateCartDisplay();});
document.addEventListener('keydown',function(e){if(e.ctrlKey&&e.key==='Enter'){e.preventDefault();checkout('CASH');}});
loadCategories();loadProducts();
</script>
{% endblock %}''')

    with open('templates/change_password.html', 'w', encoding='utf-8') as f:
        f.write('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Change Password - ISAAC SUPERMARKET</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{font-family:'Segoe UI',sans-serif;background:linear-gradient(135deg,#0B6E4F,#085239);height:100vh;display:flex;align-items:center;justify-content:center}
        .container{background:white;border-radius:20px;box-shadow:0 20px 40px rgba(0,0,0,0.2);width:450px;padding:40px}
        .logo{text-align:center;margin-bottom:30px}.logo h1{color:#0B6E4F;font-size:24px}
        .form-group{margin-bottom:20px}label{display:block;margin-bottom:8px;font-weight:500}
        input{width:100%;padding:12px;border:1px solid #E5E7EB;border-radius:10px;font-size:14px}
        input:focus{outline:none;border-color:#0B6E4F}
        button{width:100%;padding:12px;background:#0B6E4F;color:white;border:none;border-radius:10px;font-size:16px;font-weight:700;cursor:pointer}
        button:hover{background:#085239}
        .error{background:#FEE2E2;color:#DC2626;padding:10px;border-radius:8px;margin-bottom:20px;text-align:center}
        .success{background:#D1FAE5;color:#059669;padding:10px;border-radius:8px;margin-bottom:20px;text-align:center}
        .back-link{display:block;text-align:center;margin-top:20px;color:#6B7280;text-decoration:none}
    </style>
</head>
<body>
    <div class="container">
        <div class="logo"><h1>🔒 Change Password</h1></div>
        {% if error %}<div class="error">{{ error }}</div>{% endif %}
        {% if success %}<div class="success">{{ success }}</div>{% endif %}
        <form method="POST">
            <div class="form-group"><label>Current Password</label><input type="password" name="current_password" required></div>
            <div class="form-group"><label>New Password (min 6 chars)</label><input type="password" name="new_password" required minlength="6"></div>
            <div class="form-group"><label>Confirm New Password</label><input type="password" name="confirm_password" required></div>
            <button type="submit">Change Password</button>
        </form>
        {% if session.admin_id %}
        <a href="/admin-dashboard" class="back-link">← Back to Dashboard</a>
        {% elif session.customer_id %}
        <a href="/pos" class="back-link">← Back to POS</a>
        {% else %}
        <a href="/" class="back-link">← Back to Home</a>
        {% endif %}
    </div>
</body>
</html>''')

    with open('templates/receipts.html', 'w', encoding='utf-8') as f:
        f.write('''{% extends "admin_base.html" %}
{% block title %}Receipts & Purchase Details{% endblock %}
{% block extra_css %}
<style>
    .search-section{background:white;padding:20px;border-radius:12px;margin-bottom:20px;box-shadow:0 1px 3px rgba(0,0,0,0.1)}
    .search-row{display:flex;gap:15px;align-items:center;flex-wrap:wrap}
    .search-input{padding:10px;border:1px solid #E5E7EB;border-radius:8px;font-size:14px}
    .search-btn{padding:10px 20px;background:#0B6E4F;color:white;border:none;border-radius:8px;cursor:pointer;font-weight:bold}
    .search-btn:hover{background:#085239}
    .receipts-table{width:100%;background:white;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.1);margin-bottom:20px}
    .receipts-table th,.receipts-table td{padding:12px;text-align:left;border-bottom:1px solid #E5E7EB}
    .receipts-table th{background:#F9FAFB;font-weight:600}
    .receipts-table tr:hover{background:#F9FAFB}
    .view-btn{background:#3B82F6;color:white;border:none;padding:6px 12px;border-radius:4px;cursor:pointer;font-size:12px}
    .print-btn{background:#F59E0B;color:white;border:none;padding:6px 12px;border-radius:4px;cursor:pointer;font-size:12px;margin-left:5px}
    .modal{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);justify-content:center;align-items:center;z-index:1000}
    .modal-content{background:white;border-radius:12px;padding:30px;max-width:700px;width:95%;max-height:80vh;overflow-y:auto}
    .receipt-header{text-align:center;margin-bottom:20px}.receipt-header h2{color:#0B6E4F}
    .receipt-info{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:20px}
    .items-table{width:100%;border-collapse:collapse;margin-bottom:20px}
    .items-table th,.items-table td{padding:8px;border:1px solid #E5E7EB;text-align:left}
    .items-table th{background:#F9FAFB}
    .total-section{text-align:right;font-size:16px;margin-top:15px}
    .total-row{font-weight:bold;font-size:18px;color:#0B6E4F}
    @media print{body *{visibility:hidden}.modal-content,.modal-content *{visibility:visible}.modal-content{position:absolute;left:0;top:0;width:100%;max-width:100%;padding:20px}.no-print{display:none!important}}
    .no-print{margin-top:20px}
    .pagination{display:flex;justify-content:center;gap:10px;margin-top:20px}
    .pagination button{padding:8px 12px;border:1px solid #E5E7EB;background:white;border-radius:4px;cursor:pointer}
    .pagination button.active{background:#0B6E4F;color:white;border-color:#0B6E4F}
    .payment-cash{color:#059669;font-weight:bold}.payment-mpesa{color:#2563EB;font-weight:bold}
</style>
{% endblock %}
{% block content %}
<h2>Receipts & Purchase Details</h2>
<p style="margin-bottom:20px">View and print detailed receipts for all customer purchases.</p>
<div class="search-section"><div class="search-row"><input type="date" id="dateFilter" class="search-input" value="{{ today }}"><input type="text" id="receiptSearch" class="search-input" placeholder="Search by receipt number..." style="flex:1"><input type="text" id="customerSearch" class="search-input" placeholder="Search by customer name..." style="flex:1"><button class="search-btn" onclick="loadReceipts()">🔍 Search</button></div></div>
<table class="receipts-table"><thead><tr><th>Receipt #</th><th>Date & Time</th><th>Customer</th><th>Items</th><th>Total</th><th>Payment</th><th>Actions</th></tr></thead><tbody id="receiptsBody"><tr><td colspan="7" style="text-align:center">Loading receipts...</td></tr></tbody></table>
<div class="pagination" id="pagination"></div>
<div id="receiptModal" class="modal"><div class="modal-content" id="receiptContent"></div></div>
<script>
let currentPage=1,itemsPerPage=20,allReceipts=[];
function loadReceipts(){const date=document.getElementById('dateFilter').value,receiptSearch=document.getElementById('receiptSearch').value.toLowerCase(),customerSearch=document.getElementById('customerSearch').value.toLowerCase();document.getElementById('receiptsBody').innerHTML='<tr><td colspan="7" style="text-align:center">Loading...</td></tr>';fetch(`/api/all_sales?date=${date}`).then(res=>res.json()).then(data=>{allReceipts=data.sales||[];let filtered=allReceipts;if(receiptSearch)filtered=filtered.filter(r=>r.receipt_no.toLowerCase().includes(receiptSearch));if(customerSearch)filtered=filtered.filter(r=>(r.customer_name&&r.customer_name.toLowerCase().includes(customerSearch)));displayReceipts(filtered);}).catch(err=>{console.error('Error loading receipts:',err);document.getElementById('receiptsBody').innerHTML='<tr><td colspan="7" style="text-align:center;color:red">Error loading receipts</td></tr>';});}
function displayReceipts(receipts){const tbody=document.getElementById('receiptsBody');if(!receipts||receipts.length===0){tbody.innerHTML='<tr><td colspan="7" style="text-align:center;padding:20px">No receipts found for this date</td></tr>';document.getElementById('pagination').innerHTML='';return;}const totalPages=Math.ceil(receipts.length/itemsPerPage),start=(currentPage-1)*itemsPerPage,pageReceipts=receipts.slice(start,start+itemsPerPage);tbody.innerHTML=pageReceipts.map(r=>{let items=[];try{items=typeof r.items==='string'?JSON.parse(r.items):r.items;}catch(e){}const itemCount=items.length,itemNames=items.map(i=>i.name).join(', ').substring(0,60),paymentClass=r.payment_method==='MPESA'?'payment-mpesa':'payment-cash';return`<tr><td><strong>${r.receipt_no}</strong></td><td>${new Date(r.created_at).toLocaleString()}</td><td>${r.customer_name||'<em>Walk-in</em>'}</td><td title="${itemNames}">${itemCount} item(s)</td><td><strong>KES ${formatNumber(r.total)}</strong></td><td><span class="${paymentClass}">${r.payment_method||'N/A'}</span></td><td><button class="view-btn" onclick="viewReceipt(${r.id})">👁 View</button><button class="print-btn" onclick="printReceipt(${r.id})">🖨 Print</button></td></tr>`;}).join('');let paginationHTML='';if(totalPages>1){for(let i=1;i<=totalPages;i++){paginationHTML+=`<button class="${i===currentPage?'active':''}" onclick="currentPage=${i};displayReceipts(allReceipts.filter(r=>{const receiptSearch=document.getElementById('receiptSearch').value.toLowerCase(),customerSearch=document.getElementById('customerSearch').value.toLowerCase();let match=true;if(receiptSearch)match=match&&r.receipt_no.toLowerCase().includes(receiptSearch);if(customerSearch)match=match&&(r.customer_name&&r.customer_name.toLowerCase().includes(customerSearch));return match;}))">${i}</button>`;}}document.getElementById('pagination').innerHTML=paginationHTML;}
function viewReceipt(receiptId){const receipt=allReceipts.find(r=>r.id===receiptId);if(!receipt)return;let items=[];try{items=typeof receipt.items==='string'?JSON.parse(receipt.items):receipt.items;}catch(e){}const subtotal=items.reduce((sum,item)=>sum+(item.qty*item.unit_price),0),tax=subtotal*0.08;document.getElementById('receiptContent').innerHTML=`<div class="receipt-header"><h2>ISAAC SUPERMARKET</h2><p>Quality * Value * Service</p><p style="font-size:12px">Nairobi, Kenya | Tel: +254 700 000000</p><hr><p><strong>RECEIPT #: ${receipt.receipt_no}</strong></p><p>Date: ${new Date(receipt.created_at).toLocaleString()}</p></div><div class="receipt-info"><div><strong>Customer:</strong> ${receipt.customer_name||'Walk-in Customer'}</div><div><strong>Phone:</strong> ${receipt.customer_phone||'N/A'}</div><div><strong>Payment Method:</strong> ${receipt.payment_method||'N/A'}</div><div><strong>M-Pesa Code:</strong> ${receipt.mpesa_code||'N/A'}</div>${receipt.loyalty_points_used>0?`<div><strong>Points Used:</strong> ${receipt.loyalty_points_used}</div>`:''}${receipt.loyalty_points_earned>0?`<div><strong>Points Earned:</strong> ${receipt.loyalty_points_earned}</div>`:''}</div><p style="font-weight:bold">Items Purchased (${items.length}):</p><table class="items-table"><thead><tr><th>#</th><th>Item Description</th><th>Qty</th><th>Unit Price</th><th>Total</th></tr></thead><tbody>${items.map((item,idx)=>`<tr><td>${idx+1}</td><td>${item.name}</td><td>${item.qty}</td><td>KES ${formatNumber(item.unit_price)}</td><td><strong>KES ${formatNumber(item.qty*item.unit_price)}</strong></td></tr>`).join('')}</tbody></table><div class="total-section"><div>Subtotal: KES ${formatNumber(subtotal)}</div><div>Tax (8% VAT): KES ${formatNumber(tax)}</div><div style="border-top:2px solid #0B6E4F;padding-top:10px;margin-top:10px" class="total-row">TOTAL: KES ${formatNumber(receipt.total)}</div></div><div style="text-align:center;margin-top:20px"><p style="color:#059669;font-weight:bold">✅ Products Purchased Successfully!</p><p style="font-size:12px;color:#6B7280">Thank you for shopping with us!</p></div><div class="no-print" style="text-align:center;border-top:1px solid #E5E7EB;padding-top:15px"><button onclick="window.print()" style="padding:10px 20px;background:#0B6E4F;color:white;border:none;border-radius:8px;cursor:pointer;margin-right:10px;font-size:14px">🖨 Print Receipt</button><button onclick="document.getElementById('receiptModal').style.display='none'" style="padding:10px 20px;background:#6B7280;color:white;border:none;border-radius:8px;cursor:pointer;font-size:14px">✕ Close</button></div>`;document.getElementById('receiptModal').style.display='flex';}
function printReceipt(receiptId){viewReceipt(receiptId);setTimeout(()=>{window.print();},500);}
document.getElementById('receiptModal').addEventListener('click',function(e){if(e.target===this){this.style.display='none';}});
document.getElementById('dateFilter').value=new Date().toISOString().split('T')[0];loadReceipts();
</script>
{% endblock %}''')

    with open('templates/customers.html', 'w', encoding='utf-8') as f:
        f.write('''{% extends "admin_base.html" %}
{% block title %}Customer Management{% endblock %}
{% block extra_css %}
<style>.customers-table{width:100%;background:white;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.1)}.customers-table th,.customers-table td{padding:12px;text-align:left;border-bottom:1px solid #E5E7EB}.customers-table th{background:#F9FAFB;font-weight:600}.customers-table tr:hover{background:#F9FAFB}</style>
{% endblock %}
{% block content %}
<h2>Customer Management</h2><p style="margin-bottom:20px">View all registered customers and their purchase history.</p>
<table class="customers-table"><thead><tr><th>ID</th><th>Name</th><th>Email</th><th>Phone</th><th>Total Purchases</th><th>Loyalty Points</th><th>Member Since</th></tr></thead><tbody id="customersBody"></tbody></table>
<script>function loadCustomers(){fetch('/api/customers').then(res=>res.json()).then(customers=>{const tbody=document.getElementById('customersBody');tbody.innerHTML=customers.map(c=>`<tr><td>${c.id}</td><td>${c.full_name}</td><td>${c.email}</td><td>${c.phone}</td><td>KES ${formatNumber(c.total_purchases||0)}</td><td><span class="status-badge status-normal">${c.loyalty_points||0}</span></td><td>${c.created_at?new Date(c.created_at).toLocaleDateString():'N/A'}</td></tr>`).join('');});}loadCustomers();</script>
{% endblock %}''')

    with open('templates/inventory.html', 'w', encoding='utf-8') as f:
        f.write('''{% extends "admin_base.html" %}
{% block title %}Inventory Management{% endblock %}
{% block extra_css %}
<style>.inventory-table{width:100%;background:white;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.1)}.inventory-table th,.inventory-table td{padding:12px;text-align:left;border-bottom:1px solid #E5E7EB}.inventory-table th{background:#F9FAFB;font-weight:600}.inventory-table tr:hover{background:#F9FAFB}.restock-input{width:70px;padding:5px;border:1px solid #E5E7EB;border-radius:4px}.restock-btn{background:#3B82F6;color:white;border:none;padding:5px 10px;border-radius:4px;cursor:pointer}.search-section{margin-bottom:20px}.search-section input{padding:10px;border:1px solid #E5E7EB;border-radius:8px;width:100%;max-width:400px}</style>
{% endblock %}
{% block content %}
<h2>Inventory Management</h2>
<div class="search-section"><input type="text" id="searchInventory" placeholder="Search products..." onkeyup="loadInventory()"></div>
<table class="inventory-table"><thead><tr><th>SKU</th><th>Name</th><th>Category</th><th>Price</th><th>Stock</th><th>Unit</th><th>Status</th><th>Restock</th></tr></thead><tbody id="inventoryBody"></tbody></table>
<script>function loadInventory(){const search=document.getElementById('searchInventory').value;fetch('/api/inventory').then(res=>res.json()).then(products=>{const filtered=search?products.filter(p=>p.name.toLowerCase().includes(search.toLowerCase())):products;const tbody=document.getElementById('inventoryBody');tbody.innerHTML=filtered.map(p=>`<tr><td>${p.sku}</td><td>${p.name}</td><td>${p.category}</td><td>KES ${formatNumber(p.price)}</td><td>${p.stock}</td><td>${p.unit}</td><td><span class="status-badge ${p.stock<10?'status-low':'status-normal'}">${p.stock<10?'Low Stock':'In Stock'}</span></td><td><input type="number" class="restock-input" id="restock_${p.id}" value="10" min="1"><button class="restock-btn" onclick="restock(${p.id})">Add Stock</button></td></tr>`).join('');});}function restock(productId){const qty=parseInt(document.getElementById('restock_'+productId).value);fetch('/api/restock',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({product_id:productId,quantity:qty})}).then(res=>res.json()).then(data=>{if(data.success){loadInventory();alert('Stock updated successfully!');}});}loadInventory();</script>
{% endblock %}''')

    with open('templates/sales.html', 'w', encoding='utf-8') as f:
        f.write('''{% extends "admin_base.html" %}
{% block title %}Daily Sales{% endblock %}
{% block extra_css %}
<style>.sales-table{width:100%;background:white;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.1)}.sales-table th,.sales-table td{padding:12px;text-align:left;border-bottom:1px solid #E5E7EB}.sales-table th{background:#F9FAFB;font-weight:600}.sales-table tr:hover{background:#F9FAFB}.total-box{background:linear-gradient(135deg,#0B6E4F 0%,#085239 100%);color:white;padding:20px;border-radius:12px;margin-bottom:20px;display:flex;justify-content:space-between;align-items:center}</style>
{% endblock %}
{% block content %}
<h2>Daily Sales</h2>
<div class="total-box"><div><h3>Total Sales for <span id="selectedDate"></span></h3></div><div style="text-align:right"><p style="font-size:14px">Total Revenue</p><p style="font-size:28px;font-weight:bold" id="totalRevenue">KES 0.00</p></div></div>
<div style="margin-bottom:20px"><input type="date" id="dateFilter" onchange="loadSales()" style="padding:10px;border:1px solid #E5E7EB;border-radius:8px"></div>
<table class="sales-table"><thead><tr><th>Receipt #</th><th>Customer</th><th>Items</th><th>Total</th><th>Payment</th><th>Time</th></tr></thead><tbody id="salesBody"></tbody></table>
<script>function loadSales(){const date=document.getElementById('dateFilter').value||new Date().toISOString().split('T')[0];document.getElementById('selectedDate').textContent=new Date(date).toLocaleDateString();fetch('/api/daily_sales?date='+date).then(res=>res.json()).then(data=>{document.getElementById('totalRevenue').textContent='KES '+formatNumber(data.total);const tbody=document.getElementById('salesBody');tbody.innerHTML=data.sales.map(s=>{let items=[];try{items=JSON.parse(s.items);}catch(e){}return`<tr><td>${s.receipt_no}</td><td>${s.customer_name||'Walk-in'}</td><td>${items.length} item(s)</td><td>KES ${formatNumber(s.total)}</td><td>${s.payment_method}</td><td>${new Date(s.created_at).toLocaleTimeString()}</td></tr>`;}).join('');});}document.getElementById('dateFilter').value=new Date().toISOString().split('T')[0];loadSales();</script>
{% endblock %}''')

    with open('templates/reports.html', 'w', encoding='utf-8') as f:
        f.write('''{% extends "admin_base.html" %}
{% block title %}Sales Reports{% endblock %}
{% block extra_css %}
<style>.report-card{background:white;border-radius:12px;padding:20px;box-shadow:0 1px 3px rgba(0,0,0,0.1);margin-bottom:20px}canvas{max-width:100%}</style>
{% endblock %}
{% block content %}
<h2>Sales Reports</h2>
<div class="report-card"><h3>Sales Trend (Last 14 Days)</h3><canvas id="salesChart"></canvas></div>
<div class="report-card"><h3>Summary Table</h3><table class="sales-table" style="width:100%"><thead><tr><th>Date</th><th>Transactions</th><th>Total Revenue</th></tr></thead><tbody id="summaryBody"></tbody></table></div>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>let chart;function loadSummary(){fetch('/api/sales_summary?days=14').then(res=>res.json()).then(data=>{const tbody=document.getElementById('summaryBody');tbody.innerHTML=data.map(d=>`<tr><td>${d.d}</td><td>${d.n}</td><td>KES ${formatNumber(d.t)}</td></tr>`).join('');if(chart)chart.destroy();const ctx=document.getElementById('salesChart').getContext('2d');chart=new Chart(ctx,{type:'bar',data:{labels:data.map(d=>d.d).reverse(),datasets:[{label:'Daily Revenue (KES)',data:data.map(d=>d.t).reverse(),backgroundColor:'#0B6E4F'}]}});});}loadSummary();</script>
{% endblock %}''')


# ============================================================
# MAIN ENTRY POINT
# ============================================================

if __name__ == "__main__":
    init_db()
    create_templates()
    if not os.path.exists("receipts"):
        os.makedirs("receipts")

    print("=" * 60)
    print("ISAAC SUPERMARKET POS SYSTEM")
    print("=" * 60)
    print("Server running at: http://127.0.0.1:5000")
    print("\nAdmin Login: admin / admin123")
    print("Customer: Register first, then login")
    print("=" * 60)

    webbrowser.open("http://127.0.0.1:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)