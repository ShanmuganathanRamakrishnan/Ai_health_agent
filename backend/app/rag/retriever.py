"""
Retrieval logic for fetching relevant patient records.
Deterministic, keyword-based intent detection and database lookup.
"""
import re
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import Patient, PatientHistory


# -------------------------------
# Intent keywords
# -------------------------------
HISTORY_KEYWORDS = {"history", "summary", "visits", "treatment", "treatments"}
CONDITIONS_KEYWORDS = {"condition", "conditions", "diagnosis", "disease", "diseases"}

# Common first names for name detection (subset for validation)
COMMON_FIRST_NAMES = {
    "james", "mary", "robert", "patricia", "john", "jennifer", "michael", "linda",
    "david", "elizabeth", "william", "barbara", "richard", "susan", "joseph", "jessica",
    "thomas", "sarah", "christopher", "karen"
}

# Common last names for name detection
COMMON_LAST_NAMES = {
    "smith", "johnson", "williams", "brown", "jones", "garcia", "miller", "davis",
    "rodriguez", "martinez", "hernandez", "lopez", "gonzalez", "wilson", "anderson",
    "thomas", "taylor", "moore", "jackson", "martin"
}


def _extract_patient_id(query: str) -> Optional[int]:
    """
    Extract patient ID from query using strict regex patterns.
    Only matches explicit patterns: "patient 3", "patient id 3", "id 3", "#3".
    """
    patterns = [
        r"\bpatient\s+id\s*[:\s]*(\d+)\b",  # "patient id 3" or "patient id: 3"
        r"\bpatient\s+(\d+)\b",              # "patient 3"
        r"\bid\s*[:\s]*(\d+)\b",             # "id 3" or "id: 3"
        r"#(\d+)\b",                          # "#3"
    ]
    
    query_lower = query.lower()
    
    for pattern in patterns:
        match = re.search(pattern, query_lower)
        if match:
            return int(match.group(1))
    
    return None


def _extract_name_candidates(query: str) -> list[str]:
    """
    Extract potential name candidates from query.
    Returns list of (full name, first name, last name) candidates.
    """
    candidates = []
    words = query.split()
    
    # Look for capitalized words that could be names
    capitalized = [w for w in words if w and w[0].isupper() and w.isalpha()]
    
    # Check for consecutive capitalized words (full name)
    for i in range(len(capitalized) - 1):
        full_name = f"{capitalized[i]} {capitalized[i + 1]}"
        candidates.append(full_name)
    
    # Add individual capitalized words as single-name candidates
    candidates.extend(capitalized)
    
    # Also check against known name lists (case-insensitive)
    words_lower = [w.lower() for w in words if w.isalpha()]
    for word in words_lower:
        if word in COMMON_FIRST_NAMES or word in COMMON_LAST_NAMES:
            # Find original casing
            for orig in words:
                if orig.lower() == word:
                    if orig not in candidates:
                        candidates.append(orig)
                    break
    
    return candidates


def _find_patient_by_name(query: str, db_session: Session) -> Optional[Patient]:
    """
    Find patient by name match (case-insensitive).
    Tries full name match first, then partial first/last name.
    Returns first match for deterministic behavior.
    """
    candidates = _extract_name_candidates(query)
    
    if not candidates:
        return None
    
    # Try each candidate
    for candidate in candidates:
        # Try exact full name match first
        patient = db_session.query(Patient).filter(
            Patient.name.ilike(candidate)
        ).first()
        if patient:
            return patient
        
        # Try partial match (first or last name)
        patient = db_session.query(Patient).filter(
            Patient.name.ilike(f"{candidate} %")  # First name
        ).first()
        if patient:
            return patient
        
        patient = db_session.query(Patient).filter(
            Patient.name.ilike(f"% {candidate}")  # Last name
        ).first()
        if patient:
            return patient
    
    return None


def _identify_patient(query: str, db_session: Session) -> Optional[Patient]:
    """
    Identify patient from query by ID or name.
    """
    # Try ID first (strict patterns only)
    patient_id = _extract_patient_id(query)
    if patient_id is not None:
        patient = db_session.query(Patient).filter(
            Patient.patient_id == patient_id
        ).first()
        if patient:
            return patient
    
    # Fall back to name search
    return _find_patient_by_name(query, db_session)


def _detect_intent(query: str) -> str:
    """
    Detect query intent using keyword matching.
    Returns: BASIC_INFO, HISTORY_SUMMARY, or CONDITIONS.
    """
    query_lower = query.lower()
    words = set(re.findall(r"\w+", query_lower))
    
    if words & HISTORY_KEYWORDS:
        return "HISTORY_SUMMARY"
    
    if words & CONDITIONS_KEYWORDS:
        return "CONDITIONS"
    
    return "BASIC_INFO"


def _fetch_history(patient_id: int, db_session: Session, limit: int = 5) -> list:
    """
    Fetch most recent patient history records (simple, unweighted).
    Used for basic retrieval.
    """
    return (
        db_session.query(PatientHistory)
        .filter(PatientHistory.patient_id == patient_id)
        .order_by(PatientHistory.visit_date.desc())
        .limit(limit)
        .all()
    )


def _fetch_all_history(patient_id: int, db_session: Session) -> list:
    """
    Fetch ALL patient history records for weighted selection.
    """
    return (
        db_session.query(PatientHistory)
        .filter(PatientHistory.patient_id == patient_id)
        .order_by(PatientHistory.visit_date.desc())
        .all()
    )


def fetch_weighted_history(patient_id: int, db_session: Session, limit: int = 5):
    """
    Fetch patient history using weighted relevance scoring.
    
    Weights:
    - Recency (40%): More recent visits score higher
    - Clinical signals (60%): Clinically significant notes score higher
    
    Returns:
        Tuple of (records, scoring_details)
    """
    from app.rag.relevance_scorer import get_weighted_history
    
    # Fetch all history for scoring
    all_history = _fetch_all_history(patient_id, db_session)
    
    if not all_history:
        return [], []
    
    # Apply weighted retrieval
    records, details = get_weighted_history(all_history, limit=limit)
    
    return records, details


def retrieve_context(query: str, db_session: Session) -> Optional[dict]:
    """
    Main retrieval function for RAG pipeline.
    
    Args:
        query: User query string.
        db_session: SQLAlchemy session.
        
    Returns:
        Dictionary with patient, history, and intent.
        None if no patient is found.
    """
    if not query or not query.strip():
        return None
    
    # Step 1: Identify patient
    patient = _identify_patient(query, db_session)
    if patient is None:
        return None
    
    # Step 2: Detect intent
    intent = _detect_intent(query)
    
    # Step 3: Retrieve data based on intent
    history = []
    
    if intent == "HISTORY_SUMMARY":
        # Fetch recent visit history
        history = _fetch_history(patient.patient_id, db_session, limit=5)
    elif intent == "CONDITIONS":
        # CONDITIONS: only primary_condition from patient, no history needed
        history = []
    else:
        # BASIC_INFO: patient demographics only, no history
        history = []
    
    return {
        "patient": patient,
        "history": history,
        "intent": intent,
    }
