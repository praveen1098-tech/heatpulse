from pymongo import MongoClient
from collections import defaultdict

# Connect to your local MongoDB
client = MongoClient("mongodb://localhost:27017/") 
db = client['heatpulse_db']
reports_collection = db['thermal_reports']

# Fetch all records
all_reports = list(reports_collection.find())

if not all_reports:
    print("Your database is currently empty! Go click the map a few times first.")
else:
    # Group the records by their coordinates
    places_data = defaultdict(list)
    for report in all_reports:
        # Extract coordinates [longitude, latitude]
        lon, lat = report['location']['coordinates']
        location_key = f"Lat: {round(lat, 4)}, Lon: {round(lon, 4)}"
        places_data[location_key].append(report)

    print("\n" + "="*50)
    print("🌍 HEATPULSE DATABASE: DATA BY LOCATION")
    print("="*50)

    # Print the data out cleanly
    for location, records in places_data.items():
        print(f"\n📍 {location}")
        print("-" * 40)
        
        # Sort records by date (oldest to newest)
        records.sort(key=lambda x: x["timestamp"])
        
        for rec in records:
            date_str = rec['timestamp'].strftime('%Y-%m-%d')
            score = rec['metrics']['score']
            status = rec['status']
            print(f"  • Date: {date_str} | Score: {score:<5} | Status: {status}")
            
    print("\n" + "="*50)