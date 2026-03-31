# Fixing Missing Crash Reports from Widget and Notification Service Extensions in Sentry

## Root Cause

Widgets and notification service extensions run as **separate processes** from your main app. Sentry SDK initialization in your main app's `AppDelegate` or `@main App` struct does **not** carry over to extension processes. Each extension has its own process lifecycle, its own memory space, and needs its own Sentry initialization. Without it, crashes in those processes are never captured.

## Fix: Initialize Sentry Separately in Each Extension

### 1. Widget Extension

In your widget's entry point, initialize Sentry before any work happens:

```swift
import WidgetKit
import SwiftUI
import Sentry

@main
struct MyWidget: Widget {
    init() {
        SentrySDK.start { options in
            options.dsn = "https://your-dsn@sentry.io/project-id"
            options.enableAutoSessionTracking = false // Extensions should not track sessions
            options.debug = false
        }
    }

    var body: some WidgetConfiguration {
        StaticConfiguration(kind: "MyWidget", provider: MyProvider()) { entry in
            MyWidgetEntryView(entry: entry)
        }
    }
}
```

### 2. Notification Service Extension

Initialize Sentry at the top of `didReceive(_:withContentHandler:)`, before you process the notification:

```swift
import UserNotifications
import Sentry

class NotificationService: UNNotificationServiceExtension {
    var contentHandler: ((UNNotificationContent) -> Void)?
    var bestAttemptContent: UNMutableNotificationContent?

    override func didReceive(
        _ request: UNNotificationRequest,
        withContentHandler contentHandler: @escaping (UNNotificationContent) -> Void
    ) {
        // Initialize Sentry for this extension process
        SentrySDK.start { options in
            options.dsn = "https://your-dsn@sentry.io/project-id"
            options.enableAutoSessionTracking = false
            options.debug = false
        }

        self.contentHandler = contentHandler
        bestAttemptContent = (request.content.mutableCopy() as? UNMutableNotificationContent)

        // ... your notification processing logic ...

        if let bestAttemptContent = bestAttemptContent {
            contentHandler(bestAttemptContent)
        }
    }

    override func serviceExtensionTimeWillExpire() {
        if let contentHandler = contentHandler, let bestAttemptContent = bestAttemptContent {
            contentHandler(bestAttemptContent)
        }
    }
}
```

### 3. Share the DSN Cleanly Using App Groups

Avoid hardcoding the DSN in multiple places. Use App Groups to share configuration:

```swift
// In your main app, store the DSN at launch:
let sharedDefaults = UserDefaults(suiteName: "group.com.yourcompany.yourapp")
sharedDefaults?.set("https://your-dsn@sentry.io/project-id", forKey: "sentryDSN")

// In each extension, read it:
func initializeSentry() {
    let sharedDefaults = UserDefaults(suiteName: "group.com.yourcompany.yourapp")
    guard let dsn = sharedDefaults?.string(forKey: "sentryDSN") else { return }

    SentrySDK.start { options in
        options.dsn = dsn
        options.enableAutoSessionTracking = false
    }
}
```

## Additional Required Steps

### 4. Enable dSYM Generation for All Extension Targets

Without dSYMs, even if crashes arrive in Sentry, they will show unsymbolicated hex addresses instead of function names.

For **each** target (main app, widget extension, notification service extension):

- Go to Build Settings and set Debug Information Format to **"DWARF with dSYM File"** for the Release configuration.
- Add the Sentry dSYM upload build phase script to **each target's** Build Phases (not just the main app).

### 5. Add Sentry as a Dependency to Each Extension Target

In your `Podfile`, `Package.swift`, or SPM settings, make sure each extension target links against the Sentry SDK:

**Podfile example:**
```ruby
target 'MyApp' do
  pod 'Sentry'
end

target 'MyWidgetExtension' do
  pod 'Sentry'
end

target 'MyNotificationServiceExtension' do
  pod 'Sentry'
end
```

**SPM:** In Xcode, select each extension target under "Frameworks, Libraries, and Embedded Content" and add the Sentry package product.

### 6. Disable Session Tracking in Extensions

Always set `options.enableAutoSessionTracking = false` in extensions. Extensions have very short lifetimes and do not represent user sessions. Enabling session tracking inflates your session count and distorts crash-free session metrics.

### 7. Be Aware of Extension Memory Limits

Widget extensions have a memory ceiling of roughly 50 MB. If the Sentry SDK plus your widget logic pushes close to this limit, the system will terminate the extension with a SIGKILL (which Sentry cannot catch since it is an immediate process kill). Monitor memory usage in your widget timeline provider and keep allocations minimal.

## Verifying the Fix

1. Add a test crash in the widget's `getTimeline()` or the notification service's `didReceive()`:
   ```swift
   SentrySDK.crash() // Remove after testing
   ```
2. Run the extension on a real device (simulators may not deliver extension crashes reliably to Sentry).
3. Relaunch the main app or the extension -- Sentry sends stored crash reports on the next SDK initialization in that process.
4. Check your Sentry dashboard. Filter by the `app.identifier` tag to distinguish main app crashes from extension crashes.

## Summary Checklist

| Step | Main App | Widget Extension | Notification Extension |
|------|----------|-----------------|----------------------|
| `SentrySDK.start` call | In `AppDelegate` / `@main` | In `Widget.init()` | In `didReceive()` |
| `enableAutoSessionTracking` | `true` | `false` | `false` |
| Sentry SDK linked as dependency | Yes | Yes | Yes |
| dSYM format set to DWARF+dSYM | Yes | Yes | Yes |
| dSYM upload build phase added | Yes | Yes | Yes |
| App Groups for shared DSN | Configure group | Read from group | Read from group |
