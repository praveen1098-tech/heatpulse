import sqlite3
import os

try:
    from pymongo import MongoClient
    HAS_PYMONGO = True
except ImportError:
    MongoClient = None
    HAS_PYMONGO = False

DB_FILE = os.getenv("DB_FILE", "heatpulse.db")

def run_diagnostics():
    print("\n" + "="*60)
    print("🟢  HEATPULSE MASTER DATABASE DIAGNOSTICS  🟢")
    print("="*60)

    # 1. SQLite Diagnostics
    print("\n--- [💾 SQLITE LOCAL STORAGE (Primary)] ---")
    if os.path.exists(DB_FILE):
        try:
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Registered Users
            users = cursor.execute('SELECT id, name, email, created_at FROM users').fetchall()
            print(f"\n[👤 REGISTERED USERS: {len(users)}]")
            if not users:
                print("   No users registered yet.")
            else:
                for u in users:
                    print(f"   👤 ID: {u['id']} | Name: {u['name']} | 📧 Email: {u['email']} | Joined: {u['created_at']}")

            # Thermal Calculations
            reports = cursor.execute('SELECT id, lat, lon, temp, score, trees_needed, timestamp FROM thermal_reports ORDER BY timestamp DESC LIMIT 5').fetchall()
            print(f"\n[🌡️ RECENT THERMAL CALCULATIONS: {len(reports)}]")
            if not reports:
                print("   No reports generated yet.")
            else:
                for r in reports:
                    print(f"   📍 Coord: {r['lat']}, {r['lon']} | Temp: {r['temp']}°C | Score: {r['score']} | Trees Needed: {r['trees_needed']} | Time: {r['timestamp']}")

            # Orders
            orders = cursor.execute('SELECT id, order_id, customer_email, tree_type, quantity, total_cost, address, status, timestamp FROM tree_orders ORDER BY timestamp DESC LIMIT 5').fetchall()
            print(f"\n[💰 RECENT TREE ORDERS: {len(orders)}]")
            if not orders:
                print("   No orders placed yet.")
            else:
                for o in orders:
                    print(f"   🆔 Order: {o['order_id']} | Status: {o['status']}")
                    print(f"   📧 Buyer: {o['customer_email']}")
                    print(f"   🛒 Asset: {o['quantity']}x {o['tree_type']}")
                    print(f"   💳 Total: ₹{o['total_cost']}")
                    print(f"   📍 Address: {o['address']}")
                    print("   " + "-" * 40)

            conn.close()
        except Exception as e:
            print(f"   ⚠️ SQLite Read Error: {e}")
    else:
        print(f"   Database file '{DB_FILE}' does not exist yet (will be created on first app run).")

    # 2. MongoDB Diagnostics
    print("\n--- [🍃 MONGODB DISTRIBUTED CLUSTER (Secondary)] ---")
    if not HAS_PYMONGO or not MongoClient:
        print("   ℹ️ PyMongo package not installed in active environment. Application operates in standalone SQLite mode.")
    else:
        try:
            mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
            client = MongoClient(mongo_uri, serverSelectionTimeoutMS=1500)
            client.server_info()
            db = client['heatpulse_db']
            print("   ✅ Connected to MongoDB cluster successfully.")

            customers = list(db.customer.find())
            print(f"\n[👤 MONGODB CUSTOMERS: {len(customers)}]")
            for c in customers:
                print(f"   👤 Name: {c.get('name', 'Unknown')} | 📧 Email: {c.get('email', 'Unknown')}")

            reports = list(db.thermal_reports.find().sort("timestamp", -1).limit(5))
            print(f"\n[🌡️ MONGODB THERMAL REPORTS: {len(reports)}]")
            for r in reports:
                d = r.get('data', {})
                print(f"   📍 Coord: {r.get('lat')}, {r.get('lon')} | Temp: {d.get('temp')}°C | Trees Needed: {d.get('trees_needed', 'N/A')}")

            orders = list(db.tree_orders.find().sort("timestamp", -1).limit(5))
            print(f"\n[💰 MONGODB TREE ORDERS: {len(orders)}]")
            for o in orders:
                print(f"   🆔 Order: {o.get('order_id', 'N/A')}")
                print(f"   📧 Buyer: {o.get('customer_email', 'Guest')}")
                print(f"   🛒 Ordered: {o.get('quantity')}x {o.get('tree_type')}")
                print(f"   💳 Paid: ₹{o.get('total_cost')}")
                print(f"   📍 Address: {o.get('address', 'N/A')}")
                print("   " + "-" * 40)
        except Exception as e:
            print(f"   ℹ️ MongoDB cluster offline or unreachable ({e}). Application operates seamlessly via SQLite fallback.")

    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    run_diagnostics()