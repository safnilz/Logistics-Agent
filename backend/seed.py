import os
from database import engine, Base, SessionLocal, Vehicle, Job, Client
from dotenv import load_dotenv

load_dotenv()

# Create tables
print("Creating database tables...")
Base.metadata.create_all(bind=engine)

db = SessionLocal()

def seed_data():
    # If clients exist, don't reseed
    if db.query(Client).first():
        print("Database already seeded!")
        return

    print("Seeding clients...")
    c1 = Client(id="C1", name="Client A", default_job_type="Recova", location="Downtown", latitude=25.2048, longitude=55.2708, allocated_time="09:00 - 12:00", expected_bins=2, bin_size="240L")
    c2 = Client(id="C2", name="Client B", default_job_type="Recova", location="Business Bay", latitude=25.1856, longitude=55.2666, allocated_time="13:00 - 15:00", expected_bins=5, bin_size="1100L")
    c3 = Client(id="C3", name="Client C", default_job_type="ReClaim", location="JLT", latitude=25.0773, longitude=55.1403, allocated_time="10:00 - 16:00", expected_bins=1, bin_size="CBM")
    db.add_all([c1, c2, c3])
    db.commit()

    print("Seeding vehicles...")
    v1 = Vehicle(id="V1", name="Truck 1", max_weight_kg=5000.0, max_volume_m3=20.0)
    v2 = Vehicle(id="V2", name="Truck 2", max_weight_kg=3000.0, max_volume_m3=12.0)
    db.add_all([v1, v2])
    db.commit()

    print("Seeding jobs...")
    j1 = Job(id="JOB-001", type="Recova", client="Client A", location="Downtown", latitude=25.2048, longitude=55.2708, allocated_time="09:00 - 12:00", expected_bins=2, bin_size="240L", expected_weight_kg=500.0, assigned_vehicle="V1", status="pending", locked=False)
    j2 = Job(id="JOB-002", type="Recova", client="Client B", location="Business Bay", latitude=25.1856, longitude=55.2666, allocated_time="13:00 - 15:00", expected_bins=5, bin_size="1100L", expected_weight_kg=1200.0, assigned_vehicle="V1", status="pending", locked=False)
    j3 = Job(id="JOB-003", type="ReClaim", client="Client C", location="JLT", latitude=25.0773, longitude=55.1403, allocated_time="10:00 - 16:00", expected_bins=1, bin_size="CBM", expected_weight_kg=800.0, assigned_vehicle=None, status="unassigned", locked=False)
    db.add_all([j1, j2, j3])
    db.commit()
    print("Seeding complete.")

if __name__ == "__main__":
    seed_data()
    db.close()
