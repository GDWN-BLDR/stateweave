# ARTICLE X — THE 8 UNIFICATION LAWS (v1.0)

> [!CAUTION]
> These laws were ratified on 2026-03-13 at StateWeave's founding to establish
> architectural discipline from day one. Violations of any law with a BLOCK scanner
> result in deployment rejection via the Universal Compliance Engine (UCE).

> [!IMPORTANT]
> **v1.0 (2026-03-13):** Initial ratification. 8 laws, 10 scanners. UCE at **10 scanners**.

---

## Law 1: ONE Logger Convention
**Standard:** `logging.getLogger("stateweave.{layer}.{component}")`

| Layer | Example Components |
|-------|-------------------|
| `stateweave.schema` | `v1`, `validator`, `versions` |
| `stateweave.core` | `serializer`, `encryption`, `diff`, `migration`, `portability` |
| `stateweave.adapters` | `langgraph`, `mcp`, `crewai`, `autogen` |
| `stateweave.mcp_server` | `server`, `tools`, `resources` |
| `stateweave.compliance` | `registry`, `scanner_base` |

**Enforcement:** UCE scanner `logger_naming`. Mode: **BLOCK** on new violations.
**Owner:** The Perfectionist (CQO)

## Law 2: ONE Schema Version
**Standard:** ALL state payloads MUST conform to the Universal Schema specification (`stateweave/schema/v1.py`). Every `StateWeavePayload` MUST include a valid `stateweave_version` string. Schema versions are immutable — new versions are additive, never destructive.

**Enforcement:** UCE scanner `schema_integrity`. Mode: **BLOCK**.
**Owner:** The Architect

## Law 3: ONE Serialization Path
**Standard:** All cognitive state serialization and deserialization MUST transit through the `StateWeaveSerializer` class. No side-channel serialization via raw `json.dumps()`, `pickle`, `msgpack`, or any other serializer in production code paths. The serializer is the single chokepoint for all state I/O.

**Exemptions:** Test fixtures may use `json.dumps()` for constructing test payloads.

**Enforcement:** UCE scanner `serialization_safety`. Mode: **BLOCK**.
**Owner:** The Guardian / The Engineer

## Law 4: ONE Adapter Contract
**Standard:** Every framework adapter MUST extend the `StateWeaveAdapter` ABC and implement all required methods:
- `framework_name` property → `str`
- `export_state(agent_id, **kwargs)` → `StateWeavePayload`
- `import_state(payload, **kwargs)` → framework-native agent reference
- `list_agents()` → `List[AgentInfo]`

No adapter may bypass the ABC contract. Custom adapters from external contributors MUST also conform.

| Archetype | Base Class | Entry Points | Returns |
|-----------|-----------|-------------|---------|
| **Adapter** | `StateWeaveAdapter` | `export_state()`, `import_state()`, `list_agents()` | `StateWeavePayload` / agent ref |
| **Scanner** | `BaseScanner` | `scan(config, project_root)` | `ScanResult` |

**Enforcement:** UCE scanner `adapter_contract`. Mode: **BLOCK**.
**Owner:** The Architect

## Law 5: ONE Encryption & Signing Path
**Standard:** All sensitive state transiting any boundary (network, disk, inter-process) MUST be encrypted via AES-256-GCM through the `EncryptionFacade` (`stateweave/core/encryption.py`). No raw `cryptography` calls, no custom encryption implementations, no unencrypted state in transit.

All payload signing MUST use Ed25519 through `EncryptionFacade.sign()` and `EncryptionFacade.verify()`. No direct use of `cryptography.hazmat` signing primitives outside the facade.

The facade provides:
- AES-256-GCM authenticated encryption with associated data (AEAD)
- Unique nonce per encryption operation
- Key derivation from user-supplied passphrase (PBKDF2)
- Key rotation support via versioned key IDs
- Ed25519 digital signatures for payload authenticity verification
- Signing key pair generation via `generate_signing_keypair()`

**Enforcement:** UCE scanner `encryption_compliance`. Mode: **BLOCK**.
**Owner:** The Guardian

## Law 6: ONE Exception Pattern
**Standard:** All `except` blocks must:
1. Use typed exceptions (`except ValueError`, `except SerializationError`) — NEVER bare `except:`
2. Log with structured messages including context (`framework`, `agent_id`, `operation`)
3. Include `exc_info=True` for unexpected failures
4. Raise `StateWeaveError` subclasses for all domain errors

**Enforcement:** UCE scanner `import_discipline` (sub-check: exception patterns). Mode: **BLOCK**.
**Owner:** The Perfectionist (CQO)

## Law 7: ONE Import Discipline
**Standard:** Strict layering. No circular imports. No cross-layer imports that violate the dependency graph:

```
stateweave.schema  ← (no imports from other stateweave modules)
     ↑
stateweave.core    ← (may import schema only)
     ↑
stateweave.adapters ← (may import schema + core)
     ↑
stateweave.mcp_server ← (may import schema + core + adapters)
```

**Forbidden:** Adapters importing core internals (private functions/classes). Core importing from adapters. Schema importing from anything.

**Enforcement:** UCE scanner `import_discipline`. Mode: **BLOCK**.
**Owner:** The Engineer

## Law 8: ONE Test Discipline
**Standard:** Every public function and class MUST have at least one unit test. Adapters MUST have integration tests demonstrating round-trip state migration. No untested code reaches the `main` branch.

**Coverage requirements:**
- Minimum 80% line coverage on `stateweave/schema/`
- Minimum 80% line coverage on `stateweave/core/`
- Minimum 70% line coverage on `stateweave/adapters/`
- All UCE scanners must have test coverage

**Enforcement:** UCE scanner `test_coverage_gate`. Mode: **BLOCK**.
**Owner:** The Perfectionist (CQO)

---

## UCE SCANNER REGISTRY

All scanners live as plugins in `stateweave/compliance/scanners/`. Configuration in `stateweave/compliance/rules.yaml`. Run:
```bash
python scripts/uce.py
```

| Scanner | File | Law | Owner | Mode | Added |
|---------|------|-----|-------|------|-------|
| `schema_integrity` | `schema_integrity.py` | 2 | Architect / Engineer | BLOCK | 2026-03-13 |
| `adapter_contract` | `adapter_contract.py` | 4 | Architect | BLOCK | 2026-03-13 |
| `serialization_safety` | `serialization_safety.py` | 3 | Guardian | BLOCK | 2026-03-13 |
| `encryption_compliance` | `encryption_compliance.py` | 5 | Guardian | BLOCK | 2026-03-13 |
| `mcp_protocol` | `mcp_protocol.py` | — | Engineer | BLOCK | 2026-03-13 |
| `import_discipline` | `import_discipline.py` | 7 | Perfectionist / Engineer | BLOCK | 2026-03-13 |
| `logger_naming` | `logger_naming.py` | 1 | Perfectionist | BLOCK | 2026-03-13 |
| `test_coverage_gate` | `test_coverage_gate.py` | 8 | Perfectionist | BLOCK | 2026-03-13 |
| `file_architecture` | `file_architecture.py` | — | Engineer | WARN | 2026-03-13 |
| `dependency_cycles` | `dependency_cycles.py` | — | Engineer | BLOCK | 2026-03-13 |

### Scanner Addition Protocol
New scanners require:
1. Board vote with majority approval
2. Plugin file in `stateweave/compliance/scanners/`
3. Configuration block in `stateweave/compliance/rules.yaml`
4. Entry in this registry table
5. Corresponding Veto Condition added to the owning Board member
