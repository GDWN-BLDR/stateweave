# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.3.x   | ✅        |
| 0.2.x   | ✅        |
| 0.1.x   | ✅        |

## Reporting a Vulnerability

If you discover a security vulnerability in StateWeave, **please do NOT open a public issue.**

Instead, please report it privately:

1. **Email**: security@stateweave.dev
2. **Subject**: `[SECURITY] Brief description of vulnerability`
3. **Include**:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We will acknowledge receipt within **48 hours** and provide a detailed response within **7 days**.

## Security Design

### Encryption
- **Algorithm**: AES-256-GCM (authenticated encryption with associated data)
- **Key Derivation**: PBKDF2-HMAC-SHA256 with 600,000 iterations (OWASP 2024 recommendation)
- **Nonce**: Unique 12-byte nonce generated per encryption operation (never reused)
- **Associated Data**: Optional metadata binding to prevent ciphertext transplant attacks

### Data Handling
- **Credential Stripping**: API keys, tokens, passwords, and secrets are automatically detected and stripped during export. These appear in `non_portable_warnings[]` with severity `CRITICAL`.
- **No Silent Data Loss**: Every non-portable element is explicitly documented. The `PortabilityAnalyzer` scans for sensitive patterns including: `api_key`, `secret`, `password`, `token`, `credential`, `auth`, `private_key`.
- **No Pickle**: StateWeave never uses Python pickle for serialization. All data transits as validated JSON through the `StateWeaveSerializer`.

### Architecture
- **Single Serialization Path** (Law 3): All data flows through `StateWeaveSerializer`. No side-channel serialization is permitted.
- **Single Encryption Path** (Law 5): All encryption and signing goes through `EncryptionFacade`. No direct use of cryptographic primitives elsewhere.
- **Import Discipline** (Law 7): Adapters cannot import core internals. This prevents accidental security bypass.

### Payload Signing
- **Algorithm**: Ed25519 (elliptic curve digital signatures)
- **Purpose**: Sender identity verification and tamper detection
- **Key Management**: `generate_signing_keypair()` produces 32-byte raw key pairs
- **Signature Format**: Base64-encoded, attached to `PayloadSignature` model on the payload
- **Verification**: `verify(data, signature, public_key)` returns boolean, logs warnings on failure

## Dependency Security

| Dependency | Purpose | Minimum Version |
|------------|---------|-----------------|
| `cryptography` | AES-256-GCM, PBKDF2 | ≥41.0 |
| `pydantic` | Schema validation | ≥2.0 |
| `pyyaml` | UCE rules config | ≥6.0 |

We monitor dependencies via `pip-audit` and Dependabot.
