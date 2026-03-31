# CancellationError in SwiftUI `.task {}` -- Not a Bug, but Your Code Has a Real Problem

## Short Answer

`CancellationError` is **not a real problem** -- it is normal SwiftUI lifecycle behavior. When a view disappears (user navigates away, tab switches, sheet dismisses), SwiftUI cancels the `.task {}` work by throwing `CancellationError`. This is expected and correct.

However, **your code has an observability problem**: you are recording `CancellationError` as a non-fatal error in your crash reports. This pollutes your error dashboard with noise, making it harder to spot genuine failures.

## Why CancellationError Happens

The `.task` modifier's closure has the signature `@Sendable () async -> Void`. When the view disappears, SwiftUI cooperatively cancels the structured task. Any `try await` call that respects cancellation (which `URLSession` and most well-behaved async APIs do) will throw `CancellationError` at the next suspension point.

Common scenarios:
- User taps back before the network call finishes
- A `TabView` switches tabs while data is loading
- A sheet or `NavigationLink` destination is dismissed quickly
- A `.task(id:)` restarts because its `id` value changed, cancelling the previous run

All of these are normal user interactions, not failures.

## The Fix

Filter `CancellationError` **before** reporting to your crash SDK. Cancellation is lifecycle, not an error:

```swift
.task {
    do {
        data = try await service.fetch()
    } catch is CancellationError {
        // View disappeared -- this is expected, not a failure.
        // Do NOT report to ErrorReporter. Do NOT set error state.
        return
    } catch {
        Logger.networking.error(
            "Home fetch failed: \(error.localizedDescription, privacy: .public)"
        )
        ErrorReporter.shared.recordNonFatal(error, context: ["screen": "home"])
        showError = true
    }
}
```

### What Changed and Why

1. **`catch is CancellationError` comes first** -- Pattern-matching on the error type separates cancellation from real failures. The order matters: if the general `catch` runs first, it catches everything including cancellation.

2. **No `ErrorReporter` call for cancellation** -- Reporting cancellation as a non-fatal creates noise. If your crash dashboard shows hundreds of `CancellationError` entries, you will miss the real failures hiding among them. This is the core issue with your current code.

3. **No `showError = true` for cancellation** -- If the user navigated away, showing an error banner on a view they already left is pointless (and can cause state issues if the view reappears).

4. **Added `Logger` for real errors** -- Your current code reports to the crash SDK but does not log locally with `os.Logger`. Both are needed: `Logger` gives you on-device diagnostics with privacy annotations, while `ErrorReporter` gives you remote visibility. Use `Logger` at the `.error` level so the message is always persisted to the unified logging system.

## A Deeper Pattern: Checking Cancellation Inside Long Operations

If your `service.fetch()` does multiple sequential async steps, check for cancellation between them to avoid partial work:

```swift
func fetch() async throws -> HomeData {
    let profile = try await api.getProfile()
    try Task.checkCancellation() // Bail early if view disappeared
    let feed = try await api.getFeed(for: profile.id)
    try Task.checkCancellation()
    return HomeData(profile: profile, feed: feed)
}
```

This ensures you do not start a second network call when the first one succeeded but the view is already gone.

## Summary

| Scenario | Action |
|---|---|
| `CancellationError` | Silently return -- normal lifecycle |
| Network/server error | Log with `Logger.error()` + report via `ErrorReporter` + show user error state |
| Decoding error | Log with `Logger.error()` + report via `ErrorReporter` + show user error state |

The rule: **always distinguish `CancellationError` from real errors in every `.task {}` block**. Cancellation is the SwiftUI runtime telling you the work is no longer needed -- acknowledge it and move on.
