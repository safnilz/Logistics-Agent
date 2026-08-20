import os
from database import engine, Base, SessionLocal, Vehicle, Job, Client
from dotenv import load_dotenv
from tracker import get_locator_pois

load_dotenv()

# Create tables
print("Creating database tables...")
Base.metadata.create_all(bind=engine)

db = SessionLocal()

def seed_data():
    print("Seeding vehicles...")
    if not db.query(Vehicle).first():
        v1 = Vehicle(id="V1", name="Isuzu 48390 (1-Ton)", max_weight_kg=1000.0, max_volume_m3=6.0)
        v2 = Vehicle(id="V2", name="Fuso 54127 (3-Ton)", max_weight_kg=3000.0, max_volume_m3=14.0)
        db.add_all([v1, v2])
        db.commit()

    print("Seeding clients from Locator POIs...")
    pois = get_locator_pois()
    if not pois:
        pois = [
            {"id": "POI-42399", "name": "Ehfaaz Facility", "default_job_type": "ReClaim", "location": "Al Barsha South", "latitude": 25.078304, "longitude": 55.236453, "radius": 125.0, "allocated_time": "08:00 - 18:00", "expected_bins": 5, "bin_size": "1100L"},
            {"id": "POI-42396", "name": "Eurofragance", "default_job_type": "Recova", "location": "Dubai Science Park", "latitude": 25.076491, "longitude": 55.24252, "radius": 150.0, "allocated_time": "09:00 - 12:00", "expected_bins": 2, "bin_size": "240L"},
            {"id": "POI-42369", "name": "Bloomberg LP - Dubai", "default_job_type": "Recova", "location": "DIFC / Downtown", "latitude": 25.21236, "longitude": 55.281437, "radius": 150.0, "allocated_time": "09:00 - 12:00", "expected_bins": 2, "bin_size": "240L"},
            {"id": "POI-43016", "name": "Sephora Dubai Mall", "default_job_type": "Recova", "location": "Downtown Dubai", "latitude": 25.197229, "longitude": 55.279747, "radius": 150.0, "allocated_time": "10:00 - 13:00", "expected_bins": 3, "bin_size": "240L"},
            {"id": "POI-42397", "name": "Ramada by Wyndham Downtown Dubai", "default_job_type": "Recova", "location": "Downtown Dubai", "latitude": 25.192874, "longitude": 55.272453, "radius": 150.0, "allocated_time": "11:00 - 14:00", "expected_bins": 2, "bin_size": "240L"},
            {"id": "POI-43017", "name": "Sephora Moe", "default_job_type": "Recova", "location": "Mall of the Emirates", "latitude": 25.120013, "longitude": 55.200284, "radius": 150.0, "allocated_time": "10:00 - 13:00", "expected_bins": 2, "bin_size": "240L"},
            {"id": "POI-42395", "name": "Waldorf Astoria Dubai Palm Jumeirah", "default_job_type": "Recova", "location": "Palm Jumeirah", "latitude": 25.134567, "longitude": 55.151119, "radius": 150.0, "allocated_time": "12:00 - 15:00", "expected_bins": 3, "bin_size": "240L"},
            {"id": "POI-42370", "name": "The Retreat Palm Dubai MGallery by Sofitel", "default_job_type": "Recova", "location": "Palm Jumeirah", "latitude": 25.139212, "longitude": 55.142465, "radius": 150.0, "allocated_time": "13:00 - 16:00", "expected_bins": 2, "bin_size": "240L"},
            {"id": "POI-42394", "name": "Ramada JBR", "default_job_type": "Recova", "location": "JBR Dubai", "latitude": 25.072287, "longitude": 55.129757, "radius": 150.0, "allocated_time": "14:00 - 17:00", "expected_bins": 2, "bin_size": "240L"},
            {"id": "POI-42410", "name": "CBRE", "default_job_type": "Recova", "location": "Dubai Marina", "latitude": 25.090698, "longitude": 55.152833, "radius": 200.0, "allocated_time": "09:00 - 12:00", "expected_bins": 2, "bin_size": "240L"},
            {"id": "POI-42413", "name": "Pallavi", "default_job_type": "Recova", "location": "Barsha Heights", "latitude": 25.090185, "longitude": 55.169852, "radius": 200.0, "allocated_time": "10:00 - 13:00", "expected_bins": 2, "bin_size": "240L"},
            {"id": "POI-42412", "name": "Mariska", "default_job_type": "Recova", "location": "Al Quoz", "latitude": 25.111526, "longitude": 55.368279, "radius": 200.0, "allocated_time": "11:00 - 14:00", "expected_bins": 2, "bin_size": "240L"},
            {"id": "POI-43018", "name": "Sephora Mcc", "default_job_type": "Recova", "location": "Mirdif City Centre", "latitude": 25.22195, "longitude": 55.433823, "radius": 150.0, "allocated_time": "10:00 - 13:00", "expected_bins": 2, "bin_size": "240L"},
            {"id": "POI-42400", "name": "Laing O'Rourke Ajman", "default_job_type": "ReClaim", "location": "Ajman Industrial", "latitude": 25.39384, "longitude": 55.577943, "radius": 463.3, "allocated_time": "08:00 - 14:00", "expected_bins": 1, "bin_size": "1100L"},
            {"id": "POI-47661", "name": "Bustanica dwc", "default_job_type": "ReClaim", "location": "Dubai South / DWC", "latitude": 24.861154, "longitude": 55.159049, "radius": 125.0, "allocated_time": "09:00 - 15:00", "expected_bins": 2, "bin_size": "1100L"},
            {"id": "POI-42478", "name": "Shobha Dip", "default_job_type": "ReClaim", "location": "Dubai Investment Park", "latitude": 24.975273, "longitude": 55.170246, "radius": 200.0, "allocated_time": "09:00 - 15:00", "expected_bins": 2, "bin_size": "1100L"},
            {"id": "POI-42398", "name": "Farm Location", "default_job_type": "ReClaim", "location": "Al Lisaili", "latitude": 24.728029, "longitude": 55.617836, "radius": 170.0, "allocated_time": "07:00 - 13:00", "expected_bins": 1, "bin_size": "CBM"},
            {"id": "POI-43019", "name": "Sephora Yass Mall", "default_job_type": "Recova", "location": "Yas Mall, Abu Dhabi", "latitude": 24.48882, "longitude": 54.60869, "radius": 150.0, "allocated_time": "10:00 - 14:00", "expected_bins": 2, "bin_size": "240L"},
            {"id": "POI-43020", "name": "Sephora Reem Mall", "default_job_type": "Recova", "location": "Reem Mall, Abu Dhabi", "latitude": 24.488368, "longitude": 54.400386, "radius": 150.0, "allocated_time": "10:00 - 14:00", "expected_bins": 2, "bin_size": "240L"},
            {"id": "POI-43021", "name": "Sephora Al Hamra Mall", "default_job_type": "Recova", "location": "Al Hamra Mall, RAK", "latitude": 25.682973, "longitude": 55.781791, "radius": 150.0, "allocated_time": "10:00 - 14:00", "expected_bins": 2, "bin_size": "240L"}
        ]

    for p in pois:
        existing = db.query(Client).filter((Client.id == p["id"]) | (Client.name == p["name"])).first()
        if not existing:
            c = Client(
                id=p["id"],
                name=p["name"],
                default_job_type=p.get("default_job_type", "Recova"),
                location=p.get("location", p["name"]),
                latitude=p.get("latitude"),
                longitude=p.get("longitude"),
                radius=p.get("radius", 150.0),
                allocated_time=p.get("allocated_time", "09:00 - 17:00"),
                expected_bins=p.get("expected_bins", 2),
                bin_size=p.get("bin_size", "240L")
            )
            db.add(c)
        else:
            existing.latitude = p.get("latitude")
            existing.longitude = p.get("longitude")
            existing.radius = p.get("radius", 150.0)
            existing.location = p.get("location", existing.name)
    
    db.commit()

    print("Seeding sample jobs linked to real client POIs...")
    if not db.query(Job).first():
        j1 = Job(id="JOB-001", type="Recova", client="Sephora Dubai Mall", location="Downtown Dubai", latitude=25.197229, longitude=55.279747, allocated_time="09:00 - 12:00", expected_bins=3, bin_size="240L", expected_weight_kg=400.0, assigned_vehicle="V1", status="pending", locked=False)
        j2 = Job(id="JOB-002", type="Recova", client="Bloomberg LP - Dubai", location="DIFC / Downtown", latitude=25.21236, longitude=55.281437, allocated_time="13:00 - 15:00", expected_bins=2, bin_size="240L", expected_weight_kg=1200.0, assigned_vehicle="V2", status="pending", locked=False)
        j3 = Job(id="JOB-003", type="ReClaim", client="Shobha Dip", location="Dubai Investment Park", latitude=24.975273, longitude=55.170246, allocated_time="10:00 - 16:00", expected_bins=1, bin_size="1100L", expected_weight_kg=600.0, assigned_vehicle=None, status="unassigned", locked=False)
        db.add_all([j1, j2, j3])
        db.commit()

    print("Seeding complete. Registered clients count:", db.query(Client).count())

if __name__ == "__main__":
    seed_data()
    db.close()

