# Enterprise VIPER Patterns

## How to Use This Reference

Read this for production patterns: error propagation, ViewState management, analytics integration, thread safety, and code generation for large teams.

---

## Error Propagation Chain

Errors transform at each VIPER boundary:

```text
Service layer    → catches URLError, HTTP status → wraps into ServiceError
Interactor       → catches ServiceError → transforms into BusinessError (.unauthorized, .notFound)
                   Applies retry logic HERE (not in Presenter or View)
Presenter        → receives BusinessError → transforms into ViewError (user-facing title + message)
                   Never leaks technical details to View
View             → displays whatever Presenter gives it → zero error interpretation
```

### Typed Errors at Every Boundary

```swift
// ❌ WRONG — generic Error, Presenter must guess
protocol InteractorOutput: AnyObject {
    func fetchFailed(error: Error)
}

// ✅ RIGHT — typed, exhaustive switch
enum FetchError: Error {
    case network(NetworkError)
    case business(BusinessError)
    case validation(ValidationError)
}

protocol InteractorOutput: AnyObject {
    func fetchFailed(_ error: FetchError)
}
```

### Retry Logic in Interactor

```swift
class OrderInteractor {
    private let maxRetries = 3

    func fetchOrders(attempt: Int = 0) {
        service.getOrders { [weak self] result in
            switch result {
            case .success(let orders):
                DispatchQueue.main.async { self?.output?.didFetchOrders(orders) }
            case .failure(let error) where error.isRetryable && attempt < (self?.maxRetries ?? 0):
                DispatchQueue.main.asyncAfter(deadline: .now() + pow(2, Double(attempt))) {
                    self?.fetchOrders(attempt: attempt + 1)
                }
            case .failure(let error):
                DispatchQueue.main.async { self?.output?.didFailFetchingOrders(.network(error)) }
            }
        }
    }
}
```

## ViewState Management

### Pull-to-Refresh Flow

```swift
// Presenter
func didPullToRefresh() {
    // Do NOT set .loading — keep showing old data
    interactor.fetchOrders()
}

func didFetchOrders(_ orders: [Order]) {
    let vms = orders.map(mapToViewModel)
    view?.render(state: vms.isEmpty ? .empty : .loaded(vms))
    view?.endRefreshing()  // always end refreshing
}

func didFailFetchingOrders(_ error: OrderError) {
    // On refresh failure: show toast, keep old data
    view?.showToast(message: "Refresh failed. Showing cached data.")
    view?.endRefreshing()
}
```

### Composite ViewState for Complex Screens

When a screen has multiple independent data sources:

```swift
struct DashboardViewState: Equatable {
    var profileState: ViewState<ProfileViewModel>
    var ordersState: ViewState<[OrderViewModel]>
    var recommendationsState: ViewState<[RecommendationViewModel]>
}
```

### Rich ViewState (overlapping states)

When you need stale data + refresh error simultaneously:

```swift
struct RichViewState<T: Equatable>: Equatable {
    var data: T?
    var isLoading: Bool
    var error: ViewError?
    var isRefreshing: Bool
}
```

## Analytics Integration

Fire analytics at the right layer:

| Event Type | Layer | Example |
|---|---|---|
| User action (tap, scroll) | View → Presenter fires | `button_tapped` |
| Business event | Presenter (after Interactor confirms) | `order_placed` |
| Technical event | Service/Interactor | `api_latency` |

### Decorator Pattern (avoids SRP violation)

```swift
// At composition root (Builder), wrap Presenter with analytics:
func buildOrderModule() -> UIViewController {
    let presenter = OrderPresenter()
    let analyticsPresenter = AnalyticsOrderPresenterDecorator(
        decoratee: presenter,
        analytics: analyticsService
    )
    let view = OrderViewController(presenter: analyticsPresenter)
    // ...
    return view
}

class AnalyticsOrderPresenterDecorator: OrderListPresenterInput {
    private let decoratee: OrderListPresenterInput
    private let analytics: AnalyticsServiceProtocol

    func didSelectOrder(at index: Int) {
        analytics.track("order_selected", properties: ["index": index])
        decoratee.didSelectOrder(at: index)
    }
}
```

## Accessibility

Accessibility configuration belongs in View layer. Presenter provides semantic data:

```swift
struct OrderCellViewModel: Equatable {
    let title: String
    let price: String
    let accessibilityDescription: String  // "Order: Coffee Latte, Price: $4.50"
}
```

Centralize identifiers:

```swift
enum AccessibilityID {
    enum OrderList {
        static let tableView = "orderList.tableView"
        static let addButton = "orderList.addButton"
    }
}
```

## Boilerplate Management

Minimum 5 files per module. With contracts + tests: 10-15 files. For a 100-screen app: 500-1500 files.

### Code Generation Options

1. **Xcode File Templates** — Custom templates that generate all module files at once
2. **Generamba** — Ruby-based code generator popular in VIPER projects
3. **Sourcery** — Swift meta-programming, generates from annotations
4. **Custom scripts** — Shell/Python scripts that scaffold module structure

### Xcode Template Example

Create at `~/Library/Developer/Xcode/Templates/VIPER Module.xctemplate/`:
- `___FILEBASENAME___Contract.swift`
- `___FILEBASENAME___View.swift`
- `___FILEBASENAME___Presenter.swift`
- `___FILEBASENAME___Interactor.swift`
- `___FILEBASENAME___Router.swift`
- `___FILEBASENAME___Module.swift`

## Performance Considerations

- Use `final class` on all VIPER components — enables compiler optimizations
- Minimize protocol inheritance chains — deep hierarchies slow compilation
- Consider SPM modules for incremental compilation in large projects
- Module assembly is cheap (object allocation only) — don't over-optimize Builders
