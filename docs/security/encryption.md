# Encryption

AES-256-GCM authenticated encryption for agent state payloads.

## Quick Start

```python
from stateweave import EncryptionFacade

key = EncryptionFacade.generate_key()
facade = EncryptionFacade(key)

ciphertext, nonce = facade.encrypt(plaintext_bytes)
decrypted = facade.decrypt(ciphertext, nonce)
```

## From Passphrase

```python
facade = EncryptionFacade.from_passphrase("my-secret-passphrase")
```

Uses PBKDF2-SHA256 with 600,000 iterations (OWASP recommendation for 2025+).

## Associated Data (AAD)

Bind ciphertext to metadata so it can't be replayed against a different agent:

```python
aad = f"agent:{agent_id}".encode()
ciphertext, nonce = facade.encrypt(data, associated_data=aad)
# Decryption fails if AAD doesn't match
```

## Base64 Transport

For JSON-safe encoding:

```python
b64_ct, b64_nonce = facade.encrypt_b64(data)
plaintext = facade.decrypt_b64(b64_ct, b64_nonce)
```

## Full Migration Pipeline

```python
from stateweave import MigrationEngine, EncryptionFacade

engine = MigrationEngine(encryption=EncryptionFacade(key))
result = engine.export_state(adapter, "agent-id", encrypt=True)
engine.import_state(target_adapter, encrypted_data=result.encrypted_data, nonce=result.nonce)
```

For more details, see the [Encryption API reference](../api/encryption.md).
