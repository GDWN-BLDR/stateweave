# 📋 STATEWEAVE Board Document Manifest

**Custodian:** CTO (The Engineer)
**Last Updated:** 2026-03-13 (Initial Creation)
**Review Cadence:** Every `/board` session (Step 0.5)

> [!IMPORTANT]
> Every Board member MUST verify their owned documents at each session.
> Documents with `Last Verified` > 7 days are flagged 🟡 YELLOW.
> Documents exceeding `Max Size` must be split or archived immediately.

> [!CAUTION]
> **UCE documents are P0.** If `rules.yaml` or any scanner is stale relative to
> the codebase, the UCE produces false results. UCE docs are the Engineer's
> highest-priority maintenance obligation.

---

## UCE Compliance Documents (P0 — Engineer)

| Document | Path | Owner | Purpose | Max Size | Last Verified |
|----------|------|-------|---------|----------|---------------|
| **UCE Rules Manifesto** | `stateweave/compliance/rules.yaml` | Engineer | ALL compliance rules — the constitution | 8 KB | 2026-03-13 |
| **UCE Runner** | `scripts/uce.py` | Engineer | The compliance binary | 5 KB | 2026-03-13 |
| **Scanner Base** | `stateweave/compliance/scanner_base.py` | Engineer | BaseScanner ABC interface | 3 KB | 2026-03-13 |
| **Scanner Registry** | `stateweave/compliance/registry.py` | Engineer | Auto-discovery + config loader | 3 KB | 2026-03-13 |
| **Schema Integrity Scanner** | `stateweave/compliance/scanners/schema_integrity.py` | Architect / Engineer | Universal Schema validation enforcement | 4 KB | 2026-03-13 |
| **Adapter Contract Scanner** | `stateweave/compliance/scanners/adapter_contract.py` | Architect | Framework adapter ABC compliance | 4 KB | 2026-03-13 |
| **Serialization Safety Scanner** | `stateweave/compliance/scanners/serialization_safety.py` | Guardian | Data loss detection + non-portable warnings | 4 KB | 2026-03-13 |
| **Encryption Compliance Scanner** | `stateweave/compliance/scanners/encryption_compliance.py` | Guardian | AES-256-GCM enforcement | 4 KB | 2026-03-13 |
| **MCP Protocol Scanner** | `stateweave/compliance/scanners/mcp_protocol.py` | Engineer | MCP JSON-RPC compliance | 4 KB | 2026-03-13 |
| **Import Discipline Scanner** | `stateweave/compliance/scanners/import_discipline.py` | Perfectionist | Cross-layer import hygiene | 4 KB | 2026-03-13 |
| **Logger Naming Scanner** | `stateweave/compliance/scanners/logger_naming.py` | Perfectionist | Logger convention enforcement | 3 KB | 2026-03-13 |
| **Test Coverage Gate** | `stateweave/compliance/scanners/test_coverage_gate.py` | Perfectionist | Minimum test coverage enforcement | 3 KB | 2026-03-13 |
| **File Architecture Scanner** | `stateweave/compliance/scanners/file_architecture.py` | Engineer | Orphan file detection | 3 KB | 2026-03-13 |
| **Dependency Cycles Scanner** | `stateweave/compliance/scanners/dependency_cycles.py` | Engineer | Circular dependency detection | 3 KB | 2026-03-13 |

## Schema & Protocol Documents (P0 — Architect)

| Document | Path | Owner | Purpose | Max Size | Last Verified |
|----------|------|-------|---------|----------|---------------|
| **Universal Schema v1** | `stateweave/schema/v1.py` | Architect | Pydantic models for cognitive state schema | 8 KB | 2026-03-13 |
| **Schema Validator** | `stateweave/schema/validator.py` | Architect / Engineer | JSON Schema validation utilities | 4 KB | 2026-03-13 |
| **Schema Versions** | `stateweave/schema/versions.py` | Architect | Version registry + migration | 4 KB | 2026-03-13 |
| **Adapter Base Contract** | `stateweave/adapters/base.py` | Architect | StateWeaveAdapter ABC + AdapterTier enum | 4 KB | 2026-03-13 |
| **LangGraph Adapter** | `stateweave/adapters/langgraph_adapter.py` | Engineer / Architect | LangGraph ↔ Universal Schema (Tier 1) | 8 KB | 2026-03-13 |
| **MCP Adapter** | `stateweave/adapters/mcp_adapter.py` | Engineer / Architect | MCP ↔ Universal Schema (Tier 1) | 8 KB | 2026-03-13 |
| **CrewAI Adapter** | `stateweave/adapters/crewai_adapter.py` | Engineer / Architect | CrewAI ↔ Universal Schema (Tier 1) | 8 KB | 2026-03-13 |
| **AutoGen Adapter** | `stateweave/adapters/autogen_adapter.py` | Engineer / Architect | AutoGen ↔ Universal Schema (Tier 1) | 10 KB | 2026-03-13 |
| **DSPy Adapter** | `stateweave/adapters/dspy_adapter.py` | Engineer | DSPy ↔ Universal Schema (Tier 2) | 10 KB | 2026-03-13 |
| **OpenAI Agents Adapter** | `stateweave/adapters/openai_agents_adapter.py` | Engineer | OpenAI Agents SDK ↔ Universal Schema (Tier 2) | 12 KB | 2026-03-13 |
| **Haystack Adapter** | `stateweave/adapters/haystack_adapter.py` | Community | Haystack ↔ Universal Schema (Community) | 10 KB | 2026-03-13 |
| **Letta Adapter** | `stateweave/adapters/letta_adapter.py` | Community | Letta ↔ Universal Schema (Community) | 10 KB | 2026-03-13 |
| **LlamaIndex Adapter** | `stateweave/adapters/llamaindex_adapter.py` | Community | LlamaIndex ↔ Universal Schema (Community) | 10 KB | 2026-03-13 |
| **Semantic Kernel Adapter** | `stateweave/adapters/semantic_kernel_adapter.py` | Community | Semantic Kernel ↔ Universal Schema (Community) | 10 KB | 2026-03-13 |
| **Serializer** | `stateweave/core/serializer.py` | Engineer | StateWeaveSerializer — central chokepoint | 4 KB | 2026-03-13 |
| **Encryption Facade** | `stateweave/core/encryption.py` | Guardian | AES-256-GCM AEAD encryption + Ed25519 signing | 8 KB | 2026-03-13 |
| **State Diff Engine** | `stateweave/core/diff.py` | Engineer | Structural diff between payloads | 5 KB | 2026-03-13 |
| **Delta Transport** | `stateweave/core/delta.py` | Engineer | Differential state transport (send diffs only) | 8 KB | 2026-03-13 |
| **State Merge Engine** | `stateweave/core/merge.py` | Engineer | CRDT-style conflict resolution for parallel handoffs | 10 KB | 2026-03-13 |
| **Migration Engine** | `stateweave/core/migration.py` | Engineer | Export → validate → encrypt → import pipeline | 6 KB | 2026-03-13 |
| **Portability Analyzer** | `stateweave/core/portability.py` | Guardian | Non-portable state detection | 5 KB | 2026-03-13 |
| **Framework Detector** | `stateweave/core/detect.py` | Engineer | Auto-detect source framework from state blob | 5 KB | 2026-03-13 |
| **Adapter Generator** | `stateweave/core/generator.py` | Engineer | Scaffold generator for new adapters | 5 KB | 2026-03-13 |
| **Migration Reports** | `stateweave/core/reports.py` | Engineer | Migration result report generation | 5 KB | 2026-03-13 |
| **MCP Server** | `stateweave/mcp_server/server.py` | Engineer | MCP server entry point | 8 KB | 2026-03-13 |
| **MCP Server Main** | `stateweave/mcp_server/__main__.py` | Engineer | MCP stdio transport entry | 8 KB | 2026-03-13 |
| **CLI** | `stateweave/cli.py` | Advocate | Command-line interface (export/import/diff/version) | 5 KB | 2026-03-13 |
| **REST API** | `stateweave/rest_api.py` | Engineer | HTTP REST endpoint wrapper for MCP server | 8 KB | 2026-03-13 |
| **Observability** | `stateweave/core/observability.py` | Engineer | Structured logging, metrics, and trace_operation hooks | 8 KB | 2026-03-13 |

## Governance Documents

| Document | Path | Owner | Purpose | Max Size | Last Verified |
|----------|------|-------|---------|----------|---------------|
| **Unification Laws** | `board/governance/UNIFICATION_LAWS.md` | Engineer | The 8 laws + scanner registry | 8 KB | 2026-03-13 |
| **SSOT Charter** | `board/governance/SSOT_CHARTER.md` | Architect | Data sovereignty rules: Universal Schema as the one truth | 8 KB | 2026-03-13 |
| **Board Output Template** | `board/governance/BOARD_OUTPUT_TEMPLATE.md` | Perfectionist | Session output format standard | 5 KB | 2026-03-13 |
| **Audit Ledger** | `board/governance/AUDIT_LEDGER.md` | All Members | Component grades & audit history | 10 KB | 2026-03-13 |

## Intelligence Documents

| Document | Path | Owner | Purpose | Max Size | Last Verified |
|----------|------|-------|---------|----------|---------------|
| **LangGraph Integration** | `board/intelligence/LANGGRAPH_INTEGRATION.md` | Engineer / Architect | LangGraph state internals + adapter wiring | 8 KB | 2026-03-13 |
| **MCP Integration** | `board/intelligence/MCP_INTEGRATION.md` | Engineer / Architect | MCP protocol + JSON-RPC + state mapping | 8 KB | 2026-03-13 |
| **SAMEP Alignment** | `board/intelligence/SAMEP_ALIGNMENT.md` | Architect | SAMEP schema adoption + extensions | 5 KB | 2026-03-13 |
| **Competitive Landscape** | `board/intelligence/COMPETITIVE_LANDSCAPE.md` | Strategist | Market position + competitor tracking | 8 KB | 2026-03-13 |

## Archived Documents

| Document | Path | Reason | Archived |
|----------|------|--------|----------|
| (none yet) | | | |

---

## Document Governance Rules

1. **Ownership is mandatory.** Every document has exactly one owning Board persona (or "All").
2. **Freshness SLA: 7 days.** If `Last Verified` exceeds 7 days, the owner's board review is 🟡 YELLOW.
3. **Size budgets are enforced.** Exceeding `Max Size` triggers mandatory split-or-archive at next session.
4. **No orphan docs.** Any document in `board/` not listed here is unauthorized and must be registered or deleted.
5. **Archive, don't delete.** Stale documents move to `archive/` with a reason, never deleted.
6. **UCE docs are P0.** `rules.yaml` and scanner files are the highest-priority maintenance items. If the UCE produces stale results, all enforcement is compromised.
7. **Schema docs track code.** Universal Schema and adapter contracts must be updated whenever the schema evolves. The `schema_integrity` scanner enforces this.
