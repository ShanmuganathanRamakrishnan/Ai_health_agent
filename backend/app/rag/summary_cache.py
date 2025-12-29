"""
Patient Summary Cache Module.
Caches LLM-generated patient summaries to reduce latency and LLM calls.
"""
import time
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import Patient, PatientSummary, PatientHistory
from app.llm.mistral import generate


# Summary generation prompt (strict, no hallucination)
SUMMARY_PROMPT_TEMPLATE = """You are a clinical assistant AI.
Generate a concise patient summary using ONLY the data below.
Do not infer or add new information.

Patient Information:
- Name: {name}
- Age: {age}
- Gender: {gender}
- Primary Condition: {condition}
- Risk Level: {risk_level}

Visit History:
{history_text}

Generate a brief summary including:
1. Demographics
2. Primary condition
3. High-level visit trends (no specific dates unless critical)

Summary:"""


def _format_history_for_summary(history: list) -> str:
    """Format patient history for summary generation."""
    if not history:
        return "No visit history available."
    
    lines = []
    for i, record in enumerate(history[:5], start=1):  # Limit to 5 most recent
        lines.append(f"{i}. {record.visit_date}: {record.notes or 'No notes'}")
    return "\n".join(lines)


def get_cached_summary(patient_id: int, db: Session) -> Optional[str]:
    """
    Retrieve cached summary for a patient.
    Returns None if no cache exists.
    """
    summary = db.query(PatientSummary).filter(
        PatientSummary.patient_id == patient_id
    ).first()
    
    if summary:
        return summary.summary_text
    return None


def save_summary(patient_id: int, summary_text: str, db: Session) -> None:
    """
    Save or update patient summary in cache.
    """
    existing = db.query(PatientSummary).filter(
        PatientSummary.patient_id == patient_id
    ).first()
    
    timestamp = datetime.utcnow().isoformat()
    
    if existing:
        existing.summary_text = summary_text
        existing.last_updated = timestamp
    else:
        new_summary = PatientSummary(
            patient_id=patient_id,
            summary_text=summary_text,
            last_updated=timestamp
        )
        db.add(new_summary)
    
    db.commit()


def generate_patient_summary(patient: Patient, history: list) -> str:
    """
    Generate a new patient summary using the LLM.
    """
    history_text = _format_history_for_summary(history)
    
    prompt = SUMMARY_PROMPT_TEMPLATE.format(
        name=patient.name or "Unknown",
        age=patient.age or "Unknown",
        gender=patient.gender or "Unknown",
        condition=patient.primary_condition or "Unknown",
        risk_level=patient.risk_level or "Unknown",
        history_text=history_text
    )
    
    return generate(prompt)


def get_or_generate_summary(
    patient: Patient,
    history: list,
    db: Session
) -> tuple[str, dict]:
    """
    Get summary from cache or generate new one.
    
    Returns:
        tuple: (summary_text, timing_info)
    """
    timing = {
        "cache_hit": False,
        "cache_lookup_ms": 0,
        "generation_ms": 0,
        "total_ms": 0
    }
    
    start_total = time.time()
    
    # Check cache
    start_lookup = time.time()
    cached = get_cached_summary(patient.patient_id, db)
    timing["cache_lookup_ms"] = round((time.time() - start_lookup) * 1000, 2)
    
    if cached:
        timing["cache_hit"] = True
        timing["total_ms"] = round((time.time() - start_total) * 1000, 2)
        return cached, timing
    
    # Generate new summary
    start_gen = time.time()
    summary = generate_patient_summary(patient, history)
    timing["generation_ms"] = round((time.time() - start_gen) * 1000, 2)
    
    # Save to cache
    if summary and summary.strip():
        save_summary(patient.patient_id, summary.strip(), db)
    
    timing["total_ms"] = round((time.time() - start_total) * 1000, 2)
    return summary.strip() if summary else "", timing
