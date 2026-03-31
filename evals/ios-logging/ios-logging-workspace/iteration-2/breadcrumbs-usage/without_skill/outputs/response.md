# Breadcrumbs in Crash Reporting

## What Are Breadcrumbs?

Breadcrumbs are sequential log entries that record events leading up to a crash or error. They create a chronological trail of user actions, system events, and application state changes that happened before something went wrong. When a crash occurs, the breadcrumb trail is attached to the crash report, giving developers context about what the user was doing and what the app was experiencing in the moments before the failure.

Think of them as a flight recorder (black box) for your app. Instead of just seeing a stack trace showing where the crash happened, you get a timeline of events showing the path that led there.

Most crash reporting SDKs (Sentry, Firebase Crashlytics, Datadog, Bugsnag) automatically capture some breadcrumbs, such as network requests, UI lifecycle events, and system notifications. However, there are many situations where adding manual breadcrumbs significantly improves your ability to diagnose issues.

## When to Add Manual Breadcrumbs

### 1. Key User Actions

Record meaningful user interactions that affect application flow:

```swift
// User tapped a critical button
SentrySDK.addBreadcrumb(Breadcrumb(level: .info, category: "user.action"))
// message: "User tapped 'Place Order' button"

// User toggled an important setting
SentrySDK.addBreadcrumb(Breadcrumb(level: .info, category: "user.action"))
// message: "User enabled offline mode"
```

### 2. Navigation Events

Track screen transitions to understand the user's journey:

```swift
func trackScreenView(_ screenName: String) {
    let crumb = Breadcrumb(level: .info, category: "navigation")
    crumb.message = "Navigated to \(screenName)"
    SentrySDK.addBreadcrumb(crumb)
}
```

### 3. State Changes

Record significant changes in application state:

```swift
// Authentication state changes
addBreadcrumb(category: "auth", message: "User logged in successfully")
addBreadcrumb(category: "auth", message: "Token refresh attempted")

// Connectivity changes
addBreadcrumb(category: "network", message: "Switched from WiFi to cellular")

// App lifecycle
addBreadcrumb(category: "app", message: "App entered background with active download")
```

### 4. Critical Business Logic

Add breadcrumbs around important business operations:

```swift
// Payment flow
addBreadcrumb(category: "payment", message: "Started checkout with 3 items, total: $45.99")
addBreadcrumb(category: "payment", message: "Payment method selected: Apple Pay")
addBreadcrumb(category: "payment", message: "Payment authorization received")

// Data sync
addBreadcrumb(category: "sync", message: "Started sync, 42 records pending")
addBreadcrumb(category: "sync", message: "Sync conflict detected on record ID 1234")
```

### 5. Before Risky Operations

Add breadcrumbs before operations that are known to be fragile or crash-prone:

```swift
// Before file operations
addBreadcrumb(category: "file", message: "Writing cache file, size: \(dataSize) bytes")

// Before database migrations
addBreadcrumb(category: "database", message: "Starting migration from v3 to v4")

// Before parsing external data
addBreadcrumb(category: "parsing", message: "Parsing API response, content-length: \(length)")
```

### 6. Error Recovery Paths

When your app handles an error gracefully, record it as a breadcrumb since a subsequent crash might be related:

```swift
do {
    try riskyOperation()
} catch {
    addBreadcrumb(category: "error", message: "Handled error in riskyOperation: \(error.localizedDescription)")
    // fallback logic...
}
```

## Best Practices

- **Keep messages concise**: Breadcrumbs should be short and informative. Avoid including large payloads or sensitive data.
- **Use categories consistently**: Establish a convention for category names (e.g., `navigation`, `user.action`, `network`, `auth`) so you can filter them easily.
- **Set appropriate levels**: Use `.info` for normal events, `.warning` for concerning states, and `.error` for handled failures.
- **Avoid sensitive data**: Never include passwords, tokens, full credit card numbers, or personally identifiable information in breadcrumbs.
- **Be mindful of volume**: Most SDKs keep only the last 100 or so breadcrumbs. If you add too many low-value breadcrumbs, important ones may be pushed out of the buffer before a crash occurs.
- **Include relevant context**: Add data that helps differentiate scenarios, such as item counts, identifiers (non-sensitive), or configuration flags.

## What Not to Add as Breadcrumbs

- High-frequency events (e.g., scroll position updates, every frame render)
- Sensitive user data (passwords, tokens, PII)
- Redundant information already captured automatically by the SDK
- Verbose debug logs that belong in a proper logging system instead

## Summary

Manual breadcrumbs are most valuable when they fill the gaps between automatically captured events and the actual crash. They answer the question: "What was the user doing and what state was the app in right before things went wrong?" Focus on recording decision points, state transitions, and operations around areas of your code that are complex or historically problematic.
