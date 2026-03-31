# NotificationCenter Observer Not Firing: Diagnosis and Fix

## The Problem

Your observer closure captures `self` strongly, but the real issue is likely that the **observer token is not being retained**, causing the observer to be deallocated and silently removed.

When you use the block-based `addObserver(forName:object:queue:)` API, it returns an `NSObjectProtocol` token. If you discard that token, the observer can be removed at any time by the system. Unlike the selector-based `addObserver(_:selector:name:object:)` API (which keeps the observer alive as long as the observing object exists), the block-based API requires you to hold onto the returned token yourself.

## Root Cause

```swift
func setupNotifications() {
    // The return value is discarded -- the observer may be removed at any time
    NotificationCenter.default.addObserver(
        forName: NSNotification.Name("dataUpdated"),
        object: nil,
        queue: .main
    ) { notification in
        self.refreshData()
    }
}
```

There are two issues here:

1. **Discarded observer token** -- The returned `NSObjectProtocol` is not stored, so the system may deallocate the observer at any point, causing it to silently stop firing.
2. **Strong capture of `self`** -- The closure captures `self` strongly, which can create a retain cycle if `self` also holds a strong reference to the observer token (or to an object that does).

## The Fix

Store the observer token and use `[weak self]` to avoid retain cycles:

```swift
class MyViewController: UIViewController {
    private var notificationObserver: NSObjectProtocol?

    func setupNotifications() {
        notificationObserver = NotificationCenter.default.addObserver(
            forName: NSNotification.Name("dataUpdated"),
            object: nil,
            queue: .main
        ) { [weak self] notification in
            self?.refreshData()
        }
    }

    deinit {
        if let observer = notificationObserver {
            NotificationCenter.default.removeObserver(observer)
        }
    }
}
```

## Key Changes

1. **Store the token** in a property (`notificationObserver`) so the observer stays alive for the lifetime of the object.
2. **Use `[weak self]`** in the closure to prevent a retain cycle between the observer token and the owning object.
3. **Remove the observer in `deinit`** to clean up explicitly. While modern iOS versions (iOS 9+) automatically remove selector-based observers on deallocation, block-based observers that are still retained will continue to fire unless explicitly removed.

## Additional Considerations

- **Multiple calls to `setupNotifications()`**: If this method is called more than once (e.g., in `viewWillAppear`), you will register multiple observers and the callback will fire multiple times per notification. Either guard against duplicate registration or remove the previous observer before adding a new one.

- **Notification name as a string literal**: Using raw strings like `"dataUpdated"` is fragile. Define a static constant or use `Notification.Name` extension to avoid typos:

```swift
extension Notification.Name {
    static let dataUpdated = Notification.Name("dataUpdated")
}
```

- **Thread safety**: You specified `queue: .main`, which is correct if `refreshData()` updates the UI. Be aware that the notification is dispatched asynchronously to the main queue, so there may be a slight delay compared to posting on the main thread directly.

- **Object parameter filtering**: You pass `object: nil`, meaning you observe notifications from any sender. If a specific object posts the notification, make sure the sender matches what you expect or keep `nil` for all senders.

## Debugging Tips

If the observer still does not fire after applying the fix:

1. **Verify the notification is actually posted**: Add a breakpoint or log at the `NotificationCenter.default.post(name:)` call site.
2. **Verify naming matches**: Ensure the notification name string is identical at both the post and observe sites. Using a shared constant eliminates this risk.
3. **Check object lifetime**: If the object owning the observer is deallocated before the notification is posted, the weak reference will be nil and `refreshData()` will not be called. This is correct behavior but may look like a bug.
4. **Check posting thread**: If the notification is posted from a background thread and you observe on `.main`, the block is dispatched asynchronously. The callback will fire, but not synchronously with the post.
