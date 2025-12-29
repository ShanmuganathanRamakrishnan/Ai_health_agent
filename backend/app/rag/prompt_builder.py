"""
Prompt construction for LLM with retrieved context.
Builds structured, hallucination-resistant prompts for clinical Q&A.
"""
from typing import Optional

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
Do not provide medical advice."""


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


def build_prompt(
    patient,
    history: list,
    intent: str,
    user_query: str
) -> str:
    """
    Build a structured prompt for the LLM.
    
    Args:
        patient: Patient ORM object.
        history: List of PatientHistory ORM objects.
        intent: BASIC_INFO, HISTORY_SUMMARY, or CONDITIONS.
        user_query: Original user question.
        
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
    
    # 4. User question
    sections.append(f"Question: {user_query}")
    
    # Join with double newlines for clarity
    return "\n\n".join(sections)
