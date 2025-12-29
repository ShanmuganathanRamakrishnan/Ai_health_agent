"""
ETL pipeline for loading synthetic patient data into the database.
"""
import sys
import random
from datetime import datetime, timedelta
from pathlib import Path

# Compute project root: etl_pipeline.py -> etl/ -> backend/ -> ai-patient-chatbot/
# Path structure: backend/etl/etl_pipeline.py
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.db.database import SessionLocal, init_db
from app.db.models import Patient, PatientHistory

# Fixed seed for reproducibility
random.seed(42)

# Synthetic data pools
FIRST_NAMES = [
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda",
    "David", "Elizabeth", "William", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Christopher", "Karen"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin"
]

CONDITIONS = [
    "Type 2 Diabetes",
    "Hypertension",
    "Chronic Kidney Disease",
    "Coronary Artery Disease",
    "Asthma",
    "COPD",
    "Atrial Fibrillation",
    "Heart Failure",
    "Osteoarthritis",
    "Rheumatoid Arthritis",
    "Hypothyroidism",
    "Hyperlipidemia",
    "Depression",
    "Anxiety Disorder",
    "Chronic Back Pain"
]

RISK_LEVELS = ["Low", "Medium", "High"]

CLINICIANS = [
    "Dr. Emily Carter",
    "Dr. Michael Chen",
    "Dr. Sarah Patel",
    "Dr. James Thompson",
    "Dr. Maria Rodriguez",
    "Dr. David Kim",
    "Dr. Laura Johnson",
    "Dr. Robert Singh"
]

TREATMENTS = [
    "Continued current medication regimen",
    "Adjusted medication dosage",
    "Started new medication therapy",
    "Referred to specialist for evaluation",
    "Recommended lifestyle modifications",
    "Ordered additional lab work",
    "Scheduled follow-up imaging",
    "Physical therapy referral",
    "Dietary counseling provided",
    "Blood pressure monitoring at home"
]

NOTE_TEMPLATES = [
    "Patient presents with stable {condition}. Vitals within normal limits.",
    "Follow-up visit for {condition}. Patient reports improved symptoms.",
    "Routine check for {condition}. No acute concerns noted.",
    "Patient reports mild exacerbation of {condition}. Adjusted treatment.",
    "Annual review for {condition}. Lab results reviewed with patient.",
    "Patient compliant with medications for {condition}. Symptoms well-controlled.",
    "Discussed management strategies for {condition}. Patient educated on warning signs.",
    "Patient experiencing new symptoms related to {condition}. Further workup ordered.",
    "Stable {condition}. Reinforced importance of medication adherence.",
    "Follow-up after recent hospitalization for {condition}. Recovery progressing well."
]


def generate_patients(count: int) -> list[dict]:
    """Generate synthetic patient records."""
    patients = []
    for _ in range(count):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        patients.append({
            "name": f"{first} {last}",
            "age": random.randint(25, 85),
            "gender": random.choice(["Male", "Female"]),
            "primary_condition": random.choice(CONDITIONS),
            "risk_level": random.choice(RISK_LEVELS)
        })
    return patients


def generate_history(patient_id: int, condition: str, record_count: int) -> list[dict]:
    """Generate synthetic visit history for a patient."""
    records = []
    base_date = datetime(2022, 1, 1)
    
    for i in range(record_count):
        visit_date = base_date + timedelta(days=random.randint(30, 90) * (i + 1))
        note_template = random.choice(NOTE_TEMPLATES)
        
        records.append({
            "patient_id": patient_id,
            "visit_date": visit_date.strftime("%Y-%m-%d"),
            "notes": note_template.format(condition=condition),
            "treatment": random.choice(TREATMENTS),
            "clinician": random.choice(CLINICIANS)
        })
    return records


def clear_existing_data(session):
    """Delete existing data to make ETL idempotent. Respects foreign key order."""
    # Delete history first (child table with foreign key reference)
    session.query(PatientHistory).delete()
    # Then delete patients (parent table)
    session.query(Patient).delete()
    session.commit()


def run_etl():
    """Execute the ETL pipeline."""
    # Initialize database and create tables
    init_db()
    
    # Create session
    session = SessionLocal()
    
    try:
        # Clear existing data for idempotency
        clear_existing_data(session)
        
        # Generate and insert patients
        patient_count = random.randint(10, 20)
        patient_data = generate_patients(patient_count)
        
        patients = []
        for data in patient_data:
            patient = Patient(**data)
            session.add(patient)
            patients.append((patient, data["primary_condition"]))
        
        # Flush to get patient IDs
        session.flush()
        
        # Generate and insert history records
        for patient, condition in patients:
            record_count = random.randint(5, 10)
            history_data = generate_history(patient.patient_id, condition, record_count)
            
            for data in history_data:
                record = PatientHistory(**data)
                session.add(record)
        
        # Commit all changes
        session.commit()
        
    finally:
        session.close()


if __name__ == "__main__":
    run_etl()
