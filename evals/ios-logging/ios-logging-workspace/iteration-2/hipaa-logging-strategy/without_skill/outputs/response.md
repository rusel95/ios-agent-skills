# HIPAA-Compliant Logging Strategy for SwiftUI Health Tech App

## Core Principle: Never Log PHI

The foundational rule is that Protected Health Information (PHI) must never appear in logs. This includes patient names, dates of birth, medical record numbers, diagnosis codes, device identifiers tied to patients, and any data that could identify an individual combined with their health information.

---

## 1. Architecture Overview

### Logging Subsystem Design

Use Apple's `os.log` (Unified Logging) as the foundation. It provides hardware-accelerated logging, automatic privacy redaction, and integration with Instruments and Console.app.

```swift
import OSLog

enum LogCategory: String {
    case network = "Network"
    case auth = "Auth"
    case ui = "UI"
    case dataSync = "DataSync"
    case lifecycle = "Lifecycle"
}

struct AppLogger {
    private static let subsystem = Bundle.main.bundleIdentifier ?? "com.healthapp"

    static func logger(for category: LogCategory) -> Logger {
        Logger(subsystem: subsystem, category: category.rawValue)
    }

    static let network = logger(for: .network)
    static let auth = logger(for: .auth)
    static let ui = logger(for: .ui)
    static let dataSync = logger(for: .dataSync)
    static let lifecycle = logger(for: .lifecycle)
}
```

### Privacy-Aware Logging

`os.log` supports privacy annotations natively. Use them rigorously:

```swift
// SAFE - identifiers are redacted in non-debug builds
AppLogger.network.info("Fetching resource at endpoint: \(endpoint, privacy: .public)")
AppLogger.network.debug("Request for user: \(userId, privacy: .private)")

// NEVER do this - PHI in logs
// AppLogger.network.info("Patient \(patientName) diagnosis: \(code)")
```

The `privacy: .private` annotation means the value is redacted in production log collection but visible when debugging with a physically connected device in Xcode. The `privacy: .public` annotation means the value is always visible.

**Rule of thumb:** Default to `.private`. Only mark something `.public` if it contains zero user or health data (e.g., endpoint paths without query parameters, HTTP status codes, app version strings).

---

## 2. Log Levels and What Goes Where

| Level | Use Case | Contains PHI? | Persisted? |
|-------|----------|---------------|------------|
| `.fault` | Unrecoverable errors, data corruption | Never | Yes, long-lived |
| `.error` | Recoverable errors, failed API calls | Never | Yes, moderate |
| `.info` | State transitions, sync completions | Never | Yes, short-lived |
| `.debug` | Detailed flow tracing, variable values | Redacted via `.private` | Only when log collection active |
| `.trace` | Extremely verbose, per-frame or per-item | Redacted via `.private` | No, memory only |

---

## 3. Network Layer Logging

For your REST API layer, log the shape of requests and responses without content:

```swift
func logRequest(_ request: URLRequest) {
    AppLogger.network.info("""
        API Request: \(request.httpMethod ?? "?", privacy: .public) \
        \(request.url?.path ?? "unknown", privacy: .public)
        """)
    AppLogger.network.debug("Headers count: \(request.allHTTPHeaderFields?.count ?? 0, privacy: .public)")
    // Log body size, not body content
    if let body = request.httpBody {
        AppLogger.network.debug("Body size: \(body.count, privacy: .public) bytes")
    }
}

func logResponse(_ response: HTTPURLResponse, data: Data, duration: TimeInterval) {
    AppLogger.network.info("""
        API Response: \(response.statusCode, privacy: .public) \
        \(response.url?.path ?? "unknown", privacy: .public) \
        [\(String(format: "%.0f", duration * 1000), privacy: .public)ms]
        """)
    AppLogger.network.debug("Response size: \(data.count, privacy: .public) bytes")

    if response.statusCode >= 400 {
        // Log error codes/types but NOT error message bodies that might contain PHI
        AppLogger.network.error("""
            API Error: \(response.statusCode, privacy: .public) \
            at \(response.url?.path ?? "?", privacy: .public)
            """)
    }
}
```

**Critical:** Never log request or response bodies. They will contain PHI. Log status codes, endpoint paths (without query parameters that might contain patient identifiers), durations, and payload sizes.

### Async/Await Integration

Wrap your network client to provide structured logging around async calls:

```swift
func perform<T: Decodable>(_ request: URLRequest) async throws -> T {
    let requestId = UUID().uuidString.prefix(8)
    AppLogger.network.info("[\(requestId, privacy: .public)] Starting request")
    logRequest(request)

    let startTime = CFAbsoluteTimeGetCurrent()
    do {
        let (data, response) = try await URLSession.shared.data(for: request)
        let duration = CFAbsoluteTimeGetCurrent() - startTime
        guard let httpResponse = response as? HTTPURLResponse else {
            throw NetworkError.invalidResponse
        }
        logResponse(httpResponse, data: data, duration: duration)
        return try JSONDecoder().decode(T.self, from: data)
    } catch {
        let duration = CFAbsoluteTimeGetCurrent() - startTime
        AppLogger.network.error("""
            [\(requestId, privacy: .public)] Failed after \
            \(String(format: "%.0f", duration * 1000), privacy: .public)ms: \
            \(error.localizedDescription, privacy: .private)
            """)
        throw error
    }
}
```

Note that `error.localizedDescription` is marked `.private` because error messages from the server might contain PHI.

---

## 4. Data Sanitization Layer

Create a sanitizer that strips PHI before anything touches logs:

```swift
enum LogSanitizer {
    /// Masks all but last 4 characters
    static func maskId(_ id: String) -> String {
        guard id.count > 4 else { return "****" }
        return String(repeating: "*", count: id.count - 4) + id.suffix(4)
    }

    /// Returns only the domain portion of an email
    static func maskEmail(_ email: String) -> String {
        guard let atIndex = email.firstIndex(of: "@") else { return "[redacted-email]" }
        return "***@" + email[email.index(after: atIndex)...]
    }

    /// Strips known PHI fields from a dictionary for logging
    static func sanitize(_ dict: [String: Any]) -> [String: Any] {
        let phiKeys: Set<String> = [
            "name", "firstName", "lastName", "dob", "dateOfBirth",
            "ssn", "address", "phone", "email", "mrn",
            "diagnosis", "medication", "condition", "notes"
        ]
        return dict.mapValues { value in
            if let key = value as? String, phiKeys.contains(key) {
                return "[REDACTED]"
            }
            return value
        }.filter { !phiKeys.contains($0.key) }
    }
}
```

---

## 5. SwiftUI View Lifecycle Logging

Log navigation and view lifecycle events without logging what data is displayed:

```swift
struct LoggingViewModifier: ViewModifier {
    let viewName: String

    func body(content: Content) -> some View {
        content
            .onAppear {
                AppLogger.ui.info("View appeared: \(viewName, privacy: .public)")
            }
            .onDisappear {
                AppLogger.ui.info("View disappeared: \(viewName, privacy: .public)")
            }
    }
}

extension View {
    func logLifecycle(_ name: String) -> some View {
        modifier(LoggingViewModifier(viewName: name))
    }
}

// Usage
struct PatientDetailView: View {
    let patientId: String

    var body: some View {
        VStack { /* ... */ }
            .logLifecycle("PatientDetail")
            // Log that we navigated here, but NOT which patient
            .task {
                AppLogger.ui.debug("Loading detail for entity: \(patientId, privacy: .private)")
            }
    }
}
```

---

## 6. Audit Logging (Separate from Debug Logging)

HIPAA requires an audit trail of who accessed what PHI and when. This is fundamentally different from debug logging and must be handled separately:

```swift
struct AuditEvent: Codable {
    let timestamp: Date
    let userId: String
    let action: AuditAction
    let resourceType: String
    let resourceId: String
    let outcome: AuditOutcome

    enum AuditAction: String, Codable {
        case view, create, update, delete, export, share
    }

    enum AuditOutcome: String, Codable {
        case success, failure, denied
    }
}

actor AuditLogger {
    private let encoder = JSONEncoder()

    func log(_ event: AuditEvent) async {
        // Audit logs go to your backend, NOT to os.log
        // They are stored server-side in a tamper-evident store
        do {
            try await sendToAuditEndpoint(event)
        } catch {
            // If audit logging fails, this is a critical issue
            AppLogger.auth.fault("Audit log delivery failed - action: \(event.action.rawValue, privacy: .public)")
            // Consider blocking the operation if audit cannot be recorded
        }
    }
}
```

Audit logs are sent to your server and stored in a write-once, tamper-evident store (append-only database, or a service like AWS CloudTrail). They are retained for a minimum of 6 years per HIPAA requirements. They are never mixed with debug logs.

---

## 7. Remote Log Collection

If you need to collect logs from devices in production for debugging, follow these rules:

1. **Never collect raw logs.** Use `OSLogStore` with explicit filtering to collect only your subsystem.
2. **Strip before sending.** Even though `.private` values are redacted in collected logs, apply an additional sanitization pass before transmitting.
3. **Encrypt in transit.** Use certificate pinning and TLS 1.3 for any log upload endpoint.
4. **Short retention.** Production debug logs should be retained for no more than 30 days, then automatically purged.
5. **Access controls.** Only authorized personnel should access collected logs, and that access should itself be audited.

```swift
func collectFilteredLogs() throws -> [OSLogEntryLog] {
    let store = try OSLogStore(scope: .currentProcessIdentifier)
    let position = store.position(timeIntervalSinceEnd: -3600) // last hour
    let predicate = NSPredicate(format: "subsystem == %@", Bundle.main.bundleIdentifier ?? "")

    let entries = try store.getEntries(at: position, matching: predicate)
    return entries.compactMap { $0 as? OSLogEntryLog }
}
```

---

## 8. Configuration by Environment

```swift
enum LoggingConfig {
    static func configure() {
        #if DEBUG
        // In debug builds, os.log shows .private values in Xcode console
        // All levels are active
        #else
        // In release builds:
        // - .private values are automatically redacted
        // - .debug and .trace messages are not persisted
        // - Only .info, .error, .fault persist to disk
        #endif
    }
}
```

No custom log level switching is needed because `os.log` handles this automatically: debug-level messages are only captured when a debugger is attached or log profiling is active.

---

## 9. Compliance Checklist

- [ ] No PHI appears in any log statement at any level
- [ ] All user identifiers use `privacy: .private` annotation
- [ ] Network request/response bodies are never logged
- [ ] Error messages from the server are marked `.private`
- [ ] Audit trail is separate from debug logging and sent to a secure backend
- [ ] Audit logs are retained for 6+ years
- [ ] Remote log collection encrypts data in transit
- [ ] Production logs are auto-purged after a short retention period
- [ ] URL query parameters are not logged (they may contain identifiers)
- [ ] Log access is restricted and itself audited

---

## 10. What to Log vs. What Not to Log

### Safe to Log (`.public`)
- HTTP status codes
- API endpoint paths (without query params)
- Request/response sizes in bytes
- Durations and latencies
- View names and navigation flow
- App version, build number, OS version
- Feature flags and configuration values
- Error types and categories (not messages)

### Log with Redaction (`.private`)
- User IDs, session tokens
- Device identifiers
- Error description strings
- File paths that might contain usernames

### Never Log
- Patient names, dates of birth, addresses
- Medical record numbers, diagnosis codes
- Medication names tied to a patient
- Insurance information
- Request/response bodies from health data endpoints
- Authentication credentials
- Biometric data references
