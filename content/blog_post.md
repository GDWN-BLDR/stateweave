# Why every AI agent framework has persistence but none have time-travel debugging

Every major AI agent framework can save and restore its own state.
LangGraph has checkpoints. AutoGen has `save_state()`. CrewAI has Flows
backed by LanceDB. DSPy traces execution in `dspy.settings`.

But try *debugging* a complex agent workflow? Good luck. When a 20-step
autonomous workflow derails at step 15, your only option is to restart
from scratch. All the context the agent built up — gone. All the API
calls — re-billed.

I started noticing this pattern in agent communities. Not just the
portability problem (people stuck on one framework because they'd
accumulated too much state to start over), but the far more common
debugging nightmare. Every developer running complex agent workflows
hits this wall.

So I built StateWeave — a time-travel debugger and security control
plane for AI agents.

## Time travel for agent state

The core insight: once you can serialize agent cognitive state into a
versioned format, you get `git` for free. Checkpoint at any step,
rollback to any previous state, diff between any two versions, branch
to fork an agent's cognition.

```bash
stateweave checkpoint state.json --label "before-experiment"
stateweave history my-agent
stateweave rollback my-agent 3 -o restored.json
stateweave diff step-14.json step-15.json
```

Content-addressable storage using SHA-256 hashing, with parent hash
chains linking each version to its predecessor. Fork from any checkpoint
to run experiments without risking the main line.

## Security first

Agent state contains the agent's entire cognitive history. Transferring
it unencrypted is a bad idea.

StateWeave ships with AES-256-GCM authenticated encryption, Ed25519
payload signing, and PBKDF2 key derivation with 600K iterations. API keys
and credentials are automatically flagged and stripped during export.

No pickle, no eval, no yaml.load. A compliance engine with 12 automated
scanners enforces this across the codebase.

## Smart checkpointing

Not every state change deserves a checkpoint. StateWeave's middleware
supports three strategies:

```python
# Checkpoint every 5 steps — simple and predictable
@auto_checkpoint(every_n_steps=5)
def run_agent(payload):
    return payload

# Only checkpoint on significant changes — skip noise
@auto_checkpoint(strategy="on_significant_delta", delta_threshold=3)
def smart_agent(payload):
    return payload
```

Built-in timing instrumentation lets you measure overhead:
`mw.checkpoint_overhead_ms` gives you the average ms per checkpoint.

## Cross-framework portability (bonus)

The universal schema that enables time-travel also enables something
else: cross-framework state migration.

```
LangGraph ──adapter──▶ Universal Schema ◀──adapter── CrewAI
                            ▲
AutoGen ───adapter──────────┘
```

Star topology. 10 adapters give you portability across all 10 frameworks.
Export from LangGraph, import into CrewAI — conversation history,
working memory, goals, tool results all come along.

### Zero-loss translations

Framework-specific state (like LangGraph's internal channel versions)
isn't silently dropped — it's preserved in `framework_specific` for
same-framework round-trips. Cross-framework migrations get explicit
`non_portable_warnings` for anything that can't transfer.

## Does it actually work?

The LangGraph adapter has integration tests against the real framework —
not mocks, not fake data. It creates an actual `StateGraph` with
`MemorySaver`, runs messages through it, then verifies the full
round-trip including framework-specific internal state.

## A2A protocol bridge

Google's Agent2Agent (A2A) protocol defines how agents communicate with
each other. But communication and knowledge transfer are different things.
A2A tells Agent B that Agent A wants it to do something. StateWeave tells
Agent B what Agent A already knows.

The A2A bridge packages StateWeave payloads as A2A TaskArtifacts with a
registered MIME type, so A2A-compatible agents can receive full cognitive
state — not just a task description.

## Getting started

```bash
pip install stateweave
```

GitHub: [GDWN-BLDR/stateweave](https://github.com/GDWN-BLDR/stateweave) — Apache 2.0.

This is a hobby project and still early. If you've dealt with agent
debugging or state management, I'd be interested to hear about it.
