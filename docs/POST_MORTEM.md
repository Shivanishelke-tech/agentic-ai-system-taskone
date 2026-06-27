# Post-Mortem Document
## Agentic AI System — Task 1

---

## 1. Scaling Issue I Encountered (or Anticipate)

### Issue: Sequential Step Execution Doesn't Scale for Independent Steps

The current pipeline processes every step one after another, even when
steps don't depend on each other's outputs. For a 3-step pipeline this
is fine. But consider a real-world task like:

> "Research AI, climate change, and quantum computing — then write a
> comparative report."

This decomposes into **three independent retrieve steps** followed by
one write step. In the current design those three retrieval calls run
sequentially, even though they could all run simultaneously.

**At scale:** If each retrieval takes ~800 ms and you have 10 independent
topics, the pipeline takes ~8 seconds where it could take ~0.8 seconds.

**Fix I would apply:** Add a `parallel` flag to the Pipeline. When steps
within a batch have no data dependency (no step reads from a previous
step's context key), dispatch them with `asyncio.gather()`. The batching
structure I built is already in place — this would be a ~20 line change
inside `pipeline.iter_steps()`.

---

## 2. Design Change I Would Make in Hindsight

### Change: Separate "Context" from "Step Results"

Currently, the shared `context` dict stores step results as flat keys:
```python
context["step_1_result"] = "..."
context["step_2_result"] = "..."
```

This works fine for a linear 3-step pipeline. But it breaks down when:
- Steps are reordered dynamically.
- Multiple retrieval steps produce results that should be merged, not
  overwritten.
- A failure on step 2 means step 3 silently receives a missing key.

**What I would do instead:** Use a typed `PipelineContext` dataclass with
explicit named slots:

```python
@dataclass
class PipelineContext:
    retrieved_data: list[str] = field(default_factory=list)
    analysis:       str | None = None
    final_report:   str | None = None
```

This makes dependencies explicit, enables type checking, and prevents
the silent "key not found" failure mode.

---

## 3. Trade-Off 1: Mock Agents vs. Real LLM Calls

**Decision:** Use deterministic mock agents instead of calling a real
LLM API.

**Why I made this choice:**
- Zero external dependencies → system runs offline, in CI, in any environment.
- Tests are deterministic and fast (no flaky network calls).
- The architectural patterns (async generators, retry logic, context
  passing, streaming) are fully demonstrated regardless of whether the
  agent calls GPT-4 or returns a string from a dict.

**What I traded away:**
- The output quality is limited to hand-crafted mock data.
- A real system would need API key management, rate limit handling,
  token budget tracking, and LLM error types (RateLimitError, etc.).

**Reasoning:** For an evaluation focused on system design and architecture
understanding, demonstrating the patterns cleanly matters more than
wrapping a real API. The upgrade path is explicit: replace `_execute()`
in each agent with an API call. The rest of the system doesn't change.

---

## 4. Trade-Off 2: Keyword-Based Decomposer vs. LLM-Based Decomposer

**Decision:** Parse user requests with regex and keyword matching rather
than an LLM call.

**Why I made this choice:**
- The decomposer's job is to produce a `list[Step]`. That contract is
  independent of how the parsing is done.
- A keyword-based decomposer is transparent — you can read the if-else
  logic and understand exactly what it will produce for any input.
- No latency, no cost, no API dependency for what is essentially an
  intent classification problem.

**What I traded away:**
- Brittleness on unexpected phrasing. "Can you dig up some info on AI
  and then put together a write-up?" would miss "retrieve" because it
  doesn't use any of the exact keywords.
- Cannot handle multi-topic decomposition (e.g. splitting "research AI
  AND climate change" into two separate retrieve steps).

**Reasoning:** The trade-off is justified for a demo. In production I
would replace keyword matching with a structured LLM call that returns
JSON — a single function swap with no architectural changes needed
elsewhere.

---

## Summary Table

| Area                    | Decision Made              | What Was Traded            |
|-------------------------|----------------------------|-----------------------------|
| Scaling                 | Sequential steps (safe)    | Parallelism for independent steps |
| Context management      | Flat dict with string keys | Type safety, explicit deps  |
| Agent implementation    | Mock agents (offline)      | Real LLM output quality     |
| Task decomposition      | Keyword matching           | Flexibility on varied phrasing |
