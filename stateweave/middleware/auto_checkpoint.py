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

    # Context manager
    with CheckpointMiddleware(agent_id="my-agent") as mw:
        result = my_graph.invoke(input, config)
        mw.record(result)  # auto-checkpoints when threshold hit
"""

import functools
import logging
from typing import Callable, Optional

from stateweave.core.timetravel import CheckpointStore
from stateweave.schema.v1 import StateWeavePayload

logger = logging.getLogger("stateweave.middleware")


class CheckpointMiddleware:
    """Middleware that auto-checkpoints agent state.

    Can be used as a context manager or manually.

    Args:
        agent_id: Agent identifier for checkpoints.
        every_n_steps: Checkpoint every N calls to record().
        store_dir: Optional checkpoint store directory.
        label_prefix: Prefix for auto-generated checkpoint labels.
    """

    def __init__(
        self,
        agent_id: str = "default",
        every_n_steps: int = 5,
        store_dir: Optional[str] = None,
        label_prefix: str = "auto",
    ):
        self.agent_id = agent_id
        self.every_n_steps = every_n_steps
        self.label_prefix = label_prefix
        self._store = CheckpointStore(store_dir=store_dir)
        self._step_count = 0

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
        """Record a step. Auto-checkpoints when threshold is hit.

        Args:
            payload: The current agent state.
            force: Force a checkpoint regardless of step count.

        Returns:
            True if a checkpoint was created, False otherwise.
        """
        self._step_count += 1

        if force or self._step_count % self.every_n_steps == 0:
            label = f"{self.label_prefix}-step-{self._step_count}"
            self._store.checkpoint(
                payload=payload,
                agent_id=self.agent_id,
                label=label,
            )
            logger.info(
                f"Auto-checkpoint at step {self._step_count} for '{self.agent_id}' ({label})"
            )
            return True

        return False

    @property
    def step_count(self) -> int:
        return self._step_count

    @property
    def checkpoint_count(self) -> int:
        history = self._store.history(self.agent_id)
        return history.version_count


def auto_checkpoint(
    every_n_steps: int = 5,
    agent_id: Optional[str] = None,
    store_dir: Optional[str] = None,
) -> Callable:
    """Decorator that auto-checkpoints StateWeavePayloads returned by a function.

    The decorated function must return a StateWeavePayload.
    Every N calls, the result is automatically checkpointed.

    Args:
        every_n_steps: Checkpoint frequency.
        agent_id: Agent identifier (defaults to function name).
        store_dir: Optional checkpoint store directory.

    Returns:
        Decorated function.

    Example:
        @auto_checkpoint(every_n_steps=3)
        def process_message(payload, message):
            # ... modify payload ...
            return payload
    """

    def decorator(func: Callable) -> Callable:
        _agent_id = agent_id or func.__name__
        middleware = CheckpointMiddleware(
            agent_id=_agent_id,
            every_n_steps=every_n_steps,
            store_dir=store_dir,
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
