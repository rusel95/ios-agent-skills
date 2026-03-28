# Module Assembly — Builder/Factory Patterns

## How to Use This Reference

Read this when creating module factories, wiring VIPER components, or setting up dependency injection.

---

## Recommended: Enum-Based Builder

Enums can't be instantiated — they serve as a clean namespace for the factory method:

```swift
enum OrderListModule {
    static func build(output: OrderListModuleOutput? = nil) -> UIViewController {
        let view = OrderListViewController()
        let interactor = OrderListInteractor(
            orderService: ServiceFactory.makeOrderService()
        )
        let presenter = OrderListPresenter()
        let router = OrderListRouter()

        // Wire references
        view.presenter = presenter
        presenter.view = view           // weak
        presenter.interactor = interactor
        presenter.router = router
        interactor.output = presenter   // weak
        router.viewController = view    // weak
        presenter.moduleOutput = output // weak (optional)

        return view
    }
}

// Usage:
let orderListVC = OrderListModule.build()
navigationController.pushViewController(orderListVC, animated: true)
```

## Alternative: Class-Based Builder

When you need instance state (e.g., caching built modules):

```swift
class OrderListModuleBuilder {
    private let serviceFactory: ServiceFactoryProtocol

    init(serviceFactory: ServiceFactoryProtocol) {
        self.serviceFactory = serviceFactory
    }

    func build(output: OrderListModuleOutput? = nil) -> UIViewController {
        let view = OrderListViewController()
        let interactor = OrderListInteractor(
            orderService: serviceFactory.makeOrderService()
        )
        // ... same wiring
        return view
    }
}
```

## Alternative: Static Factory on Router

Some teams prefer the Router to own the factory:

```swift
class OrderListRouter: OrderListRouterInput {
    weak var viewController: UIViewController?

    static func createModule() -> UIViewController {
        let view = OrderListViewController()
        let presenter = OrderListPresenter()
        let router = OrderListRouter()
        let interactor = OrderListInteractor(orderService: OrderService())

        view.presenter = presenter
        presenter.view = view
        presenter.router = router
        presenter.interactor = interactor
        interactor.output = presenter
        router.viewController = view

        return view
    }
}
```

**Downside:** Violates SRP — Router does navigation AND assembly. Recommended only for small projects.

## Wiring Order

The assembly must happen in a specific order to prevent nil references:

1. Create all components (view, presenter, interactor, router)
2. Wire strong references first (view→presenter, presenter→interactor, presenter→router)
3. Wire weak references (presenter→view, interactor→output, router→viewController)
4. Set external inputs (module output delegate, initial data)
5. Return the view controller

**Critical:** All wiring must complete BEFORE the VC enters the view lifecycle. If `viewDidLoad` fires with a nil Presenter, user actions crash.

## Dependency Injection Patterns

### Constructor Injection (Preferred)

```swift
class OrderInteractor: OrderInteractorInput {
    private let orderService: OrderServiceProtocol
    private let analyticsService: AnalyticsServiceProtocol

    init(orderService: OrderServiceProtocol, analyticsService: AnalyticsServiceProtocol) {
        self.orderService = orderService
        self.analyticsService = analyticsService
    }
}
```

### Service Factory

Centralize service creation for consistent injection:

```swift
enum ServiceFactory {
    static func makeOrderService() -> OrderServiceProtocol {
        OrderService(networkClient: makeNetworkClient(), decoder: JSONDecoder())
    }

    static func makeNetworkClient() -> NetworkClientProtocol {
        URLSessionNetworkClient(session: .shared)
    }
}
```

### DI Container (Large Apps)

For 20+ modules, consider a lightweight container:

```swift
protocol DependencyContainer {
    func resolve<T>(_ type: T.Type) -> T
}

class AppContainer: DependencyContainer {
    private var factories: [String: () -> Any] = [:]

    func register<T>(_ type: T.Type, factory: @escaping () -> T) {
        factories[String(describing: type)] = factory
    }

    func resolve<T>(_ type: T.Type) -> T {
        guard let factory = factories[String(describing: type)] else {
            fatalError("No registration for \(type)")
        }
        return factory() as! T
    }
}
```

## Storyboard vs Programmatic

**Programmatic (recommended for VIPER):** Full constructor injection. Builder creates VC directly.

**Storyboard:** Must use property injection after instantiation:

```swift
static func build() -> UIViewController {
    let storyboard = UIStoryboard(name: "OrderList", bundle: nil)
    let vc = storyboard.instantiateViewController(withIdentifier: "OrderListVC") as! OrderListViewController
    // Property injection (can't use init with storyboard)
    vc.presenter = presenter
    // ...
    return vc
}
```

Storyboard VCs should guard against missing Presenter:

```swift
override func viewDidLoad() {
    super.viewDidLoad()
    assert(presenter != nil, "Presenter not set — module not assembled correctly")
    presenter.viewDidLoad()
}
```
