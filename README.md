# Agentic AI System
### Multi-Step Task Orchestration — Banao Technologies Task 1

---

## What This Is

A hand-rolled agentic pipeline that:
- Accepts a complex user request as plain text
- Decomposes it into discrete, ordered steps
- Routes each step to a specialized agent (Retriever → Analyzer → Writer)
- Streams partial output token-by-token in real time
- Retries failed steps and degrades gracefully without crashing

**No LangChain. No AutoGen. No CrewAI. Every line is explicit.**

---

## Quick Start

```bash
# 1. Clone
git clone <your-repo-url>
cd agentic_ai

# 2. Install test dependencies (only pytest; no AI framework needed)
pip install -r requirements.txt

# 3. Run the demo
python main.py

# 4. Run tests
python -m pytest tests/ -v
```

---

## Demo Output (What You'll See)

**Scenario 1 — Happy Path:**
```
🧠 [Orchestrator] Received task: Research the latest AI trends...
⚙️  Decomposing task into steps...
✅  3 steps identified:
   1. [RETRIEVE] Retrieve relevant information about 'ai trends'
   2. [ANALYZE]  Analyze retrieved data and extract key insights
   3. [WRITE]    Write a structured report on 'ai trends'

▶️  [Step 1] Retrieve relevant information...
   📤 [RetrieverAgent] Output:
   Key AI trends (2024-25): (1) Multimodal models...
   ✅ Done in 0.54s
...
```

**Scenario 2 — Failure Demo:**
```
▶️  [Step 1] Retrieve relevant information...
   ⚠️  Error: Simulated retrieval failure: upstream search API timed out
       (retry 1/2)...
   ⚠️  Error: Simulated retrieval failure: upstream search API timed out
       (retry 2/2)...
   ❌ Step failed after 2 retries
   ↩️  Continuing with partial context...
```

---

## Architecture at a Glance

```
User Request
     │
     ▼
Decomposer ──► [Step(retrieve), Step(analyze), Step(write)]
                        │
                        ▼
              Orchestrator (retry logic, streaming, summary)
                        │
                        ▼
                  Pipeline (manual batching)
                        │
              ┌─────────┼─────────┐
              ▼         ▼         ▼
        Retriever   Analyzer   Writer
          Agent      Agent      Agent
```

Full design: see [`docs/SYSTEM_DESIGN.md`](docs/SYSTEM_DESIGN.md)

Post-mortem: see [`docs/POST_MORTEM.md`](docs/POST_MORTEM.md)

---

## File Structure

```
agentic_ai/
├── main.py                  # Entry point
├── requirements.txt
├── core/
│   ├── orchestrator.py      # Central coordinator + retry logic
│   ├── pipeline.py          # Manual batching
│   └── step.py              # Atomic work unit
├── agents/
│   ├── base_agent.py        # Shared contract (abstract class)
│   ├── retriever_agent.py   # Retrieves information
│   ├── analyzer_agent.py    # Extracts insights
│   └── writer_agent.py      # Writes final report
├── utils/
│   ├── decomposer.py        # Intent → Step list
│   └── logger.py            # Structured logging
├── tests/
│   └── test_system.py       # 20 unit + integration tests
└── docs/
    ├── SYSTEM_DESIGN.md
    └── POST_MORTEM.md
```

---

## Key Design Decisions

| Decision | Reason |
|---|---|
| No agent framework | Keeps every step visible and auditable |
| Async generators for streaming | Native Python; identical pattern to real LLM SDKs |
| Shared context dict | Simple; allows any agent to read any previous result |
| Failure injection via payload | Demonstrates retry logic without external API dependency |
| Mock agents | Zero external dependencies; architecture is the same with real LLMs |
