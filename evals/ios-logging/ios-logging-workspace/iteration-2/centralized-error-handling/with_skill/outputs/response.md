# Centralized Error Handling in SwiftUI Views

Setting an error string and showing an alert is a start, but it leaves you blind in production. Errors vanish the moment the user taps "OK" -- no logging, no remote reporting, no categorized recovery. Here is how to build a proper centralized error handling layer.

## The Problem With Per-View Error Strings

A typical pattern looks like this:

```swift
@State private var errorMessage = ""
@State private var showError = false

func loadData() async {
    do {
        data = try await api.fetchItems()
    } catch {
        errorMessage = error.localizedDescription  // Only visible to the user
        showError = true                            // No logging, no remote reporting
    }
}
```

This has three production-critical problems:
1. **No structured logging** -- the error never reaches `os.Logger`, so it is invisible in Console.app and on-device log archives.
2. **No remote reporting** -- if this fails for 20% of users, you will never know. The error exists only on the user's screen until they dismiss it.
3. **No categorized recovery** -- a 401 Unauthorized and a 500 Server Error both show the same generic alert with no path to retry or re-authenticate.

## Step 1: Categorize Your Errors

Define an error category system so the handler knows what to do with each error:

```swift
enum ErrorCategory {
    case retryable
    case nonRetryable
    case requiresLogout
}

protocol CategorizedError: Error {
    var category: ErrorCategory { get }
}

extension NetworkError: CategorizedError {
    var category: ErrorCategory {
        switch self {
        case .timeout, .serverError(5...):
            return .retryable
        case .notFound, .decodingFailed:
            return .nonRetryable
        case .unauthorized:
            return .requiresLogout
        }
    }
}
```

## Step 2: Build a Centralized ErrorHandler

SwiftUI has no built-in Error Boundary mechanism like React. You need to build one explicitly. Create a single `ErrorHandler` that every view routes errors through:

```swift
@MainActor
final class ErrorHandler: ObservableObject {
    @Published var currentAlert: AlertInfo?

    func handle(_ error: Error, context: String) {
        // 1. ALWAYS log with os.Logger and privacy annotations
        Logger.ui.error("\(context, privacy: .public): \(error.localizedDescription, privacy: .public)")

        // 2. ALWAYS report to your crash/error SDK
        ErrorReporter.shared.recordNonFatal(error, context: ["context": context])

        // 3. Route the user-facing response based on error category
        if let categorized = error as? CategorizedError {
            switch categorized.category {
            case .retryable:
                currentAlert = AlertInfo(
                    title: "Temporary Issue",
                    message: "Please try again in a moment.",
                    retryAction: { /* caller provides */ }
                )
            case .nonRetryable:
                currentAlert = AlertInfo(
                    title: "Something Went Wrong",
                    message: error.localizedDescription
                )
            case .requiresLogout:
                AuthManager.shared.logout()
                currentAlert = AlertInfo(
                    title: "Session Expired",
                    message: "Please sign in again."
                )
            }
        } else {
            // Uncategorized errors still get logged and reported above
            currentAlert = AlertInfo(
                title: "Error",
                message: error.localizedDescription
            )
        }
    }
}
```

The key principle: every error that passes through `handle()` is (a) logged locally with `os.Logger`, (b) reported remotely to your crash SDK, and (c) shown to the user with category-appropriate messaging. No error is silently swallowed.

## Step 3: Wire It Into SwiftUI With a ViewModifier

Create a reusable modifier so you do not duplicate alert-binding logic across views:

```swift
struct ErrorHandlingModifier: ViewModifier {
    @EnvironmentObject var errorHandler: ErrorHandler

    func body(content: Content) -> some View {
        content.alert(item: $errorHandler.currentAlert) { alert in
            Alert(
                title: Text(alert.title),
                message: Text(alert.message),
                dismissButton: .default(Text("OK"))
            )
        }
    }
}

extension View {
    func withErrorHandling() -> some View {
        modifier(ErrorHandlingModifier())
    }
}
```

Attach it once at your app root:

```swift
@main
struct MyApp: App {
    @StateObject private var errorHandler = ErrorHandler()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(errorHandler)
                .withErrorHandling()
        }
    }
}
```

## Step 4: Use It In Views

Now your views delegate error handling instead of managing it locally:

```swift
struct ItemListView: View {
    @EnvironmentObject var errorHandler: ErrorHandler
    @State private var items: [Item] = []

    var body: some View {
        List(items) { item in
            Text(item.name)
        }
        .task {
            do {
                items = try await api.fetchItems()
            } catch is CancellationError {
                // Normal -- view disappeared, do not log as an error
                return
            } catch {
                errorHandler.handle(error, context: "ItemListView.loadItems")
            }
        }
    }
}
```

Note the `CancellationError` check. SwiftUI's `.task {}` modifier cancels its task when the view disappears. This is normal lifecycle behavior, not an error. Always filter it out before routing to the error handler, otherwise you will flood your crash SDK with noise.

## Step 5: Abstract Your Crash SDK Behind a Protocol

Never call Sentry, Crashlytics, or any SDK directly throughout your codebase. Use a protocol so you can swap vendors or add a composite reporter without touching every call site:

```swift
protocol ErrorReporter: Sendable {
    func recordNonFatal(_ error: Error, context: [String: Any])
    func addBreadcrumb(message: String, category: String, level: BreadcrumbLevel, data: [String: Any]?)
    func setUserID(_ userID: String?)
}
```

Then implement it for your chosen SDK (Sentry, Crashlytics, etc.). This also makes testing straightforward -- inject a mock `ErrorReporter` in tests to verify that errors are actually reported.

## Why This Matters

Non-fatal errors affect 10-30%+ of sessions silently. Crashes affect only 1-2%. The `catch { errorMessage = error.localizedDescription }` pattern means you are blind to the vast majority of production issues. With the centralized handler, every error is:

- **Logged locally** via `os.Logger` with privacy annotations (visible in Console.app and on-device diagnostics)
- **Reported remotely** via your crash SDK (visible in Sentry/Crashlytics dashboard -- turns a 3-day debugging mystery into a 15-minute investigation)
- **Categorized for recovery** so retryable errors offer retry, auth errors trigger re-login, and permanent errors show an appropriate message
