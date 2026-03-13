#!/usr/bin/env python3
"""
Checkpoint Strategy Benchmark
==============================
Measures checkpointing overhead across all three strategies.

Usage:
    python scripts/bench_checkpoint.py
"""

import shutil
import tempfile
import time

from stateweave.middleware.auto_checkpoint import CheckpointMiddleware, CheckpointStrategy
from stateweave.schema.v1 import (
    AgentMetadata,
    CognitiveState,
    Message,
    MessageRole,
    StateWeavePayload,
)


def make_payload(messages: int = 10, task: str = "benchmark") -> StateWeavePayload:
    """Create a realistic payload for benchmarking."""
    history = [
        Message(
            role=MessageRole.HUMAN if i % 2 == 0 else MessageRole.ASSISTANT,
            content=f"This is message {i} with some realistic content that an agent would produce during a typical workflow execution step.",
        )
        for i in range(messages)
    ]
    return StateWeavePayload(
        source_framework="langgraph",
        stateweave_version="1.0.0",
        metadata=AgentMetadata(agent_id="bench-agent"),
        cognitive_state=CognitiveState(
            conversation_history=history,
            working_memory={
                "current_task": task,
                "progress": 0.5,
                "context": {"key": "value", "nested": {"deep": True}},
            },
            trust_parameters={"confidence": 0.85, "uncertainty": 0.15},
        ),
    )


def bench_strategy(
    strategy: CheckpointStrategy,
    iterations: int = 100,
    **kwargs,
) -> dict:
    """Benchmark a single strategy."""
    tmpdir = tempfile.mkdtemp()
    try:
        mw = CheckpointMiddleware(
            agent_id="bench",
            strategy=strategy,
            store_dir=tmpdir,
            every_n_steps=5,
            **kwargs,
        )

        payloads = []
        for i in range(iterations):
            payloads.append(make_payload(messages=10 + (i % 5), task=f"task-{i}"))

        start = time.monotonic()
        checkpoints_taken = 0
        for p in payloads:
            if mw.record(p):
                checkpoints_taken += 1
        elapsed = (time.monotonic() - start) * 1000  # ms

        return {
            "strategy": strategy.value,
            "iterations": iterations,
            "checkpoints_taken": checkpoints_taken,
            "total_ms": round(elapsed, 2),
            "avg_per_record_ms": round(elapsed / iterations, 3),
            "avg_checkpoint_ms": round(mw.checkpoint_overhead_ms, 3),
        }
    finally:
        shutil.rmtree(tmpdir)


def main():
    print("=" * 70)
    print("🧶 StateWeave Checkpoint Strategy Benchmark")
    print("=" * 70)
    print()

    iterations = 100

    results = [
        bench_strategy(CheckpointStrategy.EVERY_N_STEPS, iterations),
        bench_strategy(CheckpointStrategy.ON_SIGNIFICANT_DELTA, iterations, delta_threshold=3),
        bench_strategy(CheckpointStrategy.MANUAL_ONLY, iterations),
    ]

    # Print results table
    print(f"{'Strategy':<28} {'Checkpoints':<14} {'Total ms':<12} {'Avg/record':<14} {'Avg/ckpt'}")
    print("-" * 70)
    for r in results:
        print(
            f"{r['strategy']:<28} {r['checkpoints_taken']:<14} "
            f"{r['total_ms']:<12} {r['avg_per_record_ms']:<14} "
            f"{r['avg_checkpoint_ms']}ms"
        )

    print()
    print(f"Iterations per strategy: {iterations}")
    print()

    # Performance summary
    every_n = results[0]
    delta = results[1]
    manual = results[2]  # noqa: F841

    if delta["total_ms"] > 0 and every_n["total_ms"] > 0:
        savings = (1 - delta["total_ms"] / every_n["total_ms"]) * 100
        print(
            f"💡 ON_SIGNIFICANT_DELTA saves ~{savings:.0f}% overhead vs EVERY_N_STEPS "
            f"({delta['checkpoints_taken']} vs {every_n['checkpoints_taken']} checkpoints)"
        )

    print()


if __name__ == "__main__":
    main()
