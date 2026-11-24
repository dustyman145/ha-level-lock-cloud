# Authentication

## Flow summary

1. Derive the **login value** from the password (below).
2. `POST /v2/login` with `userID` and the login value. ✅
3. Read the session token from the **`AccessToken` response header**. ✅
4. If the HTTP status is **202**, or `status` contains `tfaEnabled`, complete 2FA (below). If `status` contains `loginFailed`, the credentials are wrong. 🔍
5. Send `AccessToken: <token>` on every later request. ✅
6. Separately, derive the **blob key** from the same password to decrypt the signing key. See [account-key.md](account-key.md).

Because step 6 needs the plain password, the integration must keep the password (or the decrypted private key) after setup. The token alone cannot sign lock commands.

## Login password derivation ✅

The `password` field sent to `/v2/login` is **not** the plain password.

1. UTF-8 encode the password.
2. Append the ASCII text `CFF33588-AC1D-4F77-943B-728CF61FCC1B` (with hyphens, not hex-decoded).
3. SHA-256 it **102 times**, each round hashing the previous raw 32 bytes.
4. Base64-encode the final 32 bytes.

```python
import base64, hashlib

LOGIN_SALT = b"CFF33588-AC1D-4F77-943B-728CF61FCC1B"

def login_value(password: str) -> str:
    value = password.encode("utf-8") + LOGIN_SALT
    for _ in range(102):
        value = hashlib.sha256(value).digest()
    return base64.b64encode(value).decode("ascii")
```

The blob-key derivation uses the same scheme with a **different salt**. See [account-key.md](account-key.md).

## Login

See [endpoints/post-v2-login.md](endpoints/post-v2-login.md).

## Session token

| Topic | Status |
|---|---|
| Where it comes from | `AccessToken` response header of `/v2/login` ✅ |
| How it is sent | `AccessToken` request header ✅ |
| Format | Opaque string ❓ (structure not analysed) |
| Lifetime / expiry | ❓ |
| Refresh token / refresh endpoint | ❓ none found so far |
| Rotation (new `AccessToken` header on later responses) | ❓ |
| Concurrent sessions (app + HA at once) | ❓ |
| Invalidation on password change | ❓ |
| Status code when expired | ❓ |

Until expiry behaviour is known, the integration should re-login on an auth failure. It must **not** replay a lock/unlock that may already have been sent; see [errors.md](errors.md).

## Two-factor authentication (2FA)

Traced from the APK 🔍; not tested live (owner account has 2FA off). Full details: [endpoints/2fa.md](endpoints/2fa.md).

1. Login with `X-Allow-TFA: 1` returns **HTTP 202** when 2FA is required. The app treats 202 as `tfaEnabled`.
2. The 202 response still includes an `AccessToken` header (pre-2FA token).
3. `POST /v1/2fa/otp/send` `{"method": "email" | "phone"}` with that token.
4. `POST /v1/2fa/confirm` `{"hash": sha256(code).hexdigest()[:12]}` with that token. The raw code is never sent.
5. Confirm returns the session token in its `AccessToken` response header.

Still unknown ❓: whether a code is sent automatically on the 202, wrong-code errors, and whether later logins need 2FA again (no trusted-device field found).

## Logout

`POST /v2/logout` exists. 🔍 Not called; effect on the token is unknown. See [endpoints/post-v2-logout.md](endpoints/post-v2-logout.md).

## APK sources

| Subject | Class |
|---|---|
| Login / account / logout / 2FA route construction | `_.pe` |
| Logout request | `_.pe.v` |
| Login model | `LoginInputSchema`, `LoginRespSchema` |
