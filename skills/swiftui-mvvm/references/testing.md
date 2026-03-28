# Testing @Observable ViewModels

<test_generation_rules>## Test Structure: Arrange → Act → Assert + Memory Leak Check

Every ViewModel test follows this template:

```swift
import Testing
@testable import MyApp

@Suite("ItemListViewModel")
@MainActor
struct ItemListViewModelTests {
    let mockRepository = MockItemRepository()

    @Test("loads items successfully")
    func loadItems_success() async {
        // Arrange → set stubbed data
        // Act → await sut.loadItems()
        // Assert → guard case .loaded(let items) = sut.state
        ...
    }

    @Test("sets failed state on network error")
    func loadItems_failure() async { ... }

    @Test("filters items by search query")
    func filteredItems_matchesQuery() async { ... }
}
```

## Mock Pattern

Every protocol gets a mock with stubbed returns and call tracking:

```swift
@MainActor
final class MockItemRepository: ItemRepositoryProtocol {
    // Stubbed returns
    var stubbedItems: [Item] = []
    var stubbedError: Error?

    // Call tracking
    var fetchItemsCallCount = 0
    var saveItemCallCount = 0
    var lastSavedItem: Item?
    var deleteItemsCallCount = 0
    var lastDeletedItems: [Item] = []

    func fetchItems() async throws -> [Item] { ... }   // Increment count, throw or return stub
    func saveItem(_ item: Item) async throws { ... }
    func deleteItems(_ items: [Item]) async throws { ... }
    func reset() { ... }  // Zero all counters and stubs
}
```

## Observing @Observable Property Changes

Use `withObservationTracking` to verify specific properties change:

```swift
@Test("loading sets isLoading before fetching")
func loadItems_setsLoading() async {
    // Use withObservationTracking to register tracking for 'state'
    // onChange: fulfill expectation
    // Then await action and verify state changed
    ...
}
```

**Reusable helper:**
```swift
extension XCTestCase {
    @MainActor
    func expectChange<T, V>(
        of keyPath: KeyPath<T, V>,
        on object: T,
        timeout: Double = 1.0,
        action: () async -> Void
    ) async { ... }  // withObservationTracking + expectation pattern
}
```

## Async Testing Gotchas

### Use `await fulfillment(of:)`, NEVER `wait(for:)`

```swift
// ❌ DEADLOCK: wait(for:) blocks the thread, Task inside needs the same thread
wait(for: [expectation], timeout: 1.0)

// ✅ SAFE: Suspends cooperatively
await fulfillment(of: [expectation], timeout: 1.0)
```

### @MainActor in tests

Mark test classes `@MainActor` when testing ViewModels that are `@MainActor`:

```swift
// ❌ Compiler error or runtime crash — accessing MainActor-isolated property from nonisolated context
func testLoad() async {
    let vm = ItemListViewModel(repository: mock)
    await vm.loadItems()
    XCTAssertEqual(vm.state.value?.count, 2)  // ⚠️ Isolation violation
}

// ✅ Test inherits MainActor isolation
@MainActor
func testLoad() async {
    let vm = ItemListViewModel(repository: mock)
    await vm.loadItems()
    XCTAssertEqual(vm.state.value?.count, 2)  // Safe
}
```

## Memory Leak Detection

Add this to EVERY ViewModel test — catches retain cycles early:

### XCTest pattern:
```swift
final class ItemListViewModelTests: XCTestCase {
    private var sut: ItemListViewModel!
    private var mockRepository: MockItemRepository!

    override func setUp() { ... }

    override func tearDown() {
        addTeardownBlock { [weak sut = self.sut] in
            XCTAssertNil(sut, "ItemListViewModel has a memory leak — possible retain cycle")
        }
        sut = nil
        mockRepository = nil
        super.tearDown()
    }
}
```

### Reusable helper:
```swift
extension XCTestCase {
    func assertNoMemoryLeak(_ instance: AnyObject, file: StaticString = #file, line: UInt = #line) {
        addTeardownBlock { [weak instance] in
            XCTAssertNil(instance, "Potential memory leak: \(String(describing: instance))", file: file, line: line)
        }
    }
}

// Usage: assertNoMemoryLeak(sut) — in every ViewModel test
```

## Test File Naming and Organization

```
Tests/
├── ViewModelTests/
│   ├── ItemListViewModelTests.swift
│   ├── ItemDetailViewModelTests.swift
│   └── SettingsViewModelTests.swift
├── RepositoryTests/
│   ├── RemoteItemRepositoryTests.swift
│   └── CachedItemRepositoryTests.swift
├── Mocks/
│   ├── MockItemRepository.swift
│   ├── MockHTTPClient.swift
│   └── MockAnalyticsService.swift
└── Helpers/
    ├── Item+Sample.swift
    └── XCTestCase+Extensions.swift
```

**Test data factory:**
```swift
extension Item {
    static func sample(id: String = ..., name: String = ..., price: Double = ...) -> Item { ... }
}
```
</test_generation_rules>
