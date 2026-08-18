import os
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from groq import Groq
import logging
import asyncio
import math
from datetime import datetime

from database import engine, Base, get_db, Vehicle, Job, Client, Alert, SessionLocal
from tracker import get_map_markers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Haversine Distance ---
def haversine(lat1, lon1, lat2, lon2):
    """Calculate distance in km between two lat/lon points."""
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return float('inf')
    R = 6371.0 # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# --- Fleet Automation Loop ---
async def fleet_monitoring_loop():
    logger.info("Fleet Monitoring Loop Started")
    while True:
        await asyncio.sleep(60) # Run every 60 seconds
        try:
            db = SessionLocal()
            markers = get_map_markers()
            if not markers:
                db.close()
                continue
                
            active_jobs = db.query(Job).filter(Job.status != "completed", Job.assigned_vehicle != None).all()
            
            for marker in markers:
                vid = marker['id'] # Device ID or name mapped to V1/V2 ideally. For now, match by vehicle name or assume V1/V2 maps to specific trucks if needed. But in jobs, assigned_vehicle is e.g. 'V1'. Let's match if the vehicle name contains the V1/V2 logic or we just check all active jobs against the markers.
                # Since the tracker has real truck names (e.g. Isuzu 48390) and our DB has V1, V2. We will map them manually here for demo:
                # E.g. V1 -> Isuzu, V2 -> Fuso. If V1/V2 is assigned, we look for Isuzu/Fuso marker.
                v_model = db.query(Vehicle).filter(Vehicle.id == vid).first()
                if not v_model:
                    # Try matching by name loosely
                    v_model = db.query(Vehicle).filter(Vehicle.name.ilike(f"%{marker['deviceName'].split()[0]}%")).first()
                
                matched_vid = v_model.id if v_model else None
                
                # 1. Idle Alert Check
                if marker['ignition'] and not marker['motion'] and marker['speed'] < 1:
                    # Check if we already alerted recently (simple check: any unresolved idle alert for this vehicle)
                    existing_alert = db.query(Alert).filter(Alert.vehicle_id == marker['deviceName'], Alert.type == "idle", Alert.resolved == False).first()
                    if not existing_alert:
                        new_alert = Alert(id=f"ALT-{int(datetime.now().timestamp())}", message=f"Truck {marker['deviceName']} is idling unnecessarily.", vehicle_id=marker['deviceName'], type="idle", timestamp=datetime.now().strftime("%H:%M:%S"))
                        db.add(new_alert)
                        db.commit()

                # 2. Geofencing Auto-Complete
                for job in active_jobs:
                    # If this marker belongs to the assigned vehicle
                    if matched_vid and job.assigned_vehicle == matched_vid:
                        dist = haversine(job.latitude, job.longitude, marker['latitude'], marker['longitude'])
                        if dist < 0.150: # within 150 meters
                            if not marker['motion']: # truck has stopped
                                job.status = "completed"
                                logger.info(f"Geofence Triggered: Auto-completed Job {job.id}")
                                new_alert = Alert(id=f"ALT-{int(datetime.now().timestamp())}-{job.id}", message=f"Auto-completed {job.id} at {job.client} (Geofence)", vehicle_id=marker['deviceName'], type="geofence", timestamp=datetime.now().strftime("%H:%M:%S"))
                                db.add(new_alert)
                                db.commit()
            db.close()
        except Exception as e:
            logger.error(f"Error in automation loop: {e}")

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(fleet_monitoring_loop())

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

# --- Groq Setup ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "mock_key_for_dev")
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY != "mock_key_for_dev" else None

class ChatRequest(BaseModel):
    message: str
    
from typing import Optional

class ActionRequest(BaseModel):
    type: str # "move_stop" or "create_job"
    job_id: Optional[str] = None
    vehicle_id: Optional[str] = None
    client_name: Optional[str] = None
    job_type: Optional[str] = None
    expected_weight_kg: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    allocated_time: Optional[str] = None
    expected_bins: Optional[int] = None
    bin_size: Optional[str] = None

class JobCreateRequest(BaseModel):
    client_name: str
    job_type: str
    expected_weight_kg: float
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    allocated_time: Optional[str] = None
    expected_bins: Optional[int] = None
    bin_size: Optional[str] = None

# --- AI Tools / Functions ---
def move_stop(db: Session, job_id: str, new_vehicle_id: str):
    target_job = db.query(Job).filter(Job.id == job_id).first()
    if not target_job:
        return f"Error: Job {job_id} not found."
        
    target_vehicle = db.query(Vehicle).filter(Vehicle.id == new_vehicle_id).first()
    if not target_vehicle:
        return f"Error: Vehicle {new_vehicle_id} not found."
        
    if target_job.locked:
        return f"Error: Job {job_id} is locked and cannot be moved."

    target_job.assigned_vehicle = new_vehicle_id
    target_job.status = "assigned"
    db.commit()
    
    return f"Success: Moved {job_id} to {new_vehicle_id}."

def create_job(db: Session, client_name: str, job_type: str, expected_weight_kg: float, lat: float = None, lon: float = None, allocated_time: str = None, expected_bins: int = None, bin_size: str = None):
    # Auto-generate an ID
    import uuid
    new_id = f"JOB-{str(uuid.uuid4())[:6].upper()}"
    
    # Try to find location from Client registry
    client = db.query(Client).filter(Client.name.ilike(f"%{client_name}%")).first()
    
    # Use provided values, fallback to client defaults if available
    location = client.location if client else "Unknown Location"
    final_lat = lat if lat else (client.latitude if client else None)
    final_lon = lon if lon else (client.longitude if client else None)
    final_time = allocated_time if allocated_time else (client.allocated_time if client else None)
    final_bins = expected_bins if expected_bins else (client.expected_bins if client else None)
    final_bin_size = bin_size if bin_size else (client.bin_size if client else None)
    
    new_job = Job(
        id=new_id,
        type=job_type,
        client=client_name,
        location=location,
        latitude=final_lat,
        longitude=final_lon,
        allocated_time=final_time,
        expected_bins=final_bins,
        bin_size=final_bin_size,
        expected_weight_kg=expected_weight_kg,
        assigned_vehicle=None,
        status="unassigned",
        locked=False
    )
    db.add(new_job)
    db.commit()
    
    return f"Success: Created {new_job.type} job {new_id} for {client_name}."

def get_historical_report(report_type: str):
    if report_type == "distance":
        return "Monthly Distance Covered:\nIsuzu 48390: May=4500km, Jun=4850km, Jul=5200km\nFuso 54127: May=3200km, Jun=3100km, Jul=3350km"
    elif report_type == "fuel":
        return "Monthly Fuel Consumption:\nIsuzu 48390: May=1125L, Jun=1212L, Jul=1300L\nFuso 54127: May=800L, Jun=775L, Jul=837L"
    else:
        return "Historical data for this metric is not available. Only distance and fuel are tracked."

def get_optimization_analysis(vehicle_id: str = None):
    # Simulated financial audit
    audit = "Financial & Optimization Audit:\n"
    if not vehicle_id or "isuzu" in vehicle_id.lower():
        audit += "Isuzu 48390: Operating at +12% fuel variance. Approximately 3.5L (10.6 AED) wasted today due to 45 minutes of excessive idling at collection sites. Optimization Action: Enforce a strict 5-minute engine cutoff policy during loading.\n"
    if not vehicle_id or "fuso" in vehicle_id.lower():
        audit += "Fuso 54127: Operating at -4% fuel variance (Highly Efficient). However, route optimization is poor as the vehicle is severely under-utilized (0 kg load). Optimization Action: Re-assign pending jobs from Isuzu to Fuso to balance wear-and-tear and maximize ROI on driver wages.\n"
    return audit

# --- Endpoints ---

@app.get("/api/schedule")
def get_schedule(db: Session = Depends(get_db)):
    """Returns schedule from PostgreSQL with Live ETAs."""
    vehicles = db.query(Vehicle).all()
    jobs = db.query(Job).all()
    markers = get_map_markers()
    
    jobs_response = []
    for j in jobs:
        eta = None
        if j.status != "completed" and j.assigned_vehicle and j.latitude and j.longitude:
            v_model = db.query(Vehicle).filter(Vehicle.id == j.assigned_vehicle).first()
            if v_model:
                # Hardcode mapping for the demo since DB names (Truck 1) don't match API names (Isuzu)
                mapping = {"V1": "Isuzu", "V2": "Fuso"}
                expected_device_name = mapping.get(j.assigned_vehicle, v_model.name.split()[0])
                
                matched_marker = next((m for m in markers if expected_device_name.lower() in m['deviceName'].lower()), None)
                if matched_marker and matched_marker['latitude']:
                    dist = haversine(j.latitude, j.longitude, matched_marker['latitude'], matched_marker['longitude'])
                    speed = matched_marker['speed'] if matched_marker['speed'] > 10 else 30 # assume 30km/h if stopped/slow
                    eta_mins = round((dist / speed) * 60)
                    eta = eta_mins

        jobs_response.append({
            "id": j.id, "type": j.type, "client": j.client, "location": j.location, 
            "expected_weight_kg": j.expected_weight_kg, "assigned_vehicle": j.assigned_vehicle, 
            "status": j.status, "locked": j.locked, "eta_minutes": eta
        })

    return {
        "vehicles": [
            {"id": v.id, "name": v.name, "max_weight_kg": v.max_weight_kg, "max_volume_m3": v.max_volume_m3} 
            for v in vehicles
        ],
        "jobs": jobs_response
    }

@app.get("/api/alerts")
def get_alerts(db: Session = Depends(get_db)):
    """Return all unresolved alerts."""
    alerts = db.query(Alert).filter(Alert.resolved == False).order_by(Alert.timestamp.desc()).all()
    return [{"id": a.id, "message": a.message, "vehicle_id": a.vehicle_id, "type": a.type, "timestamp": a.timestamp} for a in alerts]


@app.get("/api/tracker/live")
def get_live_tracker():
    """Returns live vehicle positions from Locator API."""
    return get_map_markers()

class ClientCreateRequest(BaseModel):
    name: str
    default_job_type: str
    location: str
    latitude: float = None
    longitude: float = None
    allocated_time: str = None
    expected_bins: int = None
    bin_size: str = None

@app.get("/api/clients")
def get_clients(db: Session = Depends(get_db)):
    """Returns registered clients."""
    clients = db.query(Client).all()
    return [{"id": c.id, "name": c.name, "default_job_type": c.default_job_type, "location": c.location, "latitude": c.latitude, "longitude": c.longitude, "allocated_time": c.allocated_time, "expected_bins": c.expected_bins, "bin_size": c.bin_size} for c in clients]

@app.post("/api/clients")
def create_client_endpoint(req: ClientCreateRequest, db: Session = Depends(get_db)):
    """Register a new client."""
    import uuid
    new_id = f"C-{str(uuid.uuid4())[:4].upper()}"
    new_client = Client(id=new_id, name=req.name, default_job_type=req.default_job_type, location=req.location, latitude=req.latitude, longitude=req.longitude, allocated_time=req.allocated_time, expected_bins=req.expected_bins, bin_size=req.bin_size)
    db.add(new_client)
    db.commit()
    return {"status": "Success", "id": new_id}

@app.post("/api/jobs")
def create_job_endpoint(req: JobCreateRequest, db: Session = Depends(get_db)):
    """Manual endpoint to create a job from UI."""
    return {"status": create_job(db, req.client_name, req.job_type, req.expected_weight_kg, req.latitude, req.longitude, req.allocated_time, req.expected_bins, req.bin_size)}

@app.post("/api/chat")
def chat_with_agent(req: ChatRequest, db: Session = Depends(get_db)):
    """
    Sends the user's message to Groq. 
    Groq decides to call functions like `move_stop` or `create_job`.
    """
    # Fetch current state to give AI context
    vehicles = db.query(Vehicle).all()
    jobs = db.query(Job).all()
    clients = db.query(Client).all()
    
    context = "Registered Clients:\n"
    for c in clients:
        context += f"- {c.name} ({c.default_job_type} at {c.location})\n"
        
    context += "\nCurrent Schedule State:\n"
    live_markers = get_map_markers()
    
    for v in vehicles:
        assigned_jobs = [j for j in jobs if j.assigned_vehicle == v.id]
        completed_jobs = [j for j in assigned_jobs if j.status == "completed"]
        pending_jobs = [j for j in assigned_jobs if j.status != "completed"]
        current_weight = sum(j.expected_weight_kg for j in assigned_jobs)
        
        context += f"- Vehicle {v.name} ({v.id}): Capacity {v.max_weight_kg}kg, Current Load: {current_weight}kg. Completed: {len(completed_jobs)}, Remaining: {len(pending_jobs)}\n"
        
        for j in pending_jobs:
            eta_str = "Unknown"
            mapping = {"V1": "Isuzu", "V2": "Fuso"}
            expected_device_name = mapping.get(j.assigned_vehicle, v.name.split()[0])
            matched_marker = next((m for m in live_markers if expected_device_name.lower() in m['deviceName'].lower()), None)
            
            if matched_marker and matched_marker['latitude'] and j.latitude and j.longitude:
                dist = haversine(j.latitude, j.longitude, matched_marker['latitude'], matched_marker['longitude'])
                speed = matched_marker['speed'] if matched_marker['speed'] > 10 else 30
                eta_str = f"{round((dist / speed) * 60)} mins"
            
            context += f"  > Job {j.id} ({j.client} at {j.location}): {j.expected_weight_kg}kg, Status: {j.status}, ETA: {eta_str}\n"
        
    context += "\nLive Vehicle KPIs:\n"
    if live_markers:
        for m in live_markers:
            context += f"- {m['deviceName']} ({m['id']}): Speed {m['speed']} km/h, Ignition {'ON' if m['ignition'] else 'OFF'}, Motion: {'Moving' if m['motion'] else 'Stopped'}, Engine Hours: {m.get('engine_hours', 0)}h, Distance: {m.get('total_distance_km', 0)}km\n"
    else:
        context += "- No live telemetry available.\n"
    
    context += "\nUnassigned Jobs:\n"
    for j in jobs:
        if not j.assigned_vehicle:
            context += f"- Job {j.id} ({j.client} at {j.location}): {j.expected_weight_kg}kg\n"
            
    system_prompt = f"""You are the Ehfaaz Logistics AI Agent.
Your job is to act as a world-class fleet analyst and logistics coordinator for Ehfaaz.
You must help plan routes, manage vehicle capacities, and optimize fleet performance based on live KPIs (utilization, idle time, distance).
Always maintain a professional, conversational, and highly analytical tone.

CRITICAL RULES:
1. Never exceed a vehicle's max weight capacity.
2. If a user asks to move or assign a job, you MUST use the `move_stop` tool. You must use an exact `job_id` from the Current Schedule State.
3. If a user asks to schedule a new collection for a client, you MUST use the `create_job` tool.
4. Be concise and conversational. Do NOT output raw data structures, XML, JSON, or code blocks to the user.
5. Only discuss the jobs, clients, and vehicles listed below. Do NOT invent new locations or names.
6. DO NOT hallucinate tool names or attempt to call tools that do not exist (like `get_vehicle` or `brave_search`). You ONLY have access to `move_stop`, `create_job`, `get_historical_report`, and `get_optimization_analysis`.
7. When asked to analyze, evaluate, or report on a truck's live performance, DO NOT USE ANY TOOLS. Simply answer directly in conversational text using the data in the "Live Vehicle KPIs" section below.
8. If the user asks for historical data, past performance, or month-over-month comparisons, you MUST call the `get_historical_report` tool to fetch the data before answering.
9. If the user asks how to optimize operations, save money, check fuel economy, or analyze route efficiency, you MUST call the `get_optimization_analysis` tool.

ANALYTICS GUIDELINES:
- **Locations & Progress**: Look at the "Current Schedule State" to report where the trucks are assigned, how many jobs are completed vs remaining, and what the ETA is to the next client location.
- **Speed & Traffic**: If a truck's speed is >80 km/h, it might be speeding. If a truck's speed is <20 km/h but motion is "Moving", assume it is in heavy traffic.
- **Idle Time**: If a truck has Ignition ON but Motion is Stopped and Speed is 0, it is idling unnecessarily. Suggest having the driver turn off the engine.
- **Optimization**: Propose moving unassigned jobs to the vehicle with the most remaining capacity, or suggest re-routing based on ETAs.

{context}
"""

    if not client:
        return {
            "reply": "I am running in mock mode. If you asked me to move a stop, I would suggest an action.",
            "suggested_action": {
                "type": "move_stop",
                "job_id": "JOB-003", 
                "vehicle_id": "V1",
                "reason": "Vehicle 1 has enough capacity for this ReClaim pickup."
            }
        }
    
    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": req.message}
        ]
        
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "move_stop",
                    "description": "Propose moving an existing job to a new vehicle.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "job_id": {"type": "string", "description": "The ID of the job (e.g. JOB-003)"},
                            "vehicle_id": {"type": "string", "description": "The ID of the vehicle (e.g. V1)"},
                            "reason": {"type": "string", "description": "Brief reason for the move."}
                        },
                        "required": ["job_id", "vehicle_id", "reason"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_job",
                    "description": "Create a new collection job for a registered client.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "client_name": {"type": "string", "description": "The exact name of the client"},
                            "job_type": {"type": "string", "description": "Type of job: 'Recova' or 'ReClaim'"},
                            "expected_weight_kg": {"type": "number", "description": "The expected weight in kg"},
                            "latitude": {"type": ["number", "null"], "description": "Optional latitude. Leave out if not provided."},
                            "longitude": {"type": ["number", "null"], "description": "Optional longitude. Leave out if not provided."},
                            "allocated_time": {"type": ["string", "null"], "description": "Optional time window (e.g. 10:00-12:00). Leave out if not provided."},
                            "expected_bins": {"type": ["integer", "null"], "description": "Optional number of bins expected. Leave out if not provided."},
                            "bin_size": {"type": ["string", "null"], "description": "Optional bin size (e.g. 240L). Leave out if not provided."},
                            "reason": {"type": "string", "description": "Brief reason for creating the job to show the user."}
                        },
                        "required": ["client_name", "job_type", "expected_weight_kg", "reason"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_historical_report",
                    "description": "Fetch historical data (e.g. last 3 months) for analytics.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "report_type": {"type": "string", "enum": ["distance", "fuel"], "description": "The type of historical data to retrieve."}
                        },
                        "required": ["report_type"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_optimization_analysis",
                    "description": "Run a financial and route optimization audit to find cost savings.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "vehicle_id": {"type": ["string", "null"], "description": "Optional vehicle ID to audit a specific truck."}
                        }
                    }
                }
            }
        ]

        for _ in range(3):
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=messages,
                tools=tools,
                tool_choice="auto"
            )
            
            msg = response.choices[0].message
            
            if not msg.tool_calls:
                return {"reply": msg.content or "No response generated.", "suggested_action": None}
                
            tool_call = msg.tool_calls[0]
            
            if tool_call.function.name == "get_historical_report":
                import json
                args = json.loads(tool_call.function.arguments)
                report_data = get_historical_report(args.get("report_type", "distance"))
                
                # Append assistant call and tool response to let model formulate final answer
                assistant_msg = msg.model_dump()
                assistant_msg = {k: v for k, v in assistant_msg.items() if v is not None} # remove Nones
                messages.append(assistant_msg)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_call.function.name,
                    "content": report_data
                })
                continue # Loop again to get text completion
                
            if tool_call.function.name == "get_optimization_analysis":
                import json
                args = json.loads(tool_call.function.arguments)
                audit_data = get_optimization_analysis(args.get("vehicle_id"))
                
                assistant_msg = msg.model_dump()
                assistant_msg = {k: v for k, v in assistant_msg.items() if v is not None}
                messages.append(assistant_msg)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_call.function.name,
                    "content": audit_data
                })
                continue

            # If it's a UI action tool (move_stop or create_job), break out and prompt user
            import json
            args = json.loads(tool_call.function.arguments)
            suggested_action = {"type": tool_call.function.name, **args}
            if "reason" not in suggested_action:
                suggested_action["reason"] = "Suggested by AI."
            reply = "I have prepared an action proposal. Please review."
            return {"reply": reply, "suggested_action": suggested_action}

        return {"reply": "Sorry, I took too long to fetch the data. Please try again.", "suggested_action": None}
        
    except Exception as e:
        logger.error(f"Groq API Error: {e}")
        return {"reply": f"Sorry, I encountered an error communicating with the AI. Make sure GROQ_API_KEY is valid. Error: {str(e)}"}

@app.post("/api/execute-action")
def execute_action(req: ActionRequest, db: Session = Depends(get_db)):
    """Endpoint for the UI to confirm an AI-suggested action."""
    if req.type == "move_stop":
        result = move_stop(db, req.job_id, req.vehicle_id)
    elif req.type == "create_job":
        result = create_job(db, req.client_name, req.job_type, req.expected_weight_kg, req.latitude, req.longitude, req.allocated_time, req.expected_bins, req.bin_size)
    else:
        result = "Unknown action type."
    return {"status": result}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
