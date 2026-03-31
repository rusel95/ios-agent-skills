# Error Handling Analysis: `loadUserProfile()`

## Problems Identified

This function has **two compounding silent failure patterns** that will make production debugging nearly impossible.

### 1. `try?` erases all diagnostic information

```swift
let profile = try? await api.fetchProfile(userId: currentUser.id)
```

`try?` converts any thrown error into `nil`, destroying the error type, message, HTTP status code, and stack context entirely. Was it a 401 unauthorized? A network timeout? A JSON decoding failure? A server 500? All of that information is permanently lost.

`try?` is only acceptable for best-effort operations where failure is genuinely irrelevant (temp file cleanup, optional cache reads, cosmetic prefetches). Fetching a user profile is a **user-facing operation** -- failure matters and must be diagnosed.

### 2. `Task {}` swallows errors silently

`Task.init` is `@discardableResult`. If the code inside throws, the error is silently discarded -- no crash, no log, no indication anything went wrong. Even though `try?` prevents the throw here, this `Task {}` body has no error handling path at all. The user will simply see no profile loaded, with no way to know why.

### 3. No observability of any kind

There is no logging (`os.Logger`), no crash SDK reporting (`ErrorReporter`), and no user-facing error state. In production, this function will silently fail and leave the user staring at a blank or stale profile screen with zero diagnostic trail.

## Corrected Implementation

```swift
import os

func loadUserProfile() {
    Task {
        do {
            let profile = try await api.fetchProfile(userId: currentUser.id)
            self.profile = profile
        } catch is CancellationError {
            // Task was cancelled (e.g., view disappeared) -- normal lifecycle, not an error
        } catch {
            Logger.networking.error(
                "Failed to load profile for user \(currentUser.id, privacy: .private): \(error.localizedDescription, privacy: .public)"
            )
            ErrorReporter.shared.recordNonFatal(error, context: [
                "operation": "loadUserProfile",
                "userId": currentUser.id
            ])
            self.loadError = error  // Surface to the UI so the user sees an error state
        }
    }
}
```

## What changed and why

| Change | Reason |
|--------|--------|
| Replaced `try?` with `do/catch` | Preserves the full error -- type, message, HTTP status, stack context -- instead of converting it to `nil` |
| Added `Logger.networking.error(...)` | Logs the failure to the unified logging system with privacy annotations, persisted to disk, searchable via Console.app and log archives |
| Added `ErrorReporter.shared.recordNonFatal(...)` | Reports the error to the remote crash SDK (Sentry/Crashlytics) so it appears in production dashboards |
| Added `CancellationError` handling | Distinguishes normal task cancellation (view disappeared) from real failures -- avoids noise in crash reports |
| Added `self.loadError = error` | Gives the UI an error state to display (retry button, error message) instead of leaving the user on a blank screen |
| Used `privacy: .private` on user ID | The user ID is PII and must not appear in plaintext in persisted logs; `privacy: .private` redacts it unless viewing on a device with a matching profile |

## The core rule

Every `Task {}` containing `try` must have an explicit `do/catch` inside it with:
1. A structured log via `os.Logger` (with privacy annotations on dynamic values)
2. A report to the remote crash/analytics SDK
3. A user-facing error state when the operation is user-visible
