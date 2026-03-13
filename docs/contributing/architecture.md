# Architecture

## Layer Model

StateWeave has four strict layers with enforced import boundaries:

```
┌──────────────────────┐
│    MCP Server        │  ← Top layer (can import everything)
├──────────────────────┤
│    Adapters          │  ← Can import core + schema
├──────────────────────┤
│    Core              │  ← Can import schema only
├──────────────────────┤
│    Schema            │  ← Foundation, imports nothing
└──────────────────────┘
```

The `import_discipline` UCE scanner enforces these boundaries.

## Core Modules

| Module | Responsibility |
|--------|---------------|
| `serializer.py` | Single chokepoint for all serialization (LAW 3) |
| `encryption.py` | AES-256-GCM + Ed25519 signing (LAW 5) |
| `migration.py` | Export/import orchestration with audit trail |
| `diff.py` | Structural diff between payloads |
| `delta.py` | Delta state transport |
| `merge.py` | CRDT-style conflict resolution |
| `portability.py` | Non-portable state detection |

## Governance

The `board/` directory contains governance documents:

- `MANIFEST.md` — all registered files
- `governance/SSOT_CHARTER.md` — single source of truth rules
- `governance/UNIFICATION_LAWS.md` — 8 architectural laws
- `governance/BOARD_OUTPUT_TEMPLATE.md` — review session format
