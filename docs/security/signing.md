# Payload Signing

Ed25519 digital signatures verify who created a payload and detect tampering.

## Generate Key Pair

```python
from stateweave import EncryptionFacade

private_key, public_key = EncryptionFacade.generate_signing_keypair()
# Both are 32-byte raw keys
```

## Sign a Payload

```python
from stateweave import StateWeaveSerializer

serializer = StateWeaveSerializer()
payload_bytes = serializer.dumps(payload)

signature = EncryptionFacade.sign(payload_bytes, private_key)
# Returns a base64-encoded string
```

## Verify on Receipt

```python
is_authentic = EncryptionFacade.verify(payload_bytes, signature, public_key)

if not is_authentic:
    raise ValueError("Payload signature invalid — possible tampering!")
```

## Schema Support

The `PayloadSignature` model can be attached to the payload:

```python
from stateweave.schema.v1 import PayloadSignature

payload.signature = PayloadSignature(
    algorithm="ed25519",
    public_key_id="key-id-here",
    signature_b64=signature,
)
```

## Key Management

Store private keys securely (e.g., environment variables, secrets manager). Distribute public keys to receivers via out-of-band channels.
