import requests
import json
import time

API_BASE = "http://127.0.0.1:8000/api"

print("--- Starting Backend API Test ---")

# 1. Fetch current schedule
print("\n[1] Fetching Schedule...")
resp = requests.get(f"{API_BASE}/schedule")
print(f"Status: {resp.status_code}")
schedule = resp.json()
print(f"Vehicles: {len(schedule['vehicles'])}, Jobs: {len(schedule['jobs'])}")

# 2. Chat to create a job
print("\n[2] Asking AI to create a job for Client A...")
resp = requests.post(f"{API_BASE}/chat", json={"message": "Schedule a new 200kg ReClaim pickup for Client A."})
print(f"Status: {resp.status_code}")
chat_data = resp.json()
print(f"AI Reply: {chat_data['reply']}")
if 'suggested_action' in chat_data:
    action = chat_data['suggested_action']
    print(f"Action Proposed: {json.dumps(action, indent=2)}")
    
    # 3. Confirm action
    print("\n[3] Executing Action (Confirming Job Creation)...")
    resp = requests.post(f"{API_BASE}/execute-action", json=action)
    print(f"Status: {resp.status_code}")
    print(f"Execute Result: {resp.json()}")
else:
    print("WARNING: No action proposed by AI!")

# 4. Fetch schedule again to find the unassigned job
time.sleep(1)
print("\n[4] Fetching Schedule Again...")
resp = requests.get(f"{API_BASE}/schedule")
schedule = resp.json()
unassigned_jobs = [j for j in schedule['jobs'] if j['status'] == 'unassigned']
print(f"Unassigned Jobs: {len(unassigned_jobs)}")
if unassigned_jobs:
    new_job_id = unassigned_jobs[-1]['id'] # Get the latest one
    print(f"Found new unassigned job: {new_job_id}")

    # 5. Ask AI to move the job
    print(f"\n[5] Asking AI to assign job {new_job_id} to V1...")
    resp = requests.post(f"{API_BASE}/chat", json={"message": f"Assign job {new_job_id} to vehicle V1."})
    chat_data = resp.json()
    print(f"AI Reply: {chat_data['reply']}")
    if 'suggested_action' in chat_data:
        action = chat_data['suggested_action']
        print(f"Action Proposed: {json.dumps(action, indent=2)}")
        
        # 6. Confirm assignment
        print("\n[6] Executing Action (Confirming Assignment)...")
        resp = requests.post(f"{API_BASE}/execute-action", json=action)
        print(f"Status: {resp.status_code}")
        print(f"Execute Result: {resp.json()}")
    else:
        print("WARNING: No action proposed by AI for assignment!")

# 7. Final Schedule Check
print("\n[7] Final Schedule Check...")
resp = requests.get(f"{API_BASE}/schedule")
schedule = resp.json()
v1_jobs = [j for j in schedule['jobs'] if j['assigned_vehicle'] == 'V1']
print(f"Jobs assigned to V1: {len(v1_jobs)}")

print("\n--- Test Complete ---")
