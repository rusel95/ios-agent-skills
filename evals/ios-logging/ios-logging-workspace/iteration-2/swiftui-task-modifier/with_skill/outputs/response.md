# What's Wrong With This SwiftUI Data Loading Pattern

This code has two critical problems that will cause silent failures in production.

## Problem 1: `try?` Inside `.task` Silently Swallows All Errors

```swift
.task {
    profile = try? await ProfileService.shared.fetch()
}
```

The `try?` converts every possible failure into `nil`. Was it a 401 unauthorized? A network timeout? A JSON decoding error? A server 500? All of that diagnostic information is permanently destroyed. In production, the user sees an infinite `ProgressView` spinner with no way for you or the user to know what went wrong.

## Problem 2: No `CancellationError` Handling

The `.task` modifier's closure has the signature `@Sendable () async -> Void`. When the view disappears (e.g., the user navigates away), SwiftUI cancels the task by throwing `CancellationError`. With `try?`, cancellation is silently absorbed just like a real error. If you later add logging without distinguishing cancellation, you will flood your error reports with false positives from normal view lifecycle behavior.

## Problem 3: No Error State for the UI

There is no `@State` property capturing the error. The view has exactly two states: loaded or loading. If the fetch fails, the user is stuck on `ProgressView()` forever with no error message, no retry button, and no way to recover.

## Fixed Version

```swift
struct ProfileView: View {
    @State private var profile: Profile?
    @State private var loadError: Error?

    var body: some View {
        VStack {
            if let profile {
                ProfileContent(profile: profile)
            } else if let loadError {
                ContentUnavailableView {
                    Label("Failed to Load", systemImage: "exclamationmark.triangle")
                } description: {
                    Text(loadError.localizedDescription)
                } actions: {
                    Button("Retry") {
                        self.loadError = nil
                        Task { await loadProfile() }
                    }
                }
            } else {
                ProgressView()
            }
        }
        .task {
            await loadProfile()
        }
    }

    private func loadProfile() async {
        do {
            profile = try await ProfileService.shared.fetch()
        } catch is CancellationError {
            // View disappeared — normal lifecycle, not an error
        } catch {
            loadError = error
            Logger.networking.error(
                "Profile fetch failed: \(error.localizedDescription, privacy: .public)"
            )
            ErrorReporter.shared.recordNonFatal(
                error,
                context: ["screen": "profile"]
            )
        }
    }
}
```

## What Changed and Why

| Aspect | Original | Fixed |
|---|---|---|
| Error visibility | `try?` destroys all error info | `do/catch` preserves the full error |
| Cancellation | Treated same as real failure | `catch is CancellationError` filters it out as normal lifecycle |
| User experience | Infinite spinner on failure | `ContentUnavailableView` with a retry button |
| Local logging | None | `Logger.networking.error()` with privacy annotations |
| Remote reporting | None | `ErrorReporter.shared.recordNonFatal()` sends to crash SDK |
| Retry | Impossible | User can tap Retry to re-attempt the fetch |

The core rule: **never use `try?` inside `.task` for network, persistence, auth, or any user-facing operation**. Always use `do/catch` with explicit `CancellationError` handling, structured logging via `os.Logger`, and remote error reporting through your crash SDK.
