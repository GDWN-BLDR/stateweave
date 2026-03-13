# 📜 SSOT Charter: The Universal Schema Is the Single Source of Truth

**Effective Date:** 2026-03-13
**Custodian:** 👔 THE ARCHITECT
**Review Cadence:** Weekly (every `/board` session)
**Last Audit:** 2026-03-13 — ✅ INITIAL RATIFICATION

---

## 🎯 Mandate

> **All cognitive state transiting between frameworks MUST flow through the Universal Schema.**

The Universal Schema (`stateweave/schema/v1.py`) is the **SOLE CANONICAL REPRESENTATION** of agent cognitive state. All adapters translate TO and FROM the Universal Schema. No adapter may translate directly between two frameworks, bypassing the canonical format.

---

## 📐 Architecture

```
LangGraph Agent                    MCP Agent                     CrewAI Agent
     │                                │                               │
     ▼                                ▼                               ▼
┌─────────────┐              ┌─────────────┐              ┌─────────────┐
│  LangGraph  │              │    MCP      │              │   CrewAI    │
│   Adapter   │              │   Adapter   │              │   Adapter   │
└──────┬──────┘              └──────┬──────┘              └──────┬──────┘
       │                            │                            │
       ▼                            ▼                            ▼
═══════════════════════════════════════════════════════════════════════════
                    UNIVERSAL SCHEMA (StateWeavePayload)
                    The Single Source of Truth
═══════════════════════════════════════════════════════════════════════════
       │                            │                            │
       ▼                            ▼                            ▼
  Encryption                  State Diff                   Portability
   Facade                      Engine                      Analyzer
```

### The Star Topology Rule

All translations follow a **star topology** with the Universal Schema at the center:

```
LangGraph  ←→  Universal Schema  ←→  MCP
                     ↕
                   CrewAI
                     ↕
                  AutoGen
```

**Never:**
```
LangGraph  ←→  MCP     ❌ (no direct translation)
CrewAI     ←→  AutoGen  ❌ (no direct translation)
```

This star topology means adding framework N requires exactly 1 new adapter, not N-1 adapters.

---

## 🔒 Non-Portable State Policy

Not all state can transfer between frameworks. The SSOT Charter requires **explicit declaration** of non-portable elements.

### Known Non-Portable Categories

| Category | Example | Why Non-Portable |
|----------|---------|-----------------|
| **Database Cursors** | SQLite cursor positions | Framework-specific DB connections |
| **Framework Ephemera** | LangGraph channel metadata, internal version counters | Implementation details, not cognitive state |
| **Custom Python Objects** | Unpicklable class instances | Require the original class definition |
| **Live Connections** | WebSocket handles, HTTP sessions | Cannot serialize network state |
| **Execution State** | Thread IDs, asyncio task references | OS/runtime specific |

### Non-Portable Warning Contract

Every adapter's `export_state()` MUST populate `non_portable_warnings[]` in the payload:

```python
{
    "non_portable_warnings": [
        {
            "field": "cognitive_state.working_memory.db_cursor",
            "reason": "SQLite cursor cannot be serialized across processes",
            "severity": "WARN",
            "data_loss": true,
            "recommendation": "Re-initialize cursor after import"
        }
    ]
}
```

---

## 🛡️ Enforcement Protocol

### Schema Validation Gate

Every state payload MUST pass JSON Schema validation before:
1. Export (adapter → Universal Schema)
2. Encryption (Universal Schema → encrypted payload)
3. Transport (encrypted payload → network/disk)
4. Import (Universal Schema → target adapter)

### UCE Enforcement

The `schema_integrity` scanner verifies:
- All Pydantic models match the published JSON Schema
- No undocumented fields in production payloads
- Version strings are valid semver
- Required fields are never null

### Architect Review (Board Session)

| Violation | Response |
|-----------|----------|
| Direct framework-to-framework translation | **HARD BLOCK** — Must route through Universal Schema |
| Undocumented non-portable state | **HARD BLOCK** — Must add to `non_portable_warnings[]` |
| Schema field added without version bump | **HARD BLOCK** — Schema versions are immutable |
| Breaking change to existing schema version | **IMMEDIATE RED LIGHT** — Trading halts equivalent |

### Veto Condition: "The Babel Tower"

> If any adapter translates directly between two frameworks without passing through the Universal Schema, the Architect issues an **IMMEDIATE RED LIGHT** and the adapter is disabled until remediation.

---

## 📊 Why SSOT Matters

### Problems Solved

| Issue | Without SSOT | With SSOT |
|-------|-------------|-----------|
| **Adapter Explosion** | N frameworks = N*(N-1) adapters | N frameworks = N adapters (star topology) |
| **Schema Drift** | Each adapter pair has its own format | One canonical schema, validated everywhere |
| **Data Loss** | Silent data loss during translation | Explicit `non_portable_warnings[]` |
| **Security** | Each path needs its own encryption | One encryption chokepoint via `EncryptionFacade` |
| **Testing** | Test every pair combination | Test each adapter against Universal Schema |
| **Versioning** | N*(N-1) version matrices | One schema version, all adapters target it |

---

## 📋 Compliance Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Direct framework-to-framework translations | **0** | ✅ 0 |
| Adapters conforming to ABC | **100%** | ✅ 100% |
| Non-portable warnings coverage | **100%** | ✅ 100% |
| Last SSOT audit | < 7 days | ✅ 2026-03-13 |

---

## 📝 Schema Evolution Process

To propose a schema change:

1. **Propose** in Board session with technical justification
2. **Architect Review** — Evaluate backward compatibility
3. **Board Vote** — Requires majority consent (Architect has veto)
4. **Implement** — New version in `stateweave/schema/vN.py`
5. **Migrate** — Schema migration function in `stateweave/schema/versions.py`
6. **Verify** — UCE `schema_integrity` scanner updated and passing

---

## 🏛️ Charter Signatories

**Approved By:**
👔 Architect | 🛡️ Guardian | ⚙️ Engineer | 📣 Advocate | 🎯 Strategist | 🧹 Perfectionist

*Unanimous consent recorded 2026-03-13*
