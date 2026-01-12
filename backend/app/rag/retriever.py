"""
Retrieval logic for fetching relevant patient records.
Deterministic, keyword-based intent detection and database lookup.
"""
import re
from typing import Optional, Tuple, List

from sqlalchemy.orm import Session

from app.db.models import Patient, PatientHistory
from app.utils.context_manager import get_context


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


def _find_patients_by_name(query: str, db_session: Session) -> List[Patient]:
    """
    Find ALL patients matching name in query (for ambiguity detection).
    Returns list of all matching patients.
    """
    candidates = _extract_name_candidates(query)
    
    if not candidates:
        return []
    
    all_matches = []
    seen_ids = set()
    
    # Try each candidate
    for candidate in candidates:
        # Try exact full name match first
        patients = db_session.query(Patient).filter(
            Patient.name.ilike(candidate)
        ).all()
        for p in patients:
            if p.patient_id not in seen_ids:
                all_matches.append(p)
                seen_ids.add(p.patient_id)
        
        if all_matches:
            continue  # Found exact matches, skip partial
        
        # Try partial match (first or last name)
        patients = db_session.query(Patient).filter(
            Patient.name.ilike(f"{candidate} %")
        ).all()
        for p in patients:
            if p.patient_id not in seen_ids:
                all_matches.append(p)
                seen_ids.add(p.patient_id)
        
        patients = db_session.query(Patient).filter(
            Patient.name.ilike(f"% {candidate}")
        ).all()
        for p in patients:
            if p.patient_id not in seen_ids:
                all_matches.append(p)
                seen_ids.add(p.patient_id)
    
    return all_matches


def _identify_patient(query: str, db_session: Session) -> Tuple[Optional[Patient], str]:
    """
    Identify patient from query using reference resolution, ID, or name.
    Returns (patient, status) tuple for ambiguity handling.
    
    Priority:
    1. Pronoun/context resolution (via resolve_patient_reference)
    2. Explicit ID patterns
    3. Name search with ambiguity detection
    
    Status values:
        - "FOUND": Unique patient found
        - "PRONOUN": Resolved via pronoun
        - "CONTEXT_FALLBACK": Resolved via context fallback
        - "AMBIGUOUS": Multiple patients match
        - "NOT_FOUND": No patient found
    """
    from app.utils.reference_resolver import resolve_patient_reference
    
    context = get_context()
    
    # Step 1: Try reference resolution (pronouns, possessives, context fallback)
    patient, resolution_method = resolve_patient_reference(query, db_session)
    
    if patient:
        # Successfully resolved via reference resolver
        if resolution_method in ("PRONOUN", "CONTEXT_FALLBACK", "POSSESSIVE"):
            return patient, resolution_method
        return patient, "FOUND"
    
    # Step 2: Check for ambiguous resolution
    if resolution_method == "AMBIGUOUS":
        return None, "AMBIGUOUS"
    
    # Step 3: Try ID (strict patterns only)
    patient_id = _extract_patient_id(query)
    if patient_id is not None:
        patient = db_session.query(Patient).filter(
            Patient.patient_id == patient_id
        ).first()
        if patient:
            # Update context with this patient
            context.set_active_patient(
                patient.patient_id,
                patient.name,
                patient.gender
            )
            return patient, "FOUND"
    
    # Step 4: Fall back to name search with ambiguity detection
    patients = _find_patients_by_name(query, db_session)
    
    if len(patients) == 1:
        patient = patients[0]
        context.set_active_patient(
            patient.patient_id,
            patient.name,
            patient.gender
        )
        print(f"[RETRIEVER] Found unique patient: id={patient.patient_id}, name={patient.name}")
        return patient, "FOUND"
    
    elif len(patients) > 1:
        names = [f"{p.name} (ID:{p.patient_id})" for p in patients]
        print(f"[RETRIEVER] Ambiguous: {len(patients)} patients match: {names}")
        return None, "AMBIGUOUS"
    
    return None, "NOT_FOUND"


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
        Dictionary with patient, history, intent, and status.
        None if no patient is found.
        
    Status values in return dict:
        - "FOUND": Unique patient identified
        - "AMBIGUOUS": Multiple patients match query
        - "NOT_FOUND": No patient found
    """
    if not query or not query.strip():
        return None
    
    # Step 1: Identify patient with ambiguity detection
    patient, status = _identify_patient(query, db_session)
    
    # Handle ambiguous case - return with status for chat.py to handle
    if status == "AMBIGUOUS":
        # Get matching patients for disambiguation message
        patients = _find_patients_by_name(query, db_session)
        return {
            "patient": None,
            "history": [],
            "intent": None,
            "status": "AMBIGUOUS",
            "matching_patients": patients
        }
    
    if patient is None:
        return {
            "patient": None,
            "history": [],
            "intent": None,
            "status": "NOT_FOUND",
            "matching_patients": []
        }
    
    # Step 2: Detect intent
    intent = _detect_intent(query)
    
    # Step 3: Retrieve data based on intent
    history = []
    
    if intent == "HISTORY_SUMMARY":
        history = _fetch_history(patient.patient_id, db_session, limit=5)
    elif intent == "CONDITIONS":
        history = []
    else:
        history = []
    
    return {
        "patient": patient,
        "history": history,
        "intent": intent,
        "status": "FOUND",
        "matching_patients": []
    }
