"""
Reference Resolution Module.
Resolves patient references using patient_id as primary identifier.
Includes gender-aware pronoun resolution and ambiguity detection.
"""
from typing import Optional, Tuple, List

from sqlalchemy.orm import Session

from app.db.models import Patient
from app.utils.text import (
    normalize_query,
    extract_possessive_name,
    contains_pronoun
)
from app.utils.context_manager import get_context


# Gender mapping for pronouns
PRONOUN_GENDER_MAP = {
    "male": {"he", "him", "his"},
    "female": {"she", "her", "hers"},
}


def _find_patients_by_name(name: str, db: Session) -> List[Patient]:
    """
    Find ALL patients matching a name (case-insensitive).
    Returns list for ambiguity detection.
    """
    if not name:
        return []
    
    name_lower = name.lower().strip()
    
    # Try exact full name match first
    patients = db.query(Patient).filter(
        Patient.name.ilike(name_lower)
    ).all()
    
    if patients:
        return patients
    
    # Try partial match (contains)
    patients = db.query(Patient).filter(
        Patient.name.ilike(f"%{name_lower}%")
    ).all()
    
    return patients


def _find_patient_by_id(patient_id: int, db: Session) -> Optional[Patient]:
    """Find a patient by ID. This is the PRIMARY lookup method."""
    return db.query(Patient).filter(
        Patient.patient_id == patient_id
    ).first()


def _check_gender_match(pronoun_gender: str, patient_gender: Optional[str]) -> bool:
    """
    Check if pronoun gender matches patient gender.
    """
    if not patient_gender:
        return True
    
    patient_gender_lower = patient_gender.lower()
    
    if pronoun_gender == "male":
        return patient_gender_lower in ("male", "m", "man")
    elif pronoun_gender == "female":
        return patient_gender_lower in ("female", "f", "woman")
    
    return False


def resolve_patient_reference(
    query: str,
    db: Session
) -> Tuple[Optional[Patient], str]:
    """
    Resolve patient reference using patient_id as source of truth.
    
    Priority:
    1. Pronouns → use patient_id from context (NO re-search)
    2. Possessive name → search DB, detect ambiguity
    3. Return None if no resolution possible
    
    Returns:
        Tuple of (Patient or None, resolution_method)
        
    Resolution methods:
        - "PRONOUN": Resolved via pronoun using patient_id from context
        - "POSSESSIVE": Resolved via possessive name
        - "GENDER_MISMATCH": Pronoun found but gender doesn't match
        - "NO_CONTEXT": Pronoun used but no patient in context
        - "AMBIGUOUS": Multiple patients found with same name
        - "NONE": No resolution possible
    """
    context = get_context()
    
    # Strategy 1: Check for pronouns FIRST - use patient_id directly
    pronoun_gender = contains_pronoun(query)
    if pronoun_gender:
        if context.has_active_patient():
            # Use patient_id from context - DO NOT re-search by name
            patient_id = context.get_active_patient_id()
            patient = _find_patient_by_id(patient_id, db)
            
            if patient:
                # Check gender compatibility
                if _check_gender_match(pronoun_gender, patient.gender):
                    print(f"[REFERENCE] Pronoun '{pronoun_gender}' resolved to patient_id={patient_id} ({patient.name})")
                    return patient, "PRONOUN"
                else:
                    print(f"[REFERENCE] Gender mismatch: pronoun={pronoun_gender}, "
                          f"patient_id={patient_id} ({patient.name}, gender={patient.gender})")
                    return None, "GENDER_MISMATCH"
        else:
            # No active patient but pronoun used
            print("[REFERENCE] Pronoun found but no patient in context")
            return None, "NO_CONTEXT"
    
    # Strategy 2: Check for possessive names with ambiguity detection
    possessive_name = extract_possessive_name(query)
    if possessive_name:
        patients = _find_patients_by_name(possessive_name, db)
        
        if len(patients) == 1:
            # Unique match - update context with patient_id
            patient = patients[0]
            context.set_active_patient(
                patient.patient_id,
                patient.name,
                patient.gender,
                query_type=None
            )
            print(f"[REFERENCE] Possessive '{possessive_name}' resolved to patient_id={patient.patient_id}")
            return patient, "POSSESSIVE"
        
        elif len(patients) > 1:
            # Ambiguous - multiple patients found
            names = [p.name for p in patients]
            print(f"[REFERENCE] Ambiguous: '{possessive_name}' matches {len(patients)} patients: {names}")
            return None, "AMBIGUOUS"
        
        # No match found
        return None, "NONE"
    
    # Strategy 3: No pronoun or possessive found
    return None, "NONE"


def resolve_explicit_patient_name(
    name: str,
    db: Session
) -> Tuple[Optional[Patient], str]:
    """
    Resolve an explicit patient name with ambiguity detection.
    Called by retriever when no pronoun reference is found.
    
    Returns:
        Tuple of (Patient or None, resolution_method)
        
    Resolution methods:
        - "FOUND": Unique patient found
        - "AMBIGUOUS": Multiple patients with same name
        - "NOT_FOUND": No patient found
    """
    context = get_context()
    
    patients = _find_patients_by_name(name, db)
    
    if len(patients) == 1:
        patient = patients[0]
        # Update context with patient_id
        context.set_active_patient(
            patient.patient_id,
            patient.name,
            patient.gender,
            query_type=None
        )
        print(f"[REFERENCE] Name '{name}' resolved to patient_id={patient.patient_id}")
        return patient, "FOUND"
    
    elif len(patients) > 1:
        names = [f"{p.name} (ID:{p.patient_id})" for p in patients]
        print(f"[REFERENCE] Ambiguous: '{name}' matches {len(patients)} patients: {names}")
        return None, "AMBIGUOUS"
    
    return None, "NOT_FOUND"


def update_context_from_patient(patient: Patient) -> None:
    """
    Update the conversation context with a successfully identified patient.
    Uses patient_id as the primary identifier.
    """
    if patient:
        context = get_context()
        context.set_active_patient(
            patient.patient_id,
            patient.name,
            patient.gender
        )
        print(f"[CONTEXT] Set active patient: id={patient.patient_id}, name={patient.name}")


def get_ambiguity_response(name: str, db: Session) -> str:
    """
    Generate a clarification response for ambiguous patient names.
    """
    patients = _find_patients_by_name(name, db)
    
    if len(patients) <= 1:
        return ""
    
    patient_list = ", ".join([f"{p.name} (age {p.age})" for p in patients[:5]])
    
    if len(patients) > 5:
        return f"I found {len(patients)} patients matching '{name}'. Could you be more specific? Some matches: {patient_list}..."
    else:
        return f"I found {len(patients)} patients matching '{name}': {patient_list}. Could you specify which one?"
