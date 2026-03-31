# Crash Reporting: Sentry vs Crashlytics

Both Sentry and Firebase Crashlytics are solid crash reporting solutions for iOS. Here is a breakdown of the trade-offs to help you decide.

---

## Firebase Crashlytics

**Pros:**

- Free with no usage limits, which makes it attractive for teams of any size.
- Deep integration with the Firebase ecosystem (Analytics, Remote Config, A/B Testing). If you already use Firebase, Crashlytics fits in naturally.
- Lightweight SDK with minimal impact on app size and performance.
- Automatic crash reporting out of the box with very little configuration.
- Google-backed with strong community adoption, meaning plenty of tutorials and Stack Overflow answers.
- Real-time crash alerting and trending dashboards.

**Cons:**

- Requires a Google/Firebase account and GoogleService-Info.plist in your project.
- The dashboard is relatively basic compared to dedicated error-tracking platforms. Filtering, searching, and custom queries are limited.
- Primarily focused on crashes and non-fatal errors. It does not cover broader observability concerns like performance traces in the same depth (Firebase Performance Monitoring is a separate product).
- Less flexibility for on-premise or self-hosted deployments; it is a fully managed Google service.
- Limited breadcrumb and context customization compared to Sentry.

---

## Sentry

**Pros:**

- A full-featured error and performance monitoring platform, not just crash reporting. You get breadcrumbs, performance tracing, session replay, and more in one SDK.
- Rich context capture by default: device state, breadcrumbs of user actions, HTTP requests, and navigation events leading up to a crash.
- Powerful query and filtering interface. You can slice and dice issues by tags, releases, environments, and custom attributes.
- Open-source and available for self-hosting if your organization has data residency or compliance requirements.
- First-class support for source context and stack trace deobfuscation with dSYM upload.
- Supports release health tracking, giving you crash-free session and user metrics per release.
- Works across platforms (iOS, Android, web, backend), so you can correlate errors across your entire stack in one dashboard.

**Cons:**

- The free tier has usage limits (errors per month, limited data retention). For large-scale apps, costs can grow.
- The SDK is heavier than Crashlytics, which may matter if you are very sensitive to binary size.
- More configuration surface area. The additional power comes with more options to set up and tune.
- If you are already deep in the Firebase ecosystem, adding Sentry means maintaining a separate service and dashboard.

---

## Recommendation Guidelines

**Choose Crashlytics if:**

- You are already using Firebase and want a zero-cost, low-friction crash reporter.
- Your needs are straightforward: see crashes, get alerts, fix them.
- You are a small team or indie developer and want minimal operational overhead.

**Choose Sentry if:**

- You need deeper diagnostics: breadcrumbs, rich context, custom tags, and advanced filtering.
- You want unified error tracking across iOS, Android, and backend services.
- You need self-hosting or have strict data compliance requirements.
- You care about performance monitoring alongside crash reporting in one tool.
- You are on a larger team where the ability to assign, triage, and query issues at scale matters.

---

## Integration Overview

### Crashlytics (via Swift Package Manager)

```swift
// AppDelegate.swift
import FirebaseCore
import FirebaseCrashlytics

func application(_ application: UIApplication,
                 didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
    FirebaseApp.configure()
    // Optional: log custom keys for extra context
    Crashlytics.crashlytics().setCustomValue("free", forKey: "account_type")
    return true
}
```

### Sentry (via Swift Package Manager)

```swift
// AppDelegate.swift
import Sentry

func application(_ application: UIApplication,
                 didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
    SentrySDK.start { options in
        options.dsn = "https://your-dsn@sentry.io/project-id"
        options.tracesSampleRate = 0.2
        options.attachScreenshot = true
        options.enableAutoSessionTracking = true
    }
    return true
}
```

Both require uploading dSYM files for symbolication. Crashlytics handles this via a build phase script or the Firebase CLI, while Sentry uses `sentry-cli` or its Fastlane plugin.

---

## Summary Table

| Criteria | Crashlytics | Sentry |
|---|---|---|
| Cost | Free | Free tier with limits; paid plans |
| Setup complexity | Low | Moderate |
| Crash reporting | Yes | Yes |
| Performance monitoring | Separate Firebase product | Built-in |
| Breadcrumbs and context | Basic | Rich |
| Dashboard and querying | Basic | Advanced |
| Self-hosting option | No | Yes |
| Cross-platform unified view | Firebase only | All platforms |
| SDK size impact | Minimal | Moderate |
| Firebase ecosystem fit | Native | Separate |

Either tool will give you reliable crash reporting. The decision comes down to whether you need a simple, free, Firebase-native solution or a more powerful, cross-platform observability platform.
