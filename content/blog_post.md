# Why your agent loses its brain when you switch frameworks

I had a LangGraph agent with 800+ messages of conversation history. Working memory full of research findings. A goal tree tracking three parallel objectives. Tool results cached from dozens of API calls.

Then I needed to run it through CrewAI.

Everything was gone. I couldn't bring any of it.

## This isn't a LangGraph problem

Every framework does this. LangGraph stores checkpoints as channel values in a `StateGraph`. CrewAI wraps state in Pydantic models inside Flows. AutoGen keeps `chat_messages` dicts. DSPy traces execution in `dspy.settings`. MCP doesn't persist state at all.

There's no common format. When you move between them, you either rebuild from scratch or write a custom translation script for that specific pair of frameworks. And if you support 10 frameworks, that's 45 translation scripts.

## Star topology, not mesh

StateWeave solves this with one idea: a universal schema.

Each framework translates to and from a single canonical format. 10 adapters, not 45 translation pairs. Adding a new framework costs one adapter and gives you 9 migration paths for free.

```
┌───────────┐     ┌──────────┐     ┌──────────┐
│ LangGraph │     │  CrewAI  │     │ AutoGen  │
│  Adapter  │     │ Adapter  │     │ Adapter  │
└─────┬─────┘     └────┬─────┘     └────┬─────┘
      │                │                │
      └────────┬───────┴────────┬───────┘
               │                │
               ▼                ▼
      ┌─────────────────────────────────┐
      │     Universal Schema            │
      └─────────────────────────────────┘
```

## What actually transfers

The schema captures everything an agent knows:

- **Conversation history** — full message thread with roles and metadata
- **Working memory** — current task state, scratchpad, intermediate results
- **Goal tree** — active objectives and their completion status
- **Tool results cache** — what the agent has already looked up
- **Trust parameters** — confidence scores and uncertainty tracking
- **Long-term memory** — facts the agent has learned over time
- **Episodic memory** — experiences and their outcomes
- **Audit trail** — what happened and when

## What doesn't transfer (and that's fine)

Database cursors, OAuth tokens, threading locks, file handles — these are inherently framework-specific. StateWeave doesn't silently drop them. Every non-portable element gets an explicit warning:

```python
NonPortableWarning(
    field="working_memory.db_cursor",
    reason="sqlite3.Cursor cannot be serialized",
    severity=NonPortableWarningSeverity.WARN,
    data_loss=True,
    recommendation="Re-establish database connection after import"
)
```

You always know exactly what transferred and what didn't.

## Security

Agent state contains the agent's entire cognitive history. Transferring it unencrypted over a network is a terrible idea.

StateWeave ships with AES-256-GCM authenticated encryption, Ed25519 payload signing for sender verification, and PBKDF2 key derivation with 600K iterations. API keys, OAuth tokens, and passwords are automatically flagged as non-portable and stripped during export.

The deserialization pipeline is JSON + Pydantic only. No pickle, no eval, no yaml.load. A compliance engine with 10 automated scanners enforces this across the codebase.

## Getting started

```bash
pip install stateweave
```

```python
from stateweave import LangGraphAdapter, MCPAdapter

payload = LangGraphAdapter().export_state("my-agent")
MCPAdapter().import_state(payload)
```

That's it. The agent's brain comes with it.

GitHub: [GDWN-BLDR/stateweave](https://github.com/GDWN-BLDR/stateweave) — Apache 2.0, 315 tests.

If you've solved agent state migration a different way, I'd be curious to hear about it.
