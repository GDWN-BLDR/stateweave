"""
Auto-Checkpoint Middleware — Invisible state versioning for agent frameworks.
==============================================================================
Wraps agent execution to automatically checkpoint state at configurable
intervals. Developers inherit StateWeave without changing their code.

Usage:
    from stateweave.middleware import auto_checkpoint

    # Decorator — checkpoint every 5 invocations
    @auto_checkpoint(every_n_steps=5)
    def run_agent(payload):
        ...

    # Smart checkpointing — only checkpoint on significant changes
    @auto_checkpoint(strategy="on_significant_delta", delta_threshold=3)
    def run_agent(payload):
        ...

    # Context manager
    with CheckpointMiddleware(agent_id="my-agent") as mw:
        result = my_graph.invoke(input, config)
        mw.record(result)  # auto-checkpoints when threshold hit
"""

import functools
import logging
import time
from enum import Enum
from typing import Callable, Optional

from stateweave.core.timetravel import CheckpointStore
from stateweave.schema.v1 import StateWeavePayload

logger = logging.getLogger("stateweave.middleware")


class CheckpointStrategy(str, Enum):
    """Checkpointing strategies.

    EVERY_N_STEPS: Checkpoint every N calls to record(). Simple and
        predictable. Good default for most workloads.

    ON_SIGNIFICANT_DELTA: Only checkpoint when the diff between current
        and last-checkpointed state exceeds `delta_threshold` changes.
        Minimizes overhead for workflows with many small state updates.

    MANUAL_ONLY: Disable auto-checkpointing entirely. Checkpoints only
        fire when force=True. For performance-critical hot paths where
        developers want full control.
    """

    EVERY_N_STEPS = "every_n_steps"
    ON_SIGNIFICANT_DELTA = "on_significant_delta"
    MANUAL_ONLY = "manual_only"


class CheckpointMiddleware:
    """Middleware that auto-checkpoints agent state.

    Can be used as a context manager or manually.

    Args:
        agent_id: Agent identifier for checkpoints.
        every_n_steps: Checkpoint every N calls to record().
        store_dir: Optional checkpoint store directory.
        label_prefix: Prefix for auto-generated checkpoint labels.
        strategy: Checkpointing strategy (default: EVERY_N_STEPS).
        delta_threshold: Minimum number of diff entries to trigger a
            checkpoint when using ON_SIGNIFICANT_DELTA strategy.
    """

    def __init__(
        self,
        agent_id: str = "default",
        every_n_steps: int = 5,
        store_dir: Optional[str] = None,
        label_prefix: str = "auto",
        strategy: CheckpointStrategy = CheckpointStrategy.EVERY_N_STEPS,
        delta_threshold: int = 3,
    ):
        self.agent_id = agent_id
        self.every_n_steps = every_n_steps
        self.label_prefix = label_prefix
        self.strategy = CheckpointStrategy(strategy)
        self.delta_threshold = delta_threshold
        self._store = CheckpointStore(store_dir=store_dir)
        self._step_count = 0
        self._last_checkpointed_payload: Optional[StateWeavePayload] = None
        self._total_checkpoint_time_ms: float = 0.0
        self._checkpoint_invocations: int = 0

    def __enter__(self):
        self._step_count = 0
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def record(
        self,
        payload: StateWeavePayload,
        force: bool = False,
    ) -> bool:
        """Record a step. Auto-checkpoints based on the configured strategy.

        Args:
            payload: The current agent state.
            force: Force a checkpoint regardless of strategy.

        Returns:
            True if a checkpoint was created, False otherwise.
        """
        self._step_count += 1

        should_checkpoint = force or self._should_checkpoint(payload)

        if should_checkpoint:
            start_time = time.monotonic()

            label = f"{self.label_prefix}-step-{self._step_count}"
            self._store.checkpoint(
                payload=payload,
                agent_id=self.agent_id,
                label=label,
            )

            elapsed_ms = (time.monotonic() - start_time) * 1000
            self._total_checkpoint_time_ms += elapsed_ms
            self._checkpoint_invocations += 1
            self._last_checkpointed_payload = payload

            logger.info(
                f"Auto-checkpoint at step {self._step_count} for '{self.agent_id}' "
                f"({label}, {elapsed_ms:.1f}ms)"
            )
            return True

        return False

    def _should_checkpoint(self, payload: StateWeavePayload) -> bool:
        """Determine whether a checkpoint should fire based on strategy."""
        if self.strategy == CheckpointStrategy.MANUAL_ONLY:
            return False

        if self.strategy == CheckpointStrategy.EVERY_N_STEPS:
            return self._step_count % self.every_n_steps == 0

        if self.strategy == CheckpointStrategy.ON_SIGNIFICANT_DELTA:
            if self._last_checkpointed_payload is None:
                # Always checkpoint the first state
                return True
            # Lazy import to avoid circular dependency at module level
            from stateweave.core.diff import diff_payloads

            diff = diff_payloads(self._last_checkpointed_payload, payload)
            return len(diff.entries) >= self.delta_threshold

        return False

    @property
    def step_count(self) -> int:
        return self._step_count

    @property
    def checkpoint_count(self) -> int:
        history = self._store.history(self.agent_id)
        return history.version_count

    @property
    def checkpoint_overhead_ms(self) -> float:
        """Average checkpoint overhead in milliseconds.

        Returns 0.0 if no checkpoints have been taken yet.
        """
        if self._checkpoint_invocations == 0:
            return 0.0
        return self._total_checkpoint_time_ms / self._checkpoint_invocations


def auto_checkpoint(
    every_n_steps: int = 5,
    agent_id: Optional[str] = None,
    store_dir: Optional[str] = None,
    strategy: str = "every_n_steps",
    delta_threshold: int = 3,
) -> Callable:
    """Decorator that auto-checkpoints StateWeavePayloads returned by a function.

    The decorated function must return a StateWeavePayload.
    Checkpointing behavior is controlled by the strategy parameter.

    Args:
        every_n_steps: Checkpoint frequency (for EVERY_N_STEPS strategy).
        agent_id: Agent identifier (defaults to function name).
        store_dir: Optional checkpoint store directory.
        strategy: Checkpointing strategy — "every_n_steps",
            "on_significant_delta", or "manual_only".
        delta_threshold: Min diff entries to trigger checkpoint
            (for ON_SIGNIFICANT_DELTA strategy).

    Returns:
        Decorated function.

    Example:
        @auto_checkpoint(every_n_steps=3)
        def process_message(payload, message):
            # ... modify payload ...
            return payload

        @auto_checkpoint(strategy="on_significant_delta", delta_threshold=5)
        def smart_process(payload):
            # Only checkpoints when ≥5 fields change
            return payload
    """

    def decorator(func: Callable) -> Callable:
        _agent_id = agent_id or func.__name__
        middleware = CheckpointMiddleware(
            agent_id=_agent_id,
            every_n_steps=every_n_steps,
            store_dir=store_dir,
            strategy=CheckpointStrategy(strategy),
            delta_threshold=delta_threshold,
        )

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)

            if isinstance(result, StateWeavePayload):
                middleware.record(result)

            return result

        # Expose middleware for inspection
        wrapper.middleware = middleware
        return wrapper

    return decorator
