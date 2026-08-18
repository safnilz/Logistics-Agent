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

# Helper to extract relevant data for the frontend map and AI
def get_map_markers():
    positions = get_latest_positions()
    markers = []
    for pos in positions:
        attrs = pos.get("attributes", {})
        
        # Convert speed from knots to km/hr (1 knot = 1.852 km/h)
        raw_speed_knots = pos.get("speed", 0)
        speed_kmh = round(raw_speed_knots * 1.852, 1)
        
        # Total distance is often in meters or kilometers depending on Traccar config, usually meters
        total_distance = round(attrs.get("totalDistance", 0) / 1000, 2) # convert to km
        
        # Engine hours (usually in ms)
        engine_hours_ms = attrs.get("hours", 0)
        engine_hours = round(engine_hours_ms / (1000 * 60 * 60), 2)
        
        # Motion status
        is_moving = attrs.get("motion", False)
        
        # Mock daily metrics for prototype by using modulo to get realistic daily values
        daily_distance = round(total_distance % 250, 2) if total_distance > 0 else 0
        daily_engine = round(engine_hours % 12, 2) if engine_hours > 0 else 0
        
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
