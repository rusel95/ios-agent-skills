# Logging and GDPR Compliance in iOS Apps

GDPR (and CCPA) classify IP addresses, device IDs, and behavioral data as personal information. As the app publisher, you are the **data controller** responsible for all data processing -- including what happens inside third-party SDKs you ship. Here is what to watch out for.

---

## 1. Never Log Authentication Secrets or Sensitive PII

Certain categories of data must never appear in logs at all, regardless of redaction:

- **Authentication data:** passwords, password hashes, JWT/OAuth tokens, refresh tokens, API keys, client secrets, session tokens, CSRF tokens
- **High-sensitivity personal identifiers:** Social Security Numbers, passport numbers, financial account or card numbers, health data (HealthKit)
- **Communication contents:** message bodies, emails

These should not be logged even with `privacy: .private` -- they should simply never reach any logging call.

## 2. Use os.Logger Privacy Annotations as Your First Line of Defense

Apple's `os.Logger` redacts dynamic strings by default in production (they appear as `<private>`). You must use explicit privacy annotations on every interpolated value:

```swift
// Mark non-sensitive operational data as public
logger.error("GET \(url.path, privacy: .public) failed: HTTP \(statusCode, privacy: .public)")

// Hash PII when you need cross-event correlation without exposing the value
logger.notice("Login attempt for \(email, privacy: .private(mask: .hash))")

// Secrets should not be logged, but if you must reference one:
logger.debug("Token status: \(tokenPresent ? "present" : "missing", privacy: .public)")
```

Key privacy annotation options:

| Annotation | When to use |
|---|---|
| `.public` | URL paths, error codes, status codes, operation names |
| `.private` | User IDs, emails, names, device IDs |
| `.private(mask: .hash)` | PII where you need to correlate events for the same user |
| `.sensitive` | Always redacted even during development |

**If unsure, default to `.private`** -- you can always relax the annotation later.

## 3. Watch for Operational Leaks (Commonly Missed)

These are the GDPR violations that slip through code review:

- **Full HTTP request/response bodies** -- may contain auth headers, user data
- **Database queries with user parameters** -- raw SQL or NSPredicate strings can contain PII
- **URL paths containing PII** -- e.g., `/users/john@example.com/profile`
- **Stack traces with user data in variable names**
- **Core Data fault descriptions** -- may contain entity values with user data

## 4. Redact PII Before Sending to Crash Reporting SDKs

Crash reporting metadata (Sentry breadcrumbs, Crashlytics custom keys) is transmitted to third-party servers. You must redact PII before attaching it as context:

```swift
enum Redactor {
    static func maskEmail(_ email: String) -> String {
        guard let at = email.firstIndex(of: "@") else { return "***" }
        return "\(email.prefix(1))***\(email[at...])"
    }

    static func maskID(_ id: String) -> String {
        guard id.count > 4 else { return "****" }
        return "***\(id.suffix(4))"
    }
}

ErrorReporter.shared.recordNonFatal(error, context: [
    "userId": Redactor.maskID(userId),       // "***4f8a"
    "email": Redactor.maskEmail(email),       // "j***@example.com"
    "operation": "checkout"                    // Non-PII: no redaction needed
])
```

## 5. Use the @Redacted Property Wrapper to Prevent Accidental Exposure

A `@Redacted` property wrapper ensures that even careless `print()` or string interpolation won't leak PII:

```swift
@propertyWrapper
struct Redacted<Value> {
    var wrappedValue: Value
}

extension Redacted: CustomStringConvertible {
    var description: String { "--redacted--" }
}

extension Redacted: CustomDebugStringConvertible {
    var debugDescription: String { "--redacted--" }
}

struct User {
    let id: String
    @Redacted var email: String
    @Redacted var phoneNumber: String
}
// print(user) outputs: User(id: "abc123", email: --redacted--, phoneNumber: --redacted--)
```

## 6. Privacy Manifests (Required Since May 2024)

Apple now **rejects App Store submissions** that lack `PrivacyInfo.xcprivacy` manifests. You must declare use of Required Reason APIs:

- `UserDefaults`
- File timestamp APIs (`NSFileCreationDate`, `NSFileModificationDate`)
- System boot time APIs
- Disk space APIs

Crash reporting SDKs like Sentry and Crashlytics ship their own privacy manifests that Xcode merges automatically. If an SDK you use lacks a manifest, you must add declarations to your own `PrivacyInfo.xcprivacy`.

## 7. Crash Reporting vs. App Tracking Transparency (ATT)

Crash reporting generally **does not** require ATT consent, provided:

- Data is used only for improving your own app
- Data is not shared with data brokers
- Data is not linked with third-party data for advertising

However, be aware of SDK-specific requirements. For example, Firebase Crashlytics's terms (Section 2.6) require developers to obtain EU user consent for data transfer and storage. Read your specific SDK's data processing terms carefully.

## 8. IDFA and IDFV

- **IDFA** (Identifier for Advertisers): requires ATT consent before access or logging
- **IDFV** (Identifier for Vendor): does not require ATT but is still personal data under GDPR -- apply `.private(mask: .hash)` if you must log it

## Summary Checklist

1. Replace all `print()` with `os.Logger` using explicit privacy annotations
2. Audit every log call for PII -- especially operational leaks like URL paths and HTTP bodies
3. Never log authentication secrets, tokens, or high-sensitivity identifiers
4. Redact PII before attaching context to crash reporting SDKs
5. Use `@Redacted` property wrappers on model types containing PII
6. Include a `PrivacyInfo.xcprivacy` manifest declaring Required Reason API usage
7. Review your crash SDK's data processing terms for EU consent requirements
8. Default to `privacy: .private` when uncertain about a value's sensitivity
