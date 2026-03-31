# Privacy Annotations for Logger Calls

## Key Principle

In `os.Logger`, **all dynamic string interpolations are redacted by default** in production logs -- they show as `<private>` unless a debugger is attached. You must add explicit privacy annotations to every interpolated value, choosing the right level based on what the data contains.

## Corrected Code

### First call -- network error

```swift
logger.error("Request to \(url, privacy: .public) failed for user \(userId, privacy: .private(mask: .hash)) with token \(authToken, privacy: .sensitive)")
```

| Value | Annotation | Rationale |
|---|---|---|
| `url` | `.public` | URL paths and endpoints are operational data, safe for anyone with log access. Needed for debugging which request failed. |
| `userId` | `.private(mask: .hash)` | PII (personal identifier), but you need a consistent hash to correlate multiple log entries for the same user across events. The hash lets you trace a user's journey without exposing the raw ID. |
| `authToken` | `.sensitive` | **Authentication secret -- ideally should not be logged at all.** Tokens, API keys, passwords, and session tokens are listed under "What to Never Log" in PII compliance guidelines. If you must reference the token's existence, use `.sensitive` so it is redacted even during development. Better yet, remove it from the log entirely: |

Preferred version with the token removed:

```swift
logger.error("Request to \(url, privacy: .public) failed for user \(userId, privacy: .private(mask: .hash))")
```

There is no diagnostic value in logging the token itself. If you need to know whether a token was present, log a boolean instead:

```swift
logger.error("Request to \(url, privacy: .public) failed for user \(userId, privacy: .private(mask: .hash)), hasToken: \(authToken != nil, privacy: .public)")
```

### Second call -- order info

```swift
logger.info("Saving order \(orderId, privacy: .public) for \(customerEmail, privacy: .private(mask: .hash)) total \(amount, privacy: .public)")
```

| Value | Annotation | Rationale |
|---|---|---|
| `orderId` | `.public` | An internal system identifier, not PII. Needed to trace the order through logs and match with backend records. |
| `customerEmail` | `.private(mask: .hash)` | PII (personal identifier under GDPR/CCPA). Using `mask: .hash` produces a consistent hash so you can correlate all log entries for the same customer without exposing their email address. |
| `amount` | `.public` | Numeric transaction amount is operational data. Integers and floats are public by default in `os.Logger`, but adding the explicit annotation makes intent clear. Not PII on its own. |

## Quick Decision Guide (from the skill)

```
Is the value safe for anyone with log access to see?
  YES (URLs, error codes, status codes, order IDs, amounts)
    -> privacy: .public
  NO -- Is it PII or user-specific?
    YES -- Do you need cross-event correlation?
      YES -> privacy: .private(mask: .hash)    (userId, email)
      NO  -> privacy: .private                 (one-off references)
    NO -- Is it a secret (token, password, key)?
      -> DO NOT LOG IT. If unavoidable: privacy: .sensitive
```

## Summary

- **Never log authentication tokens, passwords, or API keys.** Remove `authToken` from the log message entirely or replace it with a boolean flag.
- **Use `.private(mask: .hash)` for user identifiers and emails** when you need to correlate events across log entries.
- **Use `.public` for operational data** like URL paths, order IDs, error codes, and amounts.
- **Always add explicit annotations** -- relying on the default redaction means your production logs will be filled with `<private>` placeholders that provide no diagnostic value.
