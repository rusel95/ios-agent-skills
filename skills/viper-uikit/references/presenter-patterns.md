# Presenter Patterns — UIKit-Free Traffic Cop

## How to Use This Reference

Read this when creating or reviewing Presenter code. Covers the no-UIKit rule, ViewState mapping, Entity→ViewModel translation, and navigation signaling.

---

## Core Responsibility

Presenter is the "dumb translator" / "traffic cop":
- Translates raw data from Interactor into view-ready format (ViewModels)
- Decides WHEN to navigate (not HOW — that's Router)
- Decides WHICH ViewState to show (loading, error, content, empty)
- **NEVER** imports UIKit — only Foundation (and Combine if using publishers)

## The No-UIKit Rule

The most cited VIPER rule. Verified by every major VIPER resource. If you find `import UIKit` in a Presenter, it's wrong.

```swift
// ❌ BAD — UIKit in Presenter
import UIKit
class ProfilePresenter {
    func userLoaded(_ user: User) {
        let image = UIImage(named: user.avatarName)  // UIKit!
        let color: UIColor = user.isPremium ? .systemYellow : .label  // UIKit!
        view?.display(name: user.name, avatar: image, tintColor: color)
    }
}

// ✅ GOOD — Semantic data, View decides rendering
import Foundation
class ProfilePresenter {
    func userLoaded(_ user: User) {
        let vm = ProfileViewModel(
            displayName: user.displayName,
            avatarName: user.avatarName,  // String — View resolves to UIImage
            isPremium: user.tier == .premium  // Bool — View maps to color
        )
        view?.display(vm)
    }
}
```

## ViewState Mapping

Presenter owns the decision of which ViewState to emit:

```swift
@MainActor
final class OrderListPresenter: OrderListPresenterInput {
    weak var view: OrderListViewInput?
    var interactor: OrderListInteractorInput!
    var router: OrderListRouterInput!

    func viewDidLoad() {
        view?.render(state: .loading)
        interactor.fetchOrders()
    }

    func didPullToRefresh() {
        // Don't show .loading on refresh — keep showing stale data
        interactor.fetchOrders()
    }
}

extension OrderListPresenter: OrderListInteractorOutput {
    func didFetchOrders(_ orders: [Order]) {
        if orders.isEmpty {
            view?.render(state: .empty)
        } else {
            let viewModels = orders.map { order in
                OrderCellViewModel(
                    id: order.id,
                    title: order.productName,
                    subtitle: dateFormatter.string(from: order.createdAt),
                    priceText: currencyFormatter.string(from: order.total as NSDecimalNumber) ?? ""
                )
            }
            view?.render(state: .loaded(viewModels))
        }
        view?.endRefreshing()
    }

    func didFailFetchingOrders(_ error: OrderError) {
        let viewError = ViewError(
            title: "Unable to Load Orders",
            message: mapErrorMessage(error),
            isRetryable: error.isRetryable
        )
        view?.render(state: .error(viewError))
        view?.endRefreshing()
    }
}
```

## Entity → ViewModel Translation

Presenter transforms domain Entities into display-ready ViewModels. This is where formatting lives:

```swift
// Entity (from Interactor)
struct Order {
    let id: String
    let productName: String
    let total: Decimal
    let createdAt: Date
    let status: OrderStatus
}

// ViewModel (for View)
struct OrderCellViewModel: Equatable {
    let id: String
    let title: String
    let subtitle: String      // formatted date
    let priceText: String     // formatted currency
    let statusText: String    // localized status
    let isHighlighted: Bool   // View decides how to highlight
}

// Presenter does the mapping
private func mapToViewModel(_ order: Order) -> OrderCellViewModel {
    OrderCellViewModel(
        id: order.id,
        title: order.productName,
        subtitle: RelativeDateTimeFormatter().localizedString(for: order.createdAt, relativeTo: Date()),
        priceText: currencyFormatter.string(from: order.total as NSDecimalNumber) ?? "",
        statusText: order.status.localizedDescription,
        isHighlighted: order.status == .pending
    )
}
```

## Navigation Signaling

Presenter knows WHEN to navigate. Router knows HOW:

```swift
// Presenter decides WHEN
func didSelectOrder(at index: Int) {
    guard case .loaded(let viewModels) = currentState else { return }
    let orderId = viewModels[index].id
    router.navigateToOrderDetail(orderId: orderId)
}

func didTapAddOrder() {
    router.presentAddOrder(delegate: self)
}

// Router does the HOW (see router-navigation.md)
```

## Async/Await Presenter Pattern

With async/await, the Interactor Output protocol becomes unnecessary — Presenter calls Interactor directly:

```swift
@MainActor
final class OrderListPresenter: OrderListPresenterInput {
    weak var view: OrderListViewInput?
    private let interactor: OrderListInteractorInput
    var router: OrderListRouterInput!

    init(interactor: OrderListInteractorInput) {
        self.interactor = interactor
    }

    func viewDidLoad() {
        Task {
            view?.render(state: .loading)
            do {
                let orders = try await interactor.fetchOrders()
                let viewModels = orders.map(mapToViewModel)
                view?.render(state: viewModels.isEmpty ? .empty : .loaded(viewModels))
            } catch {
                view?.render(state: .error(mapError(error)))
            }
        }
    }
}
```

## Gotchas

- **Date formatters are expensive.** Create them once as properties, not in mapping functions.
- **Presenter can hold transient state** (e.g., selected item index, current page for pagination) but NOT business state. Business state belongs in Interactor.
- **Multiple Interactors.** Complex screens may have multiple Interactors. Presenter coordinates them. Each Interactor = one use case.
