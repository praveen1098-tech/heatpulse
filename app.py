import os
import datetime
import random
import logging
import uuid
import base64
import json
import requests
import sqlite3
from flask import Flask, render_template, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# Safe optional MongoDB import
try:
    from pymongo import MongoClient
    HAS_PYMONGO = True
except ImportError:
    MongoClient = None
    HAS_PYMONGO = False

# Initialize environment and logging
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("HeatPulse")

app = Flask(__name__)

# --- CONFIGURATION ---
DB_FILE = os.getenv("DB_FILE", "heatpulse.db")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
PORT = int(os.getenv("PORT", 5001))
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")

# --- MONGODB SETUP ---
mongo_db = None
if HAS_PYMONGO and MongoClient:
    try:
        mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
        mongo_db = mongo_client["heatpulse_db"]
        # Check connection
        mongo_client.server_info()
        logger.info("Connected to MongoDB successfully.")
    except Exception as e:
        logger.warning(f"MongoDB not available: {e}. Falling back to SQLite only.")
        mongo_db = None
else:
    logger.info("PyMongo library not active. Running on SQLite standalone mode.")

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
            avatar TEXT,
            provider TEXT DEFAULT 'email',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Auto-migrate columns for existing users table
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN avatar TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN provider TEXT DEFAULT 'email'")
    except sqlite3.OperationalError:
        pass

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
            condition TEXT,
            source TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Auto-migrate columns for existing thermal_reports table
    try:
        cursor.execute("ALTER TABLE thermal_reports ADD COLUMN condition TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE thermal_reports ADD COLUMN source TEXT")
    except sqlite3.OperationalError:
        pass

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
    logger.info("SQLite Database initialized and verified successfully.")

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
    return render_template('index.html', google_client_id=GOOGLE_CLIENT_ID)

@app.route('/api/health')
def health():
    mongo_status = "connected" if mongo_db is not None else "offline (fallback to SQLite)"
    masked_key = f"{OPENWEATHER_API_KEY[:4]}...{OPENWEATHER_API_KEY[-4:]}" if OPENWEATHER_API_KEY else "not_set"
    return jsonify({
        "status": "healthy",
        "service": "HeatPulse",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "database": {
            "sqlite": "active",
            "mongodb": mongo_status
        },
        "integrations": {
            "openweather_api": "active" if OPENWEATHER_API_KEY else "inactive",
            "openweather_key": masked_key,
            "google_oauth": "configured" if GOOGLE_CLIENT_ID else "ready (demo/dev enabled)"
        }
    })

@app.route('/api/signup', methods=['POST'])
def signup():
    try:
        data = request.json or {}
        name = data.get('name')
        email = data.get('email')
        password = data.get('password')

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
        cursor.execute('INSERT INTO users (name, email, password, provider) VALUES (?, ?, ?, ?)', 
                       (name, email, hashed_password, 'email'))
        conn.commit()
        conn.close()

        # Sync to MongoDB if available
        if mongo_db is not None:
            try:
                mongo_db.customer.insert_one({
                    "name": name,
                    "email": email,
                    "provider": "email",
                    "created_at": datetime.datetime.utcnow()
                })
            except Exception as m_err:
                logger.error(f"MongoDB Customer Sync Error: {m_err}")

        return jsonify({"success": True, "message": "Account created successfully"})
    except Exception as e:
        logger.error(f"Signup Error: {e}")
        return jsonify({"success": False, "message": f"Signup Error: {str(e)}"}), 500

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.json or {}
        email = data.get('email')
        password = data.get('password')

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

@app.route('/api/auth/google', methods=['POST'])
def google_auth():
    try:
        data = request.json or {}
        credential = data.get('credential')
        
        email = None
        name = None
        avatar = None

        if credential:
            # 1. Verify token with Google's tokeninfo API if reachable
            try:
                verify_url = f"https://oauth2.googleapis.com/tokeninfo?id_token={credential}"
                token_resp = requests.get(verify_url, timeout=5)
                if token_resp.status_code == 200:
                    token_data = token_resp.json()
                    email = token_data.get('email')
                    name = token_data.get('name')
                    avatar = token_data.get('picture')
                    logger.info(f"Verified Google Token for: {email}")
            except Exception as v_err:
                logger.warning(f"Google tokeninfo API warning: {v_err}. Decoding JWT locally.")

            # 2. Local JWT payload decoding fallback
            if not email:
                try:
                    parts = credential.split('.')
                    if len(parts) >= 2:
                        payload_b64 = parts[1] + '=' * (-len(parts[1]) % 4)
                        payload_json = base64.urlsafe_b64decode(payload_b64.encode('utf-8')).decode('utf-8')
                        payload = json.loads(payload_json)
                        email = payload.get('email')
                        name = payload.get('name') or payload.get('given_name')
                        avatar = payload.get('picture')
                except Exception as d_err:
                    logger.error(f"Failed to decode Google JWT payload: {d_err}")

        # 3. Direct Google profile payload (for frontend / dev flow)
        if not email:
            email = data.get('email')
            name = data.get('name')
            avatar = data.get('avatar') or data.get('picture')

        if not email:
            return jsonify({"success": False, "message": "Failed to extract Google account credentials"}), 400

        if not name:
            name = email.split('@')[0].replace('.', ' ').title()

        # Check or insert user into SQLite
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        
        if not user:
            oauth_password = generate_password_hash(f"google_{uuid.uuid4().hex}", method='pbkdf2:sha256')
            cursor = conn.cursor()
            cursor.execute('INSERT INTO users (name, email, password, avatar, provider) VALUES (?, ?, ?, ?, ?)',
                           (name, email, oauth_password, avatar, 'google'))
            conn.commit()
            logger.info(f"Created new user via Google Sign-In: {name} <{email}>")

            if mongo_db is not None:
                try:
                    mongo_db.customer.insert_one({
                        "name": name,
                        "email": email,
                        "avatar": avatar,
                        "provider": "google",
                        "created_at": datetime.datetime.utcnow()
                    })
                except Exception as m_err:
                    logger.error(f"MongoDB Google Customer Sync Error: {m_err}")
        else:
            logger.info(f"Existing user authenticated via Google: {name} <{email}>")

        conn.close()

        return jsonify({
            "success": True,
            "message": "Google authentication successful",
            "user": {
                "name": name,
                "email": email,
                "avatar": avatar or f"https://api.dicebear.com/7.x/initials/svg?seed={name}",
                "provider": "google"
            }
        })
    except Exception as e:
        logger.error(f"Google Auth Error: {e}")
        return jsonify({"success": False, "message": f"Google Auth Error: {str(e)}"}), 500

@app.route('/api/analyze', methods=['POST'])
def analyze():
    try:
        data = request.json or {}
        lat_raw = data.get('lat', 17.3850)
        lon_raw = data.get('lon', 78.4867)
        lat, lon = round(float(lat_raw), 4), round(float(lon_raw), 4)
        logger.info(f"Analyzing Grid Sector: {lat}, {lon}")

        temp = None
        hum = None
        weather_desc = "Clear Skies"
        source = "OpenWeatherMap"
        rain_prob = 15

        # 1. PRIMARY: OpenWeatherMap Live Satellite API
        if OPENWEATHER_API_KEY:
            try:
                owm_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric"
                owm_resp = requests.get(owm_url, timeout=5).json()
                if owm_resp.get("cod") == 200 or "main" in owm_resp:
                    temp = round(float(owm_resp['main']['temp']), 1)
                    hum = float(owm_resp['main']['humidity'])
                    if owm_resp.get('weather') and len(owm_resp['weather']) > 0:
                        weather_desc = owm_resp['weather'][0]['description'].title()
                    rain_prob = owm_resp.get('clouds', {}).get('all', 15)
                    source = "OpenWeatherMap"
                    logger.info(f"Live OpenWeatherMap Telemetry: Temp={temp}°C, Humidity={hum}%, Condition='{weather_desc}'")
            except Exception as owm_err:
                logger.warning(f"OpenWeatherMap API Warning: {owm_err}")

        # 2. SECONDARY: Open-Meteo Fallback
        if temp is None:
            try:
                source = "Open-Meteo"
                url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m&hourly=precipitation_probability&forecast_days=1"
                resp = requests.get(url, timeout=5).json()
                temp = round(float(resp['current']['temperature_2m']), 1)
                hum = float(resp['current']['relative_humidity_2m'])
                current_hour = datetime.datetime.utcnow().hour
                rain_prob = resp['hourly']['precipitation_probability'][current_hour]
            except Exception as weather_err:
                logger.warning(f"Weather Secondary API Error: {weather_err}")
                source = "Simulation Telemetry"
                temp, hum, rain_prob = 32.8, 52.0, 15

        ndvi = round(random.uniform(0.15, 0.55), 2)
        score, elec, gap, trees, status, color = engine.calculate(temp, ndvi, hum)
        
        # Save to SQLite
        try:
            conn = get_db_connection()
            conn.execute('INSERT INTO thermal_reports (lat, lon, temp, score, elec, gap, trees_needed, condition, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                         (lat, lon, temp, score, elec, gap, trees, weather_desc, source))
            conn.commit()
            conn.close()
        except Exception as db_err:
            logger.error(f"Report Log DB Error: {db_err}")

        # Save to MongoDB
        if mongo_db is not None:
            try:
                mongo_db.thermal_reports.insert_one({
                    "lat": lat,
                    "lon": lon,
                    "data": {
                        "temp": temp,
                        "score": score,
                        "elec": elec,
                        "gap": gap,
                        "trees_needed": trees,
                        "status": status,
                        "hum": hum,
                        "ndvi": ndvi,
                        "rain_prob": rain_prob,
                        "condition": weather_desc,
                        "source": source
                    },
                    "timestamp": datetime.datetime.utcnow()
                })
            except Exception as m_err:
                logger.error(f"MongoDB Report Sync Error: {m_err}")

        history_ndvi = [round(ndvi + random.uniform(-0.08, 0.08), 2) for _ in range(4)]
        
        return jsonify({
            "score": score, "elec": elec, "gap": gap, "trees": trees, 
            "status": status, "color": color, "temp": temp, "hum": hum, 
            "ndvi": ndvi, "history_ndvi": history_ndvi, "rain_prob": rain_prob,
            "condition": weather_desc, "source": source
        })
    except Exception as e:
        logger.error(f"Analysis Error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/order', methods=['POST'])
def place_order():
    try:
        data = request.json or {}
        customer_email = data.get('email', 'Guest')
        tree_type = data.get('tree_type', 'Restoration Sapling')
        qty = int(data.get('qty', 1))
        cost = float(data.get('cost', 0))
        address = data.get('address', 'Unspecified Sector')
        order_id = f"HP-{datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{random.randint(1000, 9999)}"

        # 1. Log to SQLite
        conn = get_db_connection()
        conn.execute('INSERT INTO tree_orders (order_id, customer_email, tree_type, quantity, total_cost, address, status) VALUES (?, ?, ?, ?, ?, ?, ?)',
                     (order_id, customer_email, tree_type, qty, cost, address, "In Processing"))
        conn.commit()
        conn.close()
        
        # 2. Log to MongoDB (Real-time storage matching verify_db expectations)
        if mongo_db is not None:
            try:
                mongo_db.tree_orders.insert_one({
                    "order_id": order_id,
                    "customer_email": customer_email,
                    "tree_type": tree_type,
                    "quantity": qty,
                    "total_cost": cost,
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

@app.route('/api/orders', methods=['GET'])
def get_orders():
    email = request.args.get('email')
    conn = get_db_connection()
    if email:
        rows = conn.execute('SELECT * FROM tree_orders WHERE customer_email = ? ORDER BY timestamp DESC', (email,)).fetchall()
    else:
        rows = conn.execute('SELECT * FROM tree_orders ORDER BY timestamp DESC LIMIT 20').fetchall()
    conn.close()
    return jsonify({
        "success": True,
        "orders": [dict(r) for r in rows]
    })

@app.route('/api/reports', methods=['GET'])
def get_reports():
    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM thermal_reports ORDER BY timestamp DESC LIMIT 20').fetchall()
    conn.close()
    return jsonify({
        "success": True,
        "reports": [dict(r) for r in rows]
    })

if __name__ == '__main__':
    app.run(debug=True, port=PORT)