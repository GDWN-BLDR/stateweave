# Smart Checkpointing

StateWeave's auto-checkpoint middleware supports three strategies for controlling when agent state is versioned. Choose the right strategy based on your workload.

## Strategies

### `every_n_steps` (Default)

Checkpoint every N calls. Simple and predictable.

```python
from stateweave.middleware import auto_checkpoint

@auto_checkpoint(every_n_steps=5)
def run_agent(payload):
    # Checkpoints at steps 5, 10, 15, ...
    return payload
```

### `on_significant_delta`

Only checkpoint when the state has changed significantly — measured by the number of diff entries between current state and last checkpoint.

```python
@auto_checkpoint(strategy="on_significant_delta", delta_threshold=3)
def run_agent(payload):
    # Only checkpoints when ≥3 fields change since last checkpoint
    return payload
```

This is the best strategy for **performance-sensitive workloads** where the agent makes many small state updates. The diff engine runs on every call, but filesystem writes only happen when truly needed.

### `manual_only`

Disable auto-checkpointing entirely. Only explicit `force=True` calls create checkpoints.

```python
@auto_checkpoint(strategy="manual_only")
def run_agent(payload):
    return payload

# Manually checkpoint when you decide
run_agent.middleware.record(payload, force=True)
```

## Measuring Overhead

Every `CheckpointMiddleware` instance tracks checkpoint timing:

```python
mw = CheckpointMiddleware(agent_id="my-agent", every_n_steps=5)

# ... run workload ...

print(f"Average checkpoint overhead: {mw.checkpoint_overhead_ms:.1f}ms")
```

Run the benchmark script to compare strategies:

```bash
python scripts/bench_checkpoint.py
```

## Strategy Comparison

| Strategy | Best For | Overhead | Checkpoints |
|----------|----------|----------|-------------|
| `every_n_steps` | General workloads | Low | Predictable, fixed interval |
| `on_significant_delta` | High-frequency small updates | Minimal | Only on meaningful changes |
| `manual_only` | Hot paths, latency-critical | Zero | Developer-controlled |

## Context Manager Usage

All strategies work with the context manager:

```python
from stateweave.middleware import CheckpointMiddleware, CheckpointStrategy

with CheckpointMiddleware(
    agent_id="my-agent",
    strategy=CheckpointStrategy.ON_SIGNIFICANT_DELTA,
    delta_threshold=5,
) as mw:
    result = my_graph.invoke(input, config)
    mw.record(result)
```
