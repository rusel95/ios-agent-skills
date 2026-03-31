# Privacy Annotations for Logger Calls

When using Apple's `os.Logger`, string interpolations in log messages are **redacted by default** in production (non-debugger) builds. You need to explicitly mark each interpolated value with a privacy annotation to control what appears in collected logs.

## Annotated Code

### First call

```swift
logger.error("Request to \(url, privacy: .public) failed for user \(userId, privacy: .private) with token \(authToken, privacy: .private(mask: .hash))")
```

### Second call

```swift
logger.info("Saving order \(orderId, privacy: .public) for \(customerEmail, privacy: .private) total \(amount, privacy: .private)")
```

## Rationale for Each Value

| Value | Annotation | Reason |
|---|---|---|
| `url` | `.public` | API endpoints are not user-identifiable data. Making them public is essential for debugging network failures. |
| `userId` | `.private` | Personally identifiable information. Should be redacted in production logs. |
| `authToken` | `.private(mask: .hash)` | Highly sensitive credential. Using `.hash` lets you correlate log entries by the same token without ever exposing the raw value. |
| `orderId` | `.public` | An internal system identifier, not personally identifiable. Useful for tracing order flow in production. |
| `customerEmail` | `.private` | PII -- must be redacted in production logs. |
| `amount` | `.private` | Financial data tied to a specific order/customer. Treat as sensitive to avoid leaking transaction details. |

## Key Concepts

- **Default behavior**: Without any annotation, string interpolations default to `privacy: .auto`. For most types this behaves like `.private`, meaning the value is replaced with `<private>` in log output collected outside of a debugger session.
- **`.public`**: The value is always visible in logs, including on-device log collection and `log collect`. Use only for non-sensitive, operationally useful data.
- **`.private`**: The value is visible when attached to a debugger but redacted in production log archives. This is the right default for any PII or sensitive data.
- **`.private(mask: .hash)`**: The value is redacted but replaced with a stable hash. This is useful for secrets or credentials where you need correlation across log lines without exposing the raw value.

## General Guidelines

1. Never mark authentication tokens, passwords, or secrets as `.public`.
2. Mark PII (emails, user IDs, names, phone numbers) as `.private`.
3. Use `.public` for system identifiers, error codes, HTTP status codes, and endpoint paths that contain no user data.
4. Use `.private(mask: .hash)` when you need to correlate redacted values across multiple log lines (e.g., session tokens, request IDs that happen to be sensitive).
