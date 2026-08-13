from pymongo import MongoClient

def run_diagnostics():
    try:
        client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=2000)
        db = client['heatpulse_db']
        client.server_info()
        
        print("\n" + "="*50)
        print("🟢 HEATPULSE MASTER DATABASE DIAGNOSTICS 🟢")
        print("="*50)

        print("\n[👤 REGISTERED CUSTOMERS]")
        customers = list(db.customer.find())
        if not customers: print("   No customers registered yet.")
        else:
            for customer in customers: print(f"   👤 Name: {customer.get('name', 'Unknown')} | 📧 Email: {customer.get('email', 'Unknown')}")

        print("\n[🌡️ LATEST THERMAL CALCULATIONS]")
        reports = list(db.thermal_reports.find().sort("timestamp", -1).limit(5))
        if not reports: print("   No reports generated yet.")
        else:
            for report in reports:
                d = report.get('data', {})
                print(f"   📍 Coord: {report.get('lat')}, {report.get('lon')} | Temp: {d.get('temp')}°C | Trees Needed: {d.get('trees_needed', 'N/A')}")

        print("\n[💰 LATEST TREE ORDERS]")
        orders = list(db.tree_orders.find().sort("timestamp", -1).limit(5))
        if not orders: print("   No orders placed yet.")
        else:
            for order in orders:
                print(f"   📧 Buyer: {order.get('customer_email', 'Guest')}")
                print(f"   🛒 Ordered: {order.get('quantity')}x {order.get('tree_type')}")
                print(f"   💳 Paid: ₹{order.get('total_cost')}")
                # NEW: Printing the address from the database
                print(f"   📍 Address: {order.get('address', 'N/A')}")
                print("   " + "-" * 40)
                
        print("\n" + "="*50 + "\n")

    except Exception as e:
        print(f"\n❌ DATABASE ERROR: {e}")

if __name__ == "__main__":
    run_diagnostics()