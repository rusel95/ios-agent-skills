# Logging API Requests: Security Concerns

No, this is **not safe** for production use. While logging requests can be helpful during development, this approach has several serious problems.

## What's Wrong

### 1. Sensitive Data Exposure in Headers

HTTP headers frequently contain sensitive information:

- **Authorization tokens** (`Bearer <token>`, API keys)
- **Cookies** and session identifiers
- **Custom authentication headers**

By logging `request.allHTTPHeaderFields`, you are dumping all of these into your logs.

### 2. Sensitive Data in Request Bodies

Request bodies often contain:

- User credentials (login endpoints with username/password)
- Personal information (names, emails, addresses, phone numbers)
- Payment information (credit card numbers, billing details)
- Any other PII the user submits through forms

### 3. Logs Are Not Secure Storage

- On-device logs can be accessed via Console.app, device sysdiag, or crash log exports.
- If you use a remote logging service, this data is transmitted over the network and stored on third-party servers.
- Logs are often retained longer than necessary and may be accessed by team members who should not see user PII.
- This can violate GDPR, CCPA, HIPAA, and other privacy regulations.

## How to Fix It

### Redact Sensitive Headers

Create an allowlist of safe headers and redact everything else:

```swift
private let safeHeaders: Set<String> = ["Content-Type", "Accept", "Accept-Language"]

func sanitizedHeaders(_ headers: [String: String]?) -> [String: String] {
    guard let headers = headers else { return [:] }
    return headers.mapValues { key, value in
        safeHeaders.contains(key) ? value : "<redacted>"
    }
}
```

### Redact Request Bodies

Never log raw request bodies. Log only structural information:

```swift
func sanitizedBody(_ data: Data?) -> String {
    guard let data = data else { return "<empty>" }
    return "<\(data.count) bytes>"
}
```

### Use OSLog with Appropriate Privacy Levels

Apple's `os.log` framework has built-in privacy controls:

```swift
import os

let logger = Logger(subsystem: "com.myapp", category: "networking")

logger.info("Request: \(request.url?.absoluteString ?? "", privacy: .public) body: \(data.count, privacy: .public) bytes")
logger.debug("Headers: \(sanitizedHeaders(request.allHTTPHeaderFields), privacy: .private)")
```

Using `privacy: .private` ensures values are redacted in production log collection while remaining visible during active debugging with a connected debugger.

### Use Compile-Time Guards

Ensure verbose logging only happens in debug builds:

```swift
#if DEBUG
logger.debug("Full request: \(request.debugDescription)")
#endif
```

## Summary

- **Never log authorization headers or raw request bodies in production.**
- Use an allowlist approach for headers rather than logging everything.
- Use `os.log` privacy levels to automatically redact sensitive data.
- Guard verbose logging behind `#if DEBUG` so it cannot appear in release builds.
- Consider privacy regulations (GDPR, CCPA) that may make logging PII a compliance violation.
