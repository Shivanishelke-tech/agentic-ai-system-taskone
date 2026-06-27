"""
core/pipeline.py
----------------
Manual pipeline implementation with explicit batching logic.

Why manual?
-----------
Black-box frameworks hide how steps are queued, batched, and iterated.
This class makes every decision visible:
  - Steps are stored in an ordered list (the "queue").
  - Batching is done by slicing that list into fixed-size windows.
  - An async generator yields steps one at a time so the Orchestrator
    can await each one before moving to the next.

Scaling note (also mentioned in post-mortem):
  For I/O-heavy pipelines you could run steps within a batch concurrently
  using asyncio.gather().  That optimisation is NOT applied here because
  later steps depend on earlier results (sequential dependency).
  The batching structure is in place so independent steps could be
  parallelised in a future version with minimal refactoring.
"""

import asyncio
from typing import AsyncGenerator

from core.step import Step
from utils.logger import get_logger

logger = get_logger("Pipeline")


class Pipeline:
    """
    Ordered container of Steps with manual batch iteration.

    Attributes
    ----------
    batch_size : int
        Number of steps per batch window.  Currently each batch is
        processed sequentially (safe for dependent steps).
    _steps     : Internal ordered list of all registered Steps.
    """

    def __init__(self, batch_size: int = 3):
        self.batch_size = batch_size
        self._steps: list[Step] = []

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load(self, steps: list[Step]) -> None:
        """Replace the current step list with a new one."""
        self._steps = list(steps)
        logger.info(
            f"Pipeline loaded with {len(self._steps)} steps "
            f"(batch_size={self.batch_size})"
        )

    # ------------------------------------------------------------------
    # Iteration – async generator so callers can stream output
    # ------------------------------------------------------------------

    async def iter_steps(self) -> AsyncGenerator[Step, None]:
        """
        Yield steps in batches.

        Each batch is logged so you can observe the batching behaviour
        in the streamed output without adding noise.

        Trade-off documented in post-mortem:
          Sequential batching is safe but slow for independent steps.
          Parallel batching is fast but risks race conditions on shared
          context dict.
        """
        batches = self._make_batches()

        for batch_idx, batch in enumerate(batches, start=1):
            logger.debug(
                f"Processing batch {batch_idx}/{len(batches)} "
                f"({len(batch)} steps)"
            )
            for step in batch:
                yield step
                # Tiny yield point so the event loop stays responsive
                await asyncio.sleep(0)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _make_batches(self) -> list[list[Step]]:
        """
        Slice self._steps into fixed-size windows.

        Example
        -------
        Steps = [1, 2, 3, 4, 5],  batch_size = 3
        → [[1, 2, 3], [4, 5]]
        """
        batches = []
        for i in range(0, len(self._steps), self.batch_size):
            batches.append(self._steps[i : i + self.batch_size])
        return batches

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    @property
    def steps(self) -> list[Step]:
        return list(self._steps)

    def __len__(self) -> int:
        return len(self._steps)
