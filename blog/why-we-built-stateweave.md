# Why We Built StateWeave: `git` for Agent Brains

*March 2026*

## The Problem Nobody Talks About

Here's a scenario every AI engineer has lived through:

You build an agent on LangGraph. It works. It learns. Over 200 conversations, it develops nuanced understanding of your domain — your coding patterns, your business rules, your preferences.

Then your team decides to switch to CrewAI. Or you need to run the agent locally through MCP because it hit a VPN wall. Or you're evaluating AutoGen for better multi-agent coordination.

**What happens to everything the agent learned?** 

You start over. Two hundred conversations of accumulated context — gone.

## Why JSON.dumps() Doesn't Cut It

The obvious answer is "just serialize to JSON." We tried that. Here's what we discovered:

1. **Framework state structures are incompatible.** LangGraph stores messages as `HumanMessage` / `AIMessage` objects with tool call metadata. CrewAI uses `TaskOutput` with agent attribution. MCP has its own resource/tool model. You can't just JSON-dump one and load it into another.

2. **Credentials leak.** Agent state often contains API keys, OAuth tokens, database cursors. Without automated stripping, you're shipping secrets across the wire.

3. **No rollback.** If the migration corrupts something, you can't undo it.

4. **N² translation pairs.** Supporting 4 frameworks means 12 translation functions. Supporting 10 means 90. This doesn't scale.

## The Star Topology Insight

The key insight that became StateWeave: **don't translate between frameworks. Translate to a universal schema.**

```
Framework A → Universal Schema → Framework B
```

Instead of N² translation pairs, you need N adapters. Adding framework #11 doesn't require touching any existing code — just one new adapter that speaks the Universal Schema.

The schema captures what agents actually think about:
- **Conversation history** — messages, tool calls, results
- **Working memory** — intermediate reasoning, scratchpad
- **Goal tree** — what the agent is trying to accomplish
- **Trust parameters** — confidence scores, delegation limits
- **Tool results cache** — expensive computations the agent shouldn't repeat

## What We Actually Built

StateWeave is a Python library (`pip install stateweave`) that does three things:

### 1. Export / Import
```python
from stateweave import LangGraphAdapter, MCPAdapter

# Export from LangGraph
payload = LangGraphAdapter().export_state("my-agent")

# Import into MCP
MCPAdapter().import_state(payload)
```

Three lines. The agent's memories transfer.

### 2. Time Travel
```python
from stateweave.core.timetravel import CheckpointStore

store = CheckpointStore()
store.checkpoint(payload, message="before risky operation")

# ... operation goes wrong ...

payload = store.rollback()  # back to safety
```

Every checkpoint is content-addressed (SHA-256), has parent hash chains, and supports branching — like git for agent state.

### 3. Security
```python
from stateweave.core.encryption import EncryptionFacade
from stateweave.core.signing import sign_payload, generate_keypair

# Encrypt with a passphrase (AES-256-GCM + PBKDF2)
facade = EncryptionFacade.from_passphrase("enterprise-key")
ciphertext, nonce = facade.encrypt(serialized_bytes)

# Sign for audit compliance (Ed25519)
private_key, public_key = generate_keypair()
signature = sign_payload(payload, private_key)
```

AES-256-GCM encryption. Ed25519 signing. PBKDF2 key derivation with 600K iterations. Credentials are auto-stripped on export with explicit `non_portable_warnings`.

## What's Next

StateWeave currently supports 10 frameworks (LangGraph, MCP, CrewAI, AutoGen, DSPy, LlamaIndex, OpenAI Agents, Haystack, Letta, and Semantic Kernel). Our highest-priority work is:

1. **Community adapters** — making it trivial for anyone to add framework #11
2. **Deeper framework integrations** — the LangGraph adapter has real integration tests; we're extending that rigor to all Tier 1 adapters
3. **Real-world stress testing** — we need teams to break it on production workloads

## Try It

```bash
pip install stateweave
python -c "from stateweave import LangGraphAdapter; print('Ready.')"
stateweave doctor
```

[GitHub](https://github.com/GDWN-BLDR/stateweave) · [PyPI](https://pypi.org/project/stateweave/) · Apache 2.0

---

*StateWeave is built by [Pantoll Ventures](https://pantollventures.com). We believe agent intelligence should be portable, auditable, and never lost.*
