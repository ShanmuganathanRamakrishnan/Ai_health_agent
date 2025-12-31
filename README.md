# AI Patient Chatbot

**Trust-Focused Clinical Decision Support (Prototype)**

A local-first, explainable question-answering system for patient health records. Built to demonstrate how AI can assist healthcare workflows without sacrificing reliability, safety, or transparency.

> This is a portfolio/educational project using synthetic data only. It is not intended for real clinical use.

---

## Project Overview

This system answers questions about patient health records using a combination of direct database lookups and local LLM reasoning. The key principle is **database-first**: factual queries are answered directly from structured data, and the LLM is only invoked when summarization or reasoning is required.

**Design priorities:**
- Reliability over creativity
- Transparency over brevity
- Refusal over guessing
- Local execution (no external API calls)

---

## Key Features

- **Query classification**: Routes queries to optimal handlers (FACTUAL, SUMMARY, COMPLEX, SEVERITY, REFUSAL)
- **Database-first answers**: Simple lookups bypass the LLM entirely, eliminating hallucination risk
- **Weighted retrieval**: Trend queries use recency + clinical signal scoring to prioritize relevant history
- **Conversation memory**: Short-term context for pronouns and follow-ups (30-minute expiry)
- **Patient ID anchoring**: Once identified, a patient is tracked by ID—not name—to prevent ambiguity
- **Confidence + evidence**: Every response includes a confidence level (High/Medium/Low) and explicit data sources
- **Safe refusals**: Medical advice requests, ambiguous queries, and gender mismatches are handled gracefully
- **Fully local**: Runs entirely offline using SQLite + local Mistral 7B (GGUF)

---

## Architecture Overview

```
┌─────────────────┐      ┌──────────────────────────────────────────┐
│  React Frontend │ ←──→ │             FastAPI Backend              │
│  (port 3000)    │      │                                          │
└─────────────────┘      │  ┌──────────────────────────────────┐   │
                         │  │  Query Classifier                 │   │
                         │  │  (FACTUAL / SUMMARY / COMPLEX /  │   │
                         │  │   SEVERITY / REFUSAL)            │   │
                         │  └──────────────────────────────────┘   │
                         │                  │                       │
                         │     ┌────────────┴────────────┐         │
                         │     ▼                         ▼         │
                         │  ┌─────────┐           ┌───────────┐    │
                         │  │ SQLite  │           │ Mistral   │    │
                         │  │ (source │           │ 7B (GGUF) │    │
                         │  │  of     │           │ via       │    │
                         │  │  truth) │           │ llama.cpp │    │
                         │  └─────────┘           └───────────┘    │
                         └──────────────────────────────────────────┘
```

**When the LLM is used:**
- Generating patient summaries (cache miss)
- Analyzing trends over time (COMPLEX queries)
- Answering questions requiring reasoning

**When the LLM is NOT used:**
- Age, diagnosis, gender, risk level (direct DB read)
- Cached summaries
- Refusals and clarifications

---

## How the System Thinks

This system takes a different approach than typical chatbots:

1. **The database is the source of truth.** Patient demographics, conditions, and risk levels come directly from structured data. The LLM never invents this information.

2. **The LLM is a reasoning tool, not a knowledge source.** It is only used to synthesize information that already exists in the database—never to generate clinical facts.

3. **Every answer is grounded.** Responses include evidence attribution (e.g., "patients.primary_condition" or "patient_history (weighted)") so users can trace where information came from.

4. **Errors are handled conservatively.** If a query is ambiguous, the system asks for clarification. If a pronoun doesn't match, it refuses rather than guessing. If medical advice is requested, it declines.

This design reduces hallucination risk and makes the system more appropriate for healthcare-adjacent use cases where trust matters.

---

## Running the Project Locally

### Prerequisites
- Python 3.10+
- Node.js 18+
- A Mistral 7B GGUF model file (e.g., `mistral-7b-instruct-v0.2.Q4_K_M.gguf`)

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn app.main:app --reload
```

### Database Setup

```bash
cd backend
python -m etl.etl_pipeline
```

This generates ~160 synthetic patients with multi-year visit histories.

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 in your browser.

### GPU Acceleration (Optional)

If you have an NVIDIA GPU with CUDA, llama-cpp-python can use GPU acceleration. This significantly improves inference speed for LLM-based queries.

---

## Example Queries

| Query | Type | Response |
|-------|------|----------|
| "What is Emily Smith diagnosed with?" | FACTUAL | "Emily Smith is diagnosed with Hypertension." |
| "Tell me about David Williams" | SUMMARY | 3-4 sentence summary of patient history |
| "How old is she?" | PRONOUN | Resolves to last mentioned patient |
| "Has his condition gotten worse?" | COMPLEX | Trend analysis using weighted history |
| "Tell me about John" | AMBIGUOUS | "Multiple patients found (5 matches)..." |
| "What medicine should he take?" | REFUSAL | "I cannot provide medical advice..." |

---

## Safety and Limitations

This project is a prototype with intentional constraints:

- **Synthetic data only**: All patient records are generated, not real.
- **No medical advice**: The system explicitly refuses treatment or medication questions.
- **No diagnosis**: It reports what is in the database, not clinical conclusions.
- **Conservative by design**: The system asks for clarification rather than guessing.
- **Single-session memory**: Context expires after 30 minutes and does not persist.

These limitations are features, not bugs. They reflect the principle that clinical decision support should be reliable and transparent, even at the cost of flexibility.

---

## Performance Notes

| Query Type | Typical Latency | Notes |
|------------|-----------------|-------|
| FACTUAL | 4-10ms | Direct DB read, no LLM |
| SUMMARY (cached) | 5-15ms | In-memory cache hit |
| SUMMARY (miss) | 15-40s | LLM generation (CPU) |
| COMPLEX | 8-15s | Weighted retrieval + LLM |

GPU acceleration reduces LLM inference time by 5-10x.

---

## Future Improvements

These are potential enhancements, not current features:

- UI-assisted patient disambiguation (clickable suggestions)
- Semantic name matching for typos and nicknames
- Larger synthetic datasets for stress testing
- Persistent storage for conversation memory (with explicit consent)
- Embedding-based retrieval for unstructured notes

---

## Disclaimer

This project is for educational and portfolio purposes only. It should not be used for actual medical decision-making. All patient data is synthetic and does not represent real individuals.

---

## License

MIT License. See LICENSE file for details.
