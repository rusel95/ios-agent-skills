# Replace print() with os.Logger and a Remote Error Reporter

## Why print() Is Wrong for Production

`print()` writes to stdout. On a production device with no debugger attached, stdout goes nowhere. Your logs are invisible. Beyond that, `print()` has no log levels, no privacy controls, no filtering, no persistence, and no way to search or stream logs remotely. When a bug shows up across thousands of devices, `print()` gives you nothing to work with.

## What to Use: Apple's os.Logger

Use the `os.Logger` API (available since iOS 14). It is Apple's unified logging system. It uses a binary representation that avoids string conversion at the call site, meaning `.debug`-level messages have effectively zero cost in production when not being streamed.

### Step 1: Create Logger Extensions with Subsystem and Category

```swift
import os

extension Logger {
    private static let subsystem = Bundle.main.bundleIdentifier!

    static let networking = Logger(subsystem: subsystem, category: "Networking")
    static let auth       = Logger(subsystem: subsystem, category: "Authentication")
    static let database   = Logger(subsystem: subsystem, category: "Database")
    static let ui         = Logger(subsystem: subsystem, category: "UI")
    static let payments   = Logger(subsystem: subsystem, category: "Payments")
    static let lifecycle  = Logger(subsystem: subsystem, category: "Lifecycle")
}
```

Add categories that match your app's domain areas. The subsystem is typically your bundle identifier; the category groups related messages for filtering in Console.app and Xcode.

### Step 2: Choose the Right Log Level

| Level | Persisted? | Use for |
|---|---|---|
| `.debug` | No (memory only, discarded if not streaming) | Development tracing, hot-path diagnostics |
| `.info` | Memory only (captured when faults occur) | Helpful but non-critical context |
| `.notice` | Persisted to disk | Important operational events |
| `.error` | Always persisted | Recoverable error conditions |
| `.fault` | Always persisted + process chain info | Bugs, unrecoverable failures |

Key point: `.debug` messages are free in production. The compiler optimizes away message creation entirely. You can leave verbose debug logging in shipping code safely.

### Step 3: Add Privacy Annotations (This Is Critical)

Dynamic strings are redacted by default in production logs -- they appear as `<private>` when no debugger is attached. You must annotate every interpolated value explicitly.

```swift
// BAD -- no privacy annotation, useless in production logs
Logger.networking.error("Request to \(url) failed for user \(userId)")
// Production output: "Request to <private> failed for user <private>"

// GOOD -- explicit privacy annotations
Logger.networking.error("Request to \(url.absoluteString, privacy: .public) failed for user \(userId, privacy: .private(mask: .hash))")
// Production output: "Request to /api/users failed for user <mask.hash: 'uZiZmp5vMXG4evDH=='>"
```

Privacy annotation cheat sheet:

| Annotation | When to use |
|---|---|
| `privacy: .public` | URL paths, error codes, status codes, operation names |
| `privacy: .private` | User IDs, emails, names, device IDs |
| `privacy: .private(mask: .hash)` | User IDs when you need to correlate events for the same user |
| `privacy: .sensitive` | Passwords, tokens, API keys (though these should not be logged at all) |

### Step 4: Systematic print() Replacement Table

| Old print() pattern | Logger replacement |
|---|---|
| `print("Loading data...")` | `Logger.networking.debug("Loading data...")` |
| `print("Error: \(error)")` | `Logger.networking.error("Failed: \(error.localizedDescription, privacy: .public)")` |
| `print("User: \(user.email)")` | `Logger.auth.info("User: \(user.email, privacy: .private(mask: .hash))")` |
| `print("Response: \(data)")` | `Logger.networking.debug("Response size: \(data.count, privacy: .public) bytes")` |
| `debugPrint(object)` | `Logger.ui.debug("State: \(String(describing: object), privacy: .private)")` |

## Logger Alone Is Not Enough: Add a Remote Error Reporter

`os.Logger` handles local device logging. But when errors happen in production, you need them reported to a remote service so you can investigate without physical access to the device. Set up an `ErrorReporter` protocol that abstracts your crash reporting SDK:

```swift
protocol ErrorReporter: Sendable {
    func recordNonFatal(_ error: Error, context: [String: Any])
    func addBreadcrumb(message: String, category: String, level: BreadcrumbLevel, data: [String: Any]?)
    func setUserID(_ userID: String?)
}
```

Then implement it for your chosen SDK (Sentry, Firebase Crashlytics, or both via a composite). Every catch block should do two things:

```swift
do {
    try await fetchItems()
} catch {
    // 1. Local structured log with privacy annotations
    Logger.networking.error("Fetch failed: \(error.localizedDescription, privacy: .public)")

    // 2. Remote report to crash SDK
    ErrorReporter.shared.recordNonFatal(error, context: ["operation": "fetchItems"])
}
```

### Which SDK to Choose

- **Firebase-heavy project** (Auth, Firestore, Push): Firebase Crashlytics (free, tight integration)
- **Standalone or wants rich observability**: Sentry (best error context, breadcrumbs, performance monitoring)
- **Needs product analytics + errors**: Sentry for crashes + PostHog for analytics and session replay

Never run two fatal crash reporters simultaneously -- they conflict on signal handlers. Pick one for fatal crashes and disable the crash handler on the secondary.

## Common Anti-Patterns to Fix While You Are At It

While replacing `print()`, also audit these patterns that silently swallow errors:

1. **`try?` on operations where failure matters** -- network, persistence, auth, and user-facing operations must use `do/catch`, not `try?`. Reserve `try?` for genuinely optional operations like temp file cleanup.

2. **`Task {}` with throwing code but no `do/catch`** -- `Task.init` is `@discardableResult`, so thrown errors vanish silently. Every `Task {}` containing `try` needs an explicit `do/catch` inside it.

3. **SwiftUI `.task {}` without error handling** -- the `.task` modifier does not throw. Errors must be caught inside it. Also distinguish `CancellationError` (normal view lifecycle) from real errors.

4. **`catch { print(error) }` with no further action** -- logging the error locally is step one, but without reporting to a remote service, you will never see it in production.

5. **URLSession not checking HTTP status codes** -- `URLSession` only throws for transport-level failures. A 500 response is returned as a successful `(Data, URLResponse)`. Always validate the status code.

## Summary

Replace `print()` with `os.Logger` using subsystem/category extensions and privacy annotations on every dynamic value. Pair it with a remote error reporter (Sentry or Crashlytics) behind a protocol abstraction. Every catch block should both log locally via Logger and report remotely via ErrorReporter. This transforms production debugging from guesswork into a structured investigation.
