# MCP (Milestone Control Plan)

## Current Status

| Field | Value |
|-------|-------|
| Current Phase | Phase 3.5: Vitals & Labs Visibility |
| Feature in Progress | None (Phase 3.5 complete) |
| Last Completed Milestone | Phase 3.5 Validation |

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

**What did NOT change:** N/A (initial implementation)

**Validation:** ✅ PASS

---

### Phase 2: Encounter Data Model
**What was added:**
- EHR-style schema: Encounter, Vital, Lab, Medication tables
- Encounter ETL: 5-15 encounters per patient, 1616 total records
- Realistic data: dates, providers, specialties, dispositions

**What did NOT change:**
- Retrieval logic
- Prompt builder
- Chat behavior

**Validation:** ✅ PASS (7-category validation)

---

### Phase 3: Vitals and Labs ETL
**What was added:**
- Vitals generation: 1-3 per encounter, 3192 total (48% abnormal)
- Labs generation: 0-4 per encounter, 2604 total (20% abnormal)
- 18 lab test types with LOINC codes and reference ranges
- Realistic clinical values with noise and abnormal flags

**What did NOT change:**
- Retrieval logic
- Prompt builder
- Chat behavior
- Query classification

**Validation:** ✅ PASS

---

### Phase 3.5: Vitals & Labs Visibility
**What was added:**
- `fetch_vitals_labs_for_patient()` function in relevance_scorer.py
- Visibility calls in SEVERITY_ASSESSMENT and COMPLEX handlers
- Structured Phase 3.5 logging with encounter/vitals/labs counts

**What did NOT change:**
- LLM prompts (vitals/labs excluded)
- Chat responses (identical)
- Confidence levels
- Evidence attribution

**Validation:** ✅ PASS

---

## Open Risks / Known Limitations

1. **Vitals/labs not in prompts** - Data retrieved but not used in reasoning yet
2. **Summary cache invalidation** - Cache persists after ETL re-runs
3. **Large LLM context** - COMPLEX/SUMMARY queries with dense histories take 15-40s
4. **Weight/height not patient-consistent** - Randomly generated per reading

---

## Next Planned Step

**Phase 4: Vitals/Labs in Prompts** (tentative)
- Include structured vitals/labs summaries in SEVERITY prompts
- Preserve current behavior for FACTUAL/SUMMARY
- Carefully scope to avoid prompt size explosion
