# Audit: OrderViewModel Silent Failure Patterns

## Summary of Issues Found

This ViewModel contains **6 distinct silent failure patterns** across its 3 methods. Every error path either discards diagnostic information entirely or logs only to stdout where it is invisible in production. None of the errors reach a crash reporting SDK.

---

## Issue-by-Issue Breakdown

### 1. `loadOrders()` -- `try?` erases all diagnostics

```swift
let result = try? await OrderService.shared.fetchOrders()
```

`try?` converts any thrown error to `nil`, destroying the error type, message, and stack context. Was it a 401 unauthorized? A timeout? A DNS failure? A decoding error from a changed API contract? All information is lost. The user sees an empty order list with no indication that something went wrong.

**Severity:** High. This is a primary user-facing data load. Failure silently presents an empty state that looks like "no orders" rather than "something broke."

### 2. `loadOrders()` -- `result ?? []` hides the failure from the UI

```swift
self.orders = result ?? []
```

There is no `@Published var error` property. The view has no way to distinguish "user has zero orders" from "the network request failed." The user is stuck on what appears to be an empty state with no recourse.

### 3. `placeOrder(_:)` -- `try?` on a critical business operation

```swift
try? await OrderService.shared.submitOrder(order)
try? await OrderService.shared.sendConfirmationEmail(order)
```

Both operations use `try?`. If `submitOrder` fails, the code proceeds to `sendConfirmationEmail` as though the order succeeded. If `sendConfirmationEmail` fails, the user never knows. These are not best-effort operations -- placing an order is a critical business transaction, and the confirmation email is an expected user-facing side effect.

**Severity:** Critical. A failed order submission is silently ignored, and the print statement still executes, lying about success.

### 4. `placeOrder(_:)` -- `print()` is not error handling

```swift
print("Order placed successfully")
```

`print()` writes to stdout. In production (no debugger attached), this is invisible. It is not part of the unified logging system, has no log levels, no privacy controls, no filtering, and no persistence. Worse, it prints "successfully" unconditionally -- even when both operations above failed silently via `try?`.

### 5. `deleteOrder(_:)` -- `Task.detached` with unhandled throw

```swift
Task.detached {
    try await OrderService.shared.deleteOrder(id)
}
```

`Task.init` (and `Task.detached`) is `@discardableResult`. If `deleteOrder` throws, the error is silently discarded. No crash, no log, nothing. The user taps delete, the UI may optimistically remove the row, but the server-side deletion failed and nobody knows.

Additionally, `Task.detached` strips priority inheritance, task-local values, and cancellation propagation. There is no reason to use `.detached` here -- a regular `Task {}` is almost always correct.

**Severity:** High. A failed deletion is invisible, leading to data inconsistency between client and server.

### 6. No `@Published var error` -- the view cannot display failures

The ViewModel exposes `orders` and `isLoading` but has no error state. The view layer has no mechanism to show an error banner, retry button, or alert. This means even if errors were caught properly, they would have nowhere to surface in the UI.

---

## Fixed ViewModel

```swift
import os

// MARK: - Logger Extension (add to your project once)

extension Logger {
    private static let subsystem = Bundle.main.bundleIdentifier!

    static let orders = Logger(subsystem: subsystem, category: "Orders")
}

// MARK: - Fixed ViewModel

@MainActor
class OrderViewModel: ObservableObject {
    @Published var orders: [Order] = []
    @Published var isLoading = false
    @Published var error: Error?

    func loadOrders() {
        isLoading = true
        error = nil

        Task {
            do {
                let fetched = try await OrderService.shared.fetchOrders()
                self.orders = fetched
            } catch is CancellationError {
                // Task was cancelled (e.g., view disappeared) -- not a failure
            } catch {
                Logger.orders.error(
                    "Failed to load orders: \(error.localizedDescription, privacy: .public)"
                )
                ErrorReporter.shared.recordNonFatal(error, context: [
                    "operation": "loadOrders"
                ])
                self.error = error
            }
            self.isLoading = false
        }
    }

    func placeOrder(_ order: Order) {
        Task {
            do {
                try await OrderService.shared.submitOrder(order)
                Logger.orders.notice(
                    "Order submitted: \(order.id, privacy: .public)"
                )
            } catch {
                Logger.orders.error(
                    "Order submission failed: \(error.localizedDescription, privacy: .public)"
                )
                ErrorReporter.shared.recordNonFatal(error, context: [
                    "operation": "submitOrder",
                    "orderId": order.id
                ])
                self.error = error
                return // Do not send confirmation if submission failed
            }

            do {
                try await OrderService.shared.sendConfirmationEmail(order)
            } catch {
                // Email failure is non-fatal -- the order succeeded.
                // Log and report, but do not surface to the user as a hard error.
                Logger.orders.warning(
                    "Confirmation email failed for order \(order.id, privacy: .public): \(error.localizedDescription, privacy: .public)"
                )
                ErrorReporter.shared.recordNonFatal(error, context: [
                    "operation": "sendConfirmationEmail",
                    "orderId": order.id
                ])
            }
        }
    }

    func deleteOrder(_ id: String) {
        Task {
            do {
                try await OrderService.shared.deleteOrder(id)
                Logger.orders.notice("Order deleted: \(id, privacy: .public)")
            } catch is CancellationError {
                // Cancelled -- not a failure
            } catch {
                Logger.orders.error(
                    "Delete failed for order \(id, privacy: .public): \(error.localizedDescription, privacy: .public)"
                )
                ErrorReporter.shared.recordNonFatal(error, context: [
                    "operation": "deleteOrder",
                    "orderId": id
                ])
                self.error = error
            }
        }
    }
}
```

---

## What Changed and Why

| # | Change | Rationale |
|---|--------|-----------|
| 1 | `try?` replaced with `do/catch` in `loadOrders` | Network fetches are not best-effort. Failure reason (401, timeout, decoding) must be captured for debugging. |
| 2 | Added `@Published var error` property | The view layer needs an error state to show alerts, retry buttons, or error banners. Without it, failures are invisible to the user. |
| 3 | `try?` replaced with `do/catch` in `placeOrder` | Order submission is a critical business operation. `try?` here means a failed payment or failed order creation is silently ignored. |
| 4 | Separated `submitOrder` and `sendConfirmationEmail` into distinct `do/catch` blocks | These have different severity. A failed submission should halt everything and surface an error. A failed email is a non-fatal degradation -- log it and report it, but the order itself succeeded. |
| 5 | `print()` removed entirely | `print()` is invisible in production, has no log levels or privacy annotations, and was printing a lie ("successfully") even on failure. Replaced with `Logger.orders.notice()` for success and `.error()` / `.warning()` for failures. |
| 6 | `Task.detached` replaced with `Task` | `Task.detached` strips actor context, priority inheritance, and task-local values. There is no reason to use it here. A regular `Task {}` inherits the `@MainActor` context, which is needed since we update `@Published` properties. |
| 7 | `do/catch` added inside `deleteOrder` Task | `Task {}` is `@discardableResult` -- if the body throws, the error is silently discarded. Wrapping in `do/catch` with `Logger` + `ErrorReporter` makes the failure observable. |
| 8 | `CancellationError` handled separately | In `loadOrders` and `deleteOrder`, cancellation is normal lifecycle behavior (view disappeared, user navigated away). Reporting it as an error would create noise in crash reporting dashboards. |
| 9 | `Logger` with privacy annotations on all dynamic values | `os.Logger` is the production logging system. Privacy annotations (`.public` on order IDs and error descriptions) ensure logs are readable in production without exposing PII. |
| 10 | `ErrorReporter.shared.recordNonFatal()` in every catch block | Local logging is necessary but not sufficient. `ErrorReporter` sends errors to a remote crash SDK (Sentry, Crashlytics, etc.) so failures are visible in dashboards, alertable, and searchable across all users. |
| 11 | `@MainActor` added to the class | The ViewModel updates `@Published` properties from `Task` bodies. Marking the class `@MainActor` ensures all property updates happen on the main thread without needing `await MainActor.run` wrappers. |
| 12 | `error = nil` at start of `loadOrders` | Clears any previous error state before a new load attempt, so the view can distinguish between a stale error and a fresh one. |

---

## Checklist for the View Layer

The fixed ViewModel now publishes an `error` property. The view should:

- Display an error alert or inline error banner when `error` is non-nil
- Provide a retry action that calls `loadOrders()` again
- Optionally use the centralized `ErrorHandler` pattern (inject via `@EnvironmentObject`) for consistent error presentation across the app

```swift
// Example view integration
struct OrdersView: View {
    @StateObject private var viewModel = OrderViewModel()

    var body: some View {
        List(viewModel.orders) { order in
            OrderRow(order: order)
        }
        .overlay {
            if viewModel.isLoading {
                ProgressView()
            }
        }
        .alert(
            "Error",
            isPresented: .init(
                get: { viewModel.error != nil },
                set: { if !$0 { viewModel.error = nil } }
            )
        ) {
            Button("Retry") { viewModel.loadOrders() }
            Button("OK", role: .cancel) {}
        } message: {
            Text(viewModel.error?.localizedDescription ?? "")
        }
        .task {
            viewModel.loadOrders()
        }
    }
}
```
