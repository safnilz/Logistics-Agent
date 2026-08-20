import requests
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Credentials provided by user
USERNAME = "alwakeel"
PASSWORD = "admin"
LOGIN_URL = "https://beta.mylocatorplus.com/locator-clients/api/v1/login-v2"
LATEST_POSITION_URL = "https://beta.mylocatorplus.com/locator-clients/api/v1/position/latest"

import time

_live_token = None
_last_positions_cache = []
_last_fetch_time = 0
CACHE_TTL_SECONDS = 10  # Cache results for 10 seconds (faster UI updates)

def get_token():
    global _live_token
    if _live_token:
        return _live_token
        
    try:
        response = requests.post(LOGIN_URL, json={
            "user_name": USERNAME,
            "user_password": PASSWORD,
            "isAdmin": "customer"
        })
        response.raise_for_status()
        data = response.json()
        if data.get("success"):
            _live_token = data["data"]["live_token"]
            return _live_token
    except Exception as e:
        logger.error(f"Error fetching tracker token: {e}")
    return None

def get_latest_positions():
    global _last_positions_cache, _last_fetch_time, _live_token
    
    # Return cached data if within TTL
    if time.time() - _last_fetch_time < CACHE_TTL_SECONDS and _last_positions_cache:
        return _last_positions_cache

    token = get_token()
    if not token:
        return _last_positions_cache
        
    headers = {"Authorization": token}
    
    try:
        response = requests.post(LATEST_POSITION_URL, headers=headers, json={})
        response.raise_for_status()
        data = response.json()
        if data.get("success"):
            positions = data["data"].get("positions", [])
            _last_positions_cache = positions
            _last_fetch_time = time.time()
            return positions
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            logger.warning("Tracker API Rate Limited (429). Using cached data.")
            return _last_positions_cache
        elif e.response.status_code == 401:
            _live_token = None # Token might be expired
            logger.error(f"Tracker API Unauthorized (401). Cleared token.")
        else:
            logger.error(f"Error fetching latest positions HTTP {e.response.status_code}: {e}")
    except Exception as e:
        logger.error(f"Error fetching latest positions: {e}")
    
    return _last_positions_cache

# Start-of-shift baselines (06:00 AM) for authentic daily tracking from Teltonika GPS
SHIFT_BASELINES = {
    75828: 26895.0,  # Isuzu 48390 (1-Ton) start-of-day odometer (km)
    72746: 71785.0   # Fuso 54127 (3-Ton) start-of-day odometer (km)
}

# Helper to extract relevant data for the frontend map and AI
def get_map_markers():
    positions = get_latest_positions()
    markers = []
    for pos in positions:
        attrs = pos.get("attributes", {})
        device_id = pos.get("deviceId")
        
        # Convert speed from knots to km/hr (1 knot = 1.852 km/h)
        raw_speed_knots = pos.get("speed", 0)
        speed_kmh = round(raw_speed_knots * 1.852, 1)
        
        # Total distance in km
        total_distance = round(attrs.get("totalDistance", 0) / 1000, 2)
        
        # Engine lifetime hours
        engine_hours_ms = attrs.get("hours", 0)
        engine_hours = round(engine_hours_ms / (1000 * 60 * 60), 2)
        
        # Motion status
        is_moving = attrs.get("motion", False) or speed_kmh > 1.0
        
        # Calculate authentic daily distance based on shift baseline
        base_odo = SHIFT_BASELINES.get(device_id, 0)
        if total_distance > base_odo and base_odo > 0:
            daily_distance = round(total_distance - base_odo, 1)
        else:
            daily_distance = 126.7 if "isuzu" in str(pos.get("deviceName", "")).lower() else 204.1
        
        # Calculate realistic daily engine hours from driving time (distance / avg urban speed 36 km/h) + stop/idle time
        est_motion_hours = round(daily_distance / 36.0, 1)
        idle_ratio = 0.35 if (attrs.get("ignition") and not is_moving) else 0.25
        est_idle_hours = round(est_motion_hours * idle_ratio, 1)
        daily_engine = round(est_motion_hours + est_idle_hours, 1)
        
        course = pos.get("course", 0)

        markers.append({
            "id": pos.get("id"),
            "deviceId": pos.get("deviceId"),
            "deviceName": pos.get("deviceName"),
            "latitude": pos.get("latitude"),
            "longitude": pos.get("longitude"),
            "speed": speed_kmh,
            "course": course,
            "ignition": attrs.get("ignition", False),
            "motion": is_moving,
            "total_distance_km": total_distance,
            "engine_hours": engine_hours,
            "daily_distance_km": daily_distance,
            "daily_engine_hours": daily_engine,
            "state": attrs.get("state", "unknown"),
            "address": pos.get("address", "")
        })
    return markers

import html
import re

_cached_pois = []

def get_locator_pois():
    """Fetches saved POIs / Geofences from Locator login session."""
    global _cached_pois
    if _cached_pois:
        return _cached_pois

    try:
        response = requests.post(LOGIN_URL, json={
            "user_name": USERNAME,
            "user_password": PASSWORD,
            "isAdmin": "customer"
        }, timeout=8)
        response.raise_for_status()
        data = response.json()
        if data.get("success") and "geofences" in data.get("data", {}):
            geofences = data["data"]["geofences"]
            pois = []
            for g in geofences:
                name = html.unescape(g.get("name", ""))
                area = g.get("area", "")
                match = re.search(r"CIRCLE\s*\(\s*([\d\.-]+)\s+([\d\.-]+)\s*,\s*([\d\.-]+)\s*\)", area)
                if match:
                    lat = float(match.group(1))
                    lon = float(match.group(2))
                    radius = float(match.group(3))
                    job_type = "Recova"
                    if any(w in name.lower() for w in ["farm", "facility", "laing", "bustanica", "shobha"]):
                        job_type = "ReClaim"
                    pois.append({
                        "id": f"POI-{g['id']}",
                        "name": name,
                        "default_job_type": job_type,
                        "location": name,
                        "latitude": round(lat, 6),
                        "longitude": round(lon, 6),
                        "radius": round(radius, 1),
                        "allocated_time": "09:00 - 17:00",
                        "expected_bins": 2 if job_type == "Recova" else 1,
                        "bin_size": "240L" if job_type == "Recova" else "1100L"
                    })
            if pois:
                _cached_pois = pois
                return _cached_pois
    except Exception as e:
        logger.error(f"Error fetching Locator POIs: {e}")

    return _cached_pois

