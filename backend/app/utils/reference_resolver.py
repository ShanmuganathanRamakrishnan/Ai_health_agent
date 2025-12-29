"""
Reference Resolution Module.
Resolves patient references from queries including pronouns and possessives.
Includes gender-aware pronoun resolution.
"""
from typing import Optional, Tuple

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


def _find_patient_by_name(name: str, db: Session) -> Optional[Patient]:
    """
    Find a patient by name (case-insensitive).
    Tries full name match, then first name, then last name.
    """
    if not name:
        return None
    
    name_lower = name.lower().strip()
    
    # Try exact full name match
    patient = db.query(Patient).filter(
        Patient.name.ilike(f"%{name_lower}%")
    ).first()
    
    if patient:
        return patient
    
    # Try first name match
    patient = db.query(Patient).filter(
        Patient.name.ilike(f"{name_lower} %")
    ).first()
    
    if patient:
        return patient
    
    # Try last name match
    patient = db.query(Patient).filter(
        Patient.name.ilike(f"% {name_lower}")
    ).first()
    
    return patient


def _find_patient_by_id(patient_id: int, db: Session) -> Optional[Patient]:
    """Find a patient by ID."""
    return db.query(Patient).filter(
        Patient.patient_id == patient_id
    ).first()


def _check_gender_match(pronoun_gender: str, patient_gender: Optional[str]) -> bool:
    """
    Check if pronoun gender matches patient gender.
    
    Args:
        pronoun_gender: "male" or "female" from pronoun detection
        patient_gender: Patient's gender from database
        
    Returns:
        True if genders match, False otherwise
    """
    if not patient_gender:
        # If patient gender is unknown, allow match
        return True
    
    patient_gender_lower = patient_gender.lower()
    
    # Normalize gender strings
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
    Resolve patient reference from query with gender-aware pronoun resolution.
    
    Priority:
    1. Possessive name (sarah's → sarah)
    2. Pronouns (he/she/her/his) → last active patient IF gender matches
    3. Return None if no resolution possible or gender mismatch
    
    Args:
        query: The user query
        db: Database session
        
    Returns:
        Tuple of (Patient or None, resolution_method)
        
    Resolution methods:
        - "POSSESSIVE": Resolved via possessive name
        - "PRONOUN": Resolved via pronoun with matching gender
        - "GENDER_MISMATCH": Pronoun found but gender doesn't match
        - "NONE": No resolution possible
    """
    context = get_context()
    normalized = normalize_query(query)
    
    # Strategy 1: Check for possessive names first
    possessive_name = extract_possessive_name(query)
    if possessive_name:
        patient = _find_patient_by_name(possessive_name, db)
        if patient:
            # Update context with this patient
            context.set_active_patient(
                patient.patient_id,
                patient.name,
                patient.gender,
                query_type=None  # Will be set by chat endpoint
            )
            return patient, "POSSESSIVE"
    
    # Strategy 2: Check for pronouns with gender validation
    pronoun_gender = contains_pronoun(query)
    if pronoun_gender:
        # Try to resolve from context
        if context.has_active_patient():
            patient_id = context.get_active_patient_id()
            patient = _find_patient_by_id(patient_id, db)
            
            if patient:
                # Check gender compatibility
                if _check_gender_match(pronoun_gender, patient.gender):
                    return patient, "PRONOUN"
                else:
                    # Gender mismatch - return special code for safe refusal
                    print(f"[REFERENCE] Gender mismatch: pronoun={pronoun_gender}, "
                          f"patient={patient.name} (gender={patient.gender})")
                    return None, "GENDER_MISMATCH"
        else:
            # No active patient but pronoun used
            return None, "NO_CONTEXT"
    
    # Strategy 3: No pronoun or possessive found
    # Let the standard retriever handle explicit names
    return None, "NONE"


def update_context_from_patient(patient: Patient) -> None:
    """
    Update the conversation context with a successfully identified patient.
    Called after retriever successfully finds a patient.
    """
    if patient:
        context = get_context()
        context.set_active_patient(
            patient.patient_id,
            patient.name,
            patient.gender
        )
