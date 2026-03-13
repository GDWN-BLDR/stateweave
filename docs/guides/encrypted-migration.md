# Encrypted Migration

Encrypt agent state during transport using AES-256-GCM authenticated encryption.

## Basic Encrypted Migration

```python
from stateweave import EncryptionFacade, MigrationEngine, LangGraphAdapter, MCPAdapter

# Generate a key (or derive from passphrase)
key = EncryptionFacade.generate_key()
engine = MigrationEngine(encryption=EncryptionFacade(key))

# Export with encryption
source = LangGraphAdapter()
result = engine.export_state(source, agent_id="my-agent", encrypt=True)

# Transport result.encrypted_data + result.nonce safely...

# Decrypt and import on the other side
target = MCPAdapter()
engine.import_state(target, encrypted_data=result.encrypted_data, nonce=result.nonce)
```

## From Passphrase

```python
facade = EncryptionFacade.from_passphrase("my-secret-passphrase")
# Uses PBKDF2-SHA256 with 600K iterations (OWASP recommended)
```

## Associated Data (AAD)

Bind ciphertext to specific agent metadata:

```python
aad = b"agent-id:my-agent"
ciphertext, nonce = facade.encrypt(payload_bytes, associated_data=aad)
plaintext = facade.decrypt(ciphertext, nonce, associated_data=aad)
```

## Payload Signing

Verify sender identity with Ed25519:

```python
private_key, public_key = EncryptionFacade.generate_signing_keypair()
signature = EncryptionFacade.sign(payload_bytes, private_key)
is_authentic = EncryptionFacade.verify(payload_bytes, signature, public_key)
```

## Security Properties

| Property | Implementation |
|----------|---------------|
| Confidentiality | AES-256-GCM (256-bit keys) |
| Integrity | GCM authentication tag |
| Key derivation | PBKDF2-SHA256, 600K iterations |
| Sender identity | Ed25519 digital signatures |
| Unique nonce | 96-bit random per operation |
