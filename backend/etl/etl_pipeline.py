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
from app.db.models import Patient, PatientHistory, Encounter, Vital, Lab

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
# ENCOUNTER DATA POOLS
# ============================================

ENCOUNTER_TYPES = [
    "office_visit",       # Most common
    "office_visit",       # Weighted
    "office_visit",       # Weighted
    "telehealth",
    "telehealth",
    "emergency",
    "urgent_care",
    "inpatient",
    "follow_up",
    "follow_up",
    "annual_physical",
]

ENCOUNTER_LOCATIONS = [
    "Main Campus - Building A",
    "Main Campus - Building B",
    "Downtown Clinic",
    "Westside Medical Center",
    "Northgate Health Center",
    "Virtual Visit",
    "Emergency Department",
    "Urgent Care - Eastside",
]

CHIEF_COMPLAINTS = [
    "Follow-up for chronic condition management",
    "Medication refill and review",
    "New symptom assessment",
    "Routine health maintenance",
    "Worsening symptoms",
    "Post-procedure follow-up",
    "Lab results review",
    "Annual wellness exam",
    "Acute illness evaluation",
    "Pain management consultation",
]

DISPOSITIONS = [
    "discharged_home",
    "discharged_home",     # Most common
    "discharged_home",     # Weighted
    "follow_up_scheduled",
    "follow_up_scheduled",
    "referred_to_specialist",
    "admitted_to_hospital",
    "transferred",
]

PROVIDER_SPECIALTIES = [
    "Internal Medicine",
    "Family Medicine",
    "Cardiology",
    "Endocrinology",
    "Pulmonology",
    "Rheumatology",
    "Nephrology",
    "Psychiatry",
    "Primary Care",
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


def generate_encounters(patient_id: int, condition: str, encounter_count: int) -> list[dict]:
    """
    Generate realistic encounter records for a patient.
    Each encounter has type, date, clinician, location, and notes.
    """
    encounters = []
    
    # Timeline: 3-6 years of encounters
    years_back = random.randint(3, 6)
    base_date = datetime.now() - timedelta(days=years_back * 365)
    current_date = base_date
    
    for i in range(encounter_count):
        # Time between encounters: 20-90 days
        days_gap = random.randint(20, 90)
        current_date = current_date + timedelta(days=days_gap)
        
        # Don't go past today
        if current_date > datetime.now():
            current_date = datetime.now() - timedelta(days=random.randint(1, 30))
        
        encounter_type = random.choice(ENCOUNTER_TYPES)
        
        # Location based on type
        if encounter_type == "telehealth":
            location = "Virtual Visit"
        elif encounter_type == "emergency":
            location = "Emergency Department"
        elif encounter_type == "urgent_care":
            location = "Urgent Care - Eastside"
        else:
            location = random.choice([l for l in ENCOUNTER_LOCATIONS if l not in ["Virtual Visit", "Emergency Department"]])
        
        # Calculate end date (same day for most, longer for inpatient)
        if encounter_type == "inpatient":
            end_date = current_date + timedelta(days=random.randint(1, 7))
        else:
            end_date = current_date
        
        clinician = random.choice(CLINICIANS)
        specialty = random.choice(PROVIDER_SPECIALTIES)
        
        encounters.append({
            "patient_id": patient_id,
            "encounter_date": current_date.strftime("%Y-%m-%d"),
            "encounter_type": encounter_type,
            "chief_complaint": random.choice(CHIEF_COMPLAINTS),
            "diagnosis_code": None,  # Placeholder for ICD-10
            "diagnosis_description": condition,
            "provider_name": clinician,
            "provider_specialty": specialty,
            "disposition": random.choice(DISPOSITIONS),
            "notes": f"{encounter_type.replace('_', ' ').title()} for {condition}. {random.choice(CHIEF_COMPLAINTS)}."
        })
    
    return encounters


# ============================================
# VITALS DATA
# ============================================

def generate_vitals(encounter_id: int, encounter_date: str) -> list[dict]:
    """
    Generate 1-3 vital sign readings per encounter.
    Values are clinically realistic with slight noise and occasional abnormals.
    """
    vitals = []
    num_readings = random.randint(1, 3)
    
    base_date = datetime.strptime(encounter_date, "%Y-%m-%d")
    
    for i in range(num_readings):
        # Add hours between readings
        reading_time = base_date + timedelta(hours=random.randint(0, 8))
        
        # Generate realistic vitals with slight noise
        # Occasional abnormals (~15% chance per vital)
        is_abnormal = False
        
        # Heart rate: normal 60-100, abnormal 40-60 or 100-140
        if random.random() < 0.15:
            heart_rate = random.choice([random.randint(40, 55), random.randint(105, 140)])
            is_abnormal = True
        else:
            heart_rate = random.randint(60, 100)
        
        # Blood pressure: normal 90-120/60-80, abnormal high or low
        if random.random() < 0.15:
            bp_systolic = random.choice([random.randint(70, 89), random.randint(140, 180)])
            bp_diastolic = random.choice([random.randint(40, 55), random.randint(90, 110)])
            is_abnormal = True
        else:
            bp_systolic = random.randint(90, 130)
            bp_diastolic = random.randint(60, 85)
        
        # Respiratory rate: normal 12-20
        if random.random() < 0.10:
            respiratory_rate = random.choice([random.randint(8, 11), random.randint(22, 30)])
            is_abnormal = True
        else:
            respiratory_rate = random.randint(12, 20)
        
        # Temperature: normal 97.0-99.0 F
        if random.random() < 0.10:
            temperature = round(random.uniform(100.0, 103.0), 1)  # Fever
            is_abnormal = True
        else:
            temperature = round(random.uniform(97.0, 99.0), 1)
        
        # Oxygen saturation: normal 95-100%
        if random.random() < 0.10:
            oxygen_sat = round(random.uniform(88.0, 94.0), 1)
            is_abnormal = True
        else:
            oxygen_sat = round(random.uniform(95.0, 100.0), 1)
        
        # Weight/height (consistent per patient, slight variation)
        weight = round(random.uniform(50, 120), 1)  # kg
        height = round(random.uniform(150, 190), 1)  # cm
        bmi = round(weight / ((height / 100) ** 2), 1)
        
        # Pain level: 0-10
        pain_level = random.choices([0, 1, 2, 3, 4, 5, 6, 7, 8], weights=[30, 20, 15, 10, 8, 7, 5, 3, 2])[0]
        
        vitals.append({
            "encounter_id": encounter_id,
            "recorded_at": reading_time.strftime("%Y-%m-%d %H:%M:%S"),
            "temperature_f": temperature,
            "heart_rate_bpm": heart_rate,
            "blood_pressure_systolic": bp_systolic,
            "blood_pressure_diastolic": bp_diastolic,
            "respiratory_rate": respiratory_rate,
            "oxygen_saturation": oxygen_sat,
            "weight_kg": weight,
            "height_cm": height,
            "bmi": bmi,
            "pain_level": pain_level,
            "is_abnormal": is_abnormal
        })
    
    return vitals


# ============================================
# LABS DATA
# ============================================

# Common lab tests with reference ranges
LAB_TESTS = [
    {"name": "Hemoglobin", "code": "718-7", "unit": "g/dL", "range": "12.0-17.5", "normal_min": 12.0, "normal_max": 17.5},
    {"name": "Hematocrit", "code": "4544-3", "unit": "%", "range": "36-52", "normal_min": 36, "normal_max": 52},
    {"name": "WBC", "code": "6690-2", "unit": "K/uL", "range": "4.5-11.0", "normal_min": 4.5, "normal_max": 11.0},
    {"name": "Platelet Count", "code": "777-3", "unit": "K/uL", "range": "150-400", "normal_min": 150, "normal_max": 400},
    {"name": "Glucose", "code": "2345-7", "unit": "mg/dL", "range": "70-100", "normal_min": 70, "normal_max": 100},
    {"name": "HbA1c", "code": "4548-4", "unit": "%", "range": "4.0-5.6", "normal_min": 4.0, "normal_max": 5.6},
    {"name": "Creatinine", "code": "2160-0", "unit": "mg/dL", "range": "0.7-1.3", "normal_min": 0.7, "normal_max": 1.3},
    {"name": "BUN", "code": "3094-0", "unit": "mg/dL", "range": "7-20", "normal_min": 7, "normal_max": 20},
    {"name": "Sodium", "code": "2951-2", "unit": "mEq/L", "range": "136-145", "normal_min": 136, "normal_max": 145},
    {"name": "Potassium", "code": "2823-3", "unit": "mEq/L", "range": "3.5-5.0", "normal_min": 3.5, "normal_max": 5.0},
    {"name": "Chloride", "code": "2075-0", "unit": "mEq/L", "range": "98-106", "normal_min": 98, "normal_max": 106},
    {"name": "Total Cholesterol", "code": "2093-3", "unit": "mg/dL", "range": "<200", "normal_min": 100, "normal_max": 200},
    {"name": "LDL Cholesterol", "code": "13457-7", "unit": "mg/dL", "range": "<100", "normal_min": 40, "normal_max": 100},
    {"name": "HDL Cholesterol", "code": "2085-9", "unit": "mg/dL", "range": ">40", "normal_min": 40, "normal_max": 80},
    {"name": "Triglycerides", "code": "2571-8", "unit": "mg/dL", "range": "<150", "normal_min": 50, "normal_max": 150},
    {"name": "TSH", "code": "3016-3", "unit": "mIU/L", "range": "0.4-4.0", "normal_min": 0.4, "normal_max": 4.0},
    {"name": "ALT", "code": "1742-6", "unit": "U/L", "range": "7-56", "normal_min": 7, "normal_max": 56},
    {"name": "AST", "code": "1920-8", "unit": "U/L", "range": "10-40", "normal_min": 10, "normal_max": 40},
]


def generate_labs(encounter_id: int, encounter_date: str) -> list[dict]:
    """
    Generate 0-4 lab results per encounter.
    ~20% of values are abnormal.
    """
    labs = []
    num_tests = random.choices([0, 1, 2, 3, 4], weights=[20, 30, 25, 15, 10])[0]
    
    if num_tests == 0:
        return labs
    
    # Select random subset of tests
    selected_tests = random.sample(LAB_TESTS, min(num_tests, len(LAB_TESTS)))
    
    base_date = datetime.strptime(encounter_date, "%Y-%m-%d")
    result_date = base_date + timedelta(days=random.randint(0, 2))
    
    for test in selected_tests:
        # 20% chance of abnormal
        is_abnormal = random.random() < 0.20
        
        normal_min = test["normal_min"]
        normal_max = test["normal_max"]
        
        if is_abnormal:
            # Generate value outside normal range
            if random.random() < 0.5:
                # Low
                value = round(random.uniform(normal_min * 0.5, normal_min * 0.95), 1)
                flag = "L"
            else:
                # High
                value = round(random.uniform(normal_max * 1.05, normal_max * 1.5), 1)
                flag = "H"
        else:
            # Normal value
            value = round(random.uniform(normal_min, normal_max), 1)
            flag = None
        
        labs.append({
            "encounter_id": encounter_id,
            "ordered_date": encounter_date,
            "result_date": result_date.strftime("%Y-%m-%d"),
            "test_name": test["name"],
            "test_code": test["code"],
            "result_value": str(value),
            "result_unit": test["unit"],
            "reference_range": test["range"],
            "is_abnormal": is_abnormal,
            "abnormal_flag": flag,
            "interpretation": None
        })
    
    return labs


def clear_existing_data(session):
    """Delete existing data to make ETL idempotent."""
    session.query(Lab).delete()
    session.query(Vital).delete()
    session.query(PatientHistory).delete()
    session.query(Encounter).delete()
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
        
        session.flush()
        
        # Generate encounter records (5-15 per patient)
        total_encounters = 0
        encounter_objs = []  # Store for vitals/labs generation
        for patient, condition, risk_level in patients:
            encounter_count = random.randint(5, 15)
            encounter_data = generate_encounters(patient.patient_id, condition, encounter_count)
            total_encounters += len(encounter_data)
            
            for data in encounter_data:
                encounter = Encounter(**data)
                session.add(encounter)
                encounter_objs.append((encounter, data["encounter_date"]))
        
        session.flush()  # Get encounter IDs
        
        # Generate vitals and labs for each encounter
        total_vitals = 0
        total_labs = 0
        abnormal_vitals = 0
        abnormal_labs = 0
        
        for encounter, encounter_date in encounter_objs:
            # Generate vitals (1-3 per encounter)
            vitals_data = generate_vitals(encounter.encounter_id, encounter_date)
            total_vitals += len(vitals_data)
            for data in vitals_data:
                if data.get("is_abnormal"):
                    abnormal_vitals += 1
                vital = Vital(**data)
                session.add(vital)
            
            # Generate labs (0-4 per encounter)
            labs_data = generate_labs(encounter.encounter_id, encounter_date)
            total_labs += len(labs_data)
            for data in labs_data:
                if data.get("is_abnormal"):
                    abnormal_labs += 1
                lab = Lab(**data)
                session.add(lab)
        
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
        print(f"")
        print(f"Total encounters:      {total_encounters}")
        print(f"Average encounters/patient: {total_encounters / patient_count:.1f}")
        print(f"")
        print(f"Total vitals:          {total_vitals}")
        print(f"  - Abnormal:          {abnormal_vitals} ({100*abnormal_vitals/max(1,total_vitals):.1f}%)")
        print(f"Total labs:            {total_labs}")
        print(f"  - Abnormal:          {abnormal_labs} ({100*abnormal_labs/max(1,total_labs):.1f}%)")
        print(f"{'='*50}\n")
        
    finally:
        session.close()


if __name__ == "__main__":
    run_etl()
