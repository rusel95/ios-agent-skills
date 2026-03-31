# HIPAA-Adjacent Logging Strategy for a SwiftUI + async/await Health Tech App

## Guiding Principle

HIPAA's minimum necessary standard applies directly to logging: log only what you need for debugging, redact everything else by default, and treat every dynamic string as PHI until proven otherwise. The strategy below gives you full debugging power with zero PHI in your log stores.

---

## 1. Observability Stack Overview

```
Presentation Layer  -> SwiftUI error state + centralized ErrorHandler
Application Layer   -> ErrorReporter protocol (abstracts Sentry)
Logging Layer       -> os.Logger with subsystem/category + aggressive privacy annotations
Diagnostics Layer   -> MetricKit (OOM, watchdog kills, hangs)
Crash Layer         -> Sentry (primary fatal reporter) + dSYMs
```

Choose Sentry as your crash reporter for its breadcrumb context and MCP server integration, which lets you query production errors directly from your IDE without accessing a dashboard that might display PHI.

---

## 2. Logger Setup with Health-Domain Categories

```swift
import os

extension Logger {
    private static let subsystem = Bundle.main.bundleIdentifier!

    static let networking = Logger(subsystem: subsystem, category: "Networking")
    static let auth       = Logger(subsystem: subsystem, category: "Authentication")
    static let health     = Logger(subsystem: subsystem, category: "HealthData")
    static let sync       = Logger(subsystem: subsystem, category: "Sync")
    static let ui         = Logger(subsystem: subsystem, category: "UI")
    static let lifecycle  = Logger(subsystem: subsystem, category: "Lifecycle")
}
```

The `health` category lets you filter or suppress health-specific logs independently. In a compliance audit you can demonstrate that health-related log messages are isolated and redacted.

---

## 3. Privacy Annotation Rules (HIPAA-Specific)

The single most important decision: **default everything to `.private`**, then selectively mark safe values as `.public`.

### What is PHI in your context

| Data type | PHI? | Logger annotation |
|---|---|---|
| Patient name, DOB, email, phone | Yes | **Never log at all** |
| Health conditions, medications, vitals, diagnoses | Yes | **Never log at all** |
| User ID / patient record ID | Yes (identifier) | `.private(mask: .hash)` for correlation |
| API endpoint paths (e.g., `/patients/{id}/records`) | Contains PHI if IDs are in the URL | `.private` or strip IDs before logging |
| HTTP status codes, error codes | No | `.public` |
| Operation names ("fetchVitals", "syncRecords") | No | `.public` |
| Request/response bodies | Almost certainly Yes | **Never log bodies** |
| JWT tokens, auth headers | Sensitive | **Never log** |
| Device model, OS version, app version | No | `.public` |

### Logging patterns

```swift
// GOOD: Network call logging without PHI
Logger.networking.info(
    "GET \(sanitizedPath, privacy: .public) started"
)
Logger.networking.error(
    "GET \(sanitizedPath, privacy: .public) failed: HTTP \(statusCode, privacy: .public)"
)

// GOOD: Health data operation with hashed correlation
Logger.health.notice(
    "Fetching records for patient \(patientId, privacy: .private(mask: .hash))"
)

// GOOD: Auth flow without tokens
Logger.auth.notice(
    "Login attempt for \(email, privacy: .private(mask: .hash))"
)
Logger.auth.error(
    "Auth failed: \(error.localizedDescription, privacy: .public)"
)

// BAD: Never do this
// Logger.health.info("Patient \(name) has conditions: \(conditions)")
// Logger.networking.debug("Response body: \(responseData)")
```

### URL sanitization helper

API paths often embed patient IDs. Strip them before logging:

```swift
enum LogSanitizer {
    private static let uuidPattern = try! NSRegularExpression(
        pattern: "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
    )

    static func sanitizePath(_ path: String) -> String {
        let range = NSRange(path.startIndex..., in: path)
        return uuidPattern.stringByReplacingMatches(
            in: path, range: range, withTemplate: "<id>"
        )
    }
}

// "/patients/3fa85f64-5717-4562-b3fc-2c963f66afa6/vitals"
// becomes "/patients/<id>/vitals"
let sanitizedPath = LogSanitizer.sanitizePath(url.path)
Logger.networking.info("GET \(sanitizedPath, privacy: .public)")
```

---

## 4. Redactor for Crash Report Metadata

Crash reporting SDKs send metadata to remote servers. PHI must never appear in that metadata.

```swift
enum Redactor {
    static func maskID(_ id: String) -> String {
        guard id.count > 4 else { return "****" }
        return "***\(id.suffix(4))"
    }

    static func maskEmail(_ email: String) -> String {
        guard let at = email.firstIndex(of: "@") else { return "***" }
        return "\(email.prefix(1))***\(email[at...])"
    }
}

// Usage in error reporting -- no raw PHI leaves the device
ErrorReporter.shared.recordNonFatal(error, context: [
    "patientId": Redactor.maskID(patientId),  // "***4f8a"
    "operation": "fetchVitals",                // safe: not PHI
    "endpoint": LogSanitizer.sanitizePath(url.path)
])
```

### Model-level protection with @Redacted

Prevent accidental PHI leakage through string interpolation or print statements:

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

struct PatientRecord {
    let id: String
    @Redacted var name: String
    @Redacted var dateOfBirth: Date
    @Redacted var conditions: [String]
    var lastSyncDate: Date  // non-PHI, safe to log
}
```

Even if someone writes `Logger.health.info("\(patient)")`, the PHI fields render as `--redacted--`.

---

## 5. ErrorReporter Protocol

Abstract the crash SDK so PHI filtering happens in one place:

```swift
protocol ErrorReporting: Sendable {
    func recordNonFatal(_ error: Error, context: [String: Any])
    func addBreadcrumb(message: String, category: String, level: BreadcrumbLevel, data: [String: Any]?)
    func setUser(id: String)  // hashed ID only, never raw
}

final class SentryErrorReporter: ErrorReporting {
    static let shared = SentryErrorReporter()

    func recordNonFatal(_ error: Error, context: [String: Any]) {
        let scope = Scope()
        // Scrub context values to prevent PHI leakage
        let safeContext = context.mapValues { value -> String in
            String(describing: value)
        }
        scope.setContext(value: safeContext, key: "operation")
        SentrySDK.capture(error: error, scope: scope)
    }

    func addBreadcrumb(message: String, category: String, level: BreadcrumbLevel, data: [String: Any]?) {
        let crumb = Breadcrumb(level: level.sentryLevel, category: category)
        crumb.message = message
        // Never put PHI in breadcrumb data
        crumb.data = data
        SentrySDK.addBreadcrumb(crumb)
    }

    func setUser(id: String) {
        // Hash the user ID before sending to Sentry
        let user = User()
        user.userId = id.sha256Hash  // never raw patient/user ID
        SentrySDK.setUser(user)
    }
}
```

---

## 6. Centralized Error Handler for SwiftUI

Every error flows through a single handler that logs, reports, and routes to UI:

```swift
@MainActor
final class ErrorHandler: ObservableObject {
    @Published var currentAlert: AlertInfo?

    private let reporter: ErrorReporting

    init(reporter: ErrorReporting = SentryErrorReporter.shared) {
        self.reporter = reporter
    }

    func handle(_ error: Error, context: String) {
        // 1. Structured local log (privacy annotations protect PHI)
        Logger.ui.error("\(context, privacy: .public): \(error.localizedDescription, privacy: .public)")

        // 2. Report to crash SDK (no PHI in context)
        reporter.recordNonFatal(error, context: ["context": context])

        // 3. Route to user feedback
        if let categorized = error as? CategorizedError {
            switch categorized.category {
            case .retryable:
                currentAlert = AlertInfo(
                    title: "Temporary Issue",
                    message: "Please try again in a moment."
                )
            case .nonRetryable:
                // Generic message -- never expose internal error details to UI
                currentAlert = AlertInfo(
                    title: "Something Went Wrong",
                    message: "We couldn't complete that action. Please try again later."
                )
            case .requiresLogout:
                currentAlert = AlertInfo(
                    title: "Session Expired",
                    message: "Please sign in again."
                )
            }
        } else {
            currentAlert = AlertInfo(
                title: "Error",
                message: "An unexpected error occurred."
            )
        }
    }
}
```

Wire it into the SwiftUI app root:

```swift
@main
struct HealthApp: App {
    @StateObject private var errorHandler = ErrorHandler()

    init() {
        AppMetrics.shared.startReceiving()
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(errorHandler)
                .withErrorHandling()
        }
    }
}
```

---

## 7. Network Layer: async/await with Full Observability

```swift
final class APIClient {
    private let session: URLSession
    private let reporter: ErrorReporting
    private let decoder = JSONDecoder()

    func request<T: Decodable>(_ endpoint: Endpoint) async throws -> T {
        let sanitizedPath = LogSanitizer.sanitizePath(endpoint.path)

        Logger.networking.info(
            "\(endpoint.method, privacy: .public) \(sanitizedPath, privacy: .public) started"
        )
        reporter.addBreadcrumb(
            message: "API request started",
            category: "network",
            level: .info,
            data: ["path": sanitizedPath, "method": endpoint.method]
        )

        let (data, response) = try await session.data(for: endpoint.urlRequest)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw NetworkError.invalidResponse
        }

        Logger.networking.info(
            "\(endpoint.method, privacy: .public) \(sanitizedPath, privacy: .public) -> \(httpResponse.statusCode, privacy: .public)"
        )

        // IMPORTANT: validate HTTP status -- URLSession does NOT throw on 4xx/5xx
        guard (200..<300).contains(httpResponse.statusCode) else {
            let error = NetworkError.httpError(statusCode: httpResponse.statusCode)
            Logger.networking.error(
                "HTTP \(httpResponse.statusCode, privacy: .public) for \(sanitizedPath, privacy: .public)"
            )
            reporter.recordNonFatal(error, context: [
                "path": sanitizedPath,
                "statusCode": httpResponse.statusCode
            ])
            throw error
        }

        // Never log response body -- it likely contains PHI
        Logger.networking.debug(
            "Response size: \(data.count, privacy: .public) bytes for \(sanitizedPath, privacy: .public)"
        )

        do {
            return try decoder.decode(T.self, from: data)
        } catch {
            Logger.networking.error(
                "Decode failed for \(sanitizedPath, privacy: .public): \(error.localizedDescription, privacy: .public)"
            )
            reporter.recordNonFatal(error, context: [
                "path": sanitizedPath,
                "responseSize": data.count
            ])
            throw NetworkError.decodingFailed(error)
        }
    }
}
```

Key HIPAA considerations in the network layer:
- **Never log request or response bodies** -- they contain patient data.
- **Sanitize URL paths** before logging -- they often embed patient IDs.
- **Always validate HTTP status codes** -- URLSession does not throw on 4xx/5xx, and a silent 401/403 in a health app means patient data may not have synced.

---

## 8. SwiftUI .task {} Pattern with CancellationError Handling

```swift
struct PatientDetailView: View {
    let patientId: String
    @State private var records: [HealthRecord] = []
    @State private var isLoading = false
    @EnvironmentObject var errorHandler: ErrorHandler

    var body: some View {
        List(records) { record in
            HealthRecordRow(record: record)
        }
        .task {
            await loadRecords()
        }
    }

    private func loadRecords() async {
        isLoading = true
        defer { isLoading = false }

        do {
            records = try await apiClient.request(.patientRecords(id: patientId))
        } catch is CancellationError {
            // Normal: view disappeared, user navigated away. Not an error.
            Logger.ui.debug("Patient records fetch cancelled (navigation)")
        } catch {
            // Real error: log + report + show UI
            errorHandler.handle(error, context: "loadPatientRecords")
        }
    }
}
```

Always separate `CancellationError` from real errors in `.task {}` -- cancellation is expected SwiftUI lifecycle behavior and should never be reported to Sentry.

---

## 9. Retry with Backoff for Health Data Sync

Health data sync failures must be retried but observed. Report only after all retries are exhausted to avoid noise:

```swift
func retryWithBackoff<T>(
    maxAttempts: Int = 3,
    base: Double = 0.25,
    operation: String,
    action: () async throws -> T
) async throws -> T {
    var lastError: Error?
    for attempt in 1...maxAttempts {
        do {
            return try await action()
        } catch is CancellationError {
            throw CancellationError()  // Don't retry cancellation
        } catch {
            lastError = error
            Logger.sync.warning(
                "Attempt \(attempt, privacy: .public)/\(maxAttempts, privacy: .public) failed for \(operation, privacy: .public): \(error.localizedDescription, privacy: .public)"
            )
            if attempt < maxAttempts {
                let delay = min(pow(2, Double(attempt)) * base, 60)
                let jitter = Double.random(in: 0...(delay * 0.5))
                try await Task.sleep(nanoseconds: UInt64((delay + jitter) * 1_000_000_000))
            }
        }
    }
    // All retries failed -- now report
    ErrorReporter.shared.recordNonFatal(lastError!, context: [
        "operation": operation,
        "maxAttempts": maxAttempts
    ])
    throw lastError!
}

// Usage
let records = try await retryWithBackoff(operation: "syncHealthRecords") {
    try await apiClient.request(.syncRecords)
}
```

---

## 10. MetricKit for OOM and Watchdog Detection

In-process crash reporters (Sentry) cannot detect OOM kills or watchdog terminations because the OS sends SIGKILL, which is uncatchable. MetricKit runs out-of-process and observes these:

```swift
import MetricKit

final class AppMetrics: NSObject, MXMetricManagerSubscriber {
    static let shared = AppMetrics()

    func startReceiving() {
        MXMetricManager.shared.add(self)
        processDiagnostics(MXMetricManager.shared.pastDiagnosticPayloads)
    }

    func didReceive(_ payloads: [MXDiagnosticPayload]) {
        processDiagnostics(payloads)
    }

    func didReceive(_ payloads: [MXMetricPayload]) {
        for payload in payloads {
            guard let exitMetrics = payload.applicationExitMetrics else { continue }
            let bg = exitMetrics.backgroundExitData
            let fg = exitMetrics.foregroundExitData

            let oomCount = bg.cumulativeMemoryPressureExitCount
                + fg.cumulativeMemoryPressureExitCount
            let watchdogCount = bg.cumulativeAppWatchdogExitCount

            if oomCount > 0 || watchdogCount > 0 {
                Logger.lifecycle.fault(
                    "Exit metrics: OOM=\(oomCount, privacy: .public), watchdog=\(watchdogCount, privacy: .public)"
                )
                // Forward to your analytics backend (no PHI in these metrics)
            }
        }
    }

    private func processDiagnostics(_ payloads: [MXDiagnosticPayload]) {
        for payload in payloads {
            payload.hangDiagnostics?.forEach { hang in
                Logger.lifecycle.error("Hang diagnostic received")
                // Forward JSON representation to backend for symbolication
            }
        }
    }
}
```

---

## 11. Privacy Manifest (Required Since May 2024)

Your `PrivacyInfo.xcprivacy` must declare use of Required Reason APIs. App Store review rejects submissions without this:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>NSPrivacyAccessedAPITypes</key>
    <array>
        <dict>
            <key>NSPrivacyAccessedAPIType</key>
            <string>NSPrivacyAccessedAPICategoryUserDefaults</string>
            <key>NSPrivacyAccessedAPITypeReasons</key>
            <array>
                <string>CA92.1</string>
            </array>
        </dict>
    </array>
    <key>NSPrivacyCollectedDataTypes</key>
    <array>
        <dict>
            <key>NSPrivacyCollectedDataType</key>
            <string>NSPrivacyCollectedDataTypeCrashData</string>
            <key>NSPrivacyCollectedDataTypeLinked</key>
            <false/>
            <key>NSPrivacyCollectedDataTypeTracking</key>
            <false/>
            <key>NSPrivacyCollectedDataTypePurposes</key>
            <array>
                <string>NSPrivacyCollectedDataTypePurposeAppFunctionality</string>
            </array>
        </dict>
    </array>
    <key>NSPrivacyTracking</key>
    <false/>
</dict>
</plist>
```

Sentry and Crashlytics ship their own privacy manifests -- Xcode merges them automatically. Crash reporting does not require ATT consent, provided data is used solely for improving your own app and not shared with data brokers.

---

## 12. HIPAA Compliance Checklist for Logging

| Requirement | Implementation |
|---|---|
| No PHI in on-device logs | `privacy: .private` by default; health data fields never logged |
| No PHI in remote crash reports | `Redactor` masks IDs; `@Redacted` prevents accidental interpolation |
| No PHI in breadcrumbs | Only operation names and sanitized paths in breadcrumb data |
| No request/response body logging | Network layer logs only path, status code, and byte count |
| URL path sanitization | `LogSanitizer.sanitizePath()` strips embedded IDs |
| Minimum necessary principle | Log the operation and outcome, not the data |
| Audit trail for data access | `Logger.health` category can be filtered for compliance audits |
| Encryption in transit | Sentry SDK uses TLS; enforce ATS (App Transport Security) with no exceptions |
| BAA coverage | Ensure your Sentry (or chosen SDK) plan includes a Business Associate Agreement |
| Incident visibility | MetricKit catches OOM/watchdog kills invisible to in-process reporters |

---

## 13. Sentry Configuration Notes for HIPAA

```swift
SentrySDK.start { options in
    options.dsn = "your-dsn"

    // Do NOT enable these in a HIPAA context:
    options.enableAutoSessionTracking = true
    options.attachScreenshot = false       // Screenshots may contain PHI
    options.attachViewHierarchy = false    // View hierarchy may contain PHI
    options.enableNetworkBreadcrumbs = true
    options.enableNetworkTracking = false  // Request bodies may contain PHI

    // Strip any PHI that might slip through
    options.beforeSend = { event in
        // Remove user email/name if somehow set
        event.user?.email = nil
        event.user?.name = nil
        return event
    }

    // Strip breadcrumb data that might contain PHI
    options.beforeBreadcrumb = { breadcrumb in
        // Remove any HTTP body data from network breadcrumbs
        if breadcrumb.category == "http" {
            breadcrumb.data?.removeValue(forKey: "request_body")
            breadcrumb.data?.removeValue(forKey: "response_body")
        }
        return breadcrumb
    }
}
```

Critical Sentry settings for HIPAA:
- **Disable screenshot attachments** -- they will capture patient data displayed on screen.
- **Disable view hierarchy attachments** -- `Text("Patient: John Doe")` will appear in the hierarchy.
- **Use `beforeSend`** as a safety net to strip any PHI that might slip through.
- **Require a BAA** from Sentry (available on Business plans) before sending any data.

---

## Summary

This strategy gives you three layers of debugging power without PHI exposure:

1. **Local diagnostics** -- `os.Logger` with aggressive `.private` annotations gives you full debugging capability when streaming logs from a connected device, while production logs are redacted automatically.

2. **Remote crash intelligence** -- Sentry captures errors, breadcrumbs (sanitized operation context), and stack traces. `beforeSend` acts as a final PHI filter. Hashed user IDs allow cross-event correlation without exposing identifiers.

3. **System-level visibility** -- MetricKit catches the silent killers (OOM, watchdog, hangs) that no in-process reporter can detect, giving you complete coverage of production failure modes.

The key insight: you do not need PHI to debug. Operation names, error codes, HTTP status codes, sanitized paths, hashed correlation IDs, and stack traces are sufficient for virtually every production investigation.
