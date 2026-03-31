# Combine Pipeline Dies After First Error

## The Problem

The pipeline works once but then permanently stops responding to new `searchQuery` values. The root cause is `replaceError(with:)`.

## Why It Breaks

In Combine, when a publisher emits an error, the subscription is **terminated** per the Reactive Streams contract. The operator `replaceError(with:)` does replace the error with a fallback value, but it also **completes the stream** immediately after delivering that fallback. The upstream `$searchQuery` publisher is still alive, but the `flatMap` inner publisher that errored has caused the entire downstream chain to finish.

Here is the sequence of events:

1. User types a query. `$searchQuery` emits the value.
2. `debounce` waits 0.3s, then forwards it.
3. `flatMap` subscribes to `APIService.search(query)`.
4. If the API call **succeeds**, the result flows through and `assign` updates `$results`. Everything works.
5. If the API call **fails**, the error propagates out of `flatMap` into the main stream.
6. `replaceError(with: [])` catches the error, emits `[]`, and then **sends a completion event**.
7. The entire pipeline is now finished. No further values from `$searchQuery` will ever be processed.

Even on the success path, this pipeline is fragile: `flatMap` by default has unlimited demand, and the first inner publisher error will kill the outer chain.

## The Fix

Move error handling **inside** the `flatMap` closure so that errors are caught per-request, not on the outer stream:

```swift
$searchQuery
    .debounce(for: .seconds(0.3), scheduler: DispatchQueue.main)
    .flatMap { query in
        APIService.search(query)
            .replaceError(with: [])  // Handle error per-request
    }
    .assign(to: &$results)
```

By placing `replaceError(with:)` on the inner publisher (the one returned by `APIService.search`), each individual network call can fail gracefully without tearing down the outer pipeline. The `flatMap` only ever sees `[SearchResult]` values (never an error), so the outer stream stays alive indefinitely.

## Alternative Approaches

### Using `catch` for More Control

```swift
$searchQuery
    .debounce(for: .seconds(0.3), scheduler: DispatchQueue.main)
    .flatMap { query in
        APIService.search(query)
            .catch { error -> Just<[SearchResult]> in
                print("Search failed: \(error.localizedDescription)")
                return Just([])
            }
    }
    .assign(to: &$results)
```

This lets you log or react to specific errors while still protecting the outer stream.

### Using `map` + `switchToLatest` with `removeDuplicates`

For search-type UIs, `switchToLatest` is often preferable to `flatMap` because it automatically cancels the previous in-flight request when a new query arrives:

```swift
$searchQuery
    .debounce(for: .seconds(0.3), scheduler: DispatchQueue.main)
    .removeDuplicates()
    .map { query in
        APIService.search(query)
            .replaceError(with: [])
    }
    .switchToLatest()
    .assign(to: &$results)
```

## General Rule

In Combine, **never let an error reach the outer/long-lived stream**. Always handle errors on the inner publisher inside `flatMap`, `map`+`switchToLatest`, or similar operators. The outer stream represents the lifecycle of your feature; if it completes or errors, it is dead and will not restart.
