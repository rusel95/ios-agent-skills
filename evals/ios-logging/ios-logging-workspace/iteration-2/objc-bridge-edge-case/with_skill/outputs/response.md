# Will Swift's do/catch Handle All Errors in My iOS App?

No. Swift's `do/catch` only catches Swift `Error` types (values conforming to the `Error` protocol). There is an entire category of failures it cannot intercept, and misunderstanding this boundary is a common source of production crashes.

## What `do/catch` Catches

Swift's error handling catches any value thrown as a Swift `Error`. This covers:

- Errors from `throws` functions (network calls, file I/O, JSON decoding, Core Data saves)
- Custom error types you define conforming to `Error`
- `NSError` instances bridged from Objective-C methods that follow the Cocoa error convention (methods returning `BOOL`/`id` with an `NSError**` out-parameter)

## What `do/catch` Does NOT Catch

### 1. Objective-C NSExceptions

This is the most critical gap. Objective-C `NSException` instances are **not** caught by Swift's `do/catch`. They terminate the app immediately, and Swift has no chance to intervene.

```swift
// Swift do/catch will NOT catch this NSRangeException
do {
    let item = nsArray.object(at: 999) // NSRangeException -> crash
} catch {
    // This catch block NEVER executes for NSException
}
```

Common `NSException` triggers include:

- **NSArray/NSDictionary** out-of-bounds or nil key access
- **Invalid KVO key paths** (typo in `#keyPath` string or unregistered observer removal)
- **Unrecognized selectors** (calling a method that does not exist on an object)
- **Core Data threading violations** (accessing managed objects from the wrong thread)
- **NSInvalidArgumentException** (wrong argument types to Objective-C methods)
- **Storyboard/Nib loading failures** (missing outlet connections, wrong class names)

### 2. Swift Runtime Traps

These are fatal and uncatchable by any Swift-level mechanism:

- Force-unwrapping `nil` (`!` on an Optional that is `nil`) -- triggers `SIGTRAP`
- Array index out of bounds on Swift arrays
- `fatalError()`, `preconditionFailure()`, `assert()` failures in release builds
- Integer overflow in non-`&` arithmetic (in debug builds)

### 3. Memory Violations

- `EXC_BAD_ACCESS` (dereferencing a dangling pointer or freed memory) -- triggers `SIGSEGV`/`SIGBUS`

## Coverage Table

| Error Type | Swift do/catch | NSExceptionHandler | Signal Handler | MetricKit |
|---|:---:|:---:|:---:|:---:|
| Swift `Error` (throws) | Yes | No | No | No |
| ObjC `NSException` | **No** | Yes | No | Yes |
| Swift trap (force unwrap nil) | No | No | Yes (SIGTRAP) | Yes |
| EXC_BAD_ACCESS | No | No | Yes (SIGSEGV) | Yes |

## The Swift-ObjC Bridge Error Gotcha

There is a subtle edge case when bridging Swift `throws` methods to Objective-C. When a Swift method is exposed to ObjC via `@objc func doWork() throws`, ObjC determines success or failure by the **return value** (nil = failure), not by whether `NSError` was set. If an ObjC caller receives a non-nil return value AND the method also set an `NSError`, Swift's catch block is never invoked -- the error is silently lost.

## Defensive Strategies

### For NSExceptions: Validate Before Calling

The correct approach is to check preconditions before calling Objective-C APIs, rather than wrapping them in `do/catch`:

```swift
// Validate before calling ObjC APIs
guard index < nsArray.count else {
    Logger.database.error("Index \(index, privacy: .public) out of bounds for array of \(nsArray.count, privacy: .public)")
    return nil
}
let item = nsArray.object(at: index)
```

### For Uncatchable Crashes: Use a Crash Reporting SDK

Crash reporting SDKs (Sentry, Firebase Crashlytics) layer three mechanisms to catch what Swift cannot:

1. `NSSetUncaughtExceptionHandler` -- catches ObjC exceptions
2. UNIX signal handlers (`sigaction`) -- catches Swift traps and memory violations
3. Mach exception handlers -- catches low-level machine exceptions

Do not install your own `NSSetUncaughtExceptionHandler` if you use a crash SDK -- a second call replaces the first and will interfere with the SDK's handler.

### For Out-of-Process Diagnostics: Use MetricKit

MetricKit captures OOM kills, watchdog terminations, and hang diagnostics that happen outside your process entirely. These are invisible to both `do/catch` and crash SDKs.

## Summary

Swift's `do/catch` is necessary but not sufficient. It handles Swift `Error` protocol conforming types only. For a complete error observability strategy, you need:

1. **`do/catch`** for Swift errors, with `Logger` + crash SDK reporting in every catch block
2. **Input validation** before calling Objective-C APIs to prevent `NSException` crashes
3. **A crash reporting SDK** (Sentry or Crashlytics) for NSExceptions, traps, and signal-level crashes
4. **MetricKit** for out-of-process terminations (OOM, watchdog kills) that no in-process handler can detect
