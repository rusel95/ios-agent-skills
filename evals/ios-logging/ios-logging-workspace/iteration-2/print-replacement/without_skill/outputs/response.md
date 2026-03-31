# Replacing print() in Your iOS App

## The Problem with print()

Using `print()` throughout an iOS app has several significant drawbacks:

- **No log levels** -- you cannot distinguish between debug noise, informational messages, warnings, and errors.
- **No filtering** -- every print statement produces output; you cannot selectively enable or disable categories of logs.
- **No metadata** -- no timestamps, subsystem labels, or source location information is attached automatically.
- **Stripped in Release by default** -- `print()` still executes in Release builds (the output just goes nowhere useful), wasting CPU cycles on string interpolation.
- **Not visible in Console.app** -- you cannot use Apple's Console application to inspect logs from a device or simulator when using `print()`.

## What to Use Instead

### 1. os.Logger (Recommended -- iOS 14+)

`os.Logger` (part of the Unified Logging system, also known as `os_log`) is Apple's recommended logging API. It is the same system that the OS itself uses.

```swift
import os

extension Logger {
    static let networking = Logger(subsystem: Bundle.main.bundleIdentifier!, category: "Networking")
    static let ui = Logger(subsystem: Bundle.main.bundleIdentifier!, category: "UI")
    static let persistence = Logger(subsystem: Bundle.main.bundleIdentifier!, category: "Persistence")
}
```

Usage:

```swift
Logger.networking.debug("Request started for URL: \(url)")
Logger.networking.info("Received response with status \(statusCode)")
Logger.networking.error("Request failed: \(error.localizedDescription)")
```

**Why os.Logger is the right choice:**

- **Five log levels**: `.debug`, `.info`, `.notice`, `.error`, `.fault` -- each with different persistence and performance characteristics.
- **Structured categories**: The subsystem/category model lets you filter logs precisely in Console.app or with the `log` CLI tool.
- **Performance**: Log messages are not fully formatted unless they will actually be displayed. Debug-level messages are discarded entirely in production builds, with near-zero overhead.
- **Privacy by default**: String interpolations are redacted in non-debug builds unless you explicitly mark them with `privacy: .public`. This prevents accidental leaking of user data in logs.
- **Console.app integration**: You can stream and filter live logs from a connected device using Console.app or `log stream --predicate 'subsystem == "com.yourapp"'`.
- **Signpost support**: Integrates with `os_signpost` for Instruments performance profiling.

### 2. OSLog (iOS 10-13 compatibility)

If you need to support iOS versions earlier than 14, use the older `os_log` function-based API:

```swift
import os.log

let networkLog = OSLog(subsystem: Bundle.main.bundleIdentifier!, category: "Networking")

os_log("Request started for %{public}@", log: networkLog, type: .debug, url.absoluteString)
os_log("Request failed: %{public}@", log: networkLog, type: .error, error.localizedDescription)
```

This uses printf-style format strings rather than string interpolation but provides the same unified logging benefits.

### 3. Log Levels Explained

| Level     | Use Case                                    | Persistence                        |
|-----------|---------------------------------------------|------------------------------------|
| `.debug`  | Developer-only detail, loops, verbose state  | Not persisted; only visible during live streaming |
| `.info`   | Helpful but non-essential information        | Persisted only during `log collect` |
| `.notice` | Default level; noteworthy runtime events     | Persisted up to storage limit       |
| `.error`  | Errors that are recoverable                  | Persisted up to storage limit       |
| `.fault`  | Bugs and unrecoverable failures              | Persisted up to storage limit       |

### 4. Practical Migration Pattern

Create a thin wrapper so you can migrate incrementally:

```swift
import os

enum Log {
    static let general = Logger(subsystem: Bundle.main.bundleIdentifier!, category: "General")
    static let network = Logger(subsystem: Bundle.main.bundleIdentifier!, category: "Network")
    static let storage = Logger(subsystem: Bundle.main.bundleIdentifier!, category: "Storage")
    static let auth    = Logger(subsystem: Bundle.main.bundleIdentifier!, category: "Auth")
}
```

Then replace `print()` calls file by file:

```swift
// Before
print("User logged in: \(user.id)")

// After
Log.auth.info("User logged in: \(user.id, privacy: .private)")
```

### 5. Privacy Annotations

One of the most important features of unified logging is automatic redaction of dynamic data:

```swift
// Redacted in release (shows <private>)
Logger.auth.info("Token: \(token)")

// Explicitly public -- use only for non-sensitive data
Logger.network.info("Endpoint: \(endpoint, privacy: .public)")

// Explicitly private with a hash for correlation
Logger.auth.info("User ID: \(userId, privacy: .private(mask: .hash))")
```

### 6. When You Might Still Use print()

- **Playgrounds and throwaway scripts** where you need quick output.
- **Command-line tools** where stdout is the expected output channel.
- **Unit test debugging** (though even here, `os.Logger` works and gives you filtering).

## Summary

Replace `print()` with `os.Logger` (iOS 14+) or `os_log` (iOS 10+). You get log levels, categories, privacy controls, near-zero overhead for disabled levels, and full integration with Console.app and Instruments. The migration can be done incrementally by defining a set of static `Logger` instances organized by subsystem area and replacing `print()` calls one file at a time.
