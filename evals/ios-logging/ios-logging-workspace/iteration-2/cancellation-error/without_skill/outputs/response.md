# CancellationError in SwiftUI `.task {}` — Is It a Real Problem?

No, `CancellationError` here is **not a crash or a bug** — it is expected behavior. However, the way your code handles it *is* a problem worth fixing.

## Why CancellationError Happens

SwiftUI's `.task {}` modifier ties the lifetime of the async work to the lifetime of the view. When the view disappears (user navigates away, tab switches, etc.), SwiftUI **automatically cancels** the structured concurrency task. If your `service.fetch()` call uses `URLSession` or any cancellation-aware async API, it will throw `CancellationError` when the task is cancelled.

This is normal, intentional, and part of how structured concurrency works in Swift.

## The Actual Problem in Your Code

The issue is that your `catch` block treats **all** errors the same. When a `CancellationError` is thrown, your code:

1. Reports it as a non-fatal error to your crash reporter — polluting your error logs with noise
2. Sets `showError = true` — showing an error alert to a user who simply navigated away

Both of these are incorrect behaviors for a cancellation.

## The Fix

Filter out `CancellationError` before handling the error:

```swift
.task {
    do {
        data = try await service.fetch()
    } catch is CancellationError {
        // Task was cancelled because the view disappeared.
        // This is expected — do nothing.
        return
    } catch {
        ErrorReporter.shared.recordNonFatal(error, context: ["screen": "home"])
        showError = true
    }
}
```

Alternatively, you can check `Task.isCancelled` at the catch site or use the error's type:

```swift
} catch {
    guard !Task.isCancelled else { return }
    ErrorReporter.shared.recordNonFatal(error, context: ["screen": "home"])
    showError = true
}
```

Both approaches work. The explicit `catch is CancellationError` pattern is generally preferred because it is more readable and clearly communicates intent.

## When CancellationError *Could* Indicate a Real Issue

There are a few scenarios where frequent cancellations might point to an underlying design problem:

- **Rapid view reloading**: If your view is being created and destroyed rapidly (e.g., inside a `List` or due to unnecessary state changes causing view identity resets), you may be starting and cancelling network requests excessively. This wastes resources even though each individual cancellation is harmless.
- **Missing data caching**: If every appearance triggers a network call that gets cancelled on disappearance, consider caching results in a view model or repository layer so repeated appearances don't repeat the fetch.

## Summary

- `CancellationError` from `.task {}` is **normal** and expected when a view disappears.
- **Always** filter it out before error reporting and user-facing error UI.
- Check whether frequent cancellations suggest a view lifecycle or caching design issue.
- Clean up your crash reports by excluding cancellation errors — they obscure real problems.
