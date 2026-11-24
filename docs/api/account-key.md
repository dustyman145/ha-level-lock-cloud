# Account signing key

Lock commands must be signed with the account's **secp256k1 private key**. The key is not returned in plain form. It is stored encrypted inside the account response from `GET /v2/account/get` and can only be decrypted with the user's password.

Status: ✅ decryption and signature verification succeeded live on the owner's account.

## Fields used

From the `account` object (see [models.md](models.md)):

| Field | Encoding | Meaning |
|---|---|---|
| `encryptedBlobKeys[]` | array | Wrapped copies of the blob key |
| `encryptedBlobKeys[].name` | string | Use the entry where `name == "password"` (another entry is for the recovery key) |
| `encryptedBlobKeys[].nonce` | 24-char hex, otherwise Base64 | 12-byte nonce |
| `encryptedBlobKeys[].value` | 64-char hex, otherwise Base64 | 32-byte encrypted blob key |
| `blob.nonce` | hex | 12-byte nonce |
| `blob.value` | hex | Encrypted BSON document |
| `blob.sign` | hex | Raw `r‖s` ECDSA signature over the encrypted `blob.value` |

The hex-or-Base64 choice for `encryptedBlobKeys` is made by **string length**, exactly as the app does (`_.td.a`): 24 / 64 characters means hex, anything else is "historical" Base64. `blob.*` is always hex.

## Step 1: derive the blob-password key

Same scheme as the login value, but a **different salt** and **no Base64**:

```python
import hashlib

BLOB_SALT = b"C0771591-BE41-4E22-8C89-D4521D9538B4"

def blob_password_key(password: str) -> bytes:
    value = password.encode("utf-8") + BLOB_SALT
    for _ in range(102):
        value = hashlib.sha256(value).digest()
    return value  # 32 raw bytes
```

## Step 2: unwrap the blob key

Decrypt the `password` entry's `value` with **ChaCha20 (RFC 8439 / "ChaCha7539")**, 256-bit key, 96-bit nonce, initial block counter **0**. Plain ChaCha20 stream cipher, **not** ChaCha20-Poly1305. Result: the 32-byte account blob key.

## Step 3: decrypt the blob

Decrypt `blob.value` with the same cipher, using the blob key and `blob.nonce`. The plaintext is **BSON** (not JSON):

```text
{ privateKey: [32 integers] }
```

Values may be Java signed bytes; normalise with `b & 0xFF`.

## Step 4: load the key

Interpret the 32 bytes as an unsigned **big-endian secp256k1 private scalar**, and derive the public key.

## Step 5: verify the blob

Verify `blob.sign` over the **encrypted** `blob.value` bytes with **ECDSA secp256k1 + SHA-512**, using the derived public key. The signature is raw `r‖s` (two equal halves, no DER). Halves can be shorter than 32 bytes if both integers are short.

## Hash functions differ

| Use | Curve | Hash |
|---|---|---|
| Account blob verification | secp256k1 | **SHA-512** |
| Firmware command signing | secp256k1 | **SHA-256** |

Using SHA-256 for the blob fails verification. This was an early mistake in the investigation.

## Python reference

```python
import bson                      # from pymongo
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms
from cryptography.hazmat.primitives.asymmetric import ec, utils
from cryptography.hazmat.primitives import hashes

def chacha20(key: bytes, nonce: bytes, data: bytes) -> bytes:
    # cryptography expects a 16-byte nonce: 4-byte little-endian counter + 12-byte nonce
    cipher = Cipher(algorithms.ChaCha20(key, (0).to_bytes(4, "little") + nonce), mode=None)
    return cipher.decryptor().update(data)

def decode_wrapped(text: str, hex_len: int) -> bytes:
    import base64
    return bytes.fromhex(text) if len(text) == hex_len else base64.b64decode(text)

def account_private_key(account: dict, password: str) -> ec.EllipticCurvePrivateKey:
    entry = next(e for e in account["encryptedBlobKeys"] if e["name"] == "password")
    blob_key = chacha20(
        blob_password_key(password),
        decode_wrapped(entry["nonce"], 24),
        decode_wrapped(entry["value"], 64),
    )
    blob = account["blob"]
    encrypted = bytes.fromhex(blob["value"])
    doc = bson.decode(chacha20(blob_key, bytes.fromhex(blob["nonce"]), encrypted))
    scalar = int.from_bytes(bytes(b & 0xFF for b in doc["privateKey"]), "big")
    key = ec.derive_private_key(scalar, ec.SECP256K1())

    sig = bytes.fromhex(blob["sign"])
    half = len(sig) // 2
    der = utils.encode_dss_signature(int.from_bytes(sig[:half], "big"), int.from_bytes(sig[half:], "big"))
    key.public_key().verify(der, encrypted, ec.ECDSA(hashes.SHA512()))  # raises if wrong
    return key
```

Dependencies: `cryptography`, `pymongo` (for `bson`). Home Assistant already ships `cryptography`. `bson` would need to be a requirement, or replaced by a minimal BSON reader for this one field.

## Which credential to use for a lock 🔍

The app (`_.lh4.d`) uses the account key when the account is listed on the device:

1. The account UUID is in the device's `UserList` (`share_account_uuid`), and its access/schedule allows it now (`_.duf.I`).
2. Otherwise, it looks for a local non-admin **pass** covering the device.
3. Otherwise: `No access to device.`

The PoC client ⚙️ only supports the simple owner/admin case:

- Exactly one `AccessMap` entry with `AccessMap_account_uuid == account.uuid` and role owner (0) or admin (1).
- Exactly one `UserList` entry with `share_account_uuid == account.uuid` and `access_level == 1` (admin).
- `access_from`, `access_until`, `rrule` all null.

`AccessMap_key` (33 integers live) is **not** used by the app's resolver and its format is unknown. Do not compare it to the public key.

## APK sources

| Subject | Class |
|---|---|
| Blob-password derivation | `_.ei1.a`, `_.rfd`, `_.g40` |
| Blob decrypt + verify | `_.lef.q`, `_.ci1.e/c/d`, `_.b92`, `_.a92` |
| Wrapped-key decoding | `_.td.a` |
| Key loading | `_.lb`, `_.kb.w`, `_.g1.w` |
| Signer registration (SHA-512 vs `ec_fw_sha256`) | `_.vd3.l` case 14, `_.kg3` cases 23/24/26/28, `_.bn3`, `_.kq4` |
| Raw signature encoding | `PlainDSAEncoder`, `_.ic5`, `_.mqh.Q`, `_.se1` |
| Credential selection | `_.lh4.d`, `_.lh4.b`, `_.duf.I` |
