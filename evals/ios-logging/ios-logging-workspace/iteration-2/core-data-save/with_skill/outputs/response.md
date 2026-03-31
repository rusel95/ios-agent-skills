## Problem: Silent Core Data Save Failure

This code has a critical observability problem -- `try?` completely discards any error thrown by `context.save()`, making Core Data failures invisible in production.

```swift
// BAD -- Silent data loss
func saveChanges() {
    try? viewContext.save()
}
```

Core Data saves fail for real, actionable reasons: validation errors, merge conflicts, unique constraint violations, and threading violations. Using `try?` destroys the error type, message, and all diagnostic context. You will never know *why* a save failed -- or even *that* it failed.

### Why this matters

`try?` is only acceptable for best-effort operations where failure is genuinely irrelevant (temp file cleanup, optional cache reads). Persistence is never irrelevant -- if a Core Data save fails, user data is lost without any indication.

### Fix: Use do/catch with full observability

```swift
import os

extension Logger {
    static let database = Logger(subsystem: Bundle.main.bundleIdentifier ?? "com.app", category: "database")
}

func saveChanges() {
    guard viewContext.hasChanges else { return }

    do {
        try viewContext.save()
    } catch {
        let nsError = error as NSError

        // 1. Structured log with privacy annotations
        Logger.database.error("Core Data save failed: code=\(nsError.code, privacy: .public) domain=\(nsError.domain, privacy: .public)")

        // 2. Surface detailed validation/conflict errors (Core Data packs multiple errors into NSDetailedErrorsKey)
        if let detailedErrors = nsError.userInfo[NSDetailedErrorsKey] as? [NSError] {
            for detail in detailedErrors {
                Logger.database.error("  Detail: \(detail.localizedDescription, privacy: .public)")
            }
        }

        // 3. Report to crash/analytics SDK for remote visibility
        ErrorReporter.shared.recordNonFatal(error, context: [
            "operation": "save",
            "errorCode": "\(nsError.code)"
        ])

        // 4. Roll back to consistent state
        viewContext.rollback()
    }
}
```

### What this fix addresses

1. **`try?` replaced with `do/catch`** -- errors are no longer silently discarded.
2. **`os.Logger` with privacy annotations** -- structured logging visible in Console.app and log archives, unlike `print()` which is invisible on production devices.
3. **`NSDetailedErrorsKey` inspection** -- Core Data often wraps multiple validation errors into a single compound error. Without unpacking this, you only see a generic failure message.
4. **Remote error reporting** -- `ErrorReporter.shared.recordNonFatal()` sends the failure to your crash SDK (Sentry, Crashlytics, etc.) so you can see it in production dashboards without a debugger attached.
5. **`context.rollback()`** -- after a failed save, the context is in an inconsistent state. Rolling back prevents corrupt data from persisting in memory and affecting subsequent operations.
6. **`hasChanges` guard** -- avoids unnecessary save calls when the context has no pending modifications.
