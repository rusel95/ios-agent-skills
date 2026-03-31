# Dual Crash Reporting SDK Conflicts: Sentry and Crashlytics

## The Core Problem

When you run both Sentry and Crashlytics in the same iOS app, they compete for the same underlying crash-handling mechanism. Both SDKs install signal handlers (for POSIX signals like `SIGSEGV`, `SIGABRT`, `SIGBUS`) and set an `NSUncaughtExceptionHandler`. The OS only supports **one active handler** for each of these at a time. When two SDKs both try to register, the second one overwrites the first, and depending on initialization order and how each SDK chains (or fails to chain) handlers, crashes can be silently swallowed by neither.

## Why Crashes Go Missing

1. **Signal handler overwriting**: SDK A installs its `SIGSEGV` handler. SDK B then installs its own, replacing A's. If B's handler does not forward to A's saved handler, A never sees the crash. If B's handler itself crashes or exits before forwarding, both miss it.

2. **NSUncaughtExceptionHandler conflicts**: Same story — only one global uncaught exception handler exists. The last SDK to call `NSSetUncaughtExceptionHandler` wins. If it does not call the previously installed handler, the other SDK gets nothing.

3. **Symbolication race conditions**: Even when both SDKs capture the crash, they may interfere with each other's dSYM upload or symbolication pipeline, resulting in unsymbolicated reports that get silently discarded or appear as "missing."

4. **Out-of-memory (OOM) and watchdog kills**: Neither SDK can reliably detect OOM terminations or watchdog kills when the other SDK is also monitoring app lifecycle state. Their heuristics (e.g., "app was in foreground and didn't call `applicationWillTerminate`") conflict and produce false negatives.

5. **Crash report file corruption**: Both SDKs write crash data to disk at crash time. If they both attempt disk I/O simultaneously in a signal handler (which is async-signal-unsafe), report files can be corrupted or truncated, and neither dashboard shows the crash.

## How to Fix It

### Option 1: Pick One SDK (Recommended)

The most reliable fix is to use a single crash reporter. Running two crash reporting SDKs in production is an anti-pattern that both Sentry and Firebase/Google explicitly warn against.

- If you need Sentry's breadcrumb/context features and performance monitoring, drop Crashlytics.
- If you need Crashlytics for its Firebase integration and simplicity, drop Sentry's crash reporting.

### Option 2: Disable Crash Reporting in One SDK

If you need both SDKs for non-crash features (e.g., Sentry for performance tracing, Crashlytics for analytics integration), disable crash handling in one of them:

**Disable Sentry's crash reporting but keep other features:**

```swift
SentrySDK.start { options in
    options.dsn = "your-dsn"
    options.enableCrashHandler = false
    // Keep performance monitoring, breadcrumbs, etc.
    options.tracesSampleRate = 1.0
}
```

**Or disable Crashlytics crash collection:**

```swift
// In your Info.plist, set:
// FirebaseCrashlyticsCollectionEnabled = false

// Then use Crashlytics only for non-fatal logging:
Crashlytics.crashlytics().record(error: someError)
```

### Option 3: Carefully Control Initialization Order

If you absolutely must run both, the initialization order matters:

```swift
// In AppDelegate.application(_:didFinishLaunchingWithOptions:)

// Step 1: Initialize Crashlytics FIRST (via Firebase)
FirebaseApp.configure()

// Step 2: Initialize Sentry SECOND
// Sentry is generally better at chaining to the previous handler
SentrySDK.start { options in
    options.dsn = "your-dsn"
}
```

Sentry's crash handler typically saves and forwards to the previously installed handler, so initializing it **after** Crashlytics gives both a better chance of capturing crashes. However, this is fragile and not guaranteed across SDK version updates.

### Additional Steps Regardless of Approach

1. **Verify dSYM uploads for both services.** Missing symbolication data is the silent killer of crash reports. Automate uploads in your CI/CD pipeline:

```bash
# Sentry
sentry-cli upload-dif --include-sources ./build/dSYMs

# Crashlytics (usually handled by the build phase script)
"${PODS_ROOT}/FirebaseCrashlytics/run"
```

2. **Test with a forced crash** in a release build (not debug — debugger-attached processes behave differently):

```swift
// Temporary test button
SentrySDK.crash() // For Sentry
fatalError("Test crash for Crashlytics") // For Crashlytics
```

3. **Check for debugger attachment.** Crashes are intercepted by Xcode's debugger and never reach either SDK. Make sure you're testing without the debugger attached (run the app from the home screen, not Xcode).

4. **Monitor `stderr` in Console.app** for messages like `"Replacing existing signal handler"` — some SDK versions log warnings when they detect another crash reporter.

## Summary

| Approach | Reliability | Effort |
|---|---|---|
| Single SDK | High | Low — remove one dependency |
| Disable crash handling in one | High | Low — one config change |
| Controlled init order | Medium | Low, but fragile across updates |
| Both SDKs, no changes | Low | N/A — this is the broken state |

The industry consensus is clear: **do not run two crash reporters simultaneously**. Choose one for crash reporting and, if needed, keep the other for its non-crash features with crash collection disabled.
