"""
Trend Analyzer Module.
Provides deterministic temporal trend analysis for patient history.
Used to ground COMPLEX queries before LLM invocation.
"""
from typing import Optional
from collections import Counter


# Keywords indicating symptom patterns (generic, not condition-specific)
WORSENING_KEYWORDS = {
    "exacerbation", "worsened", "worsening", "deteriorated", "deteriorating",
    "declined", "declining", "acute", "flare", "flare-up",
    "new symptoms", "increased", "elevated", "severe", "concerning"
}

IMPROVEMENT_KEYWORDS = {
    "improved", "improving", "better", "resolved", "stable",
    "well-controlled", "controlled", "maintained", "normal",
    "progressing well", "recovery", "recovered"
}

NEUTRAL_KEYWORDS = {
    "routine", "follow-up", "check", "review", "monitoring",
    "no acute", "no change", "consistent", "unchanged"
}


def _extract_patterns(notes: str) -> dict:
    """
    Extract pattern indicators from clinical notes.
    Returns counts of worsening, improving, and neutral mentions.
    """
    if not notes:
        return {"worsening": 0, "improving": 0, "neutral": 0}
    
    notes_lower = notes.lower()
    
    worsening = sum(1 for kw in WORSENING_KEYWORDS if kw in notes_lower)
    improving = sum(1 for kw in IMPROVEMENT_KEYWORDS if kw in notes_lower)
    neutral = sum(1 for kw in NEUTRAL_KEYWORDS if kw in notes_lower)
    
    return {
        "worsening": worsening,
        "improving": improving,
        "neutral": neutral
    }


def analyze_trend(patient_history: list) -> dict:
    """
    Analyze temporal trends in patient history.
    
    Args:
        patient_history: List of PatientHistory ORM objects
        
    Returns:
        dict with trend analysis results
    """
    if not patient_history:
        return {
            "has_history": False,
            "visit_count": 0,
            "summary": "No visit history available for trend analysis.",
            "pattern": "INSUFFICIENT_DATA",
            "details": []
        }
    
    # Sort by visit date (ascending for chronological order)
    sorted_history = sorted(
        patient_history,
        key=lambda h: h.visit_date or "",
        reverse=False
    )
    
    # Analyze each visit
    visit_details = []
    total_worsening = 0
    total_improving = 0
    total_neutral = 0
    
    for record in sorted_history:
        patterns = _extract_patterns(record.notes)
        total_worsening += patterns["worsening"]
        total_improving += patterns["improving"]
        total_neutral += patterns["neutral"]
        
        # Determine visit trend
        if patterns["worsening"] > patterns["improving"]:
            visit_trend = "WORSENING"
        elif patterns["improving"] > patterns["worsening"]:
            visit_trend = "IMPROVING"
        else:
            visit_trend = "STABLE"
        
        visit_details.append({
            "date": record.visit_date,
            "trend": visit_trend,
            "notes_snippet": (record.notes[:100] + "...") if record.notes and len(record.notes) > 100 else record.notes
        })
    
    # Determine overall pattern
    if total_worsening == 0 and total_improving == 0:
        pattern = "NO_CLEAR_TREND"
        summary = "Visit notes do not contain explicit indicators of symptom progression or worsening."
    elif total_worsening > total_improving * 2:
        pattern = "WORSENING_TREND"
        summary = f"Notes indicate potential worsening trend ({total_worsening} worsening indicators vs {total_improving} improvement indicators)."
    elif total_improving > total_worsening * 2:
        pattern = "IMPROVING_TREND"
        summary = f"Notes indicate improvement trend ({total_improving} improvement indicators vs {total_worsening} worsening indicators)."
    elif total_worsening > 0 and total_improving > 0:
        pattern = "INTERMITTENT"
        summary = f"Notes show intermittent pattern with both improvements and exacerbations ({total_improving} improving, {total_worsening} worsening)."
    else:
        pattern = "STABLE"
        summary = f"Notes indicate generally stable condition ({total_neutral} routine/stable indicators)."
    
    return {
        "has_history": True,
        "visit_count": len(sorted_history),
        "summary": summary,
        "pattern": pattern,
        "total_worsening": total_worsening,
        "total_improving": total_improving,
        "total_neutral": total_neutral,
        "details": visit_details
    }


def format_trend_context(trend_result: dict) -> str:
    """
    Format trend analysis for inclusion in LLM prompt.
    """
    if not trend_result.get("has_history"):
        return "Trend Analysis: No visit history available."
    
    lines = [
        "Trend Analysis:",
        f"- Total visits analyzed: {trend_result['visit_count']}",
        f"- Overall pattern: {trend_result['pattern']}",
        f"- {trend_result['summary']}",
    ]
    
    # Add explicit grounding statement
    if trend_result["pattern"] in ("NO_CLEAR_TREND", "STABLE", "INTERMITTENT"):
        lines.append("- NOTE: There is NO consistent worsening pattern documented in the visit notes.")
    
    return "\n".join(lines)
