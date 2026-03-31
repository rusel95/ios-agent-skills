# Handling and Reporting Errors in a Combine Pipeline Without Killing It

## The Problem With Your Current Setup

Your pipeline has a critical flaw: when `processItem(item)` emits a failure, the entire Combine pipeline **terminates permanently**. This is a fundamental Combine behavior -- once a publisher emits a `.failure` completion, it cancels itself and never publishes again. Your `receiveCompletion` closure fires once, the `print()` goes to stdout (invisible in production), and the pipeline is dead. No more items will ever be processed.

## Why This Happens

In Combine, a failure propagates up the chain and completes the entire pipeline. The `flatMap` operator forwards the inner publisher's failure to the outer pipeline. Once the outer pipeline receives that failure, it is finished -- there is no recovery.

Additionally, `print()` is not production error handling. It writes to stdout, which has no log levels, no privacy controls, no persistence, and is invisible on production devices without a debugger attached.

## The Fix: Handle Errors Inside flatMap

Error recovery must happen **inside the `flatMap` closure**, so the inner publisher's failure never reaches the outer pipeline. This keeps the outer pipeline alive to process future items.

```swift
import os
import Combine

// 1. Set up structured logging (do this once in a Logger extension file)
extension Logger {
    private static let subsystem = Bundle.main.bundleIdentifier!
    static let processing = Logger(subsystem: subsystem, category: "Processing")
}

// 2. Use an ErrorReporter protocol to abstract your crash SDK (Sentry, Crashlytics, etc.)
//    See the ErrorReporter protocol pattern below.

// 3. Fix the pipeline — catch errors inside flatMap
cancellable = publisher
    .flatMap { item in
        processItem(item)
            .catch { error -> Empty<ResultType, Never> in
                // Structured log with privacy annotations
                Logger.processing.error(
                    "processItem failed: \(error.localizedDescription, privacy: .public)"
                )
                // Report to crash/analytics SDK
                ErrorReporter.shared.recordNonFatal(
                    error,
                    context: ["operation": "processItem", "itemId": "\(item.id)"]
                )
                // Return Empty to skip this item without killing the pipeline
                return Empty()
            }
    }
    .sink(receiveValue: { result in
        handleResult(result)
    })
```

### Key changes explained:

1. **`.catch` inside `flatMap`**: The `.catch` operator on the inner publisher converts its failure into a new publisher. By returning `Empty()`, we skip the failed item and emit nothing. The outer pipeline's `Failure` type becomes `Never`, so it can never terminate from an error.

2. **`os.Logger` replaces `print()`**: `Logger.processing.error(...)` writes to Apple's unified logging system with proper log levels, persistence, and privacy annotations. The `privacy: .public` annotation ensures the error description is visible in production logs (by default, dynamic strings are redacted as `<private>`).

3. **`ErrorReporter.shared.recordNonFatal(...)`**: Reports the error to your remote crash reporting SDK (Sentry, Crashlytics, etc.) so you can see it in your dashboard. Non-fatal errors affect 10-30%+ of sessions silently -- without remote reporting, you will never know these failures are happening.

4. **`receiveCompletion` is removed**: Since the outer pipeline's `Failure` type is now `Never`, it will never complete with a failure. You only need `receiveValue`.

## Adding Retry Before Giving Up

If the operation is worth retrying (e.g., a transient network error), add `.retry()` before `.catch`:

```swift
cancellable = publisher
    .flatMap { item in
        processItem(item)
            .retry(2) // Retry up to 2 times before falling through to .catch
            .catch { error -> Empty<ResultType, Never> in
                Logger.processing.error(
                    "processItem failed after retries: \(error.localizedDescription, privacy: .public)"
                )
                ErrorReporter.shared.recordNonFatal(
                    error,
                    context: ["operation": "processItem", "itemId": "\(item.id)", "retries": "2"]
                )
                return Empty()
            }
    }
    .receive(on: DispatchQueue.main)
    .sink(receiveValue: { result in
        handleResult(result)
    })
```

## If You Want to Surface Errors to the UI

Instead of silently skipping failed items, you can use a `Result` type to propagate both successes and failures downstream:

```swift
cancellable = publisher
    .flatMap { item in
        processItem(item)
            .map { Result<ResultType, Error>.success($0) }
            .catch { error -> Just<Result<ResultType, Error>> in
                Logger.processing.error(
                    "processItem failed: \(error.localizedDescription, privacy: .public)"
                )
                ErrorReporter.shared.recordNonFatal(
                    error,
                    context: ["operation": "processItem"]
                )
                return Just(.failure(error))
            }
    }
    .receive(on: DispatchQueue.main)
    .sink(receiveValue: { result in
        switch result {
        case .success(let value):
            handleResult(value)
        case .failure(let error):
            showErrorToUser(error) // Update UI error state
        }
    })
```

## The ErrorReporter Protocol

Abstract your crash SDK behind a protocol so you can swap vendors and write testable code:

```swift
protocol ErrorReporter: Sendable {
    func recordNonFatal(_ error: Error, context: [String: Any])
    func addBreadcrumb(message: String, category: String, level: BreadcrumbLevel, data: [String: Any]?)
}

enum BreadcrumbLevel: String, Sendable {
    case debug, info, warning, error, fatal
}
```

Implement this protocol with Sentry, Crashlytics, or whichever SDK your project uses. Access it through a shared instance (`ErrorReporter.shared`) or inject it as a dependency.

## Common Mistake: replaceError at the Pipeline End

Do **not** do this:

```swift
// BAD -- pipeline dies after first error, permanently broken
publisher
    .flatMap { item in processItem(item) }
    .replaceError(with: defaultValue)  // One error = pipeline dead forever
    .assign(to: &$results)
```

`.replaceError()` changes the publisher's `Failure` type to `Never` by completing the pipeline with a replacement value when an error occurs. It does not keep the pipeline alive -- it terminates it with that final value. Error recovery must always happen inside `flatMap`.

## Summary

| Aspect | Your Current Code | Fixed Code |
|--------|------------------|------------|
| Pipeline survival | Dies after first error | Continues processing |
| Error visibility | `print()` -- invisible in production | `os.Logger` with privacy annotations |
| Remote reporting | None | `ErrorReporter.recordNonFatal()` via crash SDK |
| Error location | End of pipeline (too late) | Inside `flatMap` (keeps pipeline alive) |
| Production debugging | 3-day mystery | 15-minute investigation via crash dashboard |
