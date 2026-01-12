"""
Chat API endpoints.
POST /chat - RAG pipeline with reference resolution, query classification,
summary cache, trend analysis, LLM, and confidence + evidence attribution.
"""
import time
from typing import List, Optional
from fastapi import APIRouter
from pydantic import BaseModel

from app.db.database import SessionLocal
from app.rag.retriever import retrieve_context, _fetch_history, fetch_weighted_history
from app.rag.relevance_scorer import fetch_vitals_labs_for_patient
from app.rag.prompt_builder import build_prompt
from app.rag.summary_cache import get_or_generate_summary
from app.rag.query_classifier import classify_query, format_factual_response, format_severity_response
from app.rag.trend_analyzer import analyze_trend, format_trend_context
from app.utils.reference_resolver import resolve_patient_reference, update_context_from_patient
from app.utils.response_builder import (
    ResponseType,
    build_response,
    get_factual_evidence,
    get_summary_evidence,
    get_complex_evidence,
    get_refusal_evidence,
)
from app.llm.mistral import generate


router = APIRouter()


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    query: str


class ChatResponse(BaseModel):
    """Response model for chat endpoint with confidence and evidence."""
    answer: str
    confidence: str  # High, Medium, Low
    evidence: List[str]
    timing_ms: Optional[float] = None


@router.post("/", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Chat endpoint with intelligent query routing and confidence attribution.
    
    Flow:
    1. Validate query
    2. Resolve patient reference (pronouns, possessives, explicit names)
    3. Retrieve patient context
    4. Classify query (FACTUAL/SUMMARY/COMPLEX)
    5. Route and generate response with confidence + evidence
    """
    start_time = time.time()
    
    # Edge case: Empty query
    if not request.query or not request.query.strip():
        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        response = build_response(
            answer="Please provide a question to get started.",
            response_type=ResponseType.REFUSAL,
            evidence=get_refusal_evidence("INSUFFICIENT_DATA"),
            timing_ms=elapsed_ms
        )
        return ChatResponse(**response)
    
    # Open database session
    db = SessionLocal()
    try:
        # ============================================
        # STEP 1: Reference Resolution (pronouns, possessives)
        # ============================================
        resolved_patient, resolution_method = resolve_patient_reference(request.query, db)
        
        # Handle gender mismatch (e.g., "his" when last patient is female)
        if resolution_method == "GENDER_MISMATCH":
            elapsed_ms = round((time.time() - start_time) * 1000, 2)
            response = build_response(
                answer="I'm not sure which patient you're referring to. Could you please specify the patient's name?",
                response_type=ResponseType.REFUSAL,
                evidence=get_refusal_evidence("GENDER_MISMATCH"),
                timing_ms=elapsed_ms
            )
            return ChatResponse(**response)
        
        # Handle pronoun with no prior context
        if resolution_method == "NO_CONTEXT":
            elapsed_ms = round((time.time() - start_time) * 1000, 2)
            response = build_response(
                answer="I'm not sure which patient you're referring to. Could you please specify the patient's name?",
                response_type=ResponseType.REFUSAL,
                evidence=get_refusal_evidence("NO_CONTEXT"),
                timing_ms=elapsed_ms
            )
            return ChatResponse(**response)
        
        if resolved_patient and resolution_method in ("PRONOUN", "POSSESSIVE"):
            print(f"[REFERENCE] Resolved via {resolution_method}: {resolved_patient.name} (ID: {resolved_patient.patient_id})")
            patient = resolved_patient
            # For resolved references, use HISTORY_SUMMARY intent by default
            intent = "HISTORY_SUMMARY"
            history = _fetch_history(patient.patient_id, db, limit=5)
        else:
            # ============================================
            # STEP 2: Standard retrieval (explicit names)
            # ============================================
            context = retrieve_context(request.query, db)
            
            # Edge case: Patient not found
            if context is None:
                elapsed_ms = round((time.time() - start_time) * 1000, 2)
                response = build_response(
                    answer="Patient not found in the database.",
                    response_type=ResponseType.REFUSAL,
                    evidence=get_refusal_evidence("PATIENT_NOT_FOUND"),
                    timing_ms=elapsed_ms
                )
                return ChatResponse(**response)
            
            # Handle AMBIGUOUS status - ask for clarification
            if context.get("status") == "AMBIGUOUS":
                matching = context.get("matching_patients", [])
                count = len(matching)
                
                # Structured clarification message
                header = f"Multiple patients found ({count} matches)"
                patient_lines = [f"• {p.name}, age {p.age}" for p in matching[:5]]
                footer = "Please specify the full name or add more details."
                
                if count > 5:
                    patient_lines.append(f"• ...and {count - 5} more")
                
                clarification = f"{header}\n\n" + "\n".join(patient_lines) + f"\n\n{footer}"
                
                elapsed_ms = round((time.time() - start_time) * 1000, 2)
                response = build_response(
                    answer=clarification,
                    response_type=ResponseType.REFUSAL,
                    evidence=["ambiguous_patient_reference"],
                    timing_ms=elapsed_ms
                )
                print(f"[AMBIGUOUS] Returning clarification for {count} matches")
                return ChatResponse(**response)
            
            # Handle NOT_FOUND status
            if context.get("status") == "NOT_FOUND":
                elapsed_ms = round((time.time() - start_time) * 1000, 2)
                response = build_response(
                    answer="No matching patient found. Please check the spelling or provide more details.",
                    response_type=ResponseType.REFUSAL,
                    evidence=get_refusal_evidence("PATIENT_NOT_FOUND"),
                    timing_ms=elapsed_ms
                )
                return ChatResponse(**response)
            
            patient = context.get("patient")
            history = context.get("history", [])
            intent = context.get("intent")
            
            # Update context for future pronoun resolution (using patient_id)
            if patient:
                update_context_from_patient(patient)
                print(f"[CONTEXT] Stored active patient: id={patient.patient_id}, name={patient.name}")
        
        # Edge case: Missing required fields
        if patient is None or intent is None:
            elapsed_ms = round((time.time() - start_time) * 1000, 2)
            response = build_response(
                answer="I do not have enough information to answer that.",
                response_type=ResponseType.REFUSAL,
                evidence=get_refusal_evidence("INSUFFICIENT_DATA"),
                timing_ms=elapsed_ms
            )
            return ChatResponse(**response)
        
        # ============================================
        # STEP 3: Classify the query
        # ============================================
        classification = classify_query(request.query)
        query_type = classification["type"]
        field = classification.get("field")
        
        # ============================================
        # FACTUAL: Direct DB read (no LLM, no cache)
        # ============================================
        if query_type == "FACTUAL" and field:
            answer = format_factual_response(patient, field)
            elapsed_ms = round((time.time() - start_time) * 1000, 2)
            print(f"[FACTUAL] Patient {patient.patient_id}, field={field}: {elapsed_ms}ms")
            
            response = build_response(
                answer=answer,
                response_type=ResponseType.FACTUAL,
                evidence=get_factual_evidence(field),
                timing_ms=elapsed_ms
            )
            return ChatResponse(**response)
        
        # ============================================
        # SEVERITY_ASSESSMENT: Qualitative evaluation
        # ============================================
        if query_type == "SEVERITY_ASSESSMENT":
            # Get weighted history for clinical signals
            weighted_history, scoring_details = fetch_weighted_history(
                patient.patient_id, db, limit=5
            )
            
            # Extract clinical signals from history
            history_signals = {"worsening": 0, "improving": 0, "neutral": 0}
            worsening_keywords = {"worsen", "exacerbation", "deteriorat", "hospital", "acute"}
            improving_keywords = {"improv", "better", "recover", "stable"}
            
            for record in weighted_history:
                text = (record.notes or "").lower()
                for kw in worsening_keywords:
                    if kw in text:
                        history_signals["worsening"] += 1
                        break
                for kw in improving_keywords:
                    if kw in text:
                        history_signals["improving"] += 1
                        break
            
            answer = format_severity_response(patient, history_signals)
            elapsed_ms = round((time.time() - start_time) * 1000, 2)
            print(f"[SEVERITY_ASSESSMENT] Patient {patient.patient_id}: risk={patient.risk_level}, signals={history_signals}")
            
            # Phase 3.5: Visibility logging for vitals/labs (read-only, not in prompt)
            vitals_labs_info = fetch_vitals_labs_for_patient(patient.patient_id, db)
            
            # Confidence: Medium if we have data, Low if refusal
            has_data = patient.risk_level or len(weighted_history) > 0
            response = build_response(
                answer=answer,
                response_type=ResponseType.SEVERITY_ASSESSMENT if has_data else ResponseType.REFUSAL,
                evidence=["patients.risk_level", "patient_history (weighted)"] if has_data else ["no severity metrics available"],
                timing_ms=elapsed_ms
            )
            return ChatResponse(**response)
        
        # ============================================
        # SUMMARY: Use patient summary cache
        # ============================================
        if query_type == "SUMMARY":
            full_history = _fetch_history(patient.patient_id, db, limit=10)
            summary, timing_info = get_or_generate_summary(patient, full_history, db)
            
            if summary and summary.strip():
                elapsed_ms = round((time.time() - start_time) * 1000, 2)
                cache_hit = timing_info["cache_hit"]
                cache_status = "HIT" if cache_hit else "MISS"
                print(f"[SUMMARY {cache_status}] Patient {patient.patient_id}: "
                      f"lookup={timing_info['cache_lookup_ms']}ms, "
                      f"gen={timing_info['generation_ms']}ms, "
                      f"total={elapsed_ms}ms")
                
                response = build_response(
                    answer=summary,
                    response_type=ResponseType.SUMMARY_HIT if cache_hit else ResponseType.SUMMARY_MISS,
                    evidence=get_summary_evidence(cache_hit),
                    timing_ms=elapsed_ms
                )
                return ChatResponse(**response)
        
        # ============================================
        # COMPLEX: Weighted Retrieval + Trend Analysis + RAG + LLM
        # ============================================
        
        # Fetch weighted history (recency + clinical signals)
        full_history, scoring_details = fetch_weighted_history(patient.patient_id, db, limit=5)
        
        # Phase 3.5: Visibility logging for vitals/labs (read-only, not in prompt)
        vitals_labs_info = fetch_vitals_labs_for_patient(patient.patient_id, db)
        
        # Log weighted selection
        if scoring_details:
            print(f"[WEIGHTED] Selected {len(scoring_details)} visits:")
            for detail in scoring_details:
                print(f"  - {detail['visit_date']}: recency={detail['recency_score']}, clinical={detail['clinical_score']}, total={detail['total_score']}")
        
        # Run deterministic trend analysis
        trend_result = analyze_trend(full_history)
        trend_context = format_trend_context(trend_result)
        
        # Build prompt with trend analysis appended
        base_prompt = build_prompt(patient, full_history, intent, request.query)
        
        if not base_prompt or not base_prompt.strip():
            elapsed_ms = round((time.time() - start_time) * 1000, 2)
            response = build_response(
                answer="I do not have enough information to answer that.",
                response_type=ResponseType.REFUSAL,
                evidence=get_refusal_evidence("INSUFFICIENT_DATA"),
                timing_ms=elapsed_ms
            )
            return ChatResponse(**response)
        
        # Append trend analysis to prompt
        enhanced_prompt = f"{base_prompt}\n\n{trend_context}"
        
        print(f"[COMPLEX] Patient: {patient.name}, Trend: {trend_result.get('pattern', 'UNKNOWN')}")
        
        try:
            llm_response = generate(enhanced_prompt)
        except Exception:
            elapsed_ms = round((time.time() - start_time) * 1000, 2)
            response = build_response(
                answer="I am unable to generate a response at the moment.",
                response_type=ResponseType.REFUSAL,
                evidence=get_refusal_evidence("INSUFFICIENT_DATA"),
                timing_ms=elapsed_ms
            )
            return ChatResponse(**response)
        
        if not llm_response or not llm_response.strip():
            elapsed_ms = round((time.time() - start_time) * 1000, 2)
            response = build_response(
                answer="I do not have enough information to answer that.",
                response_type=ResponseType.REFUSAL,
                evidence=get_refusal_evidence("INSUFFICIENT_DATA"),
                timing_ms=elapsed_ms
            )
            return ChatResponse(**response)
        
        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        print(f"[COMPLEX] Intent={intent}, pattern={trend_result.get('pattern')}: {elapsed_ms}ms")
        
        response = build_response(
            answer=llm_response,
            response_type=ResponseType.COMPLEX,
            evidence=get_complex_evidence(),
            timing_ms=elapsed_ms
        )
        return ChatResponse(**response)
    
    finally:
        db.close()
