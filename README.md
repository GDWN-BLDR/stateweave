<p align="center">
  <h1 align="center">🧶 StateWeave</h1>
  <p align="center"><strong>Your AI agent switches frameworks. Its memories come with it.</strong></p>
  <p align="center">
    <a href="https://pypi.org/project/stateweave/"><img src="https://img.shields.io/pypi/v/stateweave?color=%2334D058&label=PyPI" alt="PyPI"></a>
    <a href="https://github.com/GDWN-BLDR/stateweave/actions"><img src="https://img.shields.io/github/actions/workflow/status/GDWN-BLDR/stateweave/ci.yml?label=CI" alt="CI"></a>
    <a href="https://github.com/GDWN-BLDR/stateweave/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg" alt="License"></a>
    <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/pypi/pyversions/stateweave" alt="Python"></a>
  </p>
</p>

---

<!-- mcp-name: stateweave -->

**StateWeave** is a cross-framework cognitive state serializer for AI agents. It lets agents migrate between LangGraph, MCP, CrewAI, AutoGen, DSPy, LlamaIndex, OpenAI Agents, Haystack, Letta, and Semantic Kernel while preserving their accumulated knowledge — conversation history, working memory, goals, tool results, and trust parameters.

No more rebuilding agent state from scratch when switching frameworks. No more vendor lock-in for your agent's brain.

## Why StateWeave?

Every time you move an agent between frameworks, you lose everything it learned. StateWeave solves this with a **Universal Schema** — a canonical representation of agent cognitive state that all frameworks translate to and from. One schema, N adapters, zero data loss (with explicit warnings for anything non-portable).

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  LangGraph  │     │    MCP      │     │   CrewAI    │     │   AutoGen   │
│   Adapter   │     │   Adapter   │     │   Adapter   │     │   Adapter   │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │                   │
       └───────────┬───────┴───────────┬───────┘                   │
                   │                   │                           │
                   ▼                   ▼                           ▼
            ┌──────────────────────────────────────────────────────────┐
            │              🧶  Universal Schema v1                     │
            │                                                          │
            │  conversation_history  ·  working_memory  ·  goal_tree   │
            │  tool_results_cache  ·  trust_parameters  ·  audit_trail │
            └──────────────────────────────────────────────────────────┘
```

**Star topology, not mesh.** N adapters, not N² translation pairs. Adding a new framework = one adapter, instant compatibility with everything else.

## Quick Start

### Install

```bash
pip install stateweave
```

### Export an Agent's State

```python
from stateweave import LangGraphAdapter, StateWeaveSerializer

# Export from LangGraph
adapter = LangGraphAdapter(checkpointer=my_checkpointer)
payload = adapter.export_state("my-thread-id")

# Serialize for transport
serializer = StateWeaveSerializer()
raw_bytes = serializer.dumps(payload)
```

### Import into Another Framework

```python
from stateweave import MCPAdapter

# Import into MCP
mcp_adapter = MCPAdapter()
mcp_adapter.import_state(payload)

# The agent resumes with its memories intact
```

### Migrate with Encryption

```python
from stateweave import EncryptionFacade, MigrationEngine

# Set up encrypted migration
key = EncryptionFacade.generate_key()
engine = MigrationEngine(
    encryption=EncryptionFacade(key)
)

# Full pipeline: export → validate → encrypt → transport
result = engine.export_state(
    adapter=langgraph_adapter,
    agent_id="my-agent",
    encrypt=True,
)

# Decrypt → validate → import on the other side
engine.import_state(
    adapter=mcp_adapter,
    encrypted_data=result.encrypted_data,
    nonce=result.nonce,
)
```

### Diff Two States

```python
from stateweave import diff_payloads

diff = diff_payloads(state_before, state_after)
print(diff.to_report())
# ═══════════════════════════════════════════════
# 🔍 STATEWEAVE DIFF REPORT
# ═══════════════════════════════════════════════
#   Changes: 5 (+2 -1 ~2)
#   [working_memory]
#     + working_memory.new_task: 'research'
#     ~ working_memory.confidence: 0.7 → 0.95
```

## Framework Support

| Framework | Adapter | Export | Import | Tier |
|-----------|---------|:------:|:------:|------|
| **LangGraph** | `LangGraphAdapter` | ✅ | ✅ | 🟢 Tier 1 |
| **MCP** | `MCPAdapter` | ✅ | ✅ | 🟢 Tier 1 |
| **CrewAI** | `CrewAIAdapter` | ✅ | ✅ | 🟢 Tier 1 |
| **AutoGen** | `AutoGenAdapter` | ✅ | ✅ | 🟢 Tier 1 |
| **DSPy** | `DSPyAdapter` | ✅ | ✅ | 🟡 Tier 2 |
| **OpenAI Agents** | `OpenAIAgentsAdapter` | ✅ | ✅ | 🟡 Tier 2 |
| **LlamaIndex** | `LlamaIndexAdapter` | ✅ | ✅ | 🔵 Community |
| **Haystack** | `HaystackAdapter` | ✅ | ✅ | 🔵 Community |
| **Letta / MemGPT** | `LettaAdapter` | ✅ | ✅ | 🔵 Community |
| **Semantic Kernel** | `SemanticKernelAdapter` | ✅ | ✅ | 🔵 Community |
| Custom | Extend `StateWeaveAdapter` | ✅ | ✅ | DIY |

> **Tier definitions:** 🟢 **Tier 1** = Core team maintained, guaranteed stability. 🟡 **Tier 2** = Actively maintained, patches may lag. 🔵 **Community** = Best-effort, contributed by community.

## MCP Server

StateWeave ships as an MCP Server — any MCP-compatible AI assistant can use it directly.

### Tools

| Tool | Description |
|------|-------------|
| `export_agent_state` | Export an agent's cognitive state from any supported framework |
| `import_agent_state` | Import state into a target framework with validation |
| `diff_agent_states` | Compare two states and return a detailed change report |

### Resources

| Resource | URI |
|----------|-----|
| Universal Schema spec | `stateweave://schemas/v1` |
| Migration history log | `stateweave://migrations/history` |
| Live agent snapshot | `stateweave://agents/{id}/snapshot` |

### Prompts

| Prompt | Use Case |
|--------|----------|
| `backup_before_risky_operation` | Agent self-requests state backup before risky ops |
| `migration_guide` | Step-by-step framework migration template |

## The Universal Schema

Every agent's state is represented as a `StateWeavePayload`:

```python
StateWeavePayload(
    stateweave_version="0.3.0",
    source_framework="langgraph",
    exported_at=datetime,
    cognitive_state=CognitiveState(
        conversation_history=[...],   # Full message history
        working_memory={...},         # Current task state
        goal_tree={...},              # Active goals
        tool_results_cache={...},     # Cached tool outputs
        trust_parameters={...},       # Confidence scores
        long_term_memory={...},       # Persistent knowledge
        episodic_memory=[...],        # Past experiences
    ),
    metadata=AgentMetadata(
        agent_id="my-agent",
        access_policy="private",
    ),
    audit_trail=[...],               # Full operation history
    non_portable_warnings=[...],     # Explicit data loss docs
)
```

## Security

- **AES-256-GCM** authenticated encryption with unique nonce per operation
- **PBKDF2** key derivation (600K iterations, OWASP recommended)
- **Ed25519 payload signing** — digital signatures verify sender identity and detect tampering
- **Credential stripping** — API keys, tokens, and passwords are flagged as non-portable and stripped during export
- **Non-portable warnings** — every piece of state that can't fully transfer is explicitly documented (no silent data loss)
- **Associated data** — encrypt with AAD to bind ciphertext to specific agent metadata

### Payload Signing

```python
from stateweave import EncryptionFacade

# Generate a signing key pair
private_key, public_key = EncryptionFacade.generate_signing_keypair()

# Sign serialized payload
signature = EncryptionFacade.sign(payload_bytes, private_key)

# Verify on receipt
is_authentic = EncryptionFacade.verify(payload_bytes, signature, public_key)
```

## Delta State Transport

For large state payloads, send only the changes:

```python
from stateweave.core.delta import create_delta, apply_delta

# Create delta: only the differences
delta = create_delta(old_payload, new_payload)

# Apply delta on the receiver side
updated = apply_delta(base_payload, delta)
```

## State Merge (CRDT Foundation)

Merge state from parallel agents:

```python
from stateweave.core.merge import merge_payloads, ConflictResolutionPolicy

result = merge_payloads(
    agent_a_state, agent_b_state,
    policy=ConflictResolutionPolicy.LAST_WRITER_WINS,
)
merged_payload = result.payload
```

## Non-Portable State

Not everything can transfer between frameworks. StateWeave handles this honestly:

| Category | Example | Behavior |
|----------|---------|----------|
| DB connections | `sqlite3.Cursor` | ⚠️ Stripped, warning emitted |
| Credentials | `api_key`, `oauth_token` | 🔴 Stripped, CRITICAL warning |
| Framework internals | LangGraph `__channel_versions__` | ⚠️ Stripped, warning emitted |
| Thread/async state | `threading.Lock`, `asyncio.Task` | ⚠️ Stripped, warning emitted |
| Live connections | Network sockets, file handles | ⚠️ Stripped, warning emitted |

All non-portable elements appear in `payload.non_portable_warnings[]` with severity, reason, and remediation guidance.

## Building a Custom Adapter

Extend `StateWeaveAdapter` to add support for any framework:

```python
from stateweave.adapters.base import StateWeaveAdapter
from stateweave.schema.v1 import StateWeavePayload, AgentInfo

class MyFrameworkAdapter(StateWeaveAdapter):
    @property
    def framework_name(self) -> str:
        return "my-framework"

    def export_state(self, agent_id: str, **kwargs) -> StateWeavePayload:
        # Translate your framework's state → Universal Schema
        ...

    def import_state(self, payload: StateWeavePayload, **kwargs):
        # Translate Universal Schema → your framework's state
        ...

    def list_agents(self) -> list[AgentInfo]:
        # Return available agents
        ...
```

The UCE `adapter_contract` scanner automatically validates that all adapters correctly implement the ABC.

## CLI

```bash
# Show version and available adapters
stateweave version

# Dump the Universal Schema as JSON Schema
stateweave schema -o schema.json

# Validate a payload file
stateweave validate state.json

# Export/import/diff
stateweave export -f langgraph -a my-agent -o state.json
stateweave import -f mcp --payload state.json
stateweave diff before.json after.json

# Auto-detect source framework
stateweave detect state.json

# List all available adapters
stateweave adapters

# Scaffold a new adapter
stateweave generate-adapter my-framework --output-dir ./adapters
```

## Compliance (UCE)

StateWeave enforces its own architectural standards via the **Universal Compliance Engine** — 10 automated scanners that run on every commit:

| Scanner | What It Checks | Mode |
|---------|---------------|------|
| `schema_integrity` | Universal Schema models have required fields | BLOCK |
| `adapter_contract` | All adapters implement the full ABC | BLOCK |
| `serialization_safety` | No raw pickle/json.dumps outside serializer | BLOCK |
| `encryption_compliance` | All crypto goes through EncryptionFacade | BLOCK |
| `mcp_protocol` | MCP server has all required tools | BLOCK |
| `import_discipline` | No cross-layer imports | BLOCK |
| `logger_naming` | All loggers use `stateweave.*` convention | BLOCK |
| `test_coverage_gate` | Minimum test file coverage ratio | BLOCK |
| `file_architecture` | No orphan files outside MANIFEST | WARN |
| `dependency_cycles` | No circular imports | BLOCK |

```bash
# Run UCE locally
python scripts/uce.py

# Run in CI mode (exit 1 on failure)
python scripts/uce.py --mode=CI --json
```

## Contributing

We welcome contributions! The highest-impact way to contribute is **building a new framework adapter**. See [Building a Custom Adapter](#building-a-custom-adapter) above.

### Development Setup

```bash
git clone https://github.com/GDWN-BLDR/stateweave.git
cd stateweave
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run UCE
python scripts/uce.py
```

### Architecture

```
stateweave/
├── schema/        # Universal Schema (Pydantic models)
├── core/          # Engine (serializer, encryption, diff, migration, portability)
├── adapters/      # Framework adapters (10: LangGraph, MCP, CrewAI, AutoGen, DSPy, LlamaIndex, OpenAI Agents, Haystack, Letta, Semantic Kernel)
├── mcp_server/    # MCP Server implementation
└── compliance/    # UCE scanners
```

## License

[Apache 2.0](LICENSE) — use it, modify it, ship it. Patent shield included.

---

<p align="center">
  <strong>🧶 StateWeave</strong> — Because your agent's memories shouldn't be locked to one framework.
</p>
