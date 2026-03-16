# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.2] — 2026-03-15

### Fixed

- **`stateweave generate-adapter` crash** — Template had unescaped Python expression inside `str.format()`, causing `KeyError` on every invocation
- **Dead `stateweave.dev` URLs** — Domain does not resolve; replaced with `stateweave.pantollventures.com` in migration reports, registry client, SECURITY.md, and CODE_OF_CONDUCT.md
- **Better error messages** — `_require_framework()` helper gives clear `pip install` instructions when a framework dependency is missing
- **Pytest markers** — Added `slow`, `integration`, `requires_framework` markers to `pyproject.toml` for better test organization

### Removed

- **Internal audit docs** — Removed `breakdown/` directory from git tracking (was committed before `.gitignore` rule)

---

## [0.3.1] — 2026-03-13

### Changed

- **New positioning**: `git` for agent brains — updated across README, docs, pyproject.toml, CLI, Dockerfile, llms.txt, stateweave.json, website, and all content
- **README quickstart**: Export code example is now fully self-contained and copy-paste-runnable (no undefined variables)
- **Stale numbers fixed**: Test count updated to 440+ (was variously 254/315/370/415), CLI command count corrected to 14 (was 13)
- **HN title**: Shortened to 43 chars (from 82) per launch playbook research

---

## [0.3.0] — 2026-03-13

### Added

- **Adapter Tiering** — `AdapterTier` enum (TIER_1, TIER_2, COMMUNITY) classifies all 10 adapters by stability guarantee. Tier 1: LangGraph, MCP, CrewAI, AutoGen. Tier 2: DSPy, OpenAI Agents. Community: Haystack, Letta, LlamaIndex, Semantic Kernel.
- **Payload Signing (Ed25519)** — Digital signatures for sender verification. New `sign()`, `verify()`, and `generate_signing_keypair()` static methods on `EncryptionFacade`.
- **Schema: PayloadSignature** — New `PayloadSignature` model and optional `signature` field on `StateWeavePayload` (schema v0.2.0, additive).
- **Delta State Transport** — `stateweave/core/delta.py` enables sending only state differences instead of full payloads. `create_delta()` and `apply_delta()` with hash verification.
- **State Merge Engine (CRDT Foundation)** — `stateweave/core/merge.py` with `merge_payloads()` and three conflict resolution policies: Last-Writer-Wins, Union, Manual.
- **Agent Time Travel** — `stateweave/core/timetravel.py` with `CheckpointStore` for versioning, rollback, branching, diffing. Content-addressable storage (SHA-256), parent hash chains, delta compression.
- **A2A Bridge** — `stateweave/a2a/bridge.py` integrates StateWeave as the state layer for Google's Agent2Agent protocol. TaskArtifact adapter, AgentCard capabilities, handoff tasks.
- **Auto-Detection + Live Connectors** — `stateweave/core/environment.py` scans installed frameworks and auto-selects the best adapter.
- **`stateweave doctor`** — Diagnostic health checks (Python, version, frameworks, checkpoint store, encryption, serialization safety, dependencies).
- **Auto-Checkpoint Middleware** — `stateweave/middleware/auto_checkpoint.py` with `CheckpointMiddleware` class and `@auto_checkpoint` decorator for invisible state versioning.
- **GitHub Action** — `action.yml` composite action for CI validation of `.stateweave.json` files and PR diff generation.
- **create-stateweave-agent** — `stateweave/templates/create_agent.py` scaffolds new agent projects with StateWeave pre-wired.
- **Interactive Playground** — `stateweave/playground/api.py` REST API (translate, diff, checkpoint, validate, doctor, info) with self-contained dark-theme UI.
- **Schema Registry** — `stateweave/registry/client.py` local-first registry for publishing, discovering, and reusing StateWeave payload schemas with text + tag search.
- **VS Code Extension** — `vscode-extension/` with 5 commands (validate, diff, doctor, generate-adapter, preview), status bar, and payload preview dashboard.
- **TypeScript SDK** — `sdk/typescript/src/index.ts` with full Universal Schema type definitions, `StateWeaveSerializer`, `diffPayloads()`, `createPayload()`, and `StateWeaveAdapter` interface.
- **CLI**: 14 commands total (added `scan`, `checkpoint`, `history`, `rollback`, `doctor`)
- **127 new tests** — total 440+ (up from 315)

### Changed

- Schema version bumped from `0.1.0` to `0.2.0` (additive `signature` field)
- Package version bumped to `0.3.0`
- DSPy adapter: `_get_module_state()` now supports pre-populated `_agents` dict fallback
- OpenAI Agents adapter: `_extract_state()` now supports pre-populated `_agents` dict fallback
- MANIFEST.md: 27 registered files (up from 17)

---

## [0.2.0] — 2026-03-13

### Added

- **6 new framework adapters** — DSPy, LlamaIndex, OpenAI Agents, Haystack, Letta / MemGPT, Semantic Kernel (total: 10)
- **Framework auto-detection** — `stateweave detect` identifies source framework via fingerprinting
- **Adapter scaffold generator** — `stateweave generate-adapter <name>` creates adapter files from template
- **Shareable migration reports** — HTML, Markdown, JSON reports with fidelity scores and audit trails
- **`ADAPTER_REGISTRY`** — centralized adapter management for CLI and programmatic access
- **3 new CLI commands** — `stateweave detect`, `stateweave adapters`, `stateweave generate-adapter`
- **74 new tests** — total 254 (up from 180), covering all new adapters and core modules

### Changed

- CLI now uses `ADAPTER_REGISTRY` for all adapter operations
- Version command dynamically reports available adapters

### Fixed

- CI badge URL in README pointed to wrong GitHub org
- GitHub API URL in website pointed to `stateweave/stateweave` instead of `GDWN-BLDR/stateweave`
- `ci.yml` now triggers on `v*` tags (publish job was not triggering)
- UCE scan `continue-on-error` in CI to prevent blocking on unregistered new files
- Dynamic version assertion in `test_cli.py` (was hardcoded `0.1.0`)

## [0.1.0] — 2026-03-13

### Added

- **Universal Schema v1** — `StateWeavePayload` with `CognitiveState` (conversation history, working memory, goal tree, tool results, trust parameters, long-term memory, episodic memory)
- **Core engine** — `StateWeaveSerializer` (LangGraph `SerializerProtocol` compatible), `EncryptionFacade` (AES-256-GCM + PBKDF2), `StateDiff` engine, `MigrationEngine`, `PortabilityAnalyzer`
- **4 framework adapters** — LangGraph, MCP, CrewAI, AutoGen
- **MCP Server** — `python -m stateweave.mcp_server` with 3 tools (`export_agent_state`, `import_agent_state`, `diff_agent_states`), 3 resources, 2 prompt templates
- **UCE compliance engine** — 10 scanners enforcing 8 Unification Laws
- **Board governance** — 6-persona review framework with audit ledger
- **168 tests** — unit, integration (including 4-framework roundtrip), and property-based
- **CLI** — `stateweave export`, `stateweave import`, `stateweave diff`, `stateweave version`
- **CI/CD** — GitHub Actions for test matrix (3.10-3.12), UCE compliance, PyPI publish
- **Documentation** — README, GTM playbook, CONTRIBUTING, SECURITY, CODE_OF_CONDUCT
- **Examples** — "Cloud-to-Local Sandbox Escape" demo, quickstart

### Security

- AES-256-GCM authenticated encryption with per-operation nonces
- PBKDF2 key derivation (600K iterations, OWASP recommended)
- Credential stripping: API keys, tokens, passwords flagged as non-portable and stripped during export
- No silent data loss: every non-portable element documented in `non_portable_warnings[]`
