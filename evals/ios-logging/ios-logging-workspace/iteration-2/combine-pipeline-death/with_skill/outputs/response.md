# Combine Pipeline Death: Why Your Search Stops After One Error

## The Problem

Your pipeline works once but then permanently stops responding. The root cause is **where** error handling is placed in the Combine chain.

```swift
$searchQuery
    .debounce(for: .seconds(0.3), scheduler: DispatchQueue.main)
    .flatMap { query in
        APIService.search(query)
    }
    .replaceError(with: [])  // <-- This kills the entire pipeline
    .assign(to: &$results)
```

## Why It Breaks

In Combine, when a publisher emits a **failure**, the subscription is **cancelled permanently**. The publisher-subscriber contract in Combine states that after a failure event, no further values will ever be emitted.

Here is the sequence of events:

1. User types a query. `$searchQuery` emits a value. `flatMap` calls `APIService.search(query)`. It succeeds. Results appear.
2. User types another query. This time `APIService.search(query)` fails (timeout, server error, bad JSON, anything).
3. That failure propagates up out of `flatMap` to the outer pipeline.
4. `.replaceError(with: [])` receives the failure. It emits `[]` as a final value and then **completes the pipeline with a finished event**.
5. The pipeline is now terminated. `$searchQuery` can emit new values forever -- nothing downstream will ever process them again.

The key insight: `.replaceError()` changes the publisher's `Failure` type to `Never` by converting the failure into a completion. It does not "swallow" the error and keep going. It ends the stream.

## The Fix

Move error handling **inside** `flatMap`. This way, each inner publisher handles its own errors independently, and the outer pipeline never sees a failure.

```swift
$searchQuery
    .debounce(for: .seconds(0.3), scheduler: DispatchQueue.main)
    .flatMap { query in
        APIService.search(query)
            .retry(2)
            .catch { error -> Just<[SearchResult]> in
                Logger.networking.error(
                    "Search failed for query: \(error.localizedDescription, privacy: .public)"
                )
                ErrorReporter.shared.recordNonFatal(error, context: ["query": query])
                return Just([])
            }
    }
    .receive(on: DispatchQueue.main)
    .assign(to: &$results)
```

### What changed and why

| Change | Reason |
|--------|--------|
| `.retry(2)` inside `flatMap` | Retries transient failures (e.g., network blip) before giving up |
| `.catch` inside `flatMap` | Converts the inner publisher's failure into `Just([])`, so the outer pipeline never receives an error and stays alive |
| `Logger.networking.error(...)` | Logs the failure with `os.Logger` using privacy annotations instead of silently discarding it |
| `ErrorReporter.shared.recordNonFatal(...)` | Reports the error to your crash reporting SDK (Sentry, Crashlytics, etc.) so you can see it in production dashboards |
| `.receive(on: DispatchQueue.main)` | Ensures UI updates happen on the main thread (good practice, since retry/catch may shift schedulers) |
| Removed `.replaceError(with: [])` | No longer needed -- the outer pipeline's `Failure` type is already `Never` because every inner publisher is caught |

## The General Rule

In Combine, **error recovery must happen inside `flatMap`**, not at the end of the pipeline. Any operator that converts `Failure` to `Never` at the pipeline level (`.replaceError()`, `.catch` at the top level, `.assertNoFailure()`) will terminate the entire stream on the first error.

Think of it this way:
- **Error handling at the pipeline end** = "if anything ever fails, shut everything down"
- **Error handling inside `flatMap`** = "if this one request fails, recover and keep listening for the next one"

## Debugging Tip

If you suspect a Combine pipeline has died, add a `.handleEvents` operator to trace lifecycle events:

```swift
$searchQuery
    .handleEvents(
        receiveOutput: { Logger.combine.debug("searchQuery emitted: \($0, privacy: .public)") },
        receiveCompletion: { Logger.combine.error("searchQuery pipeline completed: \($0)") },
        receiveCancel: { Logger.combine.error("searchQuery pipeline was cancelled") }
    )
    .debounce(for: .seconds(0.3), scheduler: DispatchQueue.main)
    // ... rest of pipeline
```

If you see `receiveCompletion` with a `.failure` or `.finished` after an error, the pipeline is dead and error handling needs to move inside `flatMap`.
