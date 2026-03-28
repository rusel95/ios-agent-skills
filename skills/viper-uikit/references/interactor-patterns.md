# Interactor Patterns — Single Use Case

## How to Use This Reference

Read this when creating or reviewing Interactor code. Covers the single-use-case principle, service injection, Entity boundaries, and async/Combine patterns.

---

## Core Responsibility

Interactor represents a SINGLE USE CASE — not "all business logic for this screen." It:
- Fetches, filters, sorts, validates, combines data
- Orchestrates calls to Services/DataManagers
- Applies business rules
- Maps DTOs to Entities
- Is **independent of any UI** — "the same Interactor could be used in an iOS app or an OS X app"

## Single Use Case Principle

```swift
// ❌ BAD — God Interactor doing everything for the screen
class OrderScreenInteractor {
    func fetchOrders() { ... }
    func deleteOrder() { ... }
    func calculateTax() { ... }
    func validateCoupon() { ... }
    func submitPayment() { ... }
}

// ✅ GOOD — Focused use cases
class FetchOrdersInteractor { ... }
class DeleteOrderInteractor { ... }
class SubmitPaymentInteractor { ... }
```

In practice, most teams group related use cases in one Interactor per module but keep methods focused. The key test: if a method doesn't relate to the module's primary use case, it belongs elsewhere.

## Service Injection

Network/database managers are NOT part of VIPER — they are external dependencies injected into Interactors:

```swift
class OrderListInteractor: OrderListInteractorInput {
    private let orderService: OrderServiceProtocol
    private let cacheManager: CacheManagerProtocol
    weak var output: OrderListInteractorOutput?

    init(orderService: OrderServiceProtocol, cacheManager: CacheManagerProtocol) {
        self.orderService = orderService
        self.cacheManager = cacheManager
    }

    func fetchOrders() {
        orderService.getOrders { [weak self] result in
            guard let self = self else { return }
            switch result {
            case .success(let dtos):
                let entities = dtos.map(Order.init(dto:))  // DTO → Entity
                let filtered = entities.filter { $0.status != .cancelled }
                let sorted = filtered.sorted { $0.createdAt > $1.createdAt }
                DispatchQueue.main.async {
                    self.output?.didFetchOrders(sorted)
                }
            case .failure(let error):
                DispatchQueue.main.async {
                    self.output?.didFailFetchingOrders(.network(error))
                }
            }
        }
    }
}
```

## Entity Boundaries

**Interactor NEVER passes raw Entities to Presenter.** Map to plain response structs:

```swift
// Entity (domain model, may have computed properties)
struct Order {
    let id: String
    let productName: String
    let total: Decimal
    let createdAt: Date
    let status: OrderStatus

    var isOverdue: Bool { status == .pending && createdAt < Date().addingTimeInterval(-86400 * 7) }
}

// DTO (from network layer)
struct OrderDTO: Codable {
    let orderId: String
    let product: String
    let amount: Double
    let timestamp: String
    let state: String
}

// Interactor maps DTO → Entity using business rules
extension Order {
    init(dto: OrderDTO) {
        self.id = dto.orderId
        self.productName = dto.product
        self.total = Decimal(dto.amount)
        self.createdAt = ISO8601DateFormatter().date(from: dto.timestamp) ?? Date()
        self.status = OrderStatus(rawValue: dto.state) ?? .unknown
    }
}
```

## Data Manager Pattern

For persistence-specific operations (Core Data, Realm), use a Data Manager between Interactor and the store:

```swift
protocol OrderDataManagerProtocol {
    func fetchCachedOrders() -> [Order]
    func save(orders: [Order])
    func deleteOrder(id: String)
}

// Interactor doesn't know about NSManagedObjectContext, Realm, etc.
class OrderListInteractor {
    private let apiService: OrderAPIServiceProtocol
    private let dataManager: OrderDataManagerProtocol

    func fetchOrders() {
        // Show cached first, then refresh
        let cached = dataManager.fetchCachedOrders()
        if !cached.isEmpty {
            output?.didFetchOrders(cached)
        }
        apiService.getOrders { [weak self] result in
            // update cache, notify output
        }
    }
}
```

## Async/Await Interactor

With async/await, the Output protocol becomes optional — Presenter calls directly:

```swift
protocol OrderListInteractorInput {
    func fetchOrders() async throws -> [Order]
    func deleteOrder(id: String) async throws
}

class OrderListInteractor: OrderListInteractorInput {
    private let orderService: OrderServiceProtocol

    init(orderService: OrderServiceProtocol) {
        self.orderService = orderService
    }

    func fetchOrders() async throws -> [Order] {
        let dtos = try await orderService.getOrders()
        return dtos
            .map(Order.init(dto:))
            .filter { $0.status != .cancelled }
            .sorted { $0.createdAt > $1.createdAt }
    }
}
```

## Combine Interactor

```swift
class OrderListInteractor: OrderListInteractorInput {
    private let orderService: OrderServiceProtocol
    weak var output: OrderListInteractorOutput?
    private var cancellables = Set<AnyCancellable>()

    func fetchOrders() {
        orderService.getOrdersPublisher()
            .map { dtos in dtos.map(Order.init(dto:)) }
            .map { $0.filter { $0.status != .cancelled } }
            .receive(on: DispatchQueue.main)
            .sink(
                receiveCompletion: { [weak self] completion in
                    if case .failure(let error) = completion {
                        self?.output?.didFailFetchingOrders(.network(error))
                    }
                },
                receiveValue: { [weak self] orders in
                    self?.output?.didFetchOrders(orders)
                }
            )
            .store(in: &cancellables)
    }
}
```

## Thread Safety in Interactors

If Interactor holds mutable cached state, protect access:

```swift
// Option 1: Serial queue
class DashboardInteractor {
    private let queue = DispatchQueue(label: "com.app.dashboard.interactor")
    private var _cachedOrders: [Order] = []

    func fetchOrders() {
        service.fetch { [weak self] orders in
            self?.queue.async {
                self?._cachedOrders = orders
                DispatchQueue.main.async { self?.output?.didFetch(orders) }
            }
        }
    }
}

// Option 2: Actor (Swift 5.5+)
actor DashboardInteractor {
    private var cachedOrders: [Order] = []

    func fetchOrders() async throws -> [Order] {
        let orders = try await service.fetchOrders()
        cachedOrders = orders
        return orders
    }
}
```

## Cancellation

Cancel in-flight operations when the module is dismissed:

```swift
class OrderInteractor {
    private var currentTask: Task<Void, Never>?

    func fetchOrders() {
        currentTask?.cancel()
        currentTask = Task { [weak self] in
            do {
                try Task.checkCancellation()
                let orders = try await service.fetchOrders()
                try Task.checkCancellation()
                await MainActor.run { self?.output?.didFetch(orders) }
            } catch is CancellationError {
                // Silently ignore — module is being dismissed
            } catch {
                await MainActor.run { self?.output?.didFail(error) }
            }
        }
    }

    deinit { currentTask?.cancel() }
}
```
