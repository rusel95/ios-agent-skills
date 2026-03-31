# No -- This Log Statement Has Multiple Security and PII Problems

Your logging line is unsafe for production. It dumps the full URL, all HTTP headers, and the entire request body into the log with **no privacy annotations and no redaction**. Here is what is wrong and how to fix it.

## Problems Identified

### 1. Headers Leak Authentication Tokens

`request.allHTTPHeaderFields` will capture everything in the header dictionary, which commonly includes:

- `Authorization: Bearer <JWT or OAuth token>`
- `Cookie` or `Set-Cookie` session tokens
- `X-API-Key` or custom API key headers
- `X-CSRF-Token`

Logging these means anyone with access to the device logs (or a crash reporting dashboard) can steal live credentials.

### 2. Request Body May Contain PII and Secrets

`request.httpBody` is dumped as a raw string. Depending on the endpoint, this can include:

- Passwords and credentials (login endpoints)
- Email addresses, phone numbers, full names (registration, profile update)
- Payment or financial data (checkout flows)
- Health data (HealthKit-related APIs)

Under GDPR and CCPA, all of these are personal data. Logging them without consent or a legal basis violates data protection regulations.

### 3. URLs Can Contain User Data

URLs frequently embed PII in query parameters or path segments, such as `/users/john@example.com/profile` or `?email=user@example.com&token=abc123`.

### 4. No `os.Logger` Privacy Annotations

You are using `logger.info(...)` but every interpolated value lacks a `privacy:` annotation. In Apple's `os.Logger`, dynamic strings default to `<private>` in production logs (when no debugger is attached), so this line is actually useless for production debugging anyway. But if logs are captured via `log collect` or streamed in Xcode, all values are fully visible with no redaction.

### 5. Using `logger.info` -- Wrong Level for Debugging

`.info` level is memory-only and not persisted to disk. If you need this for production debugging, the data won't survive. If you only need it during development, `.debug` is more appropriate (zero cost in production).

## The Fix: Log Safely and Usefully

Replace the single unsafe line with structured, redacted logging:

```swift
// Log what you need for debugging, redact what you don't
Logger.networking.debug("""
    Request: \(request.httpMethod ?? "?", privacy: .public) \
    \(request.url?.path ?? "", privacy: .public) \
    bodySize: \(request.httpBody?.count ?? 0, privacy: .public) bytes
    """)
```

**Key changes:**

- **URL**: Log only the path (`.public`), not query parameters (which can contain tokens or PII).
- **Headers**: Do not log headers at all. If you need to debug a specific header, log only non-sensitive ones explicitly:

```swift
Logger.networking.debug("Content-Type: \(request.value(forHTTPHeaderField: "Content-Type") ?? "none", privacy: .public)")
```

- **Body**: Log only the size, never the content. Request bodies are the most common source of PII leaks in logs.
- **Level**: Use `.debug` for development tracing -- it has zero cost in production and is not persisted.

## If You Absolutely Need Body Content During Development

Use a `#if DEBUG` guard so this code is stripped from release builds entirely:

```swift
#if DEBUG
if let body = request.httpBody, let bodyString = String(data: body, encoding: .utf8) {
    Logger.networking.debug("Request body: \(bodyString, privacy: .private)")
}
#endif
```

Note `privacy: .private` ensures the body is redacted as `<private>` even if someone streams logs from a debug build without Xcode attached.

## Never Log These Values

Per GDPR/CCPA compliance requirements, the following must never appear in production logs:

| Category | Examples |
|---|---|
| Auth tokens | JWT, OAuth tokens, refresh tokens, API keys, session cookies |
| Personal identifiers | Email, phone number, full name, SSN |
| Financial data | Card numbers, account numbers |
| Health data | HealthKit values |
| Full HTTP headers | May contain any of the above |
| Full request/response bodies | May contain any of the above |

## Summary

Your original line is a PII and credential leak. Replace it with structured logging that captures only the HTTP method, URL path, and body size using `os.Logger` with explicit `privacy:` annotations. Never log headers or body content in production code.
