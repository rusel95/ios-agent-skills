# Dependency Injection (iOS 17+)

## The Problem with Singletons and AppDelegate

Production codebases accumulate `AppDelegate.shared.networkService`, `ServiceLocator.resolve()`, and global singletons. These cause: Thread Sanitizer warnings from concurrent access, impossibility of mocking in tests, app extension crashes (no AppDelegate), hidden dependencies making refactoring dangerous, and massive initializer chains.

## Recommended: Constructor Injection + @Environment

The primary pattern. ViewModels receive dependencies through `init`. Views read from `@Environment` and pass to ViewModels.

```swift
// 1. Define protocol
protocol ItemRepositoryProtocol: Sendable {
    func fetchItems() async throws -> [Item]
    func saveItem(_ item: Item) async throws
    func deleteItems(_ items: [Item]) async throws
}

// 2. Production implementation
final class RemoteItemRepository: ItemRepositoryProtocol {
    private let httpClient: HTTPClientProtocol
    init(httpClient: HTTPClientProtocol) { ... }

    func fetchItems() async throws -> [Item] { ... }
    func saveItem(_ item: Item) async throws { ... }
    func deleteItems(_ items: [Item]) async throws { ... }
}

// 3. Register in @Environment using @Entry (iOS 17+)
extension EnvironmentValues {
    @Entry var itemRepository: ItemRepositoryProtocol = RemoteItemRepository(
        httpClient: URLSessionHTTPClient()
    )
}

// 4. ViewModel receives via init
@Observable @MainActor
final class ItemListViewModel {
    private let repository: ItemRepositoryProtocol
    init(repository: ItemRepositoryProtocol) { ... }
}

// 5. View bridges Environment → ViewModel
struct ItemListScreen: View {
    @Environment(\.itemRepository) private var repository
    @State private var viewModel: ItemListViewModel?

    var body: some View { ... }  // .task creates VM with repository from environment
}
```

**Why View bridges to ViewModel**: ViewModels cannot access `@Environment` directly — it's a SwiftUI View property wrapper. The View reads from Environment and passes via init.

## Advanced: @Injected Property Wrapper

For services needed outside the view hierarchy (in ViewModels, background services, deep utility classes), use this pattern inspired by SwiftUI's `@Environment`:

```swift
// MARK: - Infrastructure (define once, reuse everywhere)

protocol InjectionKey {
    associatedtype Value
    static var currentValue: Value { get set }
}

struct InjectedValues {
    private static var current = InjectedValues()
    static subscript<K>(key: K.Type) -> K.Value where K: InjectionKey { ... }
    static subscript<T>(_ keyPath: WritableKeyPath<InjectedValues, T>) -> T { ... }
}

@propertyWrapper
struct Injected<T> {
    private let keyPath: WritableKeyPath<InjectedValues, T>
    var wrappedValue: T { ... }
    init(_ keyPath: WritableKeyPath<InjectedValues, T>) { ... }
}

// MARK: - Registering a Dependency

private struct ItemRepositoryKey: InjectionKey {
    static var currentValue: ItemRepositoryProtocol = RemoteItemRepository(...)
}

extension InjectedValues {
    var itemRepository: ItemRepositoryProtocol {
        get { Self[ItemRepositoryKey.self] }
        set { Self[ItemRepositoryKey.self] = newValue }
    }
}

// MARK: - Usage in ViewModel

@Observable @MainActor
final class ItemListViewModel {
    @Injected(\.itemRepository) private var repository
}

// MARK: - Swap for tests
// InjectedValues[\.itemRepository] = MockItemRepository(...)
// ⚠️ Always reset in tearDown to avoid cross-test pollution
```

**Tradeoff**: Constructor injection is more explicit and testable (no global state). @Injected is more convenient but uses mutable global state — always reset in `tearDown`. Use constructor injection for ViewModels in new code; @Injected for legacy migrations or deep utility classes.

## Closure-Based Services (Zero-Protocol Alternative)

For lightweight services, replace protocols with structs containing closures:

```swift
struct AnalyticsService: Sendable {
    var trackEvent: @Sendable (String, [String: String]) -> Void
    var trackScreen: @Sendable (String) -> Void

    static let live = AnalyticsService(trackEvent: { ... }, trackScreen: { ... })
    static let mock = AnalyticsService(trackEvent: { _, _ in }, trackScreen: { _ in })
    static let preview = AnalyticsService(trackEvent: { ... }, trackScreen: { ... })
}

extension EnvironmentValues {
    @Entry var analytics: AnalyticsService = .live
}
```

**When to use**: Fire-and-forget services (analytics, logging), services with ≤3 methods, services where you want inline mock definitions for previews.

**When NOT to use**: Complex services with many methods (protocol is clearer), services that maintain state, services used in constructor injection chains.

## Service Injection in MVVM+SwiftUI

Services flow **down** through the view hierarchy. The pattern:

1. **Define** a protocol for the service
2. **Register** the default implementation in `EnvironmentValues` via `@Entry`
3. **Inject** into ViewModels through constructor injection (preferred) or `@Injected`
4. **Bridge** in the View: read from `@Environment`, pass to ViewModel's `init`

```
App / Scene
  └─ .environment(\.myService, CustomImpl())     // Override here or use @Entry default
      └─ ScreenView
          ├─ @Environment(\.myService) var svc   // View reads
          └─ .task { vm = ViewModel(service: svc) } // Passes to VM
```

**Rules:**
- ViewModels NEVER access `@Environment` — it’s a SwiftUI-only property wrapper
- One protocol per service boundary — keep interfaces small
- Use `@Entry` for lazy registration (zero launch cost)
- Prefer constructor injection for testability; `@Injected` for legacy or deep utility code

## ❌ DI Anti-Patterns

**Force-unwrapped optionals for dependencies:**
```swift
// ❌ Crashes at runtime if not registered
var networkService: NetworkService!
```

**AppDelegate as service locator:**
```swift
// ❌ Thread Sanitizer warnings, unavailable in extensions
let service = (UIApplication.shared.delegate as! AppDelegate).networkService
```

**Initializing everything eagerly at app launch:**
```swift
// ❌ Slows launch time, wastes memory
@main struct App {
    init() {
        Container.register(HeavyService())      // 200ms
        Container.register(AnotherService())     // 150ms
        Container.register(YetAnotherService())  // 100ms
        // 450ms of launch time wasted
    }
}

// ✅ Lazy initialization — create when first accessed
extension EnvironmentValues {
    @Entry var heavyService: HeavyServiceProtocol = HeavyService()  // Created on first read
}
```
