"""
agents/writer_agent.py
----------------------
Specialized agent responsible for WRITING the final deliverable.

Consumes outputs from previous steps (stored in `context`) and
assembles them into a polished, formatted report.

In production this would call an LLM with a writing prompt and the
accumulated context.  Here we use a template that injects real outputs
from the Retriever and Analyzer so the report is always grounded in the
actual pipeline run.

Failure injection:
  payload {"force_fail": true} raises a RuntimeError to demonstrate
  what happens when the final step fails.
"""

import asyncio
import random
from datetime import datetime

from agents.base_agent import BaseAgent
from core.step import Step


class WriterAgent(BaseAgent):
    """
    Assembles a structured report from accumulated pipeline context.
    """

    def __init__(self):
        super().__init__(name="WriterAgent", stream_delay=0.008)

    async def _execute(self, step: Step, context: dict) -> str:
        # ── Failure injection ─────────────────────────────────────────
        if step.payload.get("force_fail"):
            raise RuntimeError(
                "Simulated writer failure: conflicting instructions in context "
                "— cannot determine correct tone and structure"
            )

        # ── Gather upstream results ───────────────────────────────────
        raw_data = context.get("step_1_result", "No raw data available.")
        analysis = context.get("step_2_result", "No analysis available.")
        topic    = step.payload.get("topic", "the requested topic")

        # ── Simulate LLM writing time ─────────────────────────────────
        await asyncio.sleep(random.uniform(0.5, 1.0))

        # ── Build report ──────────────────────────────────────────────
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        report = self._format_report(topic, raw_data, analysis, timestamp)
        return report

    # ------------------------------------------------------------------
    # Template
    # ------------------------------------------------------------------

    @staticmethod
    def _format_report(
        topic: str, raw_data: str, analysis: str, timestamp: str
    ) -> str:
        return f"""
╔══════════════════════════════════════════════════════════╗
║              AGENTIC AI — FINAL REPORT                   ║
╚══════════════════════════════════════════════════════════╝
Topic     : {topic}
Generated : {timestamp}
Pipeline  : Retriever → Analyzer → Writer

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 1 — RAW RETRIEVED DATA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{raw_data}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 2 — ANALYTICAL INSIGHTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{analysis}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 3 — EXECUTIVE SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Based on retrieved data and structured analysis, this report
covers {topic}. The pipeline successfully retrieved relevant
information, extracted key themes and sentiment, and
synthesized the findings into this structured deliverable.

Confidence level : HIGH (all upstream steps succeeded)
Recommended action: Review findings and validate with domain expert.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
END OF REPORT
"""
