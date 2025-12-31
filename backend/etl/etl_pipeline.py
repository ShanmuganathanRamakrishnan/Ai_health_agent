"""
ETL pipeline for loading synthetic patient data into the database.
Enhanced version with 150 patients, multi-year histories, and stress-test scenarios.
"""
import sys
import random
from datetime import datetime, timedelta
from pathlib import Path

# Compute project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.db.database import SessionLocal, init_db
from app.db.models import Patient, PatientHistory

# Fixed seed for reproducibility
random.seed(42)

# ============================================
# EXPANDED DATA POOLS
# ============================================

# Repeated first names to test ambiguity
FIRST_NAMES = [
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda",
    "David", "Elizabeth", "William", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Christopher", "Karen", "Daniel", "Nancy", "Matthew", "Lisa",
    "Anthony", "Betty", "Mark", "Margaret", "Donald", "Sandra", "Steven", "Ashley",
    "Paul", "Kimberly", "Andrew", "Emily", "Joshua", "Donna", "Kenneth", "Michelle",
    # Additional names for variation
    "Brian", "Carol", "Kevin", "Amanda", "George", "Dorothy", "Edward", "Melissa",
]

# Repeated last names to test ambiguity
LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson",
    # Similar names for ambiguity testing
    "Willson", "Thomson", "Andersen", "Browne", "Smyth",
]

# Concentrated conditions (some appear more frequently)
CONDITIONS = [
    "Type 2 Diabetes",      # Common
    "Type 2 Diabetes",      # Duplicate for frequency
    "Hypertension",         # Common
    "Hypertension",         # Duplicate
    "Chronic Kidney Disease",
    "Coronary Artery Disease",
    "Asthma",
    "COPD",
    "Atrial Fibrillation",
    "Heart Failure",
    "Osteoarthritis",
    "Rheumatoid Arthritis",
    "Rheumatoid Arthritis", # Duplicate
    "Hypothyroidism",
    "Hyperlipidemia",
    "Depression",
    "Anxiety Disorder",
    "Chronic Back Pain",
    "Migraine",
    "Fibromyalgia",
]

RISK_LEVELS = ["Low", "Low", "Medium", "Medium", "Medium", "High"]  # Weighted toward Medium

CLINICIANS = [
    "Dr. Emily Carter", "Dr. Michael Chen", "Dr. Sarah Patel", "Dr. James Thompson",
    "Dr. Maria Rodriguez", "Dr. David Kim", "Dr. Laura Johnson", "Dr. Robert Singh",
    "Dr. Jennifer Lee", "Dr. William Brown", "Dr. Amanda Clark", "Dr. Christopher Davis",
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
    "Blood pressure monitoring at home",
    "Insulin adjustment",
    "Pain management protocol initiated",
    "Stress management techniques discussed",
    "Sleep hygiene recommendations",
]

# ============================================
# CLINICAL SIGNAL TEMPLATES
# ============================================

# Stable visits (weak signal)
STABLE_TEMPLATES = [
    "Patient presents with stable {condition}. Vitals within normal limits.",
    "Routine follow-up for {condition}. No acute concerns noted today.",
    "Patient compliant with medications for {condition}. Symptoms well-controlled.",
    "Stable {condition}. Reinforced importance of medication adherence.",
    "Annual review for {condition}. Lab results reviewed - all within range.",
    "Patient reports feeling well. {condition} management continues as planned.",
    "No significant changes since last visit. {condition} stable.",
    "Routine monitoring for {condition}. Patient satisfied with current regimen.",
]

# Improvement visits (positive signal)
IMPROVEMENT_TEMPLATES = [
    "Follow-up visit for {condition}. Patient reports improved symptoms.",
    "Patient shows marked improvement in {condition} control. Excellent progress.",
    "Symptoms have decreased significantly. {condition} responding well to treatment.",
    "Recovery progressing well after recent {condition} episode.",
    "Patient reports better quality of life. {condition} well managed now.",
    "Lab values improved compared to last visit. {condition} control optimized.",
]

# Worsening visits (strong clinical signal)
WORSENING_TEMPLATES = [
    "Patient reports mild exacerbation of {condition}. Adjusted treatment plan.",
    "Patient experiencing new symptoms related to {condition}. Further workup ordered.",
    "Concerning deterioration in {condition}. Specialist referral initiated.",
    "Follow-up after recent hospitalization for {condition}. Close monitoring needed.",
    "Acute flare of {condition}. Emergency intervention considered.",
    "Patient condition has worsened since last visit. Escalating care.",
    "Significant exacerbation requiring medication adjustment for {condition}.",
    "Patient reports increased symptoms. {condition} not adequately controlled.",
]

# Hospitalization events (very strong signal)
HOSPITALIZATION_TEMPLATES = [
    "Follow-up after hospitalization for {condition} complications. Recovery ongoing.",
    "Post-discharge visit. Patient was hospitalized for {condition} exacerbation.",
    "Returning after ER visit for acute {condition}. Stabilized now.",
    "Patient required inpatient care for {condition}. Adjusting outpatient plan.",
]


def generate_patients(count: int) -> list[dict]:
    """Generate synthetic patient records with realistic distribution."""
    patients = []
    used_names = set()
    
    for _ in range(count):
        # Allow some duplicate names for ambiguity testing
        for _ in range(10):  # Max attempts
            first = random.choice(FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            name = f"{first} {last}"
            
            # 10% chance to allow duplicate name
            if name not in used_names or random.random() < 0.1:
                break
        
        used_names.add(name)
        
        # Age distribution: weighted toward older patients
        age = random.choices(
            [random.randint(25, 40), random.randint(40, 60), random.randint(60, 85)],
            weights=[0.2, 0.4, 0.4]
        )[0]
        
        patients.append({
            "name": name,
            "age": age,
            "gender": random.choice(["Male", "Female"]),
            "primary_condition": random.choice(CONDITIONS),
            "risk_level": random.choice(RISK_LEVELS)
        })
    
    return patients


def generate_history(patient_id: int, condition: str, record_count: int, risk_level: str) -> list[dict]:
    """
    Generate realistic visit history with varied clinical signals.
    
    Patterns:
    - Stable patients: mostly stable visits
    - Worsening: stable → worsening events → possible improvement
    - High-risk: includes hospitalizations
    """
    records = []
    
    # Timeline: 3-6 years of history
    years_back = random.randint(3, 6)
    base_date = datetime.now() - timedelta(days=years_back * 365)
    
    # Determine patient trajectory
    if risk_level == "High":
        trajectory = random.choice(["worsening", "hospitalized", "unstable"])
    elif risk_level == "Medium":
        trajectory = random.choice(["stable", "fluctuating", "mild_worsening"])
    else:
        trajectory = random.choice(["stable", "improving", "stable"])
    
    current_date = base_date
    
    for i in range(record_count):
        # Time between visits: 30-120 days
        days_gap = random.randint(30, 120)
        current_date = current_date + timedelta(days=days_gap)
        
        # Don't go past today
        if current_date > datetime.now():
            current_date = datetime.now() - timedelta(days=random.randint(1, 30))
        
        # Select note template based on trajectory and position in timeline
        progress = i / record_count  # 0 to 1
        
        if trajectory == "stable":
            if random.random() < 0.85:
                template = random.choice(STABLE_TEMPLATES)
            else:
                template = random.choice(IMPROVEMENT_TEMPLATES)
        
        elif trajectory == "improving":
            if progress < 0.5:
                template = random.choice(STABLE_TEMPLATES) if random.random() < 0.7 else random.choice(WORSENING_TEMPLATES)
            else:
                template = random.choice(IMPROVEMENT_TEMPLATES) if random.random() < 0.7 else random.choice(STABLE_TEMPLATES)
        
        elif trajectory == "worsening":
            if progress < 0.3:
                template = random.choice(STABLE_TEMPLATES)
            elif progress < 0.7:
                template = random.choice(WORSENING_TEMPLATES) if random.random() < 0.6 else random.choice(STABLE_TEMPLATES)
            else:
                template = random.choice(WORSENING_TEMPLATES)
        
        elif trajectory == "hospitalized":
            if progress > 0.6 and random.random() < 0.3:
                template = random.choice(HOSPITALIZATION_TEMPLATES)
            elif random.random() < 0.4:
                template = random.choice(WORSENING_TEMPLATES)
            else:
                template = random.choice(STABLE_TEMPLATES)
        
        elif trajectory == "fluctuating":
            r = random.random()
            if r < 0.5:
                template = random.choice(STABLE_TEMPLATES)
            elif r < 0.75:
                template = random.choice(WORSENING_TEMPLATES)
            else:
                template = random.choice(IMPROVEMENT_TEMPLATES)
        
        elif trajectory == "unstable":
            template = random.choice(WORSENING_TEMPLATES) if random.random() < 0.5 else random.choice(STABLE_TEMPLATES)
        
        else:  # mild_worsening
            if progress > 0.5 and random.random() < 0.3:
                template = random.choice(WORSENING_TEMPLATES)
            else:
                template = random.choice(STABLE_TEMPLATES)
        
        records.append({
            "patient_id": patient_id,
            "visit_date": current_date.strftime("%Y-%m-%d"),
            "notes": template.format(condition=condition),
            "treatment": random.choice(TREATMENTS),
            "clinician": random.choice(CLINICIANS)
        })
    
    return records


def clear_existing_data(session):
    """Delete existing data to make ETL idempotent."""
    session.query(PatientHistory).delete()
    session.query(Patient).delete()
    session.commit()


def run_etl():
    """Execute the enhanced ETL pipeline."""
    init_db()
    session = SessionLocal()
    
    try:
        clear_existing_data(session)
        
        # Generate 150 patients (range for variation)
        patient_count = random.randint(140, 160)
        patient_data = generate_patients(patient_count)
        
        patients = []
        sparse_count = 0
        dense_count = 0
        total_history = 0
        
        for data in patient_data:
            patient = Patient(**data)
            session.add(patient)
            patients.append((patient, data["primary_condition"], data["risk_level"]))
        
        session.flush()
        
        # Generate history records
        for patient, condition, risk_level in patients:
            # Determine visit count: mostly 10-25, some sparse (1-3), some dense (25-40)
            r = random.random()
            if r < 0.1:  # 10% sparse
                record_count = random.randint(1, 3)
                sparse_count += 1
            elif r < 0.9:  # 80% normal
                record_count = random.randint(10, 25)
            else:  # 10% dense
                record_count = random.randint(25, 40)
                dense_count += 1
            
            history_data = generate_history(patient.patient_id, condition, record_count, risk_level)
            total_history += len(history_data)
            
            for data in history_data:
                record = PatientHistory(**data)
                session.add(record)
        
        session.commit()
        
        # Print statistics
        print(f"\n{'='*50}")
        print("ETL PIPELINE COMPLETE - DATABASE STATISTICS")
        print(f"{'='*50}")
        print(f"Total patients:        {patient_count}")
        print(f"  - Sparse history:    {sparse_count} (1-3 visits)")
        print(f"  - Dense history:     {dense_count} (25-40 visits)")
        print(f"  - Normal history:    {patient_count - sparse_count - dense_count} (10-25 visits)")
        print(f"Total visit records:   {total_history}")
        print(f"Average visits/patient: {total_history / patient_count:.1f}")
        print(f"{'='*50}\n")
        
    finally:
        session.close()


if __name__ == "__main__":
    run_etl()
