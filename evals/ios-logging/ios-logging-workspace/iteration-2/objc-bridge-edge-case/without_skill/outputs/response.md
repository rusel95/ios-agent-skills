# Will Swift's do/catch Handle All Errors in My iOS App?

No. Swift's `do/catch` mechanism only handles Swift errors — values conforming to the `Error` protocol that are explicitly thrown with `throw`. There are several important categories of failures it will not catch.

## What do/catch Handles

Swift's error handling works with functions marked `throws`. When you call a throwing function inside a `do` block, any thrown `Error` is routed to the corresponding `catch` block:

```swift
do {
    let data = try Data(contentsOf: someURL)
} catch {
    print("Caught Swift error: \(error)")
}
```

This is a structured, compile-time-checked system. The compiler enforces that you either handle or propagate thrown errors.

## What do/catch Does NOT Handle

### 1. Objective-C Exceptions (NSException)

This is one of the most critical gaps, especially in iOS development. Objective-C uses a completely separate exception mechanism based on `NSException`. Swift's `do/catch` cannot intercept these.

Common sources of `NSException` in iOS apps include:

- **Out-of-bounds array access**: `NSArray` throws `NSRangeException` when you access an invalid index.
- **KVO/KVC issues**: Setting a value for an undefined key throws `NSUnknownKeyException`.
- **Storyboard/XIB mismatches**: A missing or misconnected `@IBOutlet` causes an `NSUnknownKeyException` at runtime.
- **Core Data faults**: Accessing a deleted managed object can throw an Objective-C exception.
- **Invalid `NSInvocation` or selector calls**: Sending an unrecognized selector to an object raises `NSInvalidArgumentException`.

```swift
// This WILL crash. do/catch won't save you.
do {
    let array = NSArray(array: [1, 2, 3])
    let _ = array.object(at: 10) // NSRangeException — not caught
} catch {
    // This block is never reached
    print("This will never print")
}
```

To catch `NSException`, you need an Objective-C wrapper:

```objc
// ObjCExceptionCatcher.h
@interface ObjCExceptionCatcher : NSObject
+ (BOOL)catchException:(void (^)(void))tryBlock error:(NSError **)error;
@end
```

```objc
// ObjCExceptionCatcher.m
@implementation ObjCExceptionCatcher
+ (BOOL)catchException:(void (^)(void))tryBlock error:(NSError **)error {
    @try {
        tryBlock();
        return YES;
    } @catch (NSException *exception) {
        if (error) {
            *error = [NSError errorWithDomain:exception.name
                                         code:0
                                     userInfo:exception.userInfo];
        }
        return NO;
    }
}
@end
```

You can then call this from Swift to bridge the two exception models.

### 2. Fatal Runtime Errors (Traps)

Swift deliberately crashes the process for certain programming errors. These are unrecoverable and cannot be caught by any mechanism:

- `fatalError("message")`
- `preconditionFailure("message")`
- `assert()` / `assertionFailure()` (in debug builds)
- Force-unwrapping a `nil` optional (`let x: String = someOptional!`)
- Array index out of bounds on a Swift `Array`
- Integer overflow (in debug builds)
- Unimplemented `switch` cases hitting `default: fatalError()`

These trigger a `SIGABRT` or `SIGTRAP` signal and terminate the process immediately. They are intentionally not catchable because they represent logic errors that should be fixed in code, not handled at runtime.

### 3. Memory and System-Level Signals

Low-level failures produce Unix signals that bypass all Swift and Objective-C error handling:

- **EXC_BAD_ACCESS / SIGSEGV**: Accessing deallocated memory or null pointers.
- **SIGBUS**: Misaligned memory access.
- **SIGKILL**: The system terminating your app (e.g., exceeding memory limits, watchdog timeout).

You can install signal handlers for some of these, but you cannot meaningfully recover from them. Crash reporting SDKs (such as Firebase Crashlytics or Sentry) use signal handlers to capture diagnostic information before the process terminates.

### 4. Asynchronous and Callback-Based Errors

Errors delivered through completion handlers, delegates, or Combine publishers are not thrown and therefore are not caught by `do/catch`:

```swift
URLSession.shared.dataTask(with: url) { data, response, error in
    // 'error' here is delivered via callback, not thrown
    // A do/catch around the dataTask call would not capture this
}
```

With Swift concurrency (`async/await`), many of these are now bridged to throwing functions, but legacy callback APIs still require manual error checking.

## Practical Recommendations

1. **Use `do/catch` for Swift-native throwing APIs.** It works well for file I/O, JSON decoding, networking with `async/await`, and your own throwing functions.

2. **Guard against NSException at the boundary.** When calling Objective-C APIs known to throw exceptions (especially collection access, KVC, and UIKit/Core Data operations), validate inputs before the call rather than trying to catch after.

3. **Use crash reporting tools** to capture fatal errors and signals in production. These cannot be caught in code, but the diagnostic data is essential for fixing them.

4. **Prefer safe access patterns**: use `optional` subscripts, nil coalescing, `if let`/`guard let`, and bounds checking to avoid hitting traps and exceptions in the first place.

Swift's `do/catch` is reliable for what it is designed to handle, but understanding its boundaries — particularly the Objective-C exception gap — is essential for building robust iOS applications.
