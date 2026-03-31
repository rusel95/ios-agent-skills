# Enterprise Error Handling Patterns

## Centralized Error Handling Service

SwiftUI lacks React-style Error Boundaries — there is no built-in mechanism that catches and contains errors at a component boundary. When an error occurs inside a SwiftUI view hierarchy, it either crashes or is swallowed silently. This makes centralized error handling essential: every error should flow through a single service that decides the response based on error category.

### CategorizedError Protocol

```swift
enum ErrorCategory {
    case retryable
    case nonRetryable
    case requiresLogout
}

protocol CategorizedError: Error {
    var category: ErrorCategory { get }
}

extension NetworkError: CategorizedError {
    var category: ErrorCategory {
        switch self {
        case .timeout, .serverError(5...):
            return .retryable
        case .notFound, .decodingFailed:
            return .nonRetryable
        case .unauthorized:
            return .requiresLogout
        }
    }
}
```

### Centralized Handler

```swift
@MainActor
final class ErrorHandler: ObservableObject {
    @Published var currentAlert: AlertInfo?

    func handle(_ error: Error, context: String) {
        // 1. Always log
        Logger.ui.error("\(context, privacy: .public): \(error.localizedDescription, privacy: .public)")

        // 2. Always report
        ErrorReporter.shared.recordNonFatal(error, context: ["context": context])

        // 3. Route based on category
        if let categorized = error as? CategorizedError {
            switch categorized.category {
            case .retryable:
                currentAlert = AlertInfo(
                    title: "Temporary Issue",
                    message: "Please try again in a moment.",
                    retryAction: { /* caller provides */ }
                )
            case .nonRetryable:
                currentAlert = AlertInfo(
                    title: "Something Went Wrong",
                    message: error.localizedDescription
                )
            case .requiresLogout:
                AuthManager.shared.logout()
                currentAlert = AlertInfo(
                    title: "Session Expired",
                    message: "Please sign in again."
                )
            }
        } else {
            currentAlert = AlertInfo(
                title: "Error",
                message: error.localizedDescription
            )
        }
    }
}
```

### SwiftUI Integration

```swift
struct ErrorHandlingModifier: ViewModifier {
    @EnvironmentObject var errorHandler: ErrorHandler

    func body(content: Content) -> some View {
        content.alert(item: $errorHandler.currentAlert) { alert in
            Alert(
                title: Text(alert.title),
                message: Text(alert.message),
                dismissButton: .default(Text("OK"))
            )
        }
    }
}

extension View {
    func withErrorHandling() -> some View {
        modifier(ErrorHandlingModifier())
    }
}

// App root
@main
struct MyApp: App {
    @StateObject private var errorHandler = ErrorHandler()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(errorHandler)
                .withErrorHandling()
        }
    }
}
```

## Retry with Exponential Backoff and Observability

```swift
func retryWithBackoff<T>(
    maxAttempts: Int = 3,
    base: Double = 0.25,
    operation: String = "unknown",
    action: () async throws -> T
) async throws -> T {
    var lastError: Error?
    for attempt in 1...maxAttempts {
        do {
            return try await action()
        } catch {
            lastError = error
            Logger.networking.warning(
                "Attempt \(attempt, privacy: .public)/\(maxAttempts, privacy: .public) failed for \(operation, privacy: .public): \(error.localizedDescription, privacy: .public)"
            )
            ErrorReporter.shared.addBreadcrumb(
                message: "Retry attempt \(attempt) failed",
                category: "network", level: .warning,
                data: ["attempt": attempt, "operation": operation, "error": "\(error)"]
            )
            if attempt < maxAttempts {
                let delay = min(pow(2, Double(attempt)) * base, 60)
                let jitter = Double.random(in: 0...(delay * 0.5))
                try await Task.sleep(nanoseconds: UInt64((delay + jitter) * 1_000_000_000))
            }
        }
    }
    // All retries exhausted — report as non-fatal
    ErrorReporter.shared.recordNonFatal(lastError!, context: [
        "operation": operation,
        "maxAttempts": maxAttempts
    ])
    throw lastError!
}
```

Only report to the crash SDK **after all retries are exhausted** — prevents noise from transient failures.

## App Extensions Run in Separate Processes

Widgets, notification service extensions, share extensions, and other extensions run in their own sandboxed processes. Crash reporting SDKs must be initialized separately in each extension's entry point.

```swift
// NotificationServiceExtension — separate process
class NotificationService: UNNotificationServiceExtension {
    override func didReceive(
        _ request: UNNotificationRequest,
        withContentHandler contentHandler: @escaping (UNNotificationContent) -> Void
    ) {
        // Initialize crash SDK for this extension process
        SentrySDK.start { options in
            options.dsn = "..."
            options.enableAutoSessionTracking = false // Important for extensions
        }
        // ... handle notification
    }
}
```

**Extension checklist:**
- Each extension target needs its own crash SDK initialization
- Each extension needs dSYM upload in its build phases
- For Crashlytics: each extension needs its own `GoogleService-Info.plist`
- Use App Groups to share error configuration between main app and extensions
- Memory limits are lower in extensions (~50MB for widgets) — monitor closely

## Background Task Error Capture

BGTaskScheduler failures are invisible by default.

```swift
func registerBackgroundTasks() {
    BGTaskScheduler.shared.register(
        forTaskWithIdentifier: "com.app.sync",
        using: nil
    ) { task in
        self.handleSync(task: task as! BGProcessingTask)
    }
}

func handleSync(task: BGProcessingTask) {
    // Schedule next occurrence FIRST — before any work
    scheduleNextSync()

    // Handle expiration (system is about to kill this task)
    task.expirationHandler = {
        Logger.lifecycle.warning("Background sync expired by system")
        ErrorReporter.shared.addBreadcrumb(
            message: "BGTask expired",
            category: "background", level: .warning, data: nil
        )
        task.setTaskCompleted(success: false)
    }

    Task {
        do {
            try await performSync()
            task.setTaskCompleted(success: true)
        } catch {
            Logger.lifecycle.error("Background sync failed: \(error.localizedDescription, privacy: .public)")
            ErrorReporter.shared.recordNonFatal(error, context: ["task": "backgroundSync"])
            task.setTaskCompleted(success: false)
        }
    }
}
```

The watchdog timer produces SIGKILL for background tasks that exceed their time — unrecoverable and only visible through MetricKit's application exit metrics.
