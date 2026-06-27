# System Design Document
## Agentic AI System for Multi-Step Tasks

---

## 1. Overview

This system accepts a complex user request as plain text, decomposes it into
an ordered sequence of discrete Steps, routes each Step to a specialized Agent,
streams partial output to the user in real time, and handles failures gracefully
with configurable retry logic and graceful degradation.

---

## 2. Architecture

```
User Request (plain text)
        │
        ▼
┌───────────────────┐
│   Decomposer      │  Parses intent → produces ordered list of Steps
└────────┬──────────┘
         │ list[Step]
         ▼
┌───────────────────┐
│   Orchestrator    │  Central coordinator; owns retry logic & summary
└────────┬──────────┘
         │ feeds steps into
         ▼
┌───────────────────┐       ┌────────────────────────────────────────┐
│     Pipeline      │──────▶│  Agent Registry                        │
│  (manual batching)│       │  "retrieve" → RetrieverAgent           │
└───────────────────┘       │  "analyze"  → AnalyzerAgent            │
                            │  "write"    → WriterAgent              │
                            └────────────────────────────────────────┘
         │
         │  async generator  (token-by-token streaming)
         ▼
   Terminal / Client
```

---

## 3. Component Descriptions

### 3.1 Decomposer (`utils/decomposer.py`)

**Responsibility:** Convert free-text intent into an ordered list of `Step` objects.

**How it works:**
- Keyword matching against intent categories (retrieve / analyze / write).
- Topic extraction via regex (words after prepositions like "about", "on").
- Always appends a Write step so every pipeline produces a deliverable.

**Production upgrade path:** Replace keyword matching with a single LLM call
using structured output (JSON mode). The `Step` schema stays unchanged.

---

### 3.2 Step (`core/step.py`)

**Responsibility:** The atomic unit of work.

| Field        | Type        | Set by         | Purpose                              |
|--------------|-------------|----------------|--------------------------------------|
| `index`      | int         | Decomposer     | 1-based order in pipeline            |
| `agent_type` | str         | Decomposer     | Key into agent registry              |
| `description`| str         | Decomposer     | Human-readable label for streaming   |
| `payload`    | dict        | Decomposer     | Agent-specific input data            |
| `status`     | StepStatus  | Orchestrator   | Lifecycle state                      |
| `result`     | Any         | Agent          | Output stored for downstream steps   |
| `error`      | str \| None | Orchestrator   | Set when retries are exhausted       |

---

### 3.3 Pipeline (`core/pipeline.py`)

**Responsibility:** Manage step ordering and manual batching.

**Batching logic (explicit, no black-box abstraction):**
```python
def _make_batches(self) -> list[list[Step]]:
    batches = []
    for i in range(0, len(self._steps), self.batch_size):
        batches.append(self._steps[i : i + self.batch_size])
    return batches
```
Steps are sliced into fixed-size windows. Currently processed sequentially
(safe for dependent steps). Independent steps within a batch could be
parallelised with `asyncio.gather()` in a future version.

---

### 3.4 Orchestrator (`core/orchestrator.py`)

**Responsibility:** Execute the pipeline, stream output, handle failures.

**Retry logic:**
```
For each step:
  attempt = 0
  while attempt <= max_retries:
    try:
      run agent → stream output → break
    except Exception:
      attempt += 1
      if attempt <= max_retries: sleep(retry_delay) → retry
      else: mark step FAILED, set step.error, continue pipeline
```

**Key design decision:** Failed steps do not abort the pipeline. The Writer
agent can still produce a partial report using whatever context was
successfully collected from earlier steps.

---

### 3.5 Agents (`agents/`)

All agents inherit from `BaseAgent` which enforces a single contract:

```python
async def run(step: Step, context: dict) -> AsyncGenerator[str, None]
```

Each agent:
1. Receives the current `Step` and a shared `context` dict.
2. Calls `_execute()` (the concrete implementation).
3. Stores its result on `step.result` and in `context[f"step_{N}_result"]`.
4. Streams output character-by-character via `_stream_text()`.

| Agent           | Input                     | Output                        |
|-----------------|---------------------------|-------------------------------|
| RetrieverAgent  | `payload["query"]`        | Raw information string        |
| AnalyzerAgent   | Previous step result      | Structured insight report     |
| WriterAgent     | All previous step results | Formatted final report        |

---

## 4. Data Flow Diagram

```
Step 1 (Retrieve)
  Input : user query string
  Output: raw text → stored in context["step_1_result"]
        │
        ▼
Step 2 (Analyze)
  Input : context["step_1_result"]
  Output: insight report → stored in context["step_2_result"]
        │
        ▼
Step 3 (Write)
  Input : context["step_1_result"] + context["step_2_result"]
  Output: formatted report streamed to user
```

---

## 5. Streaming Architecture

Streaming is implemented as a chain of async generators:

```
agent._stream_text() → agent.run() → orchestrator._execute_pipeline() → orchestrator.run() → caller
```

Each generator yields `str` chunks. The caller (e.g. `main.py`) receives
tokens and can `print()` them immediately with `flush=True` — identical to
how OpenAI / Anthropic streaming SDKs work.

---

## 6. Failure Handling

| Failure Type              | Behaviour                                         |
|---------------------------|---------------------------------------------------|
| Agent raises exception    | Retry up to `max_retries` times with `retry_delay`|
| Retries exhausted         | Step marked `FAILED`, error logged, pipeline continues |
| Unknown agent type        | Step marked `SKIPPED`, pipeline continues         |
| Empty decomposition       | Pipeline aborts immediately with error message    |

---

## 7. Project Structure

```
agentic_ai/
├── main.py                    # Entry point; runs happy path + failure demo
├── requirements.txt
├── core/
│   ├── orchestrator.py        # Central coordinator
│   ├── pipeline.py            # Manual batching + step iteration
│   └── step.py                # Atomic work unit (dataclass)
├── agents/
│   ├── base_agent.py          # Abstract contract all agents implement
│   ├── retriever_agent.py     # Retrieves information
│   ├── analyzer_agent.py      # Analyzes and extracts insights
│   └── writer_agent.py        # Produces final deliverable
├── utils/
│   ├── decomposer.py          # Parses user request → Step list
│   └── logger.py              # Structured logging
└── tests/
    └── test_system.py         # 20 unit + integration tests
```

---

## 8. Running the System

```bash
# Clone and navigate
git clone <your-repo-url>
cd agentic_ai

# Install test dependencies (no other external packages needed)
pip install -r requirements.txt

# Run the demo (happy path + failure scenario)
python main.py

# Run all tests
python -m pytest tests/ -v
```
