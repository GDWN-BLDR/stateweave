# StateWeave Documentation

**`git` for agent brains.** When your agent goes wrong, see exactly where and why. Then rewind.

StateWeave debugs, time-travels, and migrates AI agent state across 10 frameworks. Export from LangGraph, import into MCP, CrewAI, AutoGen, DSPy, or any of 10 supported frameworks — with zero silent data loss.

## Quick Links

- **[Installation](getting-started/installation.md)** — `pip install stateweave` and first migration in 60 seconds
- **[Quickstart](getting-started/quickstart.md)** — Export, import, encrypt, diff
- **[API Reference](api/schema.md)** — Universal Schema, adapters, serializer, encryption
- **[Deploy with Docker](guides/docker-deployment.md)** — MCP Server and REST API deployment
- **[Build an Adapter](guides/building-adapter.md)** — Add your framework in one file

## Framework Support

| Framework | Adapter | Tier |
|-----------|---------|------|
| LangGraph | `LangGraphAdapter` | 🟢 Tier 1 |
| MCP | `MCPAdapter` | 🟢 Tier 1 |
| CrewAI | `CrewAIAdapter` | 🟢 Tier 1 |
| AutoGen | `AutoGenAdapter` | 🟢 Tier 1 |
| DSPy | `DSPyAdapter` | 🟡 Tier 2 |
| OpenAI Agents | `OpenAIAgentsAdapter` | 🟡 Tier 2 |
| LlamaIndex | `LlamaIndexAdapter` | 🔵 Community |
| Haystack | `HaystackAdapter` | 🔵 Community |
| Letta / MemGPT | `LettaAdapter` | 🔵 Community |
| Semantic Kernel | `SemanticKernelAdapter` | 🔵 Community |

## Architecture

StateWeave uses a **star topology**: every framework translates to one Universal Schema. Adding a framework = one adapter, instant compatibility with everything else.

```
LangGraph ─┐                  ┌─ MCP
CrewAI ────┤                  ├─ DSPy
AutoGen ───┼── Universal ─────┼─ OpenAI Agents
Haystack ──┤    Schema        ├─ LlamaIndex
Letta ─────┘                  └─ Semantic Kernel
```
