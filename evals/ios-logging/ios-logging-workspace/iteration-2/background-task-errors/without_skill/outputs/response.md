# Background Sync Task Fails Silently -- Diagnosis and Fix

## The Core Problem

Your `handleSync` function has a critical flaw: **exceptions thrown inside the `Task` block are not caught**, which means `task.setTaskCompleted(success:)` is never called when `performSync()` throws. When BGTaskScheduler never receives a completion signal, the system considers the task as still running until it times out, and the OS may throttle or penalize future scheduling of your task.

## What Happens When It Fails

1. `performSync()` throws an error.
2. The `try` causes the `Task` closure to exit early.
3. `task.setTaskCompleted(success: true)` is never reached.
4. The system eventually kills the task after its time budget expires.
5. No error is logged anywhere -- hence the "silent" failure.
6. The OS may reduce your app's background execution budget as a penalty for not completing tasks properly.

## The Fix

```swift
func handleSync(task: BGProcessingTask) {
    let syncTask = Task {
        do {
            try await performSync()
            task.setTaskCompleted(success: true)
        } catch {
            print("Background sync failed: \(error)")
            task.setTaskCompleted(success: false)
        }
    }

    // Handle expiration -- the system can revoke your time at any moment
    task.expirationHandler = {
        syncTask.cancel()
        task.setTaskCompleted(success: false)
    }
}
```

## Key Changes Explained

### 1. Catch errors and always call `setTaskCompleted`

The `do/catch` block ensures that `setTaskCompleted` is called on both the success and failure paths. This is the most important fix. BGTaskScheduler requires you to signal completion; failing to do so is treated as a misbehaving task.

### 2. Set an expiration handler

The system can revoke your background execution time at any moment (low battery, resource pressure, etc.). Without an `expirationHandler`, your task just gets killed mid-execution with no cleanup. The expiration handler cancels the in-flight async work and signals completion so the OS knows you handled it gracefully.

### 3. Store a reference to the Task for cancellation

By assigning the `Task` to a local variable (`syncTask`), the expiration handler can call `cancel()` on it. This triggers cooperative cancellation -- your `performSync()` should check `Task.isCancelled` periodically or use cancellation-aware APIs (like `URLSession` tasks) to stop work promptly.

## Additional Recommendations

### Make `performSync` cancellation-aware

```swift
func performSync() async throws {
    let items = try await fetchPendingItems()

    for item in items {
        try Task.checkCancellation() // Exit early if the system revoked our time
        try await syncItem(item)
    }
}
```

### Add structured logging instead of print

Replace `print` with `os.Logger` so you can actually diagnose issues in production via Console.app or device logs:

```swift
import os

private let logger = Logger(subsystem: "com.yourapp", category: "BackgroundSync")

func handleSync(task: BGProcessingTask) {
    let syncTask = Task {
        do {
            logger.info("Background sync started")
            try await performSync()
            logger.info("Background sync completed successfully")
            task.setTaskCompleted(success: true)
        } catch {
            logger.error("Background sync failed: \(error.localizedDescription)")
            task.setTaskCompleted(success: false)
        }
    }

    task.expirationHandler = {
        logger.warning("Background sync expired by system")
        syncTask.cancel()
        task.setTaskCompleted(success: false)
    }
}
```

### Schedule the next sync on failure

If the sync fails, you likely want to retry. Schedule the next background task immediately so it runs when conditions allow:

```swift
catch {
    logger.error("Background sync failed: \(error.localizedDescription)")
    task.setTaskCompleted(success: false)
    scheduleNextSync() // Re-register so the system tries again later
}
```

### Validate your task registration

Make sure you are registering the task identifier in both `Info.plist` (under `BGTaskSchedulerPermittedIdentifiers`) and in code during `application(_:didFinishLaunchingWithOptions:)`. A common cause of silent failures is a mismatched task identifier between registration and scheduling.

## Summary

| Issue | Impact | Fix |
|-------|--------|-----|
| No error handling in Task block | Errors silently swallowed, `setTaskCompleted` never called | Wrap in `do/catch`, always call `setTaskCompleted` |
| No expiration handler | System kills task with no cleanup when time runs out | Add `expirationHandler` that cancels work and signals completion |
| No cancellation support | Task keeps running after expiration, wasting resources | Store `Task` reference, check `Task.isCancelled` in sync logic |
| Using `print` for logging | No visibility into production failures | Use `os.Logger` with subsystem and category |
| No retry on failure | One failure means data stays stale until next scheduled run | Re-schedule the task in the catch block |
