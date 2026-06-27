"""
agents/base_agent.py
--------------------
Abstract base class every specialized agent must inherit from.

Why a base class?
-----------------
Enforces a single contract: every agent must implement `run()` as an
async generator.  The Orchestrator only calls `agent.run(step, context)`
— it doesn't care which concrete class it's talking to.

This is the Strategy pattern: swap agents without touching the
Orchestrator.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import AsyncGenerator

from core.step import Step
from utils.logger import get_logger


class BaseAgent(ABC):
    """
    Contract all agents must satisfy.

    Subclasses override `_execute()` which is called by the public
    `run()` method.  `run()` handles:
      - Token streaming simulation (character-by-character for demo
        realness without a real LLM)
      - Writing the result back onto the Step object
    """

    def __init__(self, name: str, stream_delay: float = 0.015):
        """
        Parameters
        ----------
        name         : Display name used in logs.
        stream_delay : Seconds between streamed tokens (simulates LLM
                       output; set to 0 in tests for speed).
        """
        self.name = name
        self.stream_delay = stream_delay
        self.logger = get_logger(name)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def run(
        self, step: Step, context: dict
    ) -> AsyncGenerator[str, None]:
        """
        Run this agent for the given step and stream output tokens.

        Stores the complete result on step.result for downstream steps.
        Raises any exception so the Orchestrator's retry loop catches it.
        """
        self.logger.info(f"Starting step {step.index}: {step.description}")

        # Call the concrete implementation
        result_text = await self._execute(step, context)

        # Store result so downstream steps can access it via context
        step.result = result_text
        context[f"step_{step.index}_result"] = result_text

        # Stream the result token-by-token (simulates real LLM streaming)
        yield f"\n   📤 [{self.name}] Output:\n   "
        async for token in self._stream_text(result_text):
            yield token
        yield "\n"

    # ------------------------------------------------------------------
    # Abstract method – subclasses implement this
    # ------------------------------------------------------------------

    @abstractmethod
    async def _execute(self, step: Step, context: dict) -> str:
        """
        Produce the output for this step.

        Parameters
        ----------
        step    : The Step being processed.
        context : Shared dict containing results from previous steps.

        Returns
        -------
        str : The agent's output (stored on step.result).

        Raises
        ------
        Exception : Any exception triggers the Orchestrator's retry loop.
        """
        ...

    # ------------------------------------------------------------------
    # Streaming helper
    # ------------------------------------------------------------------

    async def _stream_text(self, text: str) -> AsyncGenerator[str, None]:
        """
        Yield text character-by-character with a small delay to simulate
        real LLM token streaming.

        In production this would be replaced by iterating over chunks
        from the LLM provider's streaming SDK.
        """
        for char in text:
            yield char
            if self.stream_delay > 0:
                await asyncio.sleep(self.stream_delay)
