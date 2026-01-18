# AI Patient Chatbot

**A Safe, Explainable Clinical Decision Support System**

A proof-of-concept chatbot that answers questions about patient health records—without hallucinating, diagnosing, or giving medical advice.

> **Educational/Portfolio Project** — Uses synthetic data only. Not for real clinical use.

---

## What This Project Is

Healthcare AI has a trust problem. Large language models can hallucinate clinical facts, invent diagnoses, and confidently give dangerous advice. This project demonstrates a different approach:

**A chatbot that knows what it knows—and what it doesn't.**

Every answer is grounded in actual patient data. When the system doesn't have enough information, it says so. When asked for medical advice, it refuses. When a question is ambiguous, it asks for clarification.

---

## How It Works

```
User Query → Classification → Retrieval → Guarded Reasoning → Response
                                                ↓
                              [Confidence Level + Evidence Sources]
```

1. **Query Classification** — Each question is categorized (FACTUAL, SUMMARY, COMPLEX, SYNTHETIC, SEVERITY, REFUSAL)
2. **Database-First Retrieval** — Patient data is fetched from structured records, never hallucinated
3. **Guarded Reasoning** — The LLM synthesizes information but cannot invent facts
4. **Confidence + Evidence** — Every response includes a confidence level and explicit data sources

---

## Key Features

### 🎯 Intelligent Query Routing
- **FACTUAL** — Direct database lookups (age, diagnosis, risk level) — no LLM needed
- **SUMMARY** — Patient overviews with caching
- **COMPLEX** — Trend analysis with weighted retrieval
- **SYNTHETIC** — Cross-signal pattern analysis across history, vitals, and labs

### 💬 Pronoun-Aware Conversations
- "Tell me about Emily Smith" → "How old is she?" → "Has her condition changed?"
- Patient context persists across follow-up questions
- Gender-aware pronoun resolution

### 📊 Confidence & Evidence Attribution
Every response includes:
- **Confidence Level**: High / Medium / Low
- **Evidence Sources**: Exact data fields used (e.g., `patients.primary_condition`, `patient_history (weighted)`)

###  Safety Guardrails
- Refuses medical advice requests
- Blocks ambiguous patient references
- Filters forbidden clinical language
- Falls back safely when data is insufficient

---

## What This System Does NOT Do

| It Does NOT | Why |
|----------------|-----|
| Diagnose conditions | It reports what's in the database, not clinical conclusions |
| Recommend treatments | Medical advice requires a licensed professional |
| Infer beyond data | If it's not documented, it's not stated |
| Guess when uncertain | It asks for clarification or refuses |

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI (Python 3.10+) |
| Frontend | React + Vite |
| Database | SQLite |
| LLM | Mistral 7B (GGUF) via llama-cpp-python |
| Execution | Fully local — no external API calls |

---

## Running Locally

### Prerequisites
- Python 3.10+
- Node.js 18+
- Mistral 7B GGUF model file

### Quick Start

```bash
# Backend
cd backend
python -m venv venv
venv\Scripts\activate  # Windows (or: source venv/bin/activate)
pip install -r requirements.txt
python -m etl.etl_pipeline  # Generate synthetic data
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

---

## Example Queries

| Query | Type | Behavior |
|-------|------|----------|
| "What is Emily Smith diagnosed with?" | FACTUAL | Direct DB lookup, High confidence |
| "Tell me about David Williams" | SUMMARY | Cached summary, no LLM if cached |
| "How has her condition changed?" | COMPLEX | Trend analysis with weighted retrieval |
| "Looking at everything together, what patterns stand out?" | SYNTHETIC | Cross-signal analysis, Medium confidence |
| "Tell me about John" | AMBIGUOUS | "Multiple patients found (5 matches)..." |
| "What medicine should he take?" | REFUSAL | "I cannot provide medical advice..." |

---

## Performance

| Query Type | Latency | Notes |
|------------|---------|-------|
| FACTUAL | 4-10ms | Direct DB, no LLM |
| SUMMARY (cached) | 5-15ms | In-memory cache |
| SUMMARY (miss) | 15-40s | LLM generation (CPU) |
| COMPLEX | 8-15s | Weighted retrieval + LLM |
| SYNTHETIC | 20-60s | Cross-signal synthesis (CPU) |

GPU acceleration reduces LLM inference time by 5-10x.

---

## Project Status

| Phase | Status |
|-------|--------|
| Core RAG Pipeline |  Complete |
| Query Classification |  Complete |
| Weighted Retrieval |  Complete |
| Conversation Memory | Complete |
| Vitals & Labs Integration |  Complete |
| Synthetic Reasoning (Phase 5) |  Complete |
| Safety Guardrails | Complete |

**Evaluation:** SAFE TO PROCEED

---

## Disclaimer

This project is for educational and portfolio purposes only. It should not be used for actual medical decision-making. All patient data is synthetic and does not represent real individuals.

---

## License

MIT License
