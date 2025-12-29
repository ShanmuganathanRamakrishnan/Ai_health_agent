"""
Relevance Scoring Module for Patient History.
Deterministic, keyword-based scoring for weighted retrieval.
"""
from typing import List, Tuple
from datetime import datetime
import re


# Clinical signal keywords (higher relevance)
CLINICAL_SIGNAL_KEYWORDS = {
    # Worsening indicators
    "exacerbation": 3,
    "worsened": 3,
    "worsening": 3,
    "deteriorated": 3,
    "hospitalization": 4,
    "hospitalized": 4,
    "emergency": 4,
    "new symptoms": 3,
    "complication": 3,
    "flare": 2,
    "acute": 2,
    # Treatment changes
    "adjusted": 2,
    "changed medication": 3,
    "new medication": 3,
    "increased dosage": 2,
    "surgery": 4,
    "procedure": 2,
    # Improvement
    "improved": 2,
    "recovery": 2,
    "resolved": 2,
}

# Routine keywords (lower relevance)
ROUTINE_KEYWORDS = {
    "stable": -1,
    "routine": -2,
    "no acute": -1,
    "no concerns": -1,
    "well-controlled": -1,
    "unchanged": -1,
    "follow-up": -1,
    "regular check": -2,
}


def _parse_date(date_str: str) -> datetime:
    """
    Parse a date string into datetime object.
    Handles common formats.
    """
    if not date_str:
        return datetime.min
    
    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    # If no format matches, return minimum date
    return datetime.min


def _calculate_recency_score(visit_date: str) -> float:
    """
    Calculate recency score (0-10 scale).
    More recent visits score higher.
    """
    parsed_date = _parse_date(visit_date)
    
    if parsed_date == datetime.min:
        return 0
    
    # Calculate days since visit
    days_ago = (datetime.now() - parsed_date).days
    
    # Score based on recency
    if days_ago <= 30:
        return 10.0
    elif days_ago <= 90:
        return 8.0
    elif days_ago <= 180:
        return 6.0
    elif days_ago <= 365:
        return 4.0
    elif days_ago <= 730:
        return 2.0
    else:
        return 1.0


def _calculate_clinical_signal_score(notes: str, treatment: str) -> float:
    """
    Calculate clinical signal score based on keyword presence.
    """
    text = f"{notes or ''} {treatment or ''}".lower()
    
    score = 0.0
    
    # Add points for clinical signals
    for keyword, weight in CLINICAL_SIGNAL_KEYWORDS.items():
        if keyword in text:
            score += weight
    
    # Subtract points for routine indicators
    for keyword, weight in ROUTINE_KEYWORDS.items():
        if keyword in text:
            score += weight  # weight is already negative
    
    return score


def calculate_relevance_score(history_record) -> float:
    """
    Calculate total relevance score for a patient history record.
    
    Score components:
    - Recency (0-10): More recent visits score higher
    - Clinical signals (variable): Clinically significant notes score higher
    
    Returns:
        Float score (higher = more relevant)
    """
    recency_score = _calculate_recency_score(history_record.visit_date)
    clinical_score = _calculate_clinical_signal_score(
        history_record.notes, 
        history_record.treatment
    )
    
    # Weight recency at 40%, clinical signals at 60%
    total_score = (recency_score * 0.4) + (clinical_score * 0.6)
    
    return total_score


def get_weighted_history(
    history_records: list,
    limit: int = 5
) -> Tuple[List, List[dict]]:
    """
    Get top-N history records by weighted relevance score.
    Preserves chronological order of selected records.
    
    Args:
        history_records: List of PatientHistory records
        limit: Maximum number of records to return
        
    Returns:
        Tuple of (sorted_records, scoring_details)
    """
    if not history_records:
        return [], []
    
    # Calculate scores for each record
    scored_records = []
    for record in history_records:
        recency = _calculate_recency_score(record.visit_date)
        clinical = _calculate_clinical_signal_score(record.notes, record.treatment)
        total = calculate_relevance_score(record)
        
        scored_records.append({
            "record": record,
            "recency_score": recency,
            "clinical_score": clinical,
            "total_score": total,
            "visit_date": record.visit_date,
        })
    
    # Sort by total score (descending)
    scored_records.sort(key=lambda x: x["total_score"], reverse=True)
    
    # Select top N
    top_scored = scored_records[:limit]
    
    # Re-sort selected records by date (chronological order)
    top_scored.sort(key=lambda x: _parse_date(x["visit_date"]))
    
    # Extract records and scoring details
    records = [item["record"] for item in top_scored]
    details = [
        {
            "visit_date": item["visit_date"],
            "recency_score": round(item["recency_score"], 2),
            "clinical_score": round(item["clinical_score"], 2),
            "total_score": round(item["total_score"], 2),
        }
        for item in top_scored
    ]
    
    return records, details
