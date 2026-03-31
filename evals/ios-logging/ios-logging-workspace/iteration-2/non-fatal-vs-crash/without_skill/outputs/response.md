# Crash Reporting vs. Non-Fatal Error Reporting in Production iOS Apps

Both crash reporting and non-fatal error reporting are essential, but they serve different purposes and have different priorities depending on your app's maturity.

## Crash Reporting: The Non-Negotiable Baseline

Crash reporting should be your first priority. Here is why:

- **Crashes directly cause user loss.** A crash terminates the user's session immediately. Users who experience repeated crashes uninstall apps at a high rate.
- **App Store visibility.** Apple tracks crash rates. A high crash rate can affect your app's ranking and even trigger App Store review warnings.
- **Apple provides infrastructure.** Xcode Organizer surfaces crash logs from users who opt into sharing diagnostics. Third-party tools like Firebase Crashlytics, Sentry, and Datadog provide richer grouping, deduplication, and alerting.
- **Industry benchmark.** A crash-free rate below 99% is generally considered problematic. Top apps target 99.9% or higher.

At minimum, you need symbolicated crash reports with stack traces, device metadata (OS version, device model, memory state), and breadcrumbs showing what the user did before the crash.

## Non-Fatal Error Reporting: The Key to Real Quality

Once your crash-free rate is stable, non-fatal error reporting becomes the higher-leverage investment. The reason is straightforward: non-fatal errors are far more common than crashes and they silently degrade the user experience.

Examples of non-fatal errors worth tracking:

- **Network failures** -- timeouts, unexpected HTTP status codes, decoding errors
- **Business logic failures** -- failed purchases, authentication token refresh failures, data sync conflicts
- **Assertion failures and unexpected states** -- guard statement fallbacks, nil values where you expected data, invalid state transitions
- **Performance degradation** -- UI hangs that don't crash but make the app feel broken, excessive memory usage approaching limits

Non-fatal errors often reveal problems that affect a much larger portion of your user base than crashes do. A user who sees a loading spinner forever or gets a generic error message will leave your app just as readily as one who experiences a crash, but you will never know about it without non-fatal reporting.

## Practical Recommendation

**Start with crash reporting, then quickly layer in non-fatal reporting.**

1. **Week one:** Integrate a crash reporting SDK (Crashlytics, Sentry, or similar). Ensure symbolication is working correctly by uploading dSYM files as part of your CI pipeline.

2. **Week two onward:** Add non-fatal error recording at key points:
   - Network layer: log failures with endpoint, status code, and error type
   - Data layer: log decoding failures and persistence errors
   - Authentication flows: log token refresh failures and session expiration
   - Critical user flows: log when a checkout, onboarding step, or content load fails

3. **Set up alerting on both.** Monitor your crash-free rate with a threshold alert (for example, alert if it drops below 99.5%). For non-fatal errors, track error rates per endpoint or feature and alert on spikes.

## What Matters More?

If you are forced to choose one, choose crash reporting -- it is the foundation. But in practice, the question is not either/or. A mature production app needs both. Non-fatal errors typically outnumber crashes by 10x to 100x, and they represent the much larger surface area of user-facing problems. Teams that only track crashes are flying blind to the majority of issues their users actually experience.

The real insight is this: crash reporting tells you when your app broke completely, but non-fatal error reporting tells you when your app is failing your users. Both matter, and the combination gives you a complete picture of production health.
