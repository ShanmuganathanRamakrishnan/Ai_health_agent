"""
Prompt construction for LLM with retrieved context.
Builds structured, hallucination-resistant prompts for clinical Q&A.
"""
from typing import Optional, List

# -------------------------------
# System prompt (locked)
# -------------------------------
SYSTEM_PROMPT = """You are a clinical assistant AI.

Your task is to answer questions ONLY using the patient data provided below.
Do not use prior knowledge.
Do not guess or infer information that is not explicitly present.

If the requested information is not available in the data, clearly say:
'I do not have enough information to answer that.'

Be concise, factual, and neutral.
Do not provide medical advice.
Do not make diagnostic conclusions.
Describe patterns, not judgments."""


def _format_patient_info(patient) -> str:
    """
    Format patient demographics into structured text.
    Omits fields that are None or empty.
    """
    lines = ["Patient Information:"]
    
    if patient.name:
        lines.append(f"- Name: {patient.name}")
    if patient.age is not None:
        lines.append(f"- Age: {patient.age}")
    if patient.gender:
        lines.append(f"- Gender: {patient.gender}")
    if patient.risk_level:
        lines.append(f"- Risk Level: {patient.risk_level}")
    if patient.primary_condition:
        lines.append(f"- Primary Condition: {patient.primary_condition}")
    
    return "\n".join(lines)


def _format_history(history: list) -> Optional[str]:
    """
    Format patient history records into numbered list.
    Returns None if history is empty.
    """
    if not history:
        return None
    
    lines = ["Patient History:"]
    
    for i, record in enumerate(history, start=1):
        lines.append(f"{i}. Date: {record.visit_date}")
        
        if record.notes:
            lines.append(f"   Notes: {record.notes}")
        if record.treatment:
            lines.append(f"   Treatment: {record.treatment}")
        if record.clinician:
            lines.append(f"   Clinician: {record.clinician}")
    
    return "\n".join(lines)


def _format_vitals_labs_summary(vitals_labs_info: dict) -> Optional[str]:
    """
    Format vitals and labs into a descriptive summary for COMPLEX queries.
    Uses neutral, pattern-based language without diagnostic conclusions.
    
    Args:
        vitals_labs_info: Dict from fetch_vitals_labs_for_patient()
        
    Returns:
        Formatted summary string or None if no data
    """
    if not vitals_labs_info:
        return None
    
    vitals_count = vitals_labs_info.get("vitals_count", 0)
    labs_count = vitals_labs_info.get("labs_count", 0)
    abnormal_vitals = vitals_labs_info.get("abnormal_vitals_count", 0)
    abnormal_labs = vitals_labs_info.get("abnormal_labs_count", 0)
    
    if vitals_count == 0 and labs_count == 0:
        return None
    
    lines = ["Vitals & Lab Trends (Summary Only):"]
    
    # Vitals summary
    if vitals_count > 0:
        normal_vitals = vitals_count - abnormal_vitals
        abnormal_pct = (abnormal_vitals / vitals_count) * 100
        
        if abnormal_pct < 20:
            pattern = "mostly within expected ranges"
        elif abnormal_pct < 40:
            pattern = "occasional readings outside expected ranges"
        elif abnormal_pct < 60:
            pattern = "intermittent abnormal readings observed"
        else:
            pattern = "frequent readings outside expected ranges"
        
        lines.append(f"- Vitals: {vitals_count} readings recorded, {pattern}")
    
    # Labs summary
    if labs_count > 0:
        normal_labs = labs_count - abnormal_labs
        abnormal_lab_pct = (abnormal_labs / labs_count) * 100
        
        if abnormal_lab_pct < 15:
            lab_pattern = "results predominantly within reference ranges"
        elif abnormal_lab_pct < 30:
            lab_pattern = "some results outside reference ranges"
        else:
            lab_pattern = "multiple results outside reference ranges"
        
        lines.append(f"- Labs: {labs_count} tests recorded, {lab_pattern}")
    
    # Add descriptive guidance (no raw values)
    lines.append("- Note: This summary reflects recorded patterns only. Details require clinical review.")
    
    return "\n".join(lines)


def build_prompt(
    patient,
    history: list,
    intent: str,
    user_query: str,
    vitals_labs_info: dict = None
) -> str:
    """
    Build a structured prompt for the LLM.
    
    Args:
        patient: Patient ORM object.
        history: List of PatientHistory ORM objects.
        intent: BASIC_INFO, HISTORY_SUMMARY, or CONDITIONS.
        user_query: Original user question.
        vitals_labs_info: Optional dict from fetch_vitals_labs_for_patient() (COMPLEX only)
        
    Returns:
        Complete prompt string ready for LLM.
    """
    sections = []
    
    # 1. System prompt
    sections.append(SYSTEM_PROMPT)
    
    # 2. Patient information (always included)
    patient_info = _format_patient_info(patient)
    sections.append(patient_info)
    
    # 3. Patient history (only for HISTORY_SUMMARY with non-empty history)
    if intent == "HISTORY_SUMMARY" and history:
        history_text = _format_history(history)
        if history_text:
            sections.append(history_text)
    
    # 4. Vitals & Labs summary (COMPLEX queries only)
    # This is Phase 4: include descriptive patterns, no raw values
    if intent == "HISTORY_SUMMARY" and vitals_labs_info:
        vitals_labs_text = _format_vitals_labs_summary(vitals_labs_info)
        if vitals_labs_text:
            sections.append(vitals_labs_text)
            print(f"[PHASE 4] Vitals/Labs summary INCLUDED in COMPLEX prompt")
        else:
            print(f"[PHASE 4] No vitals/labs data to include")
    
    # 5. User question
    sections.append(f"Question: {user_query}")
    
    # Join with double newlines for clarity
    return "\n\n".join(sections)

