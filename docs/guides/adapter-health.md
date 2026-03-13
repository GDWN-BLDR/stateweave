# Adapter Health & Compatibility

StateWeave tests every adapter against multiple framework versions to catch breakage early.

## Compatibility Matrix

| Adapter | Framework | Pinned Version | Latest | Tier |
|---------|-----------|:--------------:|:------:|------|
| `LangGraphAdapter` | langgraph | `0.2.0` ✅ | CI tracked | 🟢 Tier 1 |
| `MCPAdapter` | mcp | `1.0.0` ✅ | CI tracked | 🟢 Tier 1 |
| `CrewAIAdapter` | crewai | `0.70` ✅ | CI tracked | 🟢 Tier 1 |
| `AutoGenAdapter` | pyautogen | `0.4` ✅ | CI tracked | 🟢 Tier 1 |
| `DSPyAdapter` | dspy | — | Unit tests | 🟡 Tier 2 |
| `OpenAIAgentsAdapter` | openai-agents | — | Unit tests | 🟡 Tier 2 |
| `LlamaIndexAdapter` | llamaindex | — | Unit tests | 🔵 Community |
| `HaystackAdapter` | haystack | — | Unit tests | 🔵 Community |
| `LettaAdapter` | letta | — | Unit tests | 🔵 Community |
| `SemanticKernelAdapter` | semantic-kernel | — | Unit tests | 🔵 Community |

## How It Works

The [adapter-matrix.yml](/.github/workflows/adapter-matrix.yml) CI workflow:

1. **Tier 1 adapters** run against both pinned (known-good) and `latest` framework versions
2. **Pinned failures** block merges — these are regressions in StateWeave
3. **Latest failures** are non-blocking — they indicate upstream framework breakage
4. **Tier 2** adapters run unit tests on every push
5. **Community** adapters run best-effort (continue-on-error)

The matrix runs:
- On every push to `main` that touches adapters
- Weekly on Monday mornings (catches upstream breakage)
- On manual trigger via `workflow_dispatch`

## Reporting Adapter Breakage

If you discover an adapter doesn't work with a new framework version:

1. Open an issue with the title: `[Adapter] <framework> v<X.Y.Z> breakage`
2. Include the error traceback and the framework version
3. Tier 1 adapters will be patched within 48 hours
4. Tier 2 patches may lag behind framework releases
5. Community adapters are best-effort

## Supported Version Ranges

| Adapter | Minimum Version | Maximum Tested |
|---------|:--------------:|:--------------:|
| LangGraph | `0.2.0` | `latest` |
| MCP | `1.0.0` | `latest` |
| CrewAI | `0.70` | `latest` |
| AutoGen | `0.4` | `latest` |
| DSPy | `2.0` | `latest` |
| OpenAI Agents | `1.0` | `latest` |

## Building a New Adapter

See the [Building an Adapter](building-adapter.md) guide. New adapters should:

1. Extend `StateWeaveAdapter` ABC
2. Include a `tier` property (start as Community)
3. Have comprehensive unit tests
4. Be added to the adapter-matrix CI workflow
