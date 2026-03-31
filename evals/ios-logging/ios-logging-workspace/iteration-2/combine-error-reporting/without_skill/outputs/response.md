# Handling and Reporting Errors in a Combine Pipeline Without Killing It

## The Problem

In your current setup, when `processItem(item)` emits a failure, the entire Combine pipeline terminates. This is by design in Combine -- once a publisher sends a `.failure` completion, the subscription is cancelled and no further values are delivered. Your `sink` receives the completion and the pipeline is dead.

## Key Strategies

### 1. Use `catch` to Replace Failures with a Fallback

The simplest approach is to catch errors and replace the failing publisher with a recovery value:

```swift
cancellable = publisher
    .flatMap { item in
        processItem(item)
            .catch { error -> Just<ResultType> in
                print("Error processing item: \(error)")
                // Return a fallback value so the outer pipeline continues
                return Just(.fallbackResult)
            }
    }
    .sink(receiveValue: { result in
        handleResult(result)
    })
```

By placing `.catch` inside the `flatMap` closure, the error is caught on the inner publisher. The outer pipeline never sees the failure, so it stays alive.

### 2. Use `replaceError(with:)` for Simple Cases

If you just need a default value on failure:

```swift
cancellable = publisher
    .flatMap { item in
        processItem(item)
            .replaceError(with: .defaultResult)
    }
    .sink(receiveValue: { result in
        handleResult(result)
    })
```

### 3. Use `Result` Type to Propagate Errors as Values

When you need to handle errors downstream without terminating the pipeline, map errors into a `Result` type:

```swift
cancellable = publisher
    .flatMap { item in
        processItem(item)
            .map { Result<ProcessedItem, Error>.success($0) }
            .catch { error in
                Just(Result<ProcessedItem, Error>.failure(error))
            }
    }
    .sink(receiveValue: { result in
        switch result {
        case .success(let value):
            handleResult(value)
        case .failure(let error):
            reportError(error)
        }
    })
```

This is the most flexible pattern because you preserve the error information and can handle it however you want in `sink`, while the pipeline itself never terminates.

### 4. Use `retry` Before Catching

If the failure might be transient (e.g., a network request), you can retry before catching:

```swift
cancellable = publisher
    .flatMap { item in
        processItem(item)
            .retry(2)
            .catch { error -> Just<ResultType> in
                reportError(error)
                return Just(.fallbackResult)
            }
    }
    .sink(receiveValue: { result in
        handleResult(result)
    })
```

### 5. Use `tryCatch` for Error Transformation

If you want to transform one error type into another or perform side effects during error handling:

```swift
cancellable = publisher
    .flatMap { item in
        processItem(item)
            .tryCatch { error -> Just<ResultType> in
                logErrorToAnalytics(error)
                if isRecoverable(error) {
                    return Just(.recoveredResult)
                }
                throw error // Re-throw if not recoverable
            }
            .replaceError(with: .criticalFallback)
    }
    .sink(receiveValue: { result in
        handleResult(result)
    })
```

## The Critical Rule

The key principle is: **handle errors on the inner publisher (inside `flatMap`), not on the outer pipeline.** If you place `.catch` or error handling operators after `flatMap`, the outer pipeline will still terminate on the first error. By handling errors inside the `flatMap` closure, each item's processing is isolated -- one failure does not affect subsequent items.

## Comparison

| Approach | Pipeline Survives | Error Info Preserved | Complexity |
|---|---|---|---|
| `catch` inside `flatMap` | Yes | Side-effect only | Low |
| `replaceError(with:)` | Yes | No | Very Low |
| `Result` wrapping | Yes | Yes, fully | Medium |
| `retry` + `catch` | Yes | Side-effect only | Medium |
| `tryCatch` | Yes | Partial | Medium |

## Recommendation

For most production code, the `Result`-wrapping pattern (option 3) is the best approach because it keeps the pipeline alive while preserving full error information for reporting, logging, or UI updates. If you have a centralized error reporting system, you can easily plug it in at the `sink` level without losing any context about what went wrong.
