# Core Concepts

## The Problem

Every AI agent framework stores state differently. LangGraph uses checkpointers, CrewAI uses crew memory, AutoGen stores chat_messages dicts. When you switch frameworks, all accumulated knowledge is lost.

## Universal Schema

StateWeave solves this with a **Universal Schema** — a canonical Pydantic model (`StateWeavePayload`) that represents everything an agent knows:

| Field | What It Stores |
|-------|---------------|
| `conversation_history` | Full message thread (human, AI, system, tool) |
| `working_memory` | Current task state, key-value pairs |
| `goal_tree` | Active goals, sub-goals, completion status |
| `tool_results_cache` | Cached tool outputs (search results, API responses) |
| `trust_parameters` | Confidence scores, reliability metrics |
| `long_term_memory` | Persistent knowledge across sessions |
| `episodic_memory` | Past experiences and learned outcomes |

## Star Topology

StateWeave uses a **star topology** — every framework translates to and from the Universal Schema. This means:

- **N adapters, not N² translations.** Adding framework N costs 1 adapter and gives N-1 migration paths.
- **New adapters are instant.** Subclass `StateWeaveAdapter`, implement 4 methods, done.

## Adapter Tiers

| Tier | Meaning | Frameworks |
|------|---------|-----------|
| 🟢 Tier 1 | Core team maintained, guaranteed stability | LangGraph, MCP, CrewAI, AutoGen |
| 🟡 Tier 2 | Actively maintained, patches may lag | DSPy, OpenAI Agents |
| 🔵 Community | Best-effort, community contributed | Haystack, Letta, LlamaIndex, Semantic Kernel |

## Non-Portable State

Not everything transfers. Database cursors, live connections, credentials, and framework-specific internals are stripped during export and documented in `non_portable_warnings[]` with severity, reason, and remediation guidance.

**StateWeave never silently drops data.** Every non-portable element is explicitly flagged.

## Encryption

All state can be encrypted with AES-256-GCM via `EncryptionFacade`. Payloads can also be signed with Ed25519 for sender verification.
