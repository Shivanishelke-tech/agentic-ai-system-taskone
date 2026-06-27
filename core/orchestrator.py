"""
orchestrator.py
---------------
Central brain of the Agentic AI System.

Responsibilities:
  1. Accept a complex user request as plain text
  2. Decompose it into an ordered list of Step objects
  3. Route each Step to the correct specialized Agent
  4. Stream partial results to the caller via an async generator
  5. Handle agent failures with retry + graceful degradation
  6. Collect the final aggregated result

Design choice: everything is hand-rolled (no LangChain / CrewAI / AutoGen).
This makes data-flow explicit and auditable.
"""

import asyncio
import time
from typing import AsyncGenerator

from agents.retriever_agent import RetrieverAgent
from agents.analyzer_agent import AnalyzerAgent
from agents.writer_agent import WriterAgent
from core.step import Step, StepStatus
from core.pipeline import Pipeline
from utils.logger import get_logger
from utils.decomposer import decompose_task

logger = get_logger("Orchestrator")


class Orchestrator:
    """
    Coordinates the full lifecycle of a multi-step agentic task.

    Attributes
    ----------
    max_retries : int
        How many times a failing step is retried before being skipped.
    retry_delay : float
        Seconds to wait between retries (simple fixed back-off).
    """

    def __init__(self, max_retries: int = 2, retry_delay: float = 1.0):
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Registry maps step type → agent instance
        # Adding a new agent = adding one line here.
        self._agent_registry = {
            "retrieve": RetrieverAgent(),
            "analyze":  AnalyzerAgent(),
            "write":    WriterAgent(),
        }

        self.pipeline = Pipeline()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(self, user_request: str) -> AsyncGenerator[str, None]:
        """
        Entry point.  Yields streamed status/result lines so the caller
        can display progress in real time.

        Usage
        -----
        async for chunk in orchestrator.run("Research AI trends and write a report"):
            print(chunk, end="", flush=True)
        """
        logger.info(f"Received request: {user_request!r}")
        yield f"\n🧠 [Orchestrator] Received task: {user_request}\n"
        yield "─" * 60 + "\n"

        # ── Step 1: Decompose ──────────────────────────────────────────
        yield "\n⚙️  [Orchestrator] Decomposing task into steps...\n"
        steps = decompose_task(user_request)

        if not steps:
            yield "❌ [Orchestrator] Could not decompose task. Aborting.\n"
            return

        yield f"✅ [Orchestrator] {len(steps)} steps identified:\n"
        for i, s in enumerate(steps, 1):
            yield f"   {i}. [{s.agent_type.upper()}] {s.description}\n"

        yield "─" * 60 + "\n"

        # ── Step 2: Load steps into pipeline ──────────────────────────
        self.pipeline.load(steps)

        # ── Step 3: Execute steps sequentially ────────────────────────
        accumulated_context: dict = {}   # passed forward between steps

        async for chunk in self._execute_pipeline(accumulated_context):
            yield chunk

        # ── Step 4: Summary ───────────────────────────────────────────
        yield "\n" + "─" * 60 + "\n"
        yield self._build_summary(steps)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _execute_pipeline(
        self, context: dict
    ) -> AsyncGenerator[str, None]:
        """Iterate through the pipeline, running each step with retries."""

        async for step in self.pipeline.iter_steps():
            yield f"\n▶️  [Step {step.index}] {step.description}\n"
            yield f"   Agent : {step.agent_type.upper()}\n"

            agent = self._agent_registry.get(step.agent_type)
            if agent is None:
                step.status = StepStatus.SKIPPED
                yield f"   ⚠️  No agent registered for type '{step.agent_type}'. Skipping.\n"
                continue

            # ── Retry loop ────────────────────────────────────────────
            attempt = 0
            while attempt <= self.max_retries:
                try:
                    step.status = StepStatus.RUNNING
                    start = time.perf_counter()

                    # Stream output from the agent
                    async for token in agent.run(step, context):
                        yield token

                    elapsed = time.perf_counter() - start
                    step.status = StepStatus.SUCCESS
                    yield f"\n   ✅ Done in {elapsed:.2f}s\n"
                    break  # success → exit retry loop

                except Exception as exc:
                    attempt += 1
                    logger.warning(
                        f"Step {step.index} attempt {attempt} failed: {exc}"
                    )
                    if attempt <= self.max_retries:
                        yield (
                            f"\n   ⚠️  Error: {exc}  "
                            f"(retry {attempt}/{self.max_retries})...\n"
                        )
                        await asyncio.sleep(self.retry_delay)
                    else:
                        # Exhausted retries → degrade gracefully
                        step.status = StepStatus.FAILED
                        step.error = str(exc)
                        yield (
                            f"\n   ❌ Step failed after {self.max_retries} "
                            f"retries: {exc}\n"
                            f"   ↩️  Continuing with partial context...\n"
                        )

    @staticmethod
    def _build_summary(steps: list[Step]) -> str:
        """Return a human-readable execution summary."""
        total   = len(steps)
        ok      = sum(1 for s in steps if s.status == StepStatus.SUCCESS)
        failed  = sum(1 for s in steps if s.status == StepStatus.FAILED)
        skipped = sum(1 for s in steps if s.status == StepStatus.SKIPPED)

        lines = [
            "📊 [Orchestrator] Execution Summary",
            f"   Total steps : {total}",
            f"   ✅ Success  : {ok}",
            f"   ❌ Failed   : {failed}",
            f"   ⏭️  Skipped  : {skipped}",
        ]

        if failed:
            lines.append("\nFailed steps:")
            for s in steps:
                if s.status == StepStatus.FAILED:
                    lines.append(f"  • Step {s.index}: {s.description}")
                    lines.append(f"    Error: {s.error}")

        lines.append("\n🏁 Pipeline complete.\n")
        return "\n".join(lines)
