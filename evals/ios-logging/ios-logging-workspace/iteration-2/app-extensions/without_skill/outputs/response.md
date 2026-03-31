# Fixing Sentry Crash Reporting in Widget and Notification Service Extensions

## Why Extension Crashes Don't Appear

App extensions run in their own separate processes, completely independent from the main app. The Sentry SDK initialized in your main app target has no visibility into crashes that occur in extension processes. Each extension needs its own Sentry initialization.

## Step 1: Add Sentry to Each Extension Target

Make sure the Sentry SDK is linked to both your widget extension and notification service extension targets. In your `Podfile` or `Package.swift`, include Sentry for each target:

**CocoaPods:**

```ruby
target 'MyApp' do
  pod 'Sentry', '~> 8.0'
end

target 'MyWidgetExtension' do
  pod 'Sentry', '~> 8.0'
end

target 'MyNotificationServiceExtension' do
  pod 'Sentry', '~> 8.0'
end
```

**Swift Package Manager:** In Xcode, select each extension target under "Frameworks, Libraries, and Embedded Content" and add the Sentry package.

## Step 2: Initialize Sentry in Each Extension's Entry Point

**Widget Extension:**

```swift
import Sentry
import WidgetKit
import SwiftUI

@main
struct MyWidget: Widget {
    init() {
        SentrySDK.start { options in
            options.dsn = "https://your-dsn@sentry.io/project-id"
            options.environment = "production"
            // Use a lower sample rate for extensions to reduce overhead
            options.sampleRate = 1.0
            options.enableAutoSessionTracking = false
            // Disable features not needed in extensions
            options.enableUIViewControllerTracing = false
            options.enableNetworkTracking = false
        }
    }

    var body: some WidgetConfiguration {
        // your widget configuration
    }
}
```

**Notification Service Extension:**

```swift
import Sentry
import UserNotifications

class NotificationService: UNNotificationServiceExtension {

    override init() {
        super.init()
        SentrySDK.start { options in
            options.dsn = "https://your-dsn@sentry.io/project-id"
            options.environment = "production"
            options.enableAutoSessionTracking = false
            options.enableUIViewControllerTracing = false
            options.enableNetworkTracking = false
        }
    }

    override func didReceive(
        _ request: UNNotificationRequest,
        withContentHandler contentHandler: @escaping (UNNotificationContent) -> Void
    ) {
        // your notification handling logic
    }

    override func serviceExtensionTimeWillExpire() {
        // flush Sentry events before the extension is terminated
        SentrySDK.flush(timeout: 2.0)
    }
}
```

## Step 3: Handle the Short Extension Lifecycle

This is the most commonly missed piece. Extensions have very limited execution time (widgets get around 30 seconds, notification service extensions get about 30 seconds). If the extension is terminated before Sentry can send the crash report, the event is lost.

- **Call `SentrySDK.flush(timeout:)`** before the extension finishes work or in `serviceExtensionTimeWillExpire()`. This forces Sentry to send any queued events synchronously.
- **Enable `options.enableCrashHandler = true`** (this is the default). Crash reports are written to disk and sent on the next launch of the extension process.

## Step 4: Distinguish Extension Events from App Events

Set tags or context so you can filter extension crashes separately in the Sentry dashboard:

```swift
SentrySDK.configureScope { scope in
    scope.setTag(value: "widget-extension", forKey: "process")
}
```

Or for the notification service extension:

```swift
SentrySDK.configureScope { scope in
    scope.setTag(value: "notification-service-extension", forKey: "process")
}
```

This lets you create Sentry alerts and filters specifically for extension crashes.

## Step 5: Verify Crash Delivery

Extensions share a sandboxed container with the main app only if they belong to the same App Group. Sentry stores crash reports on disk and sends them on the next process launch. Since extensions launch infrequently, there can be a significant delay before reports appear.

To verify your setup:

1. Force a test crash in the extension: `SentrySDK.crash()`
2. Trigger the extension again (reload the widget or send a push notification)
3. Check the Sentry dashboard -- the crash should appear on the second launch

## Common Pitfalls

- **Missing the Sentry framework in the extension target's link phase.** Double-check Build Phases > Link Binary With Libraries for each extension target.
- **App Transport Security.** Extensions inherit the main app's `Info.plist` ATS settings, but make sure Sentry's domain is not blocked.
- **Memory limits.** Widget extensions have a ~30 MB memory limit. Sentry's footprint is small, but be mindful of overall memory usage. If the extension is killed due to memory pressure, the crash may be attributed to a `SIGKILL` which Sentry cannot catch (the OS kills the process without invoking signal handlers).
- **Not calling `flush`.** Without flushing, events may sit in the queue and never be sent because the extension process is terminated before the background upload completes.
