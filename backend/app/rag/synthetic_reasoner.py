"""
Synthetic Reasoning Module for Phase 5.
Enables cross-signal pattern analysis across history, vitals, and labs.
ONLY activates for COMPLEX queries with sufficient multi-source data.
"""
import re
from typing import Optional, List, Tuple

# ============================================
# REASONING LEVELS
# ============================================
REASONING_NONE = "NONE"                # FACTUAL
REASONING_DESCRIPTIVE = "DESCRIPTIVE"  # SUMMARY
REASONING_ANALYTICAL = "ANALYTICAL"    # COMPLEX (Phase 4)
REASONING_SYNTHETIC = "SYNTHETIC"      # ADVANCED (Phase 5)

# ============================================
# FORBIDDEN WORDS (MANDATORY FILTER)
# ============================================
FORBIDDEN_WORDS = [
    "concerning", "severe", "worsening", "dangerous",
    "requires intervention", "critical", "alarming",
    "you should", "i recommend", "treatment",
    "diagnosis", "prognosis", "urgent", "emergency",
    "life-threatening", "prescribe", "medication should",
]

# ============================================
# SYNTHESIS SIGNAL PATTERNS
# Not sole triggers, but signals for synthesis
# ============================================
SYNTHESIS_SIGNAL_PATTERNS = [
    # Aggregation language
    r"\b(overall|altogether|combined|aggregate|across all)\b",
    r"\b(big picture|whole picture|full picture)\b",
    # Cross-signal phrasing
    r"\b(patterns? across|trends? across|data (together|combined))\b",
    r"\b(history and (vitals?|labs?)|vitals? and labs?)\b",
    r"\b(all (the|her|his|their) data)\b",
    # Multi-source synthesis
    r"\b(looking at everything|considering all|taking into account)\b",
    r"\b(synthesis|synthesize|comprehensive view)\b",
    # Temporal cross-reference
    r"\b(over (the )?time.*together|together.*over (the )?time)\b",
]

# ============================================
# FALLBACK RESPONSE
# ============================================
FALLBACK_RESPONSE = (
    "I do not have enough consistent information to summarize patterns "
    "across multiple data sources."
)


def _has_synthesis_signals(query: str) -> Tuple[bool, List[str]]:
    """
    Check if query contains synthesis signals.
    Returns (has_signals, matched_patterns).
    """
    query_lower = query.lower()
    matched = []
    
    for pattern in SYNTHESIS_SIGNAL_PATTERNS:
        if re.search(pattern, query_lower):
            matched.append(pattern)
    
    return len(matched) > 0, matched


def _has_temporal_variation(history_records: list) -> bool:
    """
    Check if history spans a meaningful time range.
    Qualitative check: at least 2 records with different dates.
    """
    if not history_records or len(history_records) < 2:
        return False
    
    dates = set()
    for record in history_records:
        if hasattr(record, 'visit_date') and record.visit_date:
            dates.add(record.visit_date)
    
    return len(dates) >= 2


def _has_mixed_signals(vitals_labs_info: dict) -> bool:
    """
    Check if data has both abnormal AND normal signals.
    Qualitative check for variation in clinical states.
    """
    if not vitals_labs_info:
        return False
    
    vitals_count = vitals_labs_info.get("vitals_count", 0)
    labs_count = vitals_labs_info.get("labs_count", 0)
    abnormal_vitals = vitals_labs_info.get("abnormal_vitals_count", 0)
    abnormal_labs = vitals_labs_info.get("abnormal_labs_count", 0)
    
    # Need some normal AND some abnormal readings
    normal_vitals = vitals_count - abnormal_vitals
    normal_labs = labs_count - abnormal_labs
    
    has_abnormal = (abnormal_vitals > 0) or (abnormal_labs > 0)
    has_normal = (normal_vitals > 0) or (normal_labs > 0)
    
    return has_abnormal and has_normal


def _count_data_sources(
    history_count: int,
    vitals_count: int,
    labs_count: int
) -> int:
    """
    Count how many distinct data sources have data.
    """
    count = 0
    if history_count > 0:
        count += 1
    if vitals_count > 0:
        count += 1
    if labs_count > 0:
        count += 1
    return count


def should_activate_synthetic_reasoning(
    query_type: str,
    query: str,
    history_records: list,
    vitals_labs_info: dict,
    patient_is_valid: bool,
) -> Tuple[bool, str]:
    """
    Determine if Phase 5 SYNTHETIC reasoning should activate.
    Layers on top of Phase 4 ANALYTICAL (COMPLEX).
    
    ALL conditions must pass for activation.
    If ANY fail, falls back to Phase 4 COMPLEX behavior.
    
    Returns:
        (should_activate, reason)
    """
    # Rule 1: Must be COMPLEX query type (already at ANALYTICAL level)
    if query_type != "COMPLEX":
        return False, "Not a COMPLEX query type"
    
    # Rule 2: Patient must be valid (not ambiguous)
    if not patient_is_valid:
        return False, "Patient identity is ambiguous or invalid"
    
    # Rule 3: Check for synthesis signals in query
    has_signals, matched_patterns = _has_synthesis_signals(query)
    if not has_signals:
        return False, "No synthesis signals detected in query"
    
    # Rule 4: Multi-source availability (≥2 data sources with data)
    history_count = len(history_records) if history_records else 0
    vitals_count = vitals_labs_info.get("vitals_count", 0) if vitals_labs_info else 0
    labs_count = vitals_labs_info.get("labs_count", 0) if vitals_labs_info else 0
    
    source_count = _count_data_sources(history_count, vitals_count, labs_count)
    if source_count < 2:
        return False, f"Insufficient data sources ({source_count}/2 required)"
    
    # Rule 5: Qualitative check - temporal variation in history
    if not _has_temporal_variation(history_records):
        return False, "No temporal variation in history records"
    
    # Rule 6: Qualitative check - mixed signals (abnormal + normal)
    if not _has_mixed_signals(vitals_labs_info):
        return False, "No mixed signals (abnormal + normal) in vitals/labs"
    
    # ALL checks passed
    print(f"[PHASE 5] Synthetic reasoning ACTIVATED")
    print(f"[PHASE 5]   Data sources: history={history_count}, vitals={vitals_count}, labs={labs_count}")
    print(f"[PHASE 5]   Synthesis signals: {matched_patterns[:2]}")
    
    return True, "All activation rules passed"


def build_cross_signal_summary(
    history_records: list,
    vitals_labs_info: dict,
    trend_result: dict
) -> Optional[str]:
    """
    Generate descriptive cross-signal summary for Phase 5.
    Uses neutral, observational language only.
    
    Returns:
        Formatted summary string or None if insufficient data.
    """
    if not history_records or not vitals_labs_info:
        return None
    
    lines = ["Cross-Signal Pattern Summary (Observational Only):"]
    
    # 1. Temporal alignment description
    vitals_count = vitals_labs_info.get("vitals_count", 0)
    labs_count = vitals_labs_info.get("labs_count", 0)
    encounter_count = len(vitals_labs_info.get("encounter_ids", []))
    history_count = len(history_records)
    
    lines.append(f"- Data span: {history_count} visit records, {encounter_count} encounters documented")
    
    # 2. Frequency comparisons
    abnormal_vitals = vitals_labs_info.get("abnormal_vitals_count", 0)
    abnormal_labs = vitals_labs_info.get("abnormal_labs_count", 0)
    
    if vitals_count > 0:
        vitals_abnormal_pct = (abnormal_vitals / vitals_count) * 100
        if vitals_abnormal_pct < 25:
            vitals_pattern = "predominantly within expected ranges"
        elif vitals_abnormal_pct < 50:
            vitals_pattern = "intermittent readings outside expected ranges"
        else:
            vitals_pattern = "frequent readings outside expected ranges"
        lines.append(f"- Vital signs: {vitals_pattern}")
    
    if labs_count > 0:
        labs_abnormal_pct = (abnormal_labs / labs_count) * 100
        if labs_abnormal_pct < 20:
            labs_pattern = "results predominantly within reference ranges"
        elif labs_abnormal_pct < 40:
            labs_pattern = "some results outside reference ranges"
        else:
            labs_pattern = "multiple results outside reference ranges"
        lines.append(f"- Laboratory tests: {labs_pattern}")
    
    # 3. Stability vs intermittency (from trend analysis)
    if trend_result:
        pattern = trend_result.get("pattern", "UNKNOWN")
        if pattern == "STABLE":
            stability = "Records suggest a relatively stable pattern over the documented period."
        elif pattern == "IMPROVING":
            stability = "Records suggest an improving pattern over the documented period."
        elif pattern == "WORSENING":
            # Use neutral language - no "worsening"
            stability = "Records suggest changes in condition metrics over the documented period."
        elif pattern == "INTERMITTENT":
            stability = "Records suggest variable patterns with fluctuations over time."
        else:
            stability = "Pattern across records is not clearly defined."
        lines.append(f"- Temporal pattern: {stability}")
    
    # 4. Limitation statement (MANDATORY)
    lines.append("")
    lines.append("Note: This summary reflects documented data only and does not constitute clinical assessment.")
    
    return "\n".join(lines)


def validate_output_language(text: str) -> Tuple[bool, List[str]]:
    """
    Validate LLM output does not contain forbidden medical language.
    
    Returns:
        (is_valid, list_of_violations)
    """
    if not text:
        return True, []
    
    text_lower = text.lower()
    violations = []
    
    for word in FORBIDDEN_WORDS:
        if word in text_lower:
            violations.append(word)
    
    is_valid = len(violations) == 0
    
    if not is_valid:
        print(f"[PHASE 5] Output validation FAILED - forbidden words: {violations}")
    else:
        print(f"[PHASE 5] Output validation PASSED - no forbidden words")
    
    return is_valid, violations
