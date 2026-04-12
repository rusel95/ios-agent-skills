# Async Testing Reference

## How to Use This Reference

Read this when writing tests for `async/await` functions, testing `@MainActor`-isolated code, testing loading/error state transitions deterministically, injecting `Clock` for time-dependent logic, or testing `AsyncStream` producers. See also the epam-swift-concurrency skill for TSan and Instruments guidance.

---

## The Core Problem: Non-Deterministic Async State

The most common async testing mistake is asserting intermediate state (e.g., `isLoading == true`) without controlling when the async work runs:

```swift
// FLAKY -- by the time the assert runs, loadData() may have already finished
@MainActor func testLoadingState() async {
    sut.loadData()
    XCTAssertTrue(sut.isLoading)  // Race condition: may be false already
}
```

**Two solutions:**

1. `withMainSerialExecutor` -- forces all async work to execute serially on main thread
2. `confirmation()` -- Swift Testing's callback-based async (replaces XCTestExpectation)

---

## withMainSerialExecutor -- Deterministic State Transitions

`withMainSerialExecutor` (from Point-Free's `epam-swift-concurrency-extras`) forces the cooperative thread pool to be serial.

```swift
import ConcurrencyExtras

@MainActor func test_loadData_setsLoadingState() async {
    await withMainSerialExecutor {
        let task = Task { await sut.loadData() }
        await Task.yield()
        XCTAssertTrue(sut.isLoading)        // Deterministically true

        mockClient.completeWithSuccess(items: [.sample()])
        await task.value

        XCTAssertFalse(sut.isLoading)
        XCTAssertEqual(sut.items.count, 1)
    }
}
```

**Critical caveat:** The mock's `fetch()` implementation must have at least one `await` point inside it for `Task.yield()` to pause execution there.

```swift
// WRONG -- synchronous mock body, yield doesn't pause here
func fetchItems() async throws -> [Item] {
    return stubbedItems
}

// CORRECT -- add Task.yield() inside the mock
func fetchItems() async throws -> [Item] {
    await Task.yield()
    if let error = stubbedError { throw error }
    return stubbedItems
}
```

---

## confirmation() -- Swift Testing's Async Callback

Swift Testing replaces `XCTestExpectation` with `confirmation()`.

```swift
// Confirm called exactly once (default)
@Test("delegate is notified when item is saved")
func saveDelegateCalled() async throws {
    try await confirmation("save delegate called") { confirm in
        sut.onSaveComplete = { confirm() }
        try await sut.save(.sample())
    }
}

// Confirm called exactly N times
@Test("observer receives 3 updates")
func threeUpdates() async throws {
    try await confirmation("update received", expectedCount: 3) { confirm in
        sut.onUpdate = { confirm() }
        await sut.processEvents([.a, .b, .c])
    }
}

// Assert something NEVER happens (expectedCount: 0)
@Test("logout does not trigger sync")
func logoutNoSync() async {
    await confirmation("sync triggered", expectedCount: 0) { confirm in
        sut.onSync = { confirm() }
        sut.logout()
    }
}
```

### confirmation() does NOT suspend and wait

`confirmation()` does NOT suspend and wait like `XCTestExpectation`. It checks the count when its closure RETURNS. For completion-handler APIs without await, use `withCheckedContinuation`.

```swift
// WRONG -- closure returns immediately; confirm() never called
@Test func completionHandler() async {
    await confirmation("callback") { confirm in
        legacyAPI.fetch { result in confirm() } // called AFTER closure returns
    }
}

// CORRECT -- bridge with continuation
@Test func completionHandler() async throws {
    let data = try await withCheckedThrowingContinuation { cont in
        legacyAPI.fetch { result in cont.resume(with: result) }
    }
    #expect(!data.isEmpty)
}
```

### Ranges (Swift 6.1+)

`confirmation` accepts ranges: `expectedCount: 5...10`.

---

## await fulfillment(of:) vs wait(for:)

**Always use `await fulfillment(of:)` in async contexts** -- `wait(for:)` blocks the thread and deadlocks.

```swift
// DEADLOCK IN ASYNC CONTEXT
func testLoad() async {
    let exp = expectation(description: "loaded")
    Task { @MainActor in exp.fulfill() }
    wait(for: [exp], timeout: 5)       // Blocks main thread

// FIX
    await fulfillment(of: [exp], timeout: 5)  // Suspends cooperatively
}

// wait(for:) is still fine in SYNCHRONOUS XCTestCase methods
func testSyncWithCombine() {
    let exp = expectation(description: "publisher emits")
    publisher.sink { _ in exp.fulfill() }.store(in: &cancellables)
    triggerPublisher()
    wait(for: [exp], timeout: 2.0)   // OK
}
```

---

## Clock Injection for Time-Dependent Code

Never let production code call `Date()`, `Task.sleep`, or `ContinuousClock` directly.

```swift
// Production code -- accepts any Clock
final class SessionManager<C: Clock> where C.Duration == Duration {
    private let clock: C
    init(clock: C, sessionDuration: Duration = .seconds(1800)) {
        self.clock = clock
    }

    func waitForExpiry() async throws {
        try await clock.sleep(for: sessionDuration)
        expireSession()
    }
}

// Test with ImmediateClock -- no wait
@Test func sessionExpires() async throws {
    let sut = SessionManager(clock: ImmediateClock())
    await sut.waitForExpiry()
    #expect(sut.isExpired)
}

// Test with TestClock -- precise time control
@Test func sessionActiveBeforeExpiry() async throws {
    let testClock = TestClock()
    let sut = SessionManager(clock: testClock, sessionDuration: .seconds(60))

    Task { try await sut.waitForExpiry() }
    await testClock.advance(by: .seconds(59))
    #expect(!sut.isExpired)

    await testClock.advance(by: .seconds(1))
    #expect(sut.isExpired)
}
```

| Clock | Source | Behavior | Use |
|-------|--------|---------|-----|
| `ContinuousClock` | Foundation | Real wall-clock time | Production |
| `ImmediateClock` | swift-clocks | Returns instantly | Unit tests where timing doesn't matter |
| `TestClock` | swift-clocks | Manual `.advance(by:)` | Tests needing precise time control |

**ImmediateClock collapses all time to zero -- will NOT work with debounce, throttle, delay. Use TestClock for those.**

---

## Testing @MainActor ViewModels

**Always annotate the test type with `@MainActor`** when the SUT is `@MainActor`-isolated.

```swift
// COMPILE ERROR in Swift 6
struct ViewModelTests {
    @Test func initialState() {
        let vm = ItemListViewModel() // ERROR: Main actor-isolated
    }
}

// CORRECT
@MainActor
struct ViewModelTests {
    @Test func initialState() {
        let vm = ItemListViewModel()
        #expect(vm.items.isEmpty)  // Safe
    }
}
```

---

## Testing AsyncStream Producers

Use `AsyncStream.makeStream(of:)` to get a `(stream, continuation)` pair.

```swift
@Test("processes received locations")
@MainActor func processesLocations() async throws {
    let (stream, continuation) = AsyncStream.makeStream(of: CLLocation.self)
    let sut = LocationTracker(stream: stream)

    let trackingTask = Task { await sut.startTracking() }

    let location = CLLocation(latitude: 51.5, longitude: -0.12)
    continuation.yield(location)

    await Task.yield()
    #expect(sut.lastLocation?.coordinate.latitude == 51.5)

    continuation.finish()
    await trackingTask.value
}
```

Use `prefix(_:)` to prevent tests from hanging on infinite streams.

---

## Test Timeouts

A leaked continuation, a non-terminating `AsyncStream`, or a missed `finish()` call hangs the test suite indefinitely.

```swift
// Swift Testing: built-in time limit
@Test(.timeLimit(.minutes(1)))
func testAsyncOperation() async { ... }

// XCTest: timeout on fulfillment
func test_asyncLoad() async {
    let exp = expectation(description: "load completes")
    Task { await sut.load(); exp.fulfill() }
    await fulfillment(of: [exp], timeout: 10.0)
}

// CI: global timeout
// xcodebuild test -maximum-test-execution-time-allowance 120
```

---

## Testing Task Cancellation

```swift
@Test("cancellation leaves state unchanged")
@MainActor func cancellationPreservesState() async {
    let initialItems = sut.items

    let loadTask = Task { await sut.loadItems() }
    await Task.yield()
    loadTask.cancel()
    await loadTask.value

    #expect(sut.items == initialItems)
    #expect(!sut.isLoading)
}
```

---

## Quick Async Decision Tree

```text
@Published + Combine (XCTest)?
  -> dropFirst() + expectation + sink + waitForExpectations

@Observable (XCTest)?
  -> withObservationTracking + expectation + waitForExpectations

@Observable sync (XCTest)?
  -> direct assertion, no waiting

Swift Testing + async?
  -> confirmation() for event counting
  -> withCheckedContinuation for completion handlers
  -> for await in stream.prefix(N) for AsyncStream

TCA?
  -> TestStore + await send/receive + TestClock

ViewModel with internal Task {}?
  -> expectation/confirmation or withMainSerialExecutor
```

---

## Quick Async Test Templates

### Swift Testing (Xcode 16+)

```swift
@Suite("FeatureViewModel")
@MainActor
struct FeatureViewModelTests {

    let mockRepo = MockFeatureRepository()
    var sut: FeatureViewModel

    init() { sut = FeatureViewModel(repository: mockRepo) }

    @Test("shows loaded items on success", .timeLimit(.minutes(1)))
    func loadSuccess() async {
        mockRepo.stubbedItems = [.sample(), .sample()]
        await sut.load()
        guard case .loaded(let items) = sut.state else {
            Issue.record("Expected loaded state, got \(sut.state)"); return
        }
        #expect(items.count == 2)
    }

    @Test("shows error on network failure", .timeLimit(.minutes(1)))
    func loadFailure() async {
        mockRepo.stubbedError = URLError(.notConnectedToInternet)
        await sut.load()
        guard case .failed = sut.state else {
            Issue.record("Expected failed state, got \(sut.state)"); return
        }
    }
}
```

### XCTest (Xcode 15 or older)

```swift
@MainActor
final class FeatureViewModelTests: XCTestCase {
    private var sut: FeatureViewModel!
    private var mockRepo: MockFeatureRepository!

    override func setUp() {
        super.setUp()
        mockRepo = MockFeatureRepository()
        sut = FeatureViewModel(repository: mockRepo)
    }

    override func tearDown() {
        addTeardownBlock { [weak sut = self.sut] in XCTAssertNil(sut, "Memory leak") }
        sut = nil; mockRepo = nil
        super.tearDown()
    }

    func test_load_success_showsLoadedState() async {
        mockRepo.stubbedItems = [.sample(), .sample()]
        await sut.load()
        guard case .loaded(let items) = sut.state else {
            return XCTFail("Expected .loaded, got \(sut.state)")
        }
        XCTAssertEqual(items.count, 2)
    }

    func test_load_networkError_showsFailedState() async {
        mockRepo.stubbedError = URLError(.notConnectedToInternet)
        await sut.load()
        guard case .failed = sut.state else {
            return XCTFail("Expected .failed, got \(sut.state)")
        }
    }
}
```
