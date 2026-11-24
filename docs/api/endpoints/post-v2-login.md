# `POST /v2/login`

**Purpose:** Sign in and obtain a session token.
**Evidence:** ✅ Verified (owner account, no 2FA)
**Source:** `_.pe`, `LoginInputSchema`, `LoginRespSchema`
**Used by integration:** yes

## Request

| Part | Value |
|---|---|
| URL | `https://api.level.co/v2/login` |
| Auth | none |

### Headers

| Header | Value | Notes |
|---|---|---|
| `Accept` | `application/json` | |
| `Content-Type` | `application/json` | |
| `X-Allow-TFA` | `1` | The app always sends `1`. Tells the server the client can handle a 2FA challenge 🔍 |

### Body (`LoginInputSchema`)

```json
{
  "userID": "owner@example.invalid",
  "password": "<base64 of derived 32-byte value>"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `userID` | string | yes | Email as typed, or a phone number normalised to international form without spaces, dashes or brackets (e.g. `+15555550123`) 🔍 (`_.ygb.a`) |
| `password` | string | yes | Base64 login value derived from the password; see [authentication.md](../authentication.md#login-password-derivation-) |

## Response

### Headers

| Header | Description |
|---|---|
| `AccessToken` | Session token. Send it back as the `AccessToken` request header ✅ |

The token is in a **header**, not in the JSON body. ✅

### Body (`LoginRespSchema`)

```json
{
  "status": ["<flag>", "..."]
}
```

| Field | Type | Description |
|---|---|---|
| `status` | string[] | Flags. Known: `loginFailed`, `tfaEnabled` 🔍 |

A full successful body has not been captured. Don't rely on other fields.

### Outcomes

| Condition | Meaning |
|---|---|
| 200 + `AccessToken` header, no failure flag | Signed in ✅ |
| `status` contains `loginFailed` | Wrong credentials 🔍 |
| **HTTP 202**, or `status` contains `tfaEnabled` | 2FA required. The `AccessToken` header is a pre-2FA token for the 2FA calls; see [2fa.md](2fa.md) 🔍 |
| No `AccessToken` header | No session returned (app error: `Access token expected`) |
| Non-2xx | Error body `{code, message, data: {seconds}}` ([errors.md](../errors.md)) 🔍 |

## Notes

- The same plain password is also needed to decrypt the signing key ([account-key.md](../account-key.md)). Keep it, or keep the decrypted key, after login.
- Each PoC run logs in again. Token lifetime is unknown.
