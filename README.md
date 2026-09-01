# RECOVERX AI
## Autonomous Revenue Recovery Intelligence System
### Razorpay AI Buildathon — Track 03: AI Revenue Recovery

---

> ⚠️ **Simulation Disclaimer**: All data, transactions, customers, and metrics in this system are **completely synthetic**. No real payments are processed. All outcomes are simulated using a probability model. This system is built for demonstration of the Agentic AI architecture.

---

## 🏗️ Architecture

RECOVERX AI is a **10-agent LangGraph pipeline** — not a chatbot, not a single LLM call.

```
Revenue Event
      │
      ▼
[1] Revenue Sentinel         ← Classifies recoverability, halts if DO_NOT_CONTACT
      │
      ▼
[2] Root Cause Diagnosis     ← Evidence-based failure analysis (7 root causes)
      │
      ▼
[3] Customer Context Intel   ← Fatigue score, preferred channel, behaviour profile
      │
      ▼
[4] Recovery Opportunity     ← ERV = Amount × Probability − Cost − Friction
      │
      ▼
[5] Strategy Planner         ← Generates 3-5 ranked candidate strategies
      │
      ▼
[6] Recovery Digital Twin    ← Simulates each strategy, ranks by Net Expected Value
      │
      ▼
[7] Policy Guardian          ← Enforces 7 configurable rules, can BLOCK execution
      │
      ▼
[8] Recovery Execution       ← SOLE tool-caller: payment/comms/CRM tools
      │
      ▼
[9] Outcome Monitor          ← Records result, calculates recovered amount
      │
      ▼
[10] Learning & Optimization ← Updates StrategyEffectiveness table for future runs
```

Each agent has:
- LLM reasoning (with Gemini/OpenAI) OR deterministic fallback
- Pydantic-validated outputs
- Immutable audit log entry
- Event bus publication for live feed

---

## 🚀 Quick Start (No API key needed)

### Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env       # already done — defaults to mock LLM + SQLite
uvicorn app.main:app --reload --port 8000
```

The backend auto-seeds **200 synthetic customers + 1,000 revenue events** on first run.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**

### With Gemini API key

Edit `backend/.env`:
```
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_key_here
```

---

## 📊 Features

| Feature | Description |
|---------|-------------|
| **10-Agent Pipeline** | Specialized agents with clear separation of concerns |
| **LangGraph Orchestration** | Conditional routing — early termination on policy violations |
| **Recovery Digital Twin** | Counterfactual simulation of each strategy before execution |
| **Policy Guardian** | 7 configurable rules — max retries, contact hours, cost ratio, fatigue gate |
| **Baseline Comparison** | Every metric compared against naive immediate retry + generic email |
| **Live WebSocket Feed** | Real-time agent activity stream |
| **Human Review Queue** | Policy Guardian escalates edge cases for human approval |
| **Immutable Audit Trail** | Every agent decision logged with confidence, reasoning, and duration |
| **Mock LLM Mode** | Full pipeline runs deterministically without any API key |
| **Provider Abstraction** | Swap Gemini → OpenAI → Mock via single env var |

---

## 🗂️ Project Structure

```
backend/
  app/
    agents/         # 10 specialized agents
    orchestrator/   # LangGraph state graph + runner
    llm/            # GeminiProvider, OpenAIProvider, MockProvider
    eventbus/       # InMemoryEventBus, RedisEventBus (optional)
    tools/          # payment_tools, comms_tools, crm_tools (simulated)
    simulation/     # engine, generator, baseline comparison
    models/         # SQLAlchemy ORM models
    schemas/        # Pydantic contracts
    api/            # FastAPI routes
    config.py       # Pydantic-settings
    database.py     # SQLite/PostgreSQL async engine
    main.py         # FastAPI app

frontend/
  src/
    pages/          # Dashboard, LiveFeed, CaseExplorer, AgentObservatory,
                    # SimulationLab, HumanReview, AuditExplorer
    components/     # Layout, Sidebar
    store/          # Zustand global state
    hooks/          # useWebSocket
    lib/            # Typed API client
    types/          # TypeScript types
```

---

## ⚙️ Configuration

All policy thresholds are configurable via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `mock` | `mock` / `gemini` / `openai` |
| `MAX_CONTACT_ATTEMPTS` | `5` | Max contacts before DO_NOT_CONTACT |
| `MAX_RECOVERY_COST_RATIO` | `0.05` | Max recovery cost as % of amount |
| `HUMAN_APPROVAL_THRESHOLD` | `100000` | INR amount requiring human approval |
| `HIGH_VALUE_THRESHOLD` | `50000` | INR for elevated monitoring |
| `MIN_CONFIDENCE_FOR_AUTO` | `0.60` | Below this → escalate to human |
| `CONTACT_HOURS_START` | `9` | IST hour — no contact before this |
| `CONTACT_HOURS_END` | `21` | IST hour — no contact after this |
| `EVENT_BUS` | `memory` | `memory` / `redis` |

---

## 🧪 Testing & Verification

The test suite provides isolated deterministic verification with 0 quota overhead alongside explicit live Gemini testing:

### 1. Deterministic Architecture Tests (0 Quota Usage)
```bash
cd backend
python test_suite.py
```
- Tests all 7 deterministic agents, financial math ($ERV$, $NEV$), 8 policy stopping rules, counterfactual Digital Twin rankings, and 10-Agent LangGraph workflow execution.
- Guaranteed **0 Gemini API requests**.

### 2. Live Gemini Verification Test
```bash
cd backend
python test_suite.py --live-gemini
```
- **Part B.1 runs FIRST**: Executes an isolated Gemini API request with structured JSON validation using `google.genai`.
- Clearly reports `[PASS - LIVE GEMINI]`, `[SKIPPED - LIVE GEMINI]`, or `[FAIL - LIVE GEMINI]`.
- Then executes the full deterministic suite with complete isolation.

---

*Built for Razorpay AI Buildathon 2026 — Track 03: AI Revenue Recovery*