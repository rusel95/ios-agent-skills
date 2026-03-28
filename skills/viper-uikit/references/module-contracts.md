# Module Contracts — Protocol Design

## How to Use This Reference

Read this when creating a new VIPER module or reviewing protocol design. Defines the 6 protocols per module, naming conventions, and AnyObject constraints.

---

## The 6 Protocols

Every VIPER module defines 6 protocols in a single `{Module}Contract.swift` file:

```swift
// MARK: - OrderListContract.swift

// What View can ask Presenter (user actions, lifecycle)
protocol OrderListPresenterInput: AnyObject {
    func viewDidLoad()
    func didSelectOrder(at index: Int)
    func didTapAddOrder()
    func didPullToRefresh()
}

// What Presenter can tell View (display commands)
protocol OrderListViewInput: AnyObject {
    func render(state: ViewState<[OrderCellViewModel]>)
    func showDeleteConfirmation(for orderName: String)
}

// What Presenter can ask Interactor (business operations)
protocol OrderListInteractorInput: AnyObject {
    func fetchOrders()
    func deleteOrder(id: String)
}

// What Interactor reports to Presenter (results)
protocol OrderListInteractorOutput: AnyObject {
    func didFetchOrders(_ orders: [Order])
    func didFailFetchingOrders(_ error: OrderError)
    func didDeleteOrder(id: String)
}

// What Presenter can ask Router (navigation)
protocol OrderListRouterInput: AnyObject {
    func navigateToOrderDetail(orderId: String)
    func presentAddOrder(delegate: AddOrderModuleOutput?)
}

// What child module reports back (module output)
protocol OrderListModuleOutput: AnyObject {
    func orderListDidSelect(orderId: String)
}
```

## Naming Conventions

| Protocol | Naming Pattern | Constrained? | Why |
|----------|---------------|-------------|-----|
| PresenterInput | `{Module}PresenterInput` | `AnyObject` | View holds strong ref, but AnyObject allows future weak use |
| ViewInput | `{Module}ViewInput` | `AnyObject` **required** | Presenter holds **weak** ref to View |
| InteractorInput | `{Module}InteractorInput` | `AnyObject` | Presenter holds strong ref |
| InteractorOutput | `{Module}InteractorOutput` | `AnyObject` **required** | Interactor holds **weak** ref to Presenter |
| RouterInput | `{Module}RouterInput` | `AnyObject` | Presenter holds strong ref |
| ModuleOutput | `{Module}ModuleOutput` | `AnyObject` **required** | Child module holds **weak** ref to parent |

**Rule:** Any protocol used for a `weak var` reference MUST be `AnyObject`-constrained. Without it, Swift won't allow `weak` — defaulting to strong, causing retain cycles.

## Alternative Naming Styles

Some teams use different naming. Pick one and be consistent across the project:

| Style | View→Presenter | Presenter→View | Presenter→Interactor | Interactor→Presenter |
|-------|---------------|----------------|---------------------|---------------------|
| Input/Output | PresenterInput | ViewInput | InteractorInput | InteractorOutput |
| Protocol suffix | PresenterProtocol | ViewProtocol | InteractorProtocol | InteractorOutputProtocol |
| To-direction | ViewToPresenter | PresenterToView | PresenterToInteractor | InteractorToPresenter |

## Protocol Segregation

When protocols grow beyond 8-10 methods, split by responsibility:

```swift
// Instead of one massive PresenterInput:
protocol DashboardViewEventHandler: AnyObject {
    func viewDidLoad()
    func didPullToRefresh()
}
protocol DashboardItemActions: AnyObject {
    func didSelectItem(at index: Int)
    func didDeleteItem(at index: Int)
}
protocol DashboardSearchHandler: AnyObject {
    func didSearchWith(query: String)
    func didClearSearch()
}

// Presenter conforms to all:
class DashboardPresenter: DashboardViewEventHandler, DashboardItemActions, DashboardSearchHandler { ... }

// Mocks only conform to what they test:
class MockSearchHandler: DashboardSearchHandler { ... }
```

## View Protocol Design

View methods should express content at a **higher abstraction** than UIKit widgets. The Presenter doesn't know about UILabel, UIButton, UITableView.

```swift
// ❌ BAD — leaks UIKit concepts
protocol UserViewInput: AnyObject {
    func setNameLabelText(_ text: String)
    func setAvatarImage(_ image: UIImage)
    func reloadTableView()
}

// ✅ GOOD — content-level abstraction
protocol UserViewInput: AnyObject {
    func render(state: ViewState<UserProfileViewModel>)
    func showNoContentMessage()
    func showDeleteConfirmation(for userName: String)
}
```

## ViewState Enum

Shared across modules — define once in a common location:

```swift
enum ViewState<T: Equatable>: Equatable {
    case idle
    case loading
    case loaded(T)
    case empty
    case error(ViewError)
}

struct ViewError: Equatable {
    let title: String
    let message: String
    let isRetryable: Bool
}
```

For complex screens with multiple independent data sources, use a composite struct:

```swift
struct DashboardViewState: Equatable {
    var profileState: ViewState<ProfileViewModel>
    var ordersState: ViewState<[OrderViewModel]>
    var recommendationsState: ViewState<[RecommendationViewModel]>
}
```
