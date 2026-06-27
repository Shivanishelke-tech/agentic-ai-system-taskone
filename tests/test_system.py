"""
tests/test_system.py
--------------------
Unit and integration tests for the Agentic AI System.

Run with:
    python -m pytest tests/ -v

Tests cover:
  - Step dataclass correctness
  - Pipeline batching logic
  - Individual agent happy paths
  - Agent failure injection
  - Orchestrator end-to-end (both happy and failure paths)
  - Decomposer keyword routing
"""

import asyncio
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.step import Step, StepStatus
from core.pipeline import Pipeline
from core.orchestrator import Orchestrator
from agents.retriever_agent import RetrieverAgent
from agents.analyzer_agent import AnalyzerAgent
from agents.writer_agent import WriterAgent
from utils.decomposer import decompose_task


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_step(index=1, agent_type="retrieve", desc="Test step", payload=None):
    return Step(index=index, agent_type=agent_type,
                description=desc, payload=payload or {})


async def collect(agent, step, context=None):
    """Consume an agent's async generator and return the full string."""
    out = []
    async for chunk in agent.run(step, context or {}):
        out.append(chunk)
    return "".join(out)


async def collect_orchestrator(request):
    """Run orchestrator and return full output string."""
    orch = Orchestrator(max_retries=1, retry_delay=0.0)
    chunks = []
    async for chunk in orch.run(request):
        chunks.append(chunk)
    return "".join(chunks)


# ---------------------------------------------------------------------------
# Step tests
# ---------------------------------------------------------------------------

class TestStep:
    def test_default_status_is_pending(self):
        s = make_step()
        assert s.status == StepStatus.PENDING

    def test_fields_set_correctly(self):
        s = make_step(index=3, agent_type="analyze", desc="Analyze this")
        assert s.index == 3
        assert s.agent_type == "analyze"
        assert s.description == "Analyze this"

    def test_result_and_error_default_none(self):
        s = make_step()
        assert s.result is None
        assert s.error is None


# ---------------------------------------------------------------------------
# Pipeline tests
# ---------------------------------------------------------------------------

class TestPipeline:
    def test_batching_splits_correctly(self):
        pipeline = Pipeline(batch_size=2)
        steps = [make_step(i) for i in range(1, 6)]   # 5 steps
        pipeline.load(steps)
        batches = pipeline._make_batches()
        assert len(batches) == 3           # [2, 2, 1]
        assert len(batches[0]) == 2
        assert len(batches[2]) == 1

    def test_iter_steps_yields_all(self):
        pipeline = Pipeline(batch_size=3)
        steps = [make_step(i) for i in range(1, 4)]
        pipeline.load(steps)

        collected = []
        async def _collect():
            async for s in pipeline.iter_steps():
                collected.append(s)

        asyncio.get_event_loop().run_until_complete(_collect())
        assert len(collected) == 3

    def test_len(self):
        pipeline = Pipeline()
        pipeline.load([make_step(i) for i in range(1, 5)])
        assert len(pipeline) == 4


# ---------------------------------------------------------------------------
# Retriever agent tests
# ---------------------------------------------------------------------------

class TestRetrieverAgent:
    def test_happy_path_returns_string(self):
        agent = RetrieverAgent()
        agent.stream_delay = 0   # speed up tests
        step = make_step(payload={"query": "ai trends"})
        result = asyncio.get_event_loop().run_until_complete(
            collect(agent, step)
        )
        assert "AI" in result or "ai" in result.lower()

    def test_result_stored_on_step(self):
        agent = RetrieverAgent()
        agent.stream_delay = 0
        step = make_step(payload={"query": "ai trends"})
        asyncio.get_event_loop().run_until_complete(collect(agent, step))
        assert step.result is not None
        assert step.status == StepStatus.PENDING   # status set by Orchestrator

    def test_failure_injection_raises(self):
        agent = RetrieverAgent()
        agent.stream_delay = 0
        step = make_step(payload={"force_fail": True})
        with pytest.raises(ConnectionError):
            asyncio.get_event_loop().run_until_complete(
                collect(agent, step)
            )


# ---------------------------------------------------------------------------
# Analyzer agent tests
# ---------------------------------------------------------------------------

class TestAnalyzerAgent:
    def test_returns_report_string(self):
        agent = AnalyzerAgent()
        agent.stream_delay = 0
        step = make_step(index=2, agent_type="analyze",
                         payload={"text": "AI is growing rapidly."})
        result = asyncio.get_event_loop().run_until_complete(
            collect(agent, step)
        )
        assert "Analysis Report" in result

    def test_reads_context_from_previous_step(self):
        agent = AnalyzerAgent()
        agent.stream_delay = 0
        step = make_step(index=2, agent_type="analyze")
        context = {"step_1_result": "Key AI trends include multimodal models."}
        result = asyncio.get_event_loop().run_until_complete(
            collect(agent, step, context)
        )
        assert "Analysis Report" in result

    def test_failure_injection_raises(self):
        agent = AnalyzerAgent()
        agent.stream_delay = 0
        step = make_step(index=2, agent_type="analyze",
                         payload={"force_fail": True})
        with pytest.raises(ValueError):
            asyncio.get_event_loop().run_until_complete(collect(agent, step))


# ---------------------------------------------------------------------------
# Writer agent tests
# ---------------------------------------------------------------------------

class TestWriterAgent:
    def test_returns_formatted_report(self):
        agent = WriterAgent()
        agent.stream_delay = 0
        step = make_step(index=3, agent_type="write",
                         payload={"topic": "AI trends"})
        context = {
            "step_1_result": "Raw data here.",
            "step_2_result": "Analysis here.",
        }
        result = asyncio.get_event_loop().run_until_complete(
            collect(agent, step, context)
        )
        assert "FINAL REPORT" in result
        assert "AI trends" in result

    def test_failure_injection_raises(self):
        agent = WriterAgent()
        agent.stream_delay = 0
        step = make_step(index=3, agent_type="write",
                         payload={"force_fail": True})
        with pytest.raises(RuntimeError):
            asyncio.get_event_loop().run_until_complete(collect(agent, step))


# ---------------------------------------------------------------------------
# Decomposer tests
# ---------------------------------------------------------------------------

class TestDecomposer:
    def test_research_and_write_produces_three_steps(self):
        steps = decompose_task(
            "Research AI trends, analyze findings, and write a report"
        )
        agent_types = [s.agent_type for s in steps]
        assert "retrieve" in agent_types
        assert "analyze" in agent_types
        assert "write" in agent_types

    def test_indices_are_sequential(self):
        steps = decompose_task("Research and write about climate change")
        for i, s in enumerate(steps, 1):
            assert s.index == i

    def test_always_ends_with_write(self):
        steps = decompose_task("Find information about quantum computing")
        assert steps[-1].agent_type == "write"


# ---------------------------------------------------------------------------
# Orchestrator integration tests
# ---------------------------------------------------------------------------

class TestOrchestrator:
    def test_happy_path_completes_successfully(self):
        output = asyncio.get_event_loop().run_until_complete(
            collect_orchestrator(
                "Research AI trends, analyze them, and write a report"
            )
        )
        assert "Pipeline complete" in output
        assert "Success" in output or "✅" in output

    def test_failure_case_shows_retry_messages(self):
        """
        Inject a failure into the first step by patching the decomposer,
        then verify the orchestrator logs retry attempts.
        """
        import utils.decomposer as dm
        original = dm.decompose_task

        def patched(req):
            steps = original(req)
            if steps:
                steps[0].payload["force_fail"] = True
            return steps

        dm.decompose_task = patched
        try:
            output = asyncio.get_event_loop().run_until_complete(
                collect_orchestrator(
                    "Research climate change, analyze it, and write a report"
                )
            )
            # Should show retry or failure messaging
            assert "retry" in output.lower() or "❌" in output or "failed" in output.lower()
        finally:
            dm.decompose_task = original   # always restore

    def test_unknown_agent_type_is_skipped(self):
        """
        If a step references an agent not in the registry, it should be
        skipped gracefully rather than crashing the pipeline.
        """
        import utils.decomposer as dm
        original = dm.decompose_task

        def patched(req):
            steps = original(req)
            if steps:
                steps[0].agent_type = "nonexistent_agent"
            return steps

        dm.decompose_task = patched
        try:
            output = asyncio.get_event_loop().run_until_complete(
                collect_orchestrator("Research and write about AI")
            )
            assert "Pipeline complete" in output
        finally:
            dm.decompose_task = original
