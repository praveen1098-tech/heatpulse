import os
import datetime
import random
import logging
import requests
import sqlite3
from pymongo import MongoClient
from flask import Flask, render_template, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# Initialize environment and logging
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("HeatPulse")

app = Flask(__name__)

# --- CONFIGURATION ---
DB_FILE = "heatpulse.db"
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
PORT = int(os.getenv("PORT", 5001))

# --- MONGODB SETUP ---
try:
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
    mongo_db = mongo_client["heatpulse_db"]
    # Check connection
    mongo_client.server_info()
    logger.info("Connected to MongoDB successfully.")
except Exception as e:
    logger.warning(f"MongoDB not available: {e}. Falling back to SQLite only.")
    mongo_db = None

# --- DATABASE SETUP (SQLite) ---
def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Reports Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS thermal_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lat REAL,
            lon REAL,
            temp REAL,
            score REAL,
            elec REAL,
            gap REAL,
            trees_needed INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Orders Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tree_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT UNIQUE,
            customer_email TEXT,
            tree_type TEXT,
            quantity INTEGER,
            total_cost REAL,
            address TEXT,
            status TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    logger.info("SQLite Database initialized successfully.")

init_db()

class HeatPulseEngine:
    def calculate(self, temp, ndvi, hum):
        score = (temp * (1.2 - ndvi)) + (hum / 15)
        elec_load = 18 + (max(0, score - 20) * 3.2)
        canopy_gap = round(max(0, 0.75 - ndvi) * 100, 1)
        trees_needed = int(canopy_gap * 48)
        
        if score > 28.0: status, color = "CRITICAL", "text-rose-500"
        elif score > 18.0: status, color = "WARNING", "text-amber-500"
        else: status, color = "HEALTHY", "text-emerald-500"
        
        return round(score, 2), round(elec_load, 2), canopy_gap, trees_needed, status, color

engine = HeatPulseEngine()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/signup', methods=['POST'])
def signup():
    try:
        data = request.json
        name, email, password = data.get('name'), data.get('email'), data.get('password')

        if not name or not email or not password:
            return jsonify({"success": False, "message": "Missing required fields"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if user exists
        user = cursor.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
        if user:
            conn.close()
            return jsonify({"success": False, "message": "Email already registered"}), 409

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        cursor.execute('INSERT INTO users (name, email, password) VALUES (?, ?, ?)', 
                       (name, email, hashed_password))
        conn.commit()
        conn.close()

        return jsonify({"success": True, "message": "Account created successfully"})
    except Exception as e:
        logger.error(f"Signup Error: {e}")
        return jsonify({"success": False, "message": f"Signup Error: {str(e)}"}), 500

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.json
        email, password = data.get('email'), data.get('password')

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            return jsonify({
                "success": True, 
                "message": "Login successful",
                "user": {"name": user['name'], "email": user['email']}
            })
        
        return jsonify({"success": False, "message": "Invalid email or password"}), 401
    except Exception as e:
        logger.error(f"Login Error: {e}")
        return jsonify({"success": False, "message": f"Login Error: {str(e)}"}), 500

@app.route('/api/analyze', methods=['POST'])
def analyze():
    try:
        data = request.json
        lat, lon = round(data.get('lat'), 4), round(data.get('lon'), 4)
        logger.info(f"Analyzing Grid Sector: {lat}, {lon}")

        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m&hourly=precipitation_probability&forecast_days=1"
            resp = requests.get(url, timeout=5).json()
            temp = resp['current']['temperature_2m']
            hum = resp['current']['relative_humidity_2m']
            current_hour = datetime.datetime.utcnow().hour
            rain_prob = resp['hourly']['precipitation_probability'][current_hour]
        except Exception as weather_err:
            logger.warning(f"Weather API Error: {weather_err}")
            temp, hum, rain_prob = 32.8, 52.0, 15

        ndvi = round(random.uniform(0.15, 0.55), 2)
        score, elec, gap, trees, status, color = engine.calculate(temp, ndvi, hum)
        
        try:
            conn = get_db_connection()
            conn.execute('INSERT INTO thermal_reports (lat, lon, temp, score, elec, gap, trees_needed) VALUES (?, ?, ?, ?, ?, ?, ?)',
                         (lat, lon, temp, score, elec, gap, trees))
            conn.commit()
            conn.close()
        except Exception as db_err:
            logger.error(f"Report Log DB Error: {db_err}")

        history_ndvi = [round(ndvi + random.uniform(-0.08, 0.08), 2) for _ in range(4)]
        
        return jsonify({
            "score": score, "elec": elec, "gap": gap, "trees": trees, 
            "status": status, "color": color, "temp": temp, "hum": hum, 
            "ndvi": ndvi, "history_ndvi": history_ndvi, "rain_prob": rain_prob
        })
    except Exception as e:
        logger.error(f"Analysis Error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/order', methods=['POST'])
def place_order():
    try:
        data = request.json
        customer_email = data.get('email', 'Guest')
        tree_type = data.get('tree_type')
        qty = int(data.get('qty', 1))
        cost = float(data.get('cost', 0))
        address = data.get('address', 'Unspecified Sector')

        # 1. Log to SQLite
        conn = get_db_connection()
        conn.execute('INSERT INTO tree_orders (order_id, customer_email, tree_type, quantity, total_cost, address, status) VALUES (?, ?, ?, ?, ?, ?, ?)',
                     (order_id, customer_email, tree_type, qty, cost, address, "In Processing"))
        conn.commit()
        conn.close()
        
        # 2. Log to MongoDB (Real-time storage)
        if mongo_db is not None:
            try:
                mongo_db.orders.insert_one({
                    "order_id": order_id,
                    "customer": customer_email,
                    "items": [{"type": tree_type, "qty": qty}],
                    "total": cost,
                    "address": address,
                    "status": "In Processing",
                    "timestamp": datetime.datetime.utcnow()
                })
            except Exception as m_err:
                logger.error(f"MongoDB Log Error: {m_err}")

        # 3. TERMINAL NOTIFICATION (The "WOW" factor)
        print("\n" + "═"*60)
        print(f" 🚀  \033[1;32mNEW ORDER PLACED\033[0m")
        print(f" 🆔  ID: \033[1;36m{order_id}\033[0m")
        print(f" 👤  Customer: \033[1;37m{customer_email}\033[0m")
        print(f" 🌳  Asset: \033[1;33m{qty}x {tree_type}\033[0m")
        print(f" 💰  Value: \033[1;32m₹{cost:,.2f}\033[0m")
        print(f" 📍  Sector: \033[1;37m{address}\033[0m")
        print("═"*60 + "\n")
        
        logger.info(f"Order Success: {order_id} | {qty}x {tree_type}")
        return jsonify({"success": True, "msg": f"Asset Logged: {order_id}", "order_id": order_id})
    except Exception as e:
        logger.error(f"Order Processing Error: {e}")
        return jsonify({"success": False, "msg": f"Protocol Interrupted: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=PORT)