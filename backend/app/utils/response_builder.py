"""
Response Builder Module.
Attaches deterministic confidence levels and evidence attribution to responses.
"""
from typing import List, Optional
from enum import Enum


class ConfidenceLevel(str, Enum):
    """Deterministic confidence levels based on execution path."""
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class ResponseType(str, Enum):
    """Response types for confidence mapping."""
    FACTUAL = "FACTUAL"
    SUMMARY_HIT = "SUMMARY_HIT"
    SUMMARY_MISS = "SUMMARY_MISS"
    COMPLEX = "COMPLEX"
    SEVERITY_ASSESSMENT = "SEVERITY_ASSESSMENT"
    REFUSAL = "REFUSAL"


# Confidence mapping (LOCKED - deterministic based on execution path)
CONFIDENCE_MAP = {
    ResponseType.FACTUAL: ConfidenceLevel.HIGH,
    ResponseType.SUMMARY_HIT: ConfidenceLevel.HIGH,
    ResponseType.SUMMARY_MISS: ConfidenceLevel.MEDIUM,
    ResponseType.COMPLEX: ConfidenceLevel.MEDIUM,
    ResponseType.SEVERITY_ASSESSMENT: ConfidenceLevel.MEDIUM,
    ResponseType.REFUSAL: ConfidenceLevel.LOW,
}


def build_response(
    answer: str,
    response_type: ResponseType,
    evidence: List[str],
    timing_ms: Optional[float] = None
) -> dict:
    """
    Build a standardized response with confidence and evidence.
    
    Args:
        answer: The response text
        response_type: Type of response for confidence mapping
        evidence: List of evidence sources used
        timing_ms: Optional execution time in milliseconds
        
    Returns:
        Structured response dict with answer, confidence, and evidence
    """
    confidence = CONFIDENCE_MAP.get(response_type, ConfidenceLevel.LOW)
    
    response = {
        "answer": answer,
        "confidence": confidence.value,
        "evidence": evidence,
    }
    
    if timing_ms is not None:
        response["timing_ms"] = timing_ms
    
    return response


# Evidence source constants (for consistency)
class EvidenceSource:
    """Standard evidence source strings."""
    # Database fields
    DB_PRIMARY_CONDITION = "patients.primary_condition"
    DB_AGE = "patients.age"
    DB_GENDER = "patients.gender"
    DB_RISK_LEVEL = "patients.risk_level"
    DB_NAME = "patients.name"
    
    # Cache
    CACHED_SUMMARY = "cached_patient_summary"
    
    # Generated content
    PATIENT_HISTORY = "patient_history (weighted: recency + clinical signals)"
    TREND_ANALYSIS = "trend_analysis"
    GENERATED_SUMMARY = "generated_summary"
    
    # Refusal reasons
    AMBIGUOUS_REFERENCE = "ambiguous patient reference"
    GENDER_MISMATCH = "pronoun gender mismatch"
    PATIENT_NOT_FOUND = "patient not found in database"
    INSUFFICIENT_DATA = "insufficient data for analysis"
    NO_CONTEXT = "no prior patient context"


def get_factual_evidence(field: str) -> List[str]:
    """Get evidence list for a FACTUAL query based on DB field."""
    field_to_evidence = {
        "primary_condition": [EvidenceSource.DB_PRIMARY_CONDITION],
        "age": [EvidenceSource.DB_AGE],
        "gender": [EvidenceSource.DB_GENDER],
        "risk_level": [EvidenceSource.DB_RISK_LEVEL],
    }
    return field_to_evidence.get(field, [f"patients.{field}"])


def get_summary_evidence(cache_hit: bool) -> List[str]:
    """Get evidence list for a SUMMARY query."""
    if cache_hit:
        return [EvidenceSource.CACHED_SUMMARY]
    else:
        return [EvidenceSource.PATIENT_HISTORY, EvidenceSource.GENERATED_SUMMARY]


def get_complex_evidence() -> List[str]:
    """Get evidence list for a COMPLEX query."""
    return [EvidenceSource.PATIENT_HISTORY, EvidenceSource.TREND_ANALYSIS]


def get_refusal_evidence(reason: str) -> List[str]:
    """Get evidence list for a REFUSAL response."""
    reason_to_evidence = {
        "GENDER_MISMATCH": [EvidenceSource.GENDER_MISMATCH],
        "NO_CONTEXT": [EvidenceSource.NO_CONTEXT],
        "PATIENT_NOT_FOUND": [EvidenceSource.PATIENT_NOT_FOUND],
        "INSUFFICIENT_DATA": [EvidenceSource.INSUFFICIENT_DATA],
        "AMBIGUOUS": [EvidenceSource.AMBIGUOUS_REFERENCE],
    }
    return reason_to_evidence.get(reason, [EvidenceSource.INSUFFICIENT_DATA])
