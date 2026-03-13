# Encryption

`EncryptionFacade` provides AES-256-GCM authenticated encryption and Ed25519 signing.

## Initialization

```python
from stateweave import EncryptionFacade

# From raw key
key = EncryptionFacade.generate_key()  # 32 random bytes
facade = EncryptionFacade(key)

# From passphrase (PBKDF2-SHA256, 600K iterations)
facade = EncryptionFacade.from_passphrase("my-secret")
```

## Encrypt / Decrypt

```python
ciphertext, nonce = facade.encrypt(plaintext_bytes)
plaintext = facade.decrypt(ciphertext, nonce)

# With associated data (AAD)
ciphertext, nonce = facade.encrypt(data, associated_data=b"agent-id:123")
plaintext = facade.decrypt(ciphertext, nonce, associated_data=b"agent-id:123")

# Base64-encoded (JSON-safe)
b64_ct, b64_nonce = facade.encrypt_b64(data)
plaintext = facade.decrypt_b64(b64_ct, b64_nonce)
```

## Ed25519 Signing

```python
private_key, public_key = EncryptionFacade.generate_signing_keypair()
signature = EncryptionFacade.sign(data, private_key)       # → base64 string
is_valid = EncryptionFacade.verify(data, signature, public_key)  # → bool
```

## Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `KEY_SIZE` | 32 | AES-256 key (256 bits) |
| `NONCE_SIZE` | 12 | GCM nonce (96 bits) |
| `SALT_SIZE` | 16 | PBKDF2 salt (128 bits) |
| `ITERATIONS` | 600,000 | PBKDF2 iterations (OWASP) |
