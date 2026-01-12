# MCP (Milestone Control Plan)

## Current Status

| Field | Value |
|-------|-------|
| Current Phase | Production-Ready |
| Feature in Progress | None |
| Evaluation | **SAFE TO PROCEED** |

---

## Completed Milestones

### Phase 1: Core RAG Pipeline ✅
**What was added:**
- FastAPI backend with query classification (FACTUAL/SUMMARY/COMPLEX/SEVERITY/REFUSAL)
- SQLite database with Patient and PatientHistory models
- Weighted retrieval with recency + clinical signal scoring
- Patient ID-based identity resolution
- React frontend with clinical decision-support UI

---

### Phase 2: Encounter Data Model ✅
**What was added:**
- EHR-style schema (Encounter, Vital, Lab, Medication)
- Encounter ETL pipeline

**What did NOT change:** Retrieval logic, prompt builder, chat behavior

---

### Phase 3: Vitals and Labs ETL ✅
**What was added:**
- Vitals (3192 total) with clinical thresholds
- Labs (2604 total) with LOINC codes

**What did NOT change:** Retrieval logic, prompt builder, chat behavior

---

### Phase 4: Vitals/Labs Reasoning for COMPLEX ✅
**What was added:**
- `_format_vitals_labs_summary()` in prompt_builder.py
- Pattern descriptions in COMPLEX prompts

**What did NOT change:** SEVERITY, FACTUAL, SUMMARY routing

---

### Phase 5: Advanced Synthetic Reasoning ✅
**What was added:**
- New module: `backend/app/rag/synthetic_reasoner.py`
- Reasoning levels: NONE → DESCRIPTIVE → ANALYTICAL → SYNTHETIC
- Layered activation on top of Phase 4 COMPLEX
- Qualitative activation rules (temporal variation, mixed signals, multi-source)
- Cross-signal summary builder for temporal alignment
- Forbidden word filter with mandatory fallback
- Confidence policy: SYNTHETIC = Medium only

**Activation Rules (ALL must pass):**
1. Intent = COMPLEX
2. Patient is valid (not ambiguous)
3. Synthesis signals in query
4. ≥2 data sources with data
5. Temporal variation in history
6. Mixed signals (abnormal + normal)

---

### Phase 5 Polish: Context Stability & Signal Tuning ✅
**What was added:**
- Context fallback in `reference_resolver.py` for follow-up queries
- Updated `retriever.py` to use reference resolution first
- 4 additional synthesis signal patterns
- Improved forbidden word validation (skip echoed input)
- Phase 5 stress test suite (`tests/phase5_stress_test.py`)

**Validation Results:**
- 19/21 tests pass
- 2 conservative false negatives (acceptable)
- All safety guardrails intact

---

## Safety Guardrails (ACTIVE)

| Guardrail | Status |
|-----------|--------|
| Forbidden word filter | ✅ Active |
| SYNTHETIC confidence cap (Medium) | ✅ Enforced |
| Fallback response for insufficient data | ✅ Active |
| Medical advice refusal | ✅ Active |
| Ambiguity clarification | ✅ Active |
| Gender-aware pronoun resolution | ✅ Active |

---

## What This System Does NOT Do

| Behavior | Guardrail |
|----------|-----------|
| Diagnose conditions | Reports only what's in DB |
| Recommend treatments | Refuses with safe message |
| Infer beyond data | Falls back if insufficient |
| Guess when uncertain | Asks for clarification |

---

## Open Risks / Known Limitations

1. **LLM latency on CPU** — SYNTHETIC queries take 20-60s without GPU
2. **Conservative false negatives** — Some valid synthetic queries may not activate
3. **Single-session memory** — Context expires after 30 minutes

---

## Evaluation

| Metric | Result |
|--------|--------|
| FACTUAL accuracy | ✅ 100% (direct DB) |
| SUMMARY behavior | ✅ Stable |
| COMPLEX trend analysis | ✅ Working |
| SYNTHETIC activation | ✅ 90%+ (acceptable) |
| Safety refusals | ✅ Enforced |
| Adversarial handling | ✅ Blocked |

**Final Status: SAFE TO PROCEED**
