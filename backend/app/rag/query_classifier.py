"""
Query Classifier Module.
Classifies queries to enable direct DB routing and reduce unnecessary LLM calls.

Precedence: 
1. FACTUAL (static attributes) - explicit lookups
2. SEVERITY_ASSESSMENT - qualitative evaluation queries
3. COMPLEX (temporal) - change/trend queries
4. SUMMARY - overview queries
5. FACTUAL (simple) - single field
6. COMPLEX (default)
"""
import re
from typing import Optional


# ============================================
# SEVERITY_ASSESSMENT DETECTION
# Grammar-aware structural patterns
# ============================================

# Structural patterns for qualitative assessment questions
# These detect the STRUCTURE of asking for evaluation, not just keywords
SEVERITY_ASSESSMENT_PATTERNS = [
    # "How [adjective] is [condition/it]?" patterns
    r"\bhow\s+(bad|serious|severe|critical|dangerous|concerning|worrying|urgent)\b",
    r"\bhow\s+(good|stable|mild|manageable)\b",
    
    # "Is [it/condition] [adjective]?" patterns  
    r"\bis\s+(his|her|the|this)\s+\w*\s*(serious|severe|bad|dangerous|critical|concerning|worrying)\b",
    r"\bis\s+(it|this)\s+(serious|severe|bad|dangerous|critical|concerning)\b",
    
    # "Should I [worry/be concerned]?" patterns
    r"\bshould\s+(i|we)\s+(be\s+)?(worried|concerned|alarmed)\b",
    r"\bshould\s+(i|we)\s+worry\b",
    r"\bis\s+(this|it)\s+(something\s+to\s+)?(worry|concern)\b",
    
    # "Does [he/she] have a [severe/bad] case?" patterns
    r"\b(does|do)\s+(he|she|they)\s+have\s+a\s+(severe|bad|serious|mild|moderate)\s+(case|condition)\b",
    
    # "What is the severity/seriousness?" patterns
    r"\bwhat\s+is\s+(the\s+)?(severity|seriousness|prognosis)\b",
    r"\bhow\s+(concerning|worrying)\s+is\b",
    
    # "Is this a [severe/mild] case?" patterns
    r"\bis\s+(this|it)\s+a\s+(severe|mild|serious|bad|moderate)\s+(case|condition)\b",
]

# Qualitative assessment keywords (secondary check)
# Only used in combination with structural analysis
QUALITATIVE_KEYWORDS = {
    # Degree/intensity
    "bad", "serious", "severe", "critical", "dangerous",
    "mild", "moderate", "manageable", "stable",
    # Concern/worry
    "worried", "concern", "concerning", "worrying", "alarmed",
    "worry", "alarming", "urgent",
    # Evaluation
    "seriousness", "prognosis",
}

# Explicit FACTUAL request patterns (negation for severity)
# If these patterns match, it's FACTUAL not SEVERITY
EXPLICIT_FACTUAL_PATTERNS = [
    r"\bwhat\s+(is|are)\s+(his|her|the)\s+(diagnosis|condition|disease|illness)\b",
    r"\bwhat\s+condition\s+(does|do)\b",
    r"\bwhat\s+is\s+\w+\s+(diagnosed|suffering)\b",
    r"\bhow\s+old\b",
    r"\bwhat\s+is\s+(his|her|the)\s+age\b",
    r"\brisk\s+level\b",
]


def _is_severity_assessment(query: str) -> bool:
    """
    Detect if query is asking for a qualitative severity assessment.
    
    Uses grammar-aware structural pattern matching:
    1. Check structural patterns first (how bad, is it serious, etc.)
    2. Verify not an explicit factual request
    3. Confirm qualitative keywords are present
    """
    query_lower = query.lower()
    
    # First: Exclude explicit factual requests
    for pattern in EXPLICIT_FACTUAL_PATTERNS:
        if re.search(pattern, query_lower):
            return False
    
    # Second: Check structural patterns
    for pattern in SEVERITY_ASSESSMENT_PATTERNS:
        if re.search(pattern, query_lower):
            return True
    
    # Third: Secondary check - qualitative keywords in question context
    # Only if query starts with question words and contains qualitative terms
    question_starters = ("how", "is", "are", "should", "does", "do", "what")
    has_question_start = query_lower.strip().split()[0] if query_lower.strip() else ""
    
    if has_question_start in question_starters:
        for keyword in QUALITATIVE_KEYWORDS:
            if keyword in query_lower:
                # Make sure it's not asking WHAT the condition is
                if "what condition" not in query_lower and "what is" not in query_lower[:20]:
                    return True
    
    return False


# ============================================
# STATIC ATTRIBUTE PATTERNS (FACTUAL)
# ============================================

STATIC_ATTRIBUTE_PATTERNS = [
    # Age patterns
    (r"\bhow old\b", "age"),
    (r"\bage\b", "age"),
    (r"\byears old\b", "age"),
    # Condition patterns (explicit diagnosis requests)
    (r"\bdiagnosed with\b", "primary_condition"),
    (r"\bdiagnosis\b", "primary_condition"),
    (r"\bwhat condition\b", "primary_condition"),
    (r"\bwhat is .* condition\b", "primary_condition"),
    (r"\bwhat (?:does|do) .* have\b", "primary_condition"),
    # Risk level patterns (explicit)
    (r"\brisk level\b", "risk_level"),
    (r"\bwhat is .* risk\s*level\b", "risk_level"),
    # Gender patterns
    (r"\bgender\b", "gender"),
    (r"\bwhat sex\b", "gender"),
]

# Temporal/change keywords for COMPLEX
TEMPORAL_CHANGE_KEYWORDS = {
    "changed", "changes", "changing",
    "worsened", "worsen", "worsening",
    "progressed", "progress", "progression",
    "improved", "improve", "improving",
    "deteriorated", "deteriorating",
    "over time", "over the years", "over the months",
    "throughout", "since then", "before and after",
    "trend", "trends", "pattern", "patterns",
    "compare", "comparison", "difference",
}

# Summary keywords
SUMMARY_KEYWORDS = {
    "summary", "summarize", "summarise",
    "overview", "tell me about",
    "who is", "describe", "background",
    "treatment history", "visit history", "visits",
    "history",
}

# Simple FACTUAL mappings
FACTUAL_MAPPINGS = {
    "diagnosed": "primary_condition",
    "diagnosis": "primary_condition",
    "disease": "primary_condition",
    "illness": "primary_condition",
    "age": "age",
    "old": "age",
    "gender": "gender",
    "sex": "gender",
}


def _check_static_attribute(query: str) -> Optional[str]:
    """Check if query matches a static attribute pattern."""
    query_lower = query.lower()
    
    for pattern, field in STATIC_ATTRIBUTE_PATTERNS:
        if re.search(pattern, query_lower):
            has_temporal = any(kw in query_lower for kw in TEMPORAL_CHANGE_KEYWORDS)
            if not has_temporal:
                return field
    
    return None


def _is_temporal_complex_query(query: str) -> bool:
    """Check if query requires complex temporal/change analysis."""
    query_lower = query.lower()
    
    for keyword in TEMPORAL_CHANGE_KEYWORDS:
        if keyword in query_lower:
            return True
    
    return False


def _is_summary_query(query: str) -> bool:
    """Check if query is asking for a summary."""
    query_lower = query.lower()
    
    for keyword in SUMMARY_KEYWORDS:
        if keyword in query_lower:
            return True
    
    return False


def _check_factual_field(query: str) -> Optional[str]:
    """Check if query asks for a single factual field."""
    query_lower = query.lower()
    matched_fields = set()
    
    for keyword, field in FACTUAL_MAPPINGS.items():
        if keyword in query_lower:
            matched_fields.add(field)
    
    if len(matched_fields) == 1:
        return matched_fields.pop()
    
    return None


def classify_query(query: str) -> dict:
    """
    Classify a query with grammar-aware intent detection.
    
    Precedence:
    1. FACTUAL (static attributes) - explicit lookups
    2. SEVERITY_ASSESSMENT - qualitative evaluation queries
    3. COMPLEX (temporal) - change/trend queries
    4. SUMMARY - overview queries
    5. FACTUAL (simple) - single field
    6. COMPLEX (default)
    """
    if not query or not query.strip():
        return {"type": "COMPLEX", "field": None}
    
    # 1. STATIC ATTRIBUTE - explicit factual (highest priority)
    static_field = _check_static_attribute(query)
    if static_field:
        return {"type": "FACTUAL", "field": static_field}
    
    # 2. SEVERITY_ASSESSMENT - qualitative evaluation
    if _is_severity_assessment(query):
        return {"type": "SEVERITY_ASSESSMENT", "field": None}
    
    # 3. TEMPORAL COMPLEX - change analysis
    if _is_temporal_complex_query(query):
        return {"type": "COMPLEX", "field": None}
    
    # 4. SUMMARY - overview queries
    if _is_summary_query(query):
        return {"type": "SUMMARY", "field": None}
    
    # 5. SIMPLE FACTUAL - single field lookup
    factual_field = _check_factual_field(query)
    if factual_field:
        return {"type": "FACTUAL", "field": factual_field}
    
    # 6. Default to COMPLEX
    return {"type": "COMPLEX", "field": None}


def format_factual_response(patient, field: str) -> str:
    """Format a factual response for a specific field."""
    name = patient.name or "The patient"
    
    if field == "primary_condition":
        value = patient.primary_condition or "no known condition"
        return f"{name} is diagnosed with {value}."
    
    elif field == "age":
        value = patient.age
        if value:
            return f"{name} is {value} years old."
        return f"Age information is not available for {name}."
    
    elif field == "gender":
        value = patient.gender or "not specified"
        return f"{name}'s gender is {value}."
    
    elif field == "risk_level":
        value = patient.risk_level or "not assessed"
        return f"{name} has a {value} risk level."
    
    return f"Information about {field} is not available."


def format_severity_response(patient, history_signals: dict) -> str:
    """
    Format a concise severity assessment response (2-3 sentences max).
    """
    name = patient.name or "The patient"
    risk = patient.risk_level or "unknown"
    
    # Build concise response
    parts = []
    
    # Risk level (1 sentence)
    risk_lower = (risk or "").lower()
    if risk_lower == "high":
        parts.append(f"{name} has a High risk level, indicating close monitoring is needed.")
    elif risk_lower == "medium":
        parts.append(f"{name} has a Medium risk level, suggesting moderate concern.")
    elif risk_lower == "low":
        parts.append(f"{name} has a Low risk level; the condition is currently manageable.")
    else:
        parts.append(f"No formal risk level is recorded for {name}.")
    
    # History trend (1 sentence if relevant)
    worsening = history_signals.get("worsening", 0)
    improving = history_signals.get("improving", 0)
    
    if worsening > improving:
        parts.append(f"Recent records show {worsening} concerning indicator(s).")
    elif improving > worsening:
        parts.append(f"Recent records show {improving} positive indicator(s).")
    
    # Disclaimer (1 sentence)
    parts.append("Consult a healthcare provider for clinical assessment.")
    
    return " ".join(parts)

