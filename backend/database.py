from sqlalchemy import Column, String, Integer, Float, Boolean, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# We use the existing reclaimops database if provided, else fallback to local sqlite for dev testing
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://user:password@localhost:5432/reclaimops")

if "user:password" in DATABASE_URL:
    print("Using local SQLite database for development.")
    DATABASE_URL = "sqlite:///./sql_app.db"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Client(Base):
    __tablename__ = "ai_agent_clients"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String)
    default_job_type = Column(String) # "Recova" or "ReClaim"
    location = Column(String)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    allocated_time = Column(String, nullable=True)
    expected_bins = Column(Integer, nullable=True)
    bin_size = Column(String, nullable=True)

class Vehicle(Base):
    __tablename__ = "ai_agent_vehicles"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String)
    max_weight_kg = Column(Float)
    max_volume_m3 = Column(Float)

class Job(Base):
    __tablename__ = "ai_agent_jobs"
    
    id = Column(String, primary_key=True, index=True)
    type = Column(String) # Recova or ReClaim
    client = Column(String)
    location = Column(String)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    allocated_time = Column(String, nullable=True)
    expected_bins = Column(Integer, nullable=True)
    bin_size = Column(String, nullable=True)
    expected_weight_kg = Column(Float)
    assigned_vehicle = Column(String, nullable=True) # V1, V2 etc.
    status = Column(String) # unassigned, assigned, completed
    locked = Column(Boolean, default=False)

class Alert(Base):
    __tablename__ = "ai_agent_alerts"
    
    id = Column(String, primary_key=True, index=True)
    message = Column(String)
    vehicle_id = Column(String, nullable=True)
    type = Column(String) # "idle", "geofence"
    timestamp = Column(String)
    resolved = Column(Boolean, default=False)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
