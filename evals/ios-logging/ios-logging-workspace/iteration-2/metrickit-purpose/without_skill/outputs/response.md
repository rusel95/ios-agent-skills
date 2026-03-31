## MetricKit Overview

MetricKit is an Apple framework introduced in iOS 13 that allows you to collect and process performance and diagnostic metrics from your app as reported by the operating system. It provides two main types of data:

1. **MXMetricPayload** (iOS 13+) — Aggregated performance metrics delivered roughly once every 24 hours, covering areas like:
   - CPU usage and GPU time
   - Memory usage (peak and average)
   - Disk I/O
   - Network transfer statistics
   - App launch time and hang rate
   - Battery usage (cellular, CPU, GPU, location, display, networking)
   - Animation hitches

2. **MXDiagnosticPayload** (iOS 14+) — Diagnostic reports that include:
   - Crash reports with full stack traces
   - Hang diagnostics (main thread unresponsiveness)
   - Disk write exception diagnostics
   - CPU exception diagnostics

To use it, you subscribe to `MXMetricManager` by conforming to `MXMetricManagerSubscriber` and implementing the delegate callbacks `didReceive(_:)` for metric payloads and diagnostic payloads.

## Should You Use MetricKit Alongside Sentry?

Yes, using MetricKit alongside Sentry is generally a good idea. They serve complementary purposes:

- **Sentry** gives you real-time crash reporting, error tracking, breadcrumbs, user context, and release health monitoring. It captures events as they happen and lets you triage issues immediately through its dashboard.

- **MetricKit** provides OS-level aggregated performance data that Sentry does not have direct access to. Apple collects this data at the system level, so it can report on metrics like actual battery drain, cellular usage, and system-level hang detection with a level of accuracy that third-party SDKs cannot replicate.

### Practical Recommendations

- **Use Sentry as your primary crash and error reporting tool.** It provides immediate, actionable crash reports with rich context (user info, breadcrumbs, tags, release tracking).

- **Use MetricKit as a supplementary data source** for system-level performance insights. Forward MetricKit payloads to your backend or even to Sentry as custom events so you have everything in one place.

- **Be aware of overlap in crash reporting.** Both Sentry and MetricKit (iOS 14+) can capture crash data. The MetricKit crash reports come from Apple's own crash reporter and may occasionally capture crashes that Sentry misses (for example, watchdog terminations or memory-pressure kills that do not go through standard signal handlers). Conversely, Sentry provides much richer context per crash.

- **MetricKit data is delayed.** Payloads arrive up to 24 hours after the metrics were collected, so it is not suitable for real-time alerting. Sentry handles that role.

- **Note that Sentry's iOS SDK already integrates some MetricKit data.** Recent versions of the Sentry Cocoa SDK can automatically subscribe to MetricKit diagnostic payloads and attach them to Sentry events, so check your Sentry SDK configuration before building a custom integration.

In summary, MetricKit and Sentry are not competing tools — they complement each other well. Use Sentry for real-time observability and MetricKit for Apple's own system-level performance and diagnostic insights.
