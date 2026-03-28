# Testing VIPER Modules

## How to Use This Reference

Read this when writing tests for VIPER modules. Covers testing priority, mock patterns, and layer-specific strategies.

---

## Testing Priority Order

1. **Interactor (HIGHEST)** — Pure business logic, no UI dependencies, easiest to test. Start TDD here.
2. **Presenter** — Verify correct View methods called with correct ViewModels, correct Router methods called.
3. **Router** — Verify correct VCs instantiated/pushed/presented.
4. **View (LOWEST)** — Use snapshot tests, not unit tests. View only renders what Presenter gives it.
5. **Entity** — Test only if it has computed properties or Codable conformance.

## Mock/Spy/Stub Patterns

| Pattern | Purpose | VIPER Usage |
|---------|---------|-------------|
| **Stub** | Returns canned data | MockService returning fixed Result |
| **Spy** | Records calls + args | MockView tracking `showErrorCalled` |
| **Mock** | Spy + verification | Assert specific call counts |
| **Fake** | Working alternative | In-memory store replacing CoreData |

### Standard Mock Template

```swift
class MockOrderListView: OrderListViewInput {
    var renderCallCount = 0
    var lastRenderedState: ViewState<[OrderCellViewModel]>?
    var endRefreshingCalled = false

    func render(state: ViewState<[OrderCellViewModel]>) {
        renderCallCount += 1
        lastRenderedState = state
    }

    func endRefreshing() {
        endRefreshingCalled = true
    }
}
```

## Interactor Tests

```swift
class OrderListInteractorTests: XCTestCase {
    var sut: OrderListInteractor!
    var mockService: MockOrderService!
    var mockOutput: MockInteractorOutput!

    override func setUp() {
        super.setUp()
        mockService = MockOrderService()
        mockOutput = MockInteractorOutput()
        sut = OrderListInteractor(orderService: mockService)
        sut.output = mockOutput
    }

    override func tearDown() {
        sut = nil
        mockService = nil
        mockOutput = nil
        super.tearDown()
    }

    func test_fetchOrders_callsService() {
        sut.fetchOrders()
        XCTAssertTrue(mockService.getOrdersCalled)
    }

    func test_fetchOrders_success_filtersAndSortsBeforeOutput() {
        mockService.stubbedResult = .success([
            Order.stub(status: .active, createdAt: .distantPast),
            Order.stub(status: .cancelled),  // should be filtered
            Order.stub(status: .active, createdAt: .now)
        ])

        let exp = expectation(description: "output called")
        mockOutput.onDidFetchOrders = { orders in
            XCTAssertEqual(orders.count, 2, "Cancelled orders should be filtered")
            XCTAssertTrue(orders[0].createdAt > orders[1].createdAt, "Should be sorted newest first")
            exp.fulfill()
        }

        sut.fetchOrders()
        wait(for: [exp], timeout: 1)
    }
}
```

## Presenter Tests

```swift
class OrderListPresenterTests: XCTestCase {
    var sut: OrderListPresenter!
    var mockView: MockOrderListView!
    var mockInteractor: MockOrderListInteractor!
    var mockRouter: MockOrderListRouter!

    override func setUp() {
        super.setUp()
        mockView = MockOrderListView()
        mockInteractor = MockOrderListInteractor()
        mockRouter = MockOrderListRouter()
        sut = OrderListPresenter()
        sut.view = mockView
        sut.interactor = mockInteractor
        sut.router = mockRouter
    }

    func test_viewDidLoad_showsLoadingAndFetches() {
        sut.viewDidLoad()
        XCTAssertEqual(mockView.lastRenderedState, .loading)
        XCTAssertTrue(mockInteractor.fetchOrdersCalled)
    }

    func test_didFetchOrders_empty_showsEmptyState() {
        sut.didFetchOrders([])
        XCTAssertEqual(mockView.lastRenderedState, .empty)
    }

    func test_didFetchOrders_mapsToViewModels() {
        let orders = [Order.stub(productName: "Coffee", total: 4.50)]
        sut.didFetchOrders(orders)

        if case .loaded(let vms) = mockView.lastRenderedState {
            XCTAssertEqual(vms.first?.title, "Coffee")
        } else {
            XCTFail("Expected .loaded state")
        }
    }

    func test_didSelectOrder_navigatesToDetail() {
        // First load some data
        sut.didFetchOrders([Order.stub(id: "123")])
        sut.didSelectOrder(at: 0)
        XCTAssertEqual(mockRouter.lastNavigatedOrderId, "123")
    }
}
```

## Router Tests

Router tests need a strong VC reference (Router holds weak ref):

```swift
class MockNavigationController: UINavigationController {
    var pushedViewController: UIViewController?
    override func pushViewController(_ vc: UIViewController, animated: Bool) {
        pushedViewController = vc
        super.pushViewController(vc, animated: false)
    }
}

class OrderListRouterTests: XCTestCase {
    func test_navigateToDetail_pushesDetailVC() {
        let sut = OrderListRouter()
        let mockNav = MockNavigationController(rootViewController: UIViewController())
        // Keep strong reference — Router only has weak ref
        let hostVC = mockNav.viewControllers.first!
        sut.viewController = hostVC

        sut.navigateToOrderDetail(orderId: "123")

        XCTAssertTrue(mockNav.pushedViewController is OrderDetailViewController)
    }
}
```

## Module Assembly Tests

```swift
func test_moduleAssembly_wiresAllComponents() {
    let vc = OrderListModule.build() as! OrderListViewController

    XCTAssertNotNil(vc.presenter)

    let presenter = vc.presenter as! OrderListPresenter
    XCTAssertNotNil(presenter.view)
    XCTAssertNotNil(presenter.interactor)
    XCTAssertNotNil(presenter.router)

    let interactor = presenter.interactor as! OrderListInteractor
    XCTAssertNotNil(interactor.output)

    let router = presenter.router as! OrderListRouter
    XCTAssertNotNil(router.viewController)
}
```

## Memory Leak Tests

```swift
func test_module_doesNotLeakMemory() {
    var vc: UIViewController? = OrderListModule.build()
    weak var weakVC = vc

    vc = nil

    XCTAssertNil(weakVC, "Module leaked — check weak references")
}

// More detailed version:
func test_module_allComponentsDeallocate() {
    var vc: OrderListViewController? = OrderListModule.build() as? OrderListViewController

    weak var weakPresenter = vc?.presenter as? OrderListPresenter
    weak var weakInteractor = (vc?.presenter as? OrderListPresenter)?.interactor as? OrderListInteractor

    addTeardownBlock { [weak vc] in
        XCTAssertNil(vc, "ViewController leaked")
    }

    vc = nil

    XCTAssertNil(weakPresenter, "Presenter leaked")
    XCTAssertNil(weakInteractor, "Interactor leaked")
}
```

## Snapshot Testing (View)

Using Point-Free's swift-snapshot-testing:

```swift
import SnapshotTesting

class OrderListSnapshotTests: XCTestCase {
    func test_loadedState() {
        let vc = OrderListViewController()
        let stubPresenter = StubOrderListPresenter()
        vc.presenter = stubPresenter
        vc.loadViewIfNeeded()

        // Inject ViewModels directly through the View protocol
        vc.render(state: .loaded([
            OrderCellViewModel(id: "1", title: "Coffee", subtitle: "2 hours ago", priceText: "$4.50")
        ]))

        assertSnapshot(of: vc, as: .image(on: .iPhone13))
    }

    func test_emptyState() {
        let vc = OrderListViewController()
        let stubPresenter = StubOrderListPresenter()
        vc.presenter = stubPresenter
        vc.loadViewIfNeeded()
        vc.render(state: .empty)

        assertSnapshot(of: vc, as: .image(on: .iPhone13))
    }
}
```
