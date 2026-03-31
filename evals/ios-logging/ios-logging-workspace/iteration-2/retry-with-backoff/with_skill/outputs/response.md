# Retry with Exponential Backoff, Jitter, and Full Observability

## Prerequisites

Before implementing retry logic, you need the `os.Logger` extension and `ErrorReporter` protocol from your observability stack. If you don't have these yet, set them up first.

### Logger Extension

```swift
import os

extension Logger {
    private static let subsystem = Bundle.main.bundleIdentifier!

    static let networking = Logger(subsystem: subsystem, category: "Networking")
}
```

### ErrorReporter Protocol

```swift
protocol ErrorReporter: Sendable {
    func recordNonFatal(_ error: Error, context: [String: Any])
    func addBreadcrumb(message: String, category: String, level: BreadcrumbLevel, data: [String: Any]?)
    func setUserID(_ userID: String?)
    func setCustomKey(_ key: String, value: Any)
    func log(_ message: String)
}

enum BreadcrumbLevel: String, Sendable {
    case debug, info, warning, error, fatal
}
```

Wrap your chosen crash SDK (Sentry, Crashlytics, etc.) behind this protocol. Never call SDK APIs directly throughout your codebase.

## Retry Function with Observability

```swift
import os

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

            // 1. ALWAYS log with os.Logger and privacy annotations
            Logger.networking.warning(
                "Attempt \(attempt, privacy: .public)/\(maxAttempts, privacy: .public) failed for \(operation, privacy: .public): \(error.localizedDescription, privacy: .public)"
            )

            // 2. ALWAYS add a breadcrumb for crash report context
            ErrorReporter.shared.addBreadcrumb(
                message: "Retry attempt \(attempt) failed",
                category: "network",
                level: .warning,
                data: [
                    "attempt": attempt,
                    "operation": operation,
                    "error": "\(error)"
                ]
            )

            // 3. Wait with exponential backoff + jitter before next attempt
            if attempt < maxAttempts {
                let delay = min(pow(2, Double(attempt)) * base, 60)
                let jitter = Double.random(in: 0...(delay * 0.5))
                try await Task.sleep(nanoseconds: UInt64((delay + jitter) * 1_000_000_000))
            }
        }
    }

    // All retries exhausted -- report as non-fatal to crash SDK
    ErrorReporter.shared.recordNonFatal(lastError!, context: [
        "operation": operation,
        "maxAttempts": maxAttempts
    ])
    throw lastError!
}
```

### Key design decisions

**Exponential backoff formula:** `min(2^attempt * base, 60)`. With `base = 0.25`, the delays before jitter are:

| Attempt | Base delay | With up to 50% jitter |
|---------|-----------|----------------------|
| 1 (after 1st failure) | 0.5s | 0.5 -- 0.75s |
| 2 (after 2nd failure) | 1.0s | 1.0 -- 1.5s |
| 3 would exceed max | n/a | throws |

The 60-second cap prevents absurd waits if you increase `maxAttempts`.

**Jitter range:** `0...(delay * 0.5)` adds up to 50% randomness on top of the base delay. This decorrelates retries across multiple clients hitting the same endpoint, preventing thundering herd problems. The jitter is additive (not replacing the base), so you always wait at least the base delay.

**Report only after all retries are exhausted.** Individual attempt failures are logged as breadcrumbs (`.warning` level), but `recordNonFatal` is called only once, after the final failure. This prevents noise from transient failures flooding your crash dashboard.

## Usage Examples

### Network request with retry

```swift
func fetchUserProfile(id: String) async throws -> UserProfile {
    let profile = try await retryWithBackoff(
        maxAttempts: 3,
        operation: "fetchUserProfile"
    ) {
        let (data, response) = try await URLSession.shared.data(
            from: URL(string: "https://api.example.com/users/\(id)")!
        )

        // Validate HTTP status -- URLSession does NOT throw on 4xx/5xx
        guard let httpResponse = response as? HTTPURLResponse else {
            throw NetworkError.invalidResponse
        }

        guard (200...299).contains(httpResponse.statusCode) else {
            throw NetworkError.serverError(httpResponse.statusCode)
        }

        return try JSONDecoder().decode(UserProfile.self, from: data)
    }
    return profile
}
```

**Important:** `URLSession` does not throw on HTTP 4xx/5xx status codes. It only throws on transport-level failures (no network, DNS failure, TLS errors). You must check the status code yourself, otherwise a 500 response silently succeeds.

### SwiftUI integration with `.task {}` modifier

```swift
struct ProfileView: View {
    @State private var profile: UserProfile?
    @State private var errorMessage: String?
    @EnvironmentObject var errorHandler: ErrorHandler

    var body: some View {
        Group {
            if let profile {
                ProfileContent(profile: profile)
            } else if let errorMessage {
                ErrorView(message: errorMessage)
            } else {
                ProgressView()
            }
        }
        .task {
            do {
                profile = try await fetchUserProfile(id: "123")
            } catch is CancellationError {
                // Normal -- view disappeared, do NOT log as error
                return
            } catch {
                errorMessage = error.localizedDescription
                errorHandler.handle(error, context: "ProfileView.loadProfile")
            }
        }
    }
}
```

**Always distinguish `CancellationError` from real errors in `.task {}` modifiers.** SwiftUI cancels the task when the view disappears. Logging cancellation as an error creates false noise.

### Categorizing errors for retry decisions

Not all errors should be retried. Combine the retry function with error categorization so you only retry transient failures:

```swift
enum NetworkError: Error {
    case timeout
    case serverError(Int)
    case notFound
    case decodingFailed(Error)
    case unauthorized
    case invalidResponse
    case noConnection
}

extension NetworkError: CategorizedError {
    var category: ErrorCategory {
        switch self {
        case .timeout, .serverError(500...599), .noConnection:
            return .retryable
        case .notFound, .decodingFailed, .invalidResponse:
            return .nonRetryable
        case .unauthorized:
            return .requiresLogout
        case .serverError:
            return .nonRetryable
        }
    }
}
```

Then gate retries on the category:

```swift
func fetchWithSmartRetry<T>(
    maxAttempts: Int = 3,
    base: Double = 0.25,
    operation: String,
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
                category: "network",
                level: .warning,
                data: [
                    "attempt": attempt,
                    "operation": operation,
                    "error": "\(error)"
                ]
            )

            // Stop retrying if the error is not transient
            if let categorized = error as? CategorizedError,
               categorized.category != .retryable {
                Logger.networking.error(
                    "Non-retryable error for \(operation, privacy: .public), aborting retries"
                )
                break
            }

            if attempt < maxAttempts {
                let delay = min(pow(2, Double(attempt)) * base, 60)
                let jitter = Double.random(in: 0...(delay * 0.5))
                try await Task.sleep(nanoseconds: UInt64((delay + jitter) * 1_000_000_000))
            }
        }
    }

    ErrorReporter.shared.recordNonFatal(lastError!, context: [
        "operation": operation,
        "maxAttempts": maxAttempts
    ])
    throw lastError!
}
```

This avoids wasting time retrying a 404 or a decoding error that will never succeed.

## What the observability gives you

When a retry-exhausted failure hits your crash dashboard, you see:

1. **Breadcrumb trail** showing each attempt's failure reason and timing
2. **Non-fatal error** with the final error details and operation name
3. **Structured os.Logger output** filterable by the `Networking` category in Console.app or Xcode's structured logging console
4. **Privacy-safe logs** -- operation names and attempt counts are `.public`, while user data stays redacted

This turns a "the network call sometimes fails" report into a 15-minute investigation: check the breadcrumbs for the pattern (all timeouts? mixed 500s? auth failures?), filter by operation name, and correlate with server-side logs.
