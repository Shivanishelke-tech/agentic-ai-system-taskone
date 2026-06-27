import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from core.orchestrator import Orchestrator
from core.step import Step
from utils.decomposer import decompose_task


async def run_happy_path():
    print("\n" + "═" * 60)
    print("  SCENARIO 1: Happy Path — AI Trends Research")
    print("═" * 60)
    orchestrator = Orchestrator(max_retries=2, retry_delay=0.5)
    async for chunk in orchestrator.run(
        "Research the latest AI trends, analyze the findings, and write a detailed report about artificial intelligence"
    ):
        print(chunk, end="", flush=True)


async def run_failure_demo():
    print("\n" + "═" * 60)
    print("  SCENARIO 2: FAILURE DEMO — Retrieval Agent Crashes")
    print("═" * 60)

    orchestrator = Orchestrator(max_retries=2, retry_delay=0.5)

    # Manually build steps with force_fail on Step 1
    steps = decompose_task(
        "Research climate change, analyze the trends, and write a report about climate"
    )
    steps[0].payload["force_fail"] = True  # FORCE Step 1 to fail

    # Load directly into pipeline
    orchestrator.pipeline.load(steps)

    print(f"\n🧠 [Orchestrator] Task loaded with FORCED FAILURE on Step 1\n")
    print("─" * 60 + "\n")

    context = {}
    async for chunk in orchestrator._execute_pipeline(context):
        print(chunk, end="", flush=True)

    print("\n" + "─" * 60)
    print(orchestrator._build_summary(steps))


async def main():
    print("\n" + "★" * 60)
    print("  AGENTIC AI SYSTEM — Multi-Step Task Orchestration Demo")
    print("★" * 60)

    await run_happy_path()

    print("\n\n" + "─" * 60)
    input("  Press ENTER to run Scenario 2: Failure Demo...")

    await run_failure_demo()


if __name__ == "__main__":
    asyncio.run(main())