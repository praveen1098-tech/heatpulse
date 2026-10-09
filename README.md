# 🌿 HeatPulse | Premium Earth Restoration Sentinel

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.1.3-000000?style=flat-square&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![SQLite](https://img.shields.io/badge/SQLite-Local_Storage-003B57?style=flat-square&logo=sqlite&logoColor=white)](https://sqlite.org)
[![MongoDB](https://img.shields.io/badge/MongoDB-Optional_Sync-47A248?style=flat-square&logo=mongodb&logoColor=white)](https://mongodb.com)
[![OpenWeatherMap](https://img.shields.io/badge/OpenWeatherMap-Live_Telemetry-EB6E4B?style=flat-square&logo=openweathermap&logoColor=white)](https://openweathermap.org/)
[![Google Identity](https://img.shields.io/badge/Google_Sign--In-GIS_Ready-4285F4?style=flat-square&logo=google&logoColor=white)](https://developers.google.com/identity)

**HeatPulse** is a real-time thermal monitoring, ecological analysis, and earth restoration platform. It detects urban heat islands, assesses canopy deficits using live weather satellite feeds, and translates environmental deficits into actionable, orderable nature-based restorative assets.

---

## 🚀 Key Features

- **🛰️ Live OpenWeatherMap Satellite Feed**: Real-time atmospheric metrics (temperature, humidity, cloud cover, and sky conditions) fetched per geo-coordinate grid.
- **🔐 Google Sign-In & Secure Auth**: Seamless authentication via Google Identity Services (GIS), custom Google account selector, and salted PBKDF2 hashed password credentials.
- **🗺️ Interactive Sentinel Map**: Built on Leaflet.js with CartoDB tiles and Nominatim reverse geocoding for pinpoint sector identification.
- **📊 Real-Time Thermal & NDVI Engine**: Proprietary calculation engine assessing canopy gaps, energy cooling loads, and restorative tree units required.
- **🛒 Ecological Asset Store**: Direct procurement and allocation of climate-resilient tree species (Neem, Peepal, Pongamia, Banyan).
- **💾 Dual-Database Architecture**: SQLite as the high-availability local database with automatic real-time sync to MongoDB when connected.
- **🌌 Dynamic Celestial Sky Engine**: Interactive day-night sky simulation with orbiting sun/moon and twinkling stars.
- **🔍 CLI Diagnostic Tooling**: `verify_db.py` script for instant inspection of registered users, thermal calculations, and tree orders.

---

## 🛠 Tech Stack

- **Backend**: Python 3.11+ / Flask 3.1.3, Werkzeug, Requests, Python-Dotenv
- **Databases**: SQLite3 (primary local storage) + PyMongo (distributed cluster sync)
- **External APIs**: OpenWeatherMap API, Open-Meteo API, OpenStreetMap / Nominatim
- **Authentication**: Google Identity Services (GIS) OAuth + PBKDF2:SHA256
- **Frontend**: Vanilla HTML5/CSS3, Tailwind CSS, Leaflet.js, Chart.js

---

## 💻 Quick Start & Setup

### 1. Prerequisites
- Python 3.11 or higher
- Git

### 2. Clone & Setup Environment
```bash
# Clone the repository
git clone https://github.com/praveen1098-tech/heatpulse.git
cd heatpulse

# Create and activate Python virtual environment
python3 -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate

# Install required packages
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Create a `.env` file in the project root (see `.env.example`):
```env
# OpenWeatherMap API Key
OPENWEATHER_API_KEY=your_openweathermap_api_key_here

# Google OAuth 2.0 Client ID (Optional for Google Identity Services)
GOOGLE_CLIENT_ID=

# Server Configuration
PORT=5001
DB_FILE=heatpulse.db

# MongoDB URI (Optional)
MONGO_URI=mongodb://localhost:27017
```

### 4. Run the Application
```bash
python app.py
```
Open **[http://localhost:5001](http://localhost:5001)** in your browser.

---

## 🔍 Database Diagnostics & Inspection

Inspect registered users, recent calculations, and placed orders across both SQLite and MongoDB:
```bash
python verify_db.py
```

---

## 🌐 API Reference

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/` | `GET` | Main Sentinel dashboard interface |
| `/api/health` | `GET` | Health status and integration status (OpenWeatherMap & Google OAuth) |
| `/api/auth/google` | `POST` | Authenticate Google credentials (GIS ID token or account profile) |
| `/api/signup` | `POST` | Register a new user with email & password |
| `/api/login` | `POST` | Authenticate an existing user |
| `/api/analyze` | `POST` | Analyze coordinates (`lat`, `lon`), fetch OpenWeatherMap data, return risk score |
| `/api/order` | `POST` | Place tree restorative asset orders with unique tracking ID |
| `/api/orders` | `GET` | Retrieve order history (filter by `?email=...`) |
| `/api/reports` | `GET` | Retrieve latest thermal calculation reports |

---

## 📄 License
ISC License © 2026 Praveen Reddy

