# Security Overview

StateWeave implements defense-in-depth for agent state security.

## Threat Model

| Threat | Mitigation |
|--------|-----------|
| State interception in transit | AES-256-GCM authenticated encryption |
| State tampering | GCM authentication tag + Ed25519 signatures |
| Credential leakage | `PortabilityAnalyzer` strips credentials and emits CRITICAL warnings |
| Weak key derivation | PBKDF2-SHA256 with 600K iterations (OWASP recommended) |
| Deserialization attacks | JSON + Pydantic only — no pickle, no eval, no exec |
| Replay attacks | Unique 96-bit nonce per encryption operation |

## Architecture

- **No pickle.** StateWeave uses JSON + Pydantic exclusively. The `serialization_safety` UCE scanner blocks any introduction of pickle, msgpack, or raw json.dumps.
- **Single facade.** All cryptographic operations go through `EncryptionFacade`. The `encryption_compliance` UCE scanner enforces this.
- **Explicit data loss.** Every non-portable element is documented in `non_portable_warnings[]` with severity, reason, and remediation.

## Reporting Vulnerabilities

See [SECURITY.md](https://github.com/GDWN-BLDR/stateweave/blob/main/SECURITY.md) for responsible disclosure.
