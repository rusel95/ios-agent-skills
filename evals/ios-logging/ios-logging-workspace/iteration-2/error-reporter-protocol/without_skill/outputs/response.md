# Why Directly Calling SentrySDK.capture() Everywhere Is Problematic

Your tech lead is right to flag this. Scattering direct `SentrySDK.capture()` calls throughout your codebase creates several significant problems:

## 1. Tight Coupling to a Third-Party SDK

By calling `SentrySDK.capture()` directly, every file that reports an error now has a hard dependency on the Sentry framework. This means:

- You need to `import Sentry` in dozens (or hundreds) of files.
- If you ever want to switch to a different error reporting service (Crashlytics, Datadog, Bugsnag, etc.), you have to find and update every single call site.
- You cannot compile or test those files without the Sentry dependency being available.

## 2. Violates the Dependency Inversion Principle

Good architecture depends on abstractions, not concretions. Your business logic and domain layers should not know or care which error reporting vendor you use. The correct approach is to define your own protocol:

```swift
protocol ErrorReporter {
    func report(_ error: Error, context: [String: Any])
}
```

Then create a concrete implementation that wraps Sentry:

```swift
final class SentryErrorReporter: ErrorReporter {
    func report(_ error: Error, context: [String: Any]) {
        let scope = Scope()
        for (key, value) in context {
            scope.setExtra(value: value, key: key)
        }
        SentrySDK.capture(error: error, scope: scope)
    }
}
```

Now only one file in your entire project imports Sentry.

## 3. Makes Unit Testing Difficult or Impossible

When your code calls `SentrySDK.capture()` directly, you cannot easily:

- Verify that errors are being reported in your tests.
- Assert that the correct metadata or context is attached.
- Run tests without Sentry attempting real network calls.

With a protocol, you simply inject a mock:

```swift
final class MockErrorReporter: ErrorReporter {
    var reportedErrors: [(Error, [String: Any])] = []

    func report(_ error: Error, context: [String: Any]) {
        reportedErrors.append((error, context))
    }
}
```

## 4. No Centralized Control Over Reporting Behavior

When calls are scattered everywhere, you lose the ability to:

- **Filter or throttle** error reports globally (e.g., suppress noisy non-critical errors).
- **Enrich context uniformly** (e.g., always attach the current user ID, app version, or session state).
- **Apply consistent severity levels** across the app.
- **Disable reporting** in debug builds with a single toggle.
- **Log locally** in addition to reporting remotely.

A centralized abstraction gives you one place to add all of this logic.

## 5. Vendor Lock-In Risk

Sentry's API can change between major versions. If you upgrade and method signatures change, you face a massive find-and-replace across your entire codebase. With an abstraction layer, you update exactly one file.

## The Recommended Pattern

1. **Define a protocol** (`ErrorReporter`) that describes what your app needs.
2. **Create a concrete implementation** (`SentryErrorReporter`) that wraps the SDK.
3. **Inject the dependency** through initializers or a dependency container.
4. **Import Sentry in only one file** -- the concrete implementation.

This is a standard application of the Adapter pattern combined with Dependency Injection, and it applies equally to any third-party SDK (analytics, networking, feature flags, etc.), not just error reporting.
