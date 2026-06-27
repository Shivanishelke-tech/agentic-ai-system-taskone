"""
core/step.py
------------
Defines the atomic unit of work that flows through the pipeline.

A Step is intentionally a plain dataclass (no framework magic) so every
field is visible and testable without mocking anything.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StepStatus(str, Enum):
    """Lifecycle states a step can be in."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED  = "failed"
    SKIPPED = "skipped"


@dataclass
class Step:
    """
    Represents one discrete unit of work in the agentic pipeline.

    Parameters
    ----------
    index       : 1-based position in the pipeline (used for logging).
    agent_type  : Key that maps to an agent in the Orchestrator registry.
                  Must be one of: "retrieve", "analyze", "write".
    description : Human-readable label shown in the streamed output.
    payload     : Arbitrary data the agent needs to complete the step
                  (e.g. search query, text to analyse, writing prompt).
    status      : Updated in-place by the Orchestrator as the step runs.
    result      : Populated by the agent upon success; shared downstream.
    error       : Populated by the Orchestrator when retries are exhausted.
    metadata    : Optional bag for timing, token counts, etc.
    """
    index:       int
    agent_type:  str
    description: str
    payload:     dict = field(default_factory=dict)

    # Mutable runtime fields – set by the Orchestrator / agents
    status:   StepStatus       = field(default=StepStatus.PENDING, init=False)
    result:   Any              = field(default=None,                init=False)
    error:    str | None       = field(default=None,                init=False)
    metadata: dict             = field(default_factory=dict,        init=False)

    def __repr__(self) -> str:
        return (
            f"Step(index={self.index}, agent={self.agent_type!r}, "
            f"status={self.status.value}, desc={self.description!r})"
        )
