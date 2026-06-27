"""
agents/retriever_agent.py
-------------------------
Specialized agent responsible for RETRIEVING information.

In a production system this agent would:
  - Call a search API (SerpAPI, Brave, Tavily)
  - Query a vector database (Pinecone, Weaviate, Chroma)
  - Fetch web pages and parse HTML

Here we use realistic mock data keyed to common research topics so the
demo is meaningful without an API key.

Failure injection:
  If the payload contains  {"force_fail": true}  the agent deliberately
  raises an exception so the Orchestrator's retry + graceful degradation
  logic can be demonstrated.
"""

import asyncio
import random

from agents.base_agent import BaseAgent
from core.step import Step


# ---------------------------------------------------------------------------
# Mock knowledge base
# ---------------------------------------------------------------------------

MOCK_DATA: dict[str, str] = {
    "ai trends": (
        "Key AI trends (2024-25): (1) Multimodal models (GPT-4o, Gemini) are "
        "becoming the default interface. (2) Agentic systems that decompose "
        "tasks are replacing single-prompt pipelines. (3) On-device inference "
        "(Apple M-series, Qualcomm NPU) is reducing cloud dependence. "
        "(4) Retrieval-Augmented Generation (RAG) is the dominant pattern for "
        "grounding LLMs in fresh data. (5) AI safety and alignment research is "
        "growing 3× faster than capability research by paper count."
    ),
    "climate change": (
        "Climate data (2024): Global average temperature is +1.35 °C above "
        "pre-industrial baseline. Arctic sea ice hit its second-lowest extent "
        "on record. Renewable energy now supplies 30 % of global electricity. "
        "The IEA projects net-zero by 2050 requires tripling renewable "
        "capacity by 2030."
    ),
    "default": (
        "Retrieved 5 relevant documents on the topic. Key themes: "
        "(1) Recent developments show accelerating progress. "
        "(2) Expert consensus highlights three main challenges. "
        "(3) Case studies from leading organizations provide actionable "
        "insights. (4) Statistical trends suggest a compound annual growth "
        "rate of ~18 %. (5) Regulatory landscape is evolving rapidly."
    ),
}


class RetrieverAgent(BaseAgent):
    """
    Retrieves relevant information for a given query.

    Simulates network latency with asyncio.sleep so the async pipeline
    behaves realistically.
    """

    def __init__(self):
        super().__init__(name="RetrieverAgent", stream_delay=0.012)

    async def _execute(self, step: Step, context: dict) -> str:
        # ── Failure injection ─────────────────────────────────────────
        if step.payload.get("force_fail"):
            raise ConnectionError(
                "Simulated retrieval failure: upstream search API timed out"
            )

        # ── Simulate network I/O ──────────────────────────────────────
        latency = random.uniform(0.3, 0.8)   # 300–800 ms realistic fetch
        await asyncio.sleep(latency)

        # ── Pick mock result ──────────────────────────────────────────
        query = step.payload.get("query", "").lower()
        for keyword, data in MOCK_DATA.items():
            if keyword in query:
                return data
        return MOCK_DATA["default"]
