# MCP (Milestone Control Plan)

## Current Status

| Field | Value |
|-------|-------|
| Current Phase | Phase 4: Vitals/Labs Reasoning for COMPLEX |
| Feature in Progress | None (Phase 4 complete) |
| Last Completed Milestone | Phase 4 Validation |

---

## Completed Milestones

### Phase 1: Core RAG Pipeline
**What was added:**
- FastAPI backend with query classification (FACTUAL/SUMMARY/COMPLEX/SEVERITY/REFUSAL)
- SQLite database with Patient and PatientHistory models
- Weighted retrieval with recency + clinical signal scoring
- Short-term conversation memory (pronouns, follow-ups)
- Patient ID-based identity resolution
- Confidence + evidence attribution
- Safe refusals for medical advice
- React frontend with clinical decision-support UI

**Validation:** ✅ PASS

---

### Phase 2: Encounter Data Model
**What was added:**
- EHR-style schema: Encounter, Vital, Lab, Medication tables
- Encounter ETL: 5-15 encounters per patient, 1616 total records

**What did NOT change:** Retrieval logic, prompt builder, chat behavior

**Validation:** ✅ PASS

---

### Phase 3: Vitals and Labs ETL
**What was added:**
- Vitals generation: 1-3 per encounter, 3192 total (48% abnormal)
- Labs generation: 0-4 per encounter, 2604 total (20% abnormal)
- 18 lab test types with LOINC codes and reference ranges

**What did NOT change:** Retrieval logic, prompt builder, chat behavior

**Validation:** ✅ PASS

---

### Phase 3.5: Vitals & Labs Visibility
**What was added:**
- `fetch_vitals_labs_for_patient()` function for read-only retrieval
- Visibility logging in SEVERITY_ASSESSMENT and COMPLEX handlers

**What did NOT change:** LLM prompts, chat responses, confidence levels

**Validation:** ✅ PASS

---

### Phase 4: Vitals/Labs Reasoning for COMPLEX
**What was added:**
- `_format_vitals_labs_summary()` in prompt_builder.py
- Vitals/Labs summary section in COMPLEX prompts only
- Pattern-based descriptions (no raw values, no diagnoses)
- Language constraints: neutral, descriptive, no medical advice

**What did NOT change:**
- SEVERITY logic (unchanged)
- FACTUAL routing (unchanged)
- SUMMARY caching (unchanged)
- Confidence calculation (unchanged)
- Evidence attribution (unchanged)

**Before/After:**
- Before: "Her condition has shown an intermittent pattern..."
- After: "The patient's condition has shown an intermittent pattern with both improvements and exacerbations..." (informed by vitals/labs)

**Validation:** ✅ PASS

---

## Open Risks / Known Limitations

1. **SEVERITY still excludes vitals/labs** - By design for conservative reasoning
2. **Summary cache invalidation** - Cache persists after ETL re-runs
3. **LLM latency** - COMPLEX queries take 15-40s on CPU

---

## Next Planned Step

**Phase 5: Enhanced Evidence Attribution** (tentative)
- Include vitals/labs counts in evidence array for COMPLEX
- Add trend direction to evidence metadata
