# Audit: OrderViewModel Silent Failure Patterns

## Issues Found

### 1. `loadOrders()` -- `try?` swallows all errors silently

```swift
let result = try? await OrderService.shared.fetchOrders()
```

**Problem:** If the network call fails (no connectivity, server 500, decoding error), the error is discarded. The UI shows an empty list with no indication anything went wrong. The user sees a blank screen and has no way to know whether they have zero orders or the load failed.

**Secondary issue:** `isLoading` is never reset on early exit if the Task is cancelled.

---

### 2. `placeOrder(_:)` -- Two independent `try?` calls create a dangerous partial-success scenario

```swift
try? await OrderService.shared.submitOrder(order)
try? await OrderService.shared.sendConfirmationEmail(order)
print("Order placed successfully")
```

**Problem (critical):**
- If `submitOrder` fails, the code continues to attempt `sendConfirmationEmail` on an order that was never submitted -- potentially sending a confirmation for a non-existent order.
- If `submitOrder` succeeds but `sendConfirmationEmail` fails, there is no record of the email failure. The user never receives confirmation.
- `print("Order placed successfully")` executes regardless of whether either call succeeded, creating misleading console output.
- No UI state is updated -- the caller has no way to know the order was placed (or failed).

---

### 3. `deleteOrder(_:)` -- `Task.detached` with unhandled throw

```swift
Task.detached {
    try await OrderService.shared.deleteOrder(id)
}
```

**Problem:**
- `Task.detached` creates an unstructured task that inherits no actor context. If `deleteOrder` throws, the error vanishes with zero logging or UI feedback.
- The deleted order is never removed from the local `orders` array, so the UI is stale until the next full reload.
- Because it is detached, there is no way for the caller to cancel this operation.

---

### 4. No `@Published var errorMessage` or error state

The ViewModel provides no mechanism for the view layer to display errors. Every failure path results in the UI either showing stale data or an empty state with no explanation.

---

## Fixed ViewModel

```swift
import os.log

private let logger = Logger(subsystem: Bundle.main.bundleIdentifier ?? "com.app", category: "OrderViewModel")

@MainActor
class OrderViewModel: ObservableObject {
    @Published var orders: [Order] = []
    @Published var isLoading = false
    @Published var errorMessage: String?

    // MARK: - Load Orders

    func loadOrders() {
        isLoading = true
        errorMessage = nil

        Task {
            do {
                let fetched = try await OrderService.shared.fetchOrders()
                self.orders = fetched
                logger.info("Loaded \(fetched.count) orders")
            } catch is CancellationError {
                logger.debug("loadOrders cancelled")
            } catch {
                logger.error("Failed to load orders: \(error.localizedDescription)")
                self.errorMessage = "Unable to load orders. Please try again."
            }
            self.isLoading = false
        }
    }

    // MARK: - Place Order

    func placeOrder(_ order: Order) {
        isLoading = true
        errorMessage = nil

        Task {
            // Step 1: Submit the order -- hard stop on failure
            do {
                try await OrderService.shared.submitOrder(order)
                logger.info("Order \(order.id) submitted")
            } catch {
                logger.error("Order submission failed: \(error.localizedDescription)")
                self.errorMessage = "Failed to place order. You have not been charged."
                self.isLoading = false
                return
            }

            // Step 2: Send confirmation -- non-fatal, but logged and surfaced
            do {
                try await OrderService.shared.sendConfirmationEmail(order)
                logger.info("Confirmation email sent for order \(order.id)")
            } catch {
                logger.warning("Confirmation email failed for order \(order.id): \(error.localizedDescription)")
                // Order succeeded, so we don't set a blocking error -- but we inform the user
                self.errorMessage = "Order placed, but confirmation email could not be sent."
            }

            self.isLoading = false
        }
    }

    // MARK: - Delete Order

    func deleteOrder(_ id: String) {
        Task {
            do {
                try await OrderService.shared.deleteOrder(id)
                self.orders.removeAll { $0.id == id }
                logger.info("Deleted order \(id)")
            } catch {
                logger.error("Failed to delete order \(id): \(error.localizedDescription)")
                self.errorMessage = "Could not delete order. Please try again."
            }
        }
    }
}
```

## Summary of Changes

| Original Pattern | Problem | Fix |
|---|---|---|
| `try?` in `loadOrders` | Network/decode errors silently discarded; empty list shown | `do/catch` with error logging and user-facing `errorMessage` |
| `try?` + `try?` in `placeOrder` | Partial success: email sent for unsubmitted order; misleading `print` | Sequential `do/catch` blocks; early return if submission fails; separate handling for email failure |
| `Task.detached` + `try` in `deleteOrder` | Thrown error disappears; local state never updated | Regular `Task` (inherits `@MainActor`); `do/catch` with local array removal on success |
| No error state property | View layer cannot display errors | Added `@Published var errorMessage: String?` |
| `print()` for success logging | Not available in production; no structured output | Replaced with `os.log` `Logger` at appropriate levels (`info`, `warning`, `error`) |
| No `CancellationError` handling | Cancelled tasks logged as errors | Explicit `CancellationError` catch in `loadOrders` |
| Class not `@MainActor` | `@Published` mutations wrapped in `MainActor.run` manually (error-prone) | Entire class annotated `@MainActor`; all `@Published` writes are safe by default |
