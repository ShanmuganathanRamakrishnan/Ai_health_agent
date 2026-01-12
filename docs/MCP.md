# MCP (Milestone Control Plan)

## Current Status

| Field | Value |
|-------|-------|
| Current Phase | Phase 5: Synthetic Reasoning |
| Feature in Progress | None (Phase 5 complete) |
| Last Completed Milestone | Phase 5 Validation |

---

## Completed Milestones

### Phase 1: Core RAG Pipeline
**What was added:**
- FastAPI backend with query classification (FACTUAL/SUMMARY/COMPLEX/SEVERITY/REFUSAL)
- SQLite database with Patient and PatientHistory models
- Weighted retrieval with recency + clinical signal scoring
- Patient ID-based identity resolution
- React frontend with clinical decision-support UI

**Validation:** ✅ PASS

---

### Phase 2: Encounter Data Model
**What was added:** EHR-style schema (Encounter, Vital, Lab, Medication), Encounter ETL

**What did NOT change:** Retrieval logic, prompt builder, chat behavior

**Validation:** ✅ PASS

---

### Phase 3: Vitals and Labs ETL
**What was added:** Vitals (3192 total), Labs (2604 total) with LOINC codes

**What did NOT change:** Retrieval logic, prompt builder, chat behavior

**Validation:** ✅ PASS

---

### Phase 4: Vitals/Labs Reasoning for COMPLEX
**What was added:** `_format_vitals_labs_summary()` in prompt_builder.py, pattern descriptions in COMPLEX prompts

**What did NOT change:** SEVERITY, FACTUAL, SUMMARY routing

**Validation:** ✅ PASS

---

### Phase 5: Synthetic Reasoning (ADVANCED)
**What was added:**
- New module: `backend/app/rag/synthetic_reasoner.py`
- Reasoning levels: NONE → DESCRIPTIVE → ANALYTICAL → SYNTHETIC
- Layered activation on top of Phase 4 COMPLEX
- Qualitative activation rules (temporal variation, mixed signals, multi-source)
- Synthesis signal detection (aggregation language, cross-signal phrasing)
- `build_cross_signal_summary()` for temporal alignment and frequency comparisons
- `validate_output_language()` with forbidden word filter
- Mandatory fallback for insufficient data or forbidden words
- Confidence policy: SYNTHETIC = Medium only

**Activation Rules (ALL must pass):**
1. Intent = COMPLEX
2. Patient is valid (not ambiguous)
3. Synthesis signals in query
4. ≥2 data sources with data
5. Temporal variation in history
6. Mixed signals (abnormal + normal)

**Forbidden Words:**
`concerning, severe, worsening, dangerous, requires intervention, critical, alarming, you should, i recommend, treatment, diagnosis, prognosis, urgent, emergency, life-threatening, prescribe, medication should`

**What did NOT change:**
- FACTUAL routing ✅
- SUMMARY caching ✅
- SEVERITY logic ✅
- Confidence calculation rules ✅
- Evidence attribution format ✅
- Pronoun resolution ✅
- Ambiguity handling ✅

**Validation:** ✅ PASS
- FACTUAL: "Emily Smith is diagnosed with Hypertension." [High]
- SEVERITY: "Medium risk level..." [Medium]
- COMPLEX (Phase 4): "Intermittent pattern..." [Medium]
- SYNTHETIC (Phase 5): Cross-signal patterns [Medium]
- AMBIGUOUS: "5 matches" [Low]

---

## Open Risks / Known Limitations

1. **Forbidden word false positives** - May block legitimate neutral language
2. **Synthesis signal detection** - Humans may phrase queries unpredictably
3. **LLM latency** - SYNTHETIC queries take 20-60s on CPU
4. **Evidence attribution** - SYNTHETIC uses fixed evidence array

---

## Next Planned Step

**Phase 6: Enhanced Fallback Messaging** (tentative)
- Improve fallback responses with data availability hints
- Consider query rephrasing suggestions
