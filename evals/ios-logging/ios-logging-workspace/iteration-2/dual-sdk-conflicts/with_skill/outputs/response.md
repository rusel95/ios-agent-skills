# Why Crashes Disappear When Running Both Sentry and Crashlytics

## The Root Cause: Signal Handler Conflicts

Running Sentry and Crashlytics simultaneously as fatal crash reporters causes **signal handler conflicts**. Both SDKs install handlers for the same POSIX signals (SIGABRT, SIGSEGV, SIGBUS, etc.), and only the last one registered actually receives the signal when a crash occurs. Additionally, `NSSetUncaughtExceptionHandler` only supports a single handler -- the second call replaces the first entirely.

The result: when a fatal crash occurs, whichever SDK registered its handler second gets the signal. The other SDK never sees it. Worse, if the winning handler itself fails or the process is in a corrupted state, neither SDK captures the crash. This is why crashes "disappear" from both dashboards.

## The Fix: One Primary Fatal Reporter, One Secondary for Non-Fatals

Pick **one SDK** as your fatal crash reporter and disable crash handling on the other.

### Option A: Crashlytics as primary (recommended if you already use Firebase)

```swift
import Sentry

SentrySDK.start { options in
    options.dsn = "https://your-dsn@sentry.io/project"
    options.enableCrashHandler = false  // Disable Sentry's fatal crash handling
    // Sentry still captures non-fatals, breadcrumbs, and performance
}
```

Crashlytics initializes normally and is the sole fatal crash handler.

### Option B: Sentry as primary (recommended for standalone / richer observability)

```swift
import FirebaseCrashlytics

// Initialize Firebase as usual, but disable Crashlytics crash collection
// In your Info.plist, set FirebaseCrashlyticsCollectionEnabled = false
// Or programmatically:
Crashlytics.crashlytics().setCrashlyticsCollectionEnabled(false)
```

Sentry initializes normally and is the sole fatal crash handler.

## Use an ErrorReporter Abstraction

Rather than calling Sentry or Crashlytics directly throughout your codebase, wrap both behind a protocol so non-fatal errors are reported to both backends:

```swift
protocol ErrorReporter: Sendable {
    func recordNonFatal(_ error: Error, context: [String: Any])
    func addBreadcrumb(message: String, category: String, level: BreadcrumbLevel, data: [String: Any]?)
    func setUserID(_ userID: String?)
    func setCustomKey(_ key: String, value: Any)
    func log(_ message: String)
}

enum BreadcrumbLevel: String, Sendable {
    case debug, info, warning, error, fatal
}
```

Then use a composite reporter to fan out non-fatals to both SDKs:

```swift
final class CompositeErrorReporter: ErrorReporter {
    private let reporters: [ErrorReporter]

    init(_ reporters: ErrorReporter...) {
        self.reporters = reporters
    }

    func recordNonFatal(_ error: Error, context: [String: Any]) {
        reporters.forEach { $0.recordNonFatal(error, context: context) }
    }

    func addBreadcrumb(message: String, category: String, level: BreadcrumbLevel, data: [String: Any]?) {
        reporters.forEach { $0.addBreadcrumb(message: message, category: category, level: level, data: data) }
    }

    // ... delegate all methods similarly
}

// At app startup:
let reporter = CompositeErrorReporter(
    SentryErrorReporter(),       // non-fatals + breadcrumbs only (crash handler disabled)
    CrashlyticsErrorReporter()   // non-fatals + fatals
)
```

## Crashes That Neither SDK Will Ever Catch

Even after fixing the dual-SDK conflict, some crashes will still be missing from both dashboards. In-process crash reporters (Sentry and Crashlytics both) install signal handlers inside your app's process. When the OS terminates your app with SIGKILL -- which **cannot be caught** -- neither SDK runs:

- **OOM (out-of-memory) terminations** -- the OS kills the process instantly
- **Watchdog kills** -- the system terminates apps that hang too long (e.g., blocked main thread during launch)
- **Background task timeouts** -- the OS kills the app when a background task exceeds its time limit
- **Thermal throttle kills** -- the OS terminates apps under extreme thermal pressure

### The Solution: Add MetricKit

MetricKit runs **out-of-process** in a separate system daemon, so it observes these invisible terminations:

```swift
import MetricKit

class AppMetrics: NSObject, MXMetricManagerSubscriber {
    static let shared = AppMetrics()

    func startReceiving() {
        MXMetricManager.shared.add(self)
        // iOS 15+: process any pending diagnostics immediately
        processDiagnostics(MXMetricManager.shared.pastDiagnosticPayloads)
    }

    func didReceive(_ payloads: [MXDiagnosticPayload]) {
        processDiagnostics(payloads)
    }

    func didReceive(_ payloads: [MXMetricPayload]) {
        for payload in payloads {
            if let exitMetrics = payload.applicationExitMetrics {
                let bg = exitMetrics.backgroundExitData
                let fg = exitMetrics.foregroundExitData

                let oomCount = bg.cumulativeMemoryPressureExitCount
                    + fg.cumulativeMemoryPressureExitCount
                let watchdogCount = bg.cumulativeAppWatchdogExitCount

                if oomCount > 0 || watchdogCount > 0 {
                    // Forward to your analytics backend
                }
            }
        }
    }

    private func processDiagnostics(_ payloads: [MXDiagnosticPayload]) {
        for payload in payloads {
            payload.crashDiagnostics?.forEach { crash in
                // Forward crash.jsonRepresentation() to backend
            }
            payload.hangDiagnostics?.forEach { hang in
                // Forward hang data
            }
        }
    }
}
```

Initialize it early in your app entry point:

```swift
@main
struct MyApp: App {
    init() {
        AppMetrics.shared.startReceiving()
    }

    var body: some Scene {
        WindowGroup { ContentView() }
    }
}
```

**Note:** MetricKit stacks are unsymbolicated, so you need server-side symbolication with dSYMs. Also, MetricKit data only comes from users who have opted in to "Share with App Developers" in Settings.

## dSYM Verification

Crashes that do get captured may still appear unsymbolicated (showing hex addresses instead of function names) if dSYMs are missing. Verify:

- Build Settings > Debug Information Format is set to **"DWARF with dSYM File"** for all configurations (especially Release)
- This applies to **all targets**: main app, extensions, widgets, watch app
- dSYM upload scripts are in your Build Phases for both Sentry and Crashlytics
- Bitcode is deprecated since Xcode 14, so local dSYMs are authoritative

## Summary

| Problem | Cause | Fix |
|---|---|---|
| Crashes missing from both dashboards | Dual signal handler conflict | Disable crash handler on one SDK |
| OOM / watchdog kills missing | SIGKILL cannot be caught in-process | Add MetricKit for out-of-process detection |
| Crash reports show hex addresses | Missing dSYMs | Set "DWARF with dSYM" for all targets, upload dSYMs |
| Non-fatals only in one dashboard | Direct SDK calls scattered in code | Use CompositeErrorReporter abstraction |

The recommended observability stack is: **one primary crash SDK** (Sentry or Crashlytics, not both for fatals) + **MetricKit** for OS-level terminations + **os.Logger** for local structured logging with privacy annotations.
