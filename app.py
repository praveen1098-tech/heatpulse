from flask import Flask, render_template, request, jsonify, Response
from pymongo import MongoClient
import datetime
import random
import requests

# --- CALCULATION ENGINE ---
class HeatPulseEngine:
    def __init__(self):
        print("HeatPulse Physics Engine v4.0 Online")

    def run_calculation(self, temp, ndvi, humidity):
        """
        Formula: (Temp * (1 - NDVI)) + (Humidity / 20)
        High Score = High Risk (Urban Heat Island)
        """
        score = (temp * (1 - ndvi)) + (humidity / 20)
        return round(score, 2)

    def get_risk_profile(self, score):
        if score > 30:
            return "CRITICAL HEAT ISLAND", "text-red-500", "Immediate intervention: Increase canopy by 40% and install cool pavements."
        elif score > 18:
            return "THERMAL WARNING", "text-yellow-500", "Proactive: Urban thinning detected. Reforestation recommended."
        return "OPTIMAL ECOSYSTEM", "text-green-500", "Stable: High vegetation density providing natural cooling."

# --- FLASK SETUP ---
app = Flask(__name__)
engine = HeatPulseEngine()

# MongoDB Connection
client = MongoClient("mongodb://localhost:27017/")
db = client['heatpulse_db']
collection = db['thermal_reports']

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze():
    data = request.json
    lat = round(data.get('lat'), 4)
    lon = round(data.get('lon'), 4)

    # 1. Fetch Real Weather Data
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m"
        resp = requests.get(url, timeout=5).json()
        temp = resp['current']['temperature_2m']
        humidity = resp['current']['relative_humidity_2m']
    except:
        temp, humidity = 35.0, 45.0 # Fallback data

    # 2. Mock NDVI (Satellite Vegetation Index)
    ndvi = round(random.uniform(0.1, 0.7), 2)

    # 3. Perform Scientific Calculation
    score = engine.run_calculation(temp, ndvi, humidity)
    status, color, action = engine.get_risk_profile(score)

    # 4. Save to Database
    report_doc = {
        "timestamp": datetime.datetime.utcnow(),
        "lat": lat, "lon": lon,
        "metrics": {"temp": temp, "humidity": humidity, "ndvi": ndvi, "score": score},
        "status": status, "action": action
    }
    collection.insert_one(report_doc)

    return jsonify({
        "lat": lat, "lon": lon, "temp": temp, "humidity": humidity,
        "ndvi": ndvi, "score": score, "status": status, "color": color, "action": action
    })

@app.route('/api/export')
def export_csv():
    records = collection.find().sort("timestamp", -1)
    def generate():
        yield "Timestamp,Lat,Lon,Temp,Score,Status\n"
        for r in records:
            yield f"{r['timestamp']},{r['lat']},{r['lon']},{r['metrics']['temp']},{r['metrics']['score']},{r['status']}\n"
    return Response(generate(), mimetype='text/csv', headers={"Content-Disposition":"attachment; filename=heatpulse_data.csv"})

if __name__ == '__main__':
    app.run(debug=True, port=5001)