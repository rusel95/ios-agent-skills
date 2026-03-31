# MetricKit and Using It Alongside Sentry

## What Is MetricKit?

MetricKit is Apple's first-party diagnostic framework (available since iOS 13, with diagnostics from iOS 14 and immediate delivery from iOS 15). Its defining characteristic is that it runs **out-of-process** -- in a separate system process managed by the OS, not inside your app.

This matters because it can detect termination events that in-process crash reporters like Sentry fundamentally cannot catch:

- **OOM (Out-of-Memory) kills** -- when the OS terminates your app due to memory pressure, it sends SIGKILL, which cannot be intercepted by any in-process signal handler.
- **Watchdog kills** -- when your app takes too long to launch, resume, or complete a background task, the system terminates it the same way.
- **Background terminations** -- the OS silently killing your app while it is suspended.
- **Hangs** -- main thread blocks exceeding 250ms.
- **Excessive disk I/O and CPU usage** -- resource abuse diagnostics.

MetricKit delivers these diagnostics through the `MXMetricManagerSubscriber` protocol. You register a subscriber at app launch, and the system delivers `MXMetricPayload` (aggregate performance metrics) and `MXDiagnosticPayload` (crash stacks, hang stacks, resource exception stacks) to your app on the next launch.

## Should You Use It Alongside Sentry?

**Yes, absolutely.** They are complementary, not competing tools. Here is why:

### What Sentry does well that MetricKit does not

| Capability | Sentry | MetricKit |
|---|---|---|
| Automatic symbolication | Yes (with dSYM upload) | No -- stacks are unsymbolicated; you need server-side symbolication |
| Breadcrumbs (what the user did before the crash) | Yes | No |
| Rich context, tags, and custom metadata | Yes | No |
| Coverage of all users | Yes | Only users who opt in to "Share with App Developers" in Settings |
| Non-fatal error reporting | Yes | No |
| Real-time alerting | Yes | No (delivered on next app launch) |

### What MetricKit catches that Sentry cannot

| Capability | MetricKit | Sentry |
|---|---|---|
| OOM detection | Reliable (out-of-process observation) | Heuristic only (infers OOM by process of elimination) |
| Watchdog kills | Yes | No |
| Background termination counts | Yes (via `applicationExitMetrics`) | No |
| Hang diagnostics with call stacks | Yes | Limited |

### How to combine them

Use Sentry as your **primary crash and error reporter** -- it gives you rich context, breadcrumbs, automatic symbolication, and full user coverage. Use MetricKit as a **supplementary diagnostics layer** specifically for the termination classes that Sentry cannot observe.

In practice, this means:

1. **Sentry handles fatal crashes and non-fatal errors.** Every `catch` block reports through Sentry (via an `ErrorReporter` protocol abstraction). Sentry captures signal-based crashes (SIGABRT, SIGSEGV, etc.) with full breadcrumb trails.

2. **MetricKit handles OOM, watchdog, and resource diagnostics.** Register an `MXMetricManagerSubscriber` at app launch. Forward the diagnostic payloads to your backend for analysis.

Here is the minimal MetricKit setup:

```swift
import MetricKit

class AppMetrics: NSObject, MXMetricManagerSubscriber {
    static let shared = AppMetrics()

    func startReceiving() {
        MXMetricManager.shared.add(self)
        // iOS 15+: process any diagnostics already waiting
        processDiagnostics(MXMetricManager.shared.pastDiagnosticPayloads)
    }

    func didReceive(_ payloads: [MXDiagnosticPayload]) {
        processDiagnostics(payloads)
    }

    func didReceive(_ payloads: [MXMetricPayload]) {
        // Extract applicationExitMetrics for OOM/watchdog counts
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
                // Forward hang.jsonRepresentation() to backend
            }
        }
    }
}
```

Initialize it in your app entry point:

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

## Key caveats

- **MetricKit stacks are unsymbolicated.** You need to set up server-side symbolication using your dSYMs, or cross-reference addresses manually against your build artifacts.
- **MetricKit only covers opted-in users.** Users must have "Share with App Developers" enabled in Settings > Privacy > Analytics. This typically represents a subset of your user base, not all of it.
- **Do not use MetricKit crash diagnostics as a replacement for Sentry crash reporting.** The crash stacks from MetricKit overlap with what Sentry already captures (and Sentry does it better with symbolication, breadcrumbs, and full coverage). The unique value of MetricKit is the termination types that no in-process reporter can see.

## Summary

MetricKit and Sentry occupy different layers in the observability stack. Sentry is your in-process crash and error reporter with rich context. MetricKit is your out-of-process diagnostic layer for OS-level terminations. Use both together for complete production visibility.
