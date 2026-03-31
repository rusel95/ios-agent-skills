Your code has three silent failure patterns that can cause the observer to appear to "not fire":

## 1. Observer token is not stored -- observation silently deallocates

`addObserver(forName:object:queue:using:)` returns an `NSObjectProtocol` token. If you discard it, the observation is immediately eligible for deallocation and may be removed before any notification is posted. This is the most likely cause of your issue.

```swift
// BAD -- token discarded, observer can be deallocated immediately
func setupNotifications() {
    NotificationCenter.default.addObserver(
        forName: NSNotification.Name("dataUpdated"),
        object: nil,
        queue: .main
    ) { notification in
        self.refreshData()
    }
}
```

Store the token as a property and remove it on deinit:

```swift
private var notificationToken: NSObjectProtocol?

func setupNotifications() {
    notificationToken = NotificationCenter.default.addObserver(
        forName: .dataUpdated,
        object: nil,
        queue: .main
    ) { [weak self] notification in
        guard let self else { return }
        self.refreshData()
    }
}

deinit {
    if let token = notificationToken {
        NotificationCenter.default.removeObserver(token)
    }
}
```

## 2. String-based notification name -- typos cause silent mismatches

You are using a raw string `"dataUpdated"`. If the posting side uses a slightly different string (e.g., `"DataUpdated"`, `"data_updated"`), the observer will never match and no compiler warning is generated.

Define a typed constant so the compiler catches mismatches:

```swift
extension Notification.Name {
    static let dataUpdated = Notification.Name("dataUpdated")
}

// Post site:
NotificationCenter.default.post(name: .dataUpdated, object: nil)

// Observer site:
notificationToken = NotificationCenter.default.addObserver(
    forName: .dataUpdated, ...
)
```

## 3. Strong reference cycle via closure capture

Your closure captures `self` strongly. This creates a retain cycle where `self` keeps the token alive and the token's closure keeps `self` alive. The object never deallocates, which can cause duplicate observers on repeated calls and other lifecycle issues. Use `[weak self]` as shown above.

## 4. Add observability so you know when it fails

Even after fixing the structural issues, add logging so that in production you can tell whether observers are being registered and whether notifications are being received:

```swift
import os

extension Logger {
    static let notifications = Logger(subsystem: Bundle.main.bundleIdentifier ?? "app", category: "notifications")
}

func setupNotifications() {
    notificationToken = NotificationCenter.default.addObserver(
        forName: .dataUpdated,
        object: nil,
        queue: .main
    ) { [weak self] notification in
        guard let self else {
            Logger.notifications.error("dataUpdated received but self was deallocated")
            return
        }
        Logger.notifications.debug("dataUpdated notification received, refreshing data")
        self.refreshData()
    }
    Logger.notifications.debug("Registered observer for dataUpdated")
}
```

Use `os.Logger` instead of `print()` -- `print()` is invisible on production devices (no debugger attached), has no log levels, no privacy controls, and is not part of the unified logging system.

## Summary

| Problem | Fix |
|---------|-----|
| Observer token not stored | Store as property, remove in `deinit` |
| String-based notification name | Use typed `Notification.Name` extension |
| Strong capture of `self` | Use `[weak self]` in closure |
| No observability | Add `os.Logger` calls at registration and receipt |
