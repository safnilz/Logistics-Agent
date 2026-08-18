# Logistics & Fleet Management AI Agent

An intelligent logistics and fleet coordination platform built for Ehfaaz Logistics, combining real-time vehicle telemetry, automated geofencing, route management, and an LLM-powered operations agent.

## 🚀 Features

- **Fleet Telemetry & Tracking**: Real-time GPS location, ignition, motion status, and speed tracking for fleet vehicles.
- **Automated Geofencing**: Automatic job completion detection when vehicles arrive within 150m radius of job sites.
- **Idle Alert System**: Detects unnecessary vehicle idling and generates alerts.
- **AI Logistics Agent**: Powered by Groq (llama-3.1-8b-instant) with function calling tools to:
  - Reassign and move stops between vehicles (move_stop)
  - Create on-demand collection jobs (create_job)
  - Analyze historical distance and fuel metrics (get_historical_report)
  - Generate financial and optimization audits (get_optimization_analysis)
- **Interactive UI**: React 19 + Vite dashboard featuring interactive maps (Leaflet), live job schedules, vehicle status cards, and chat assistant.

---

## 🛠️ Project Structure

\\\
.
├── backend/
│   ├── main.py             # FastAPI server & AI agent integration
│   ├── database.py         # SQLAlchemy models (Vehicle, Job, Client, Alert)
│   ├── tracker.py          # Telemetry and map markers provider
│   ├── seed.py             # Database seed script
│   ├── test_flow.py        # Integration test script
│   └── requirements.txt    # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── App.tsx         # Main dashboard & map UI
│   │   ├── main.tsx        # React entry point
│   │   └── index.css       # Tailwind / app styles
│   ├── package.json        # Frontend dependencies
│   └── vite.config.ts      # Vite configuration
└── .gitignore
\\\

---

## ⚡ Getting Started

### 1. Backend Setup

\\\ash
cd backend
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
\\\

Copy environment template and set your Groq API key:
\\\ash
cp .env.example .env
\\\

Run the backend:
\\\ash
python main.py
\\\
Server starts at \http://localhost:8000\.

### 2. Frontend Setup

\\\ash
cd frontend
npm install
npm run dev
\\\
Dashboard will be available at \http://localhost:5173\.
