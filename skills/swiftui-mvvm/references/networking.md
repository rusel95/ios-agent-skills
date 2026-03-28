# Networking Layer (async/await)

## Architecture: View → ViewModel → Repository → HTTPClient

ViewModels never touch URLSession. Repositories abstract data sources. HTTPClient handles raw HTTP.

## ViewState Enum: The Single Source of Truth

```swift
enum ViewState<T> {
    case idle
    case loading
    case loaded(T)
    case failed(Error)

    var value: T? { ... }
    var isLoading: Bool { ... }
    var error: Error? { ... }
}
```

## Generic AsyncContentView

Eliminate boilerplate across every screen:

```swift
struct AsyncContentView<T, Content: View, ErrorContent: View>: View {
    let state: ViewState<T>
    let retryAction: (() async -> Void)?
    @ViewBuilder let content: (T) -> Content
    @ViewBuilder let errorContent: (Error) -> ErrorContent

    init(state:retryAction:content:errorContent:) { ... }

    var body: some View {
        // Switches on state: .idle → Color.clear, .loading → ProgressView(),
        // .loaded → content(data), .failed → errorContent + optional retry button
        ...
    }
}

// Usage:
AsyncContentView(state: viewModel.state, retryAction: viewModel.loadItems) { items in
    List(items) { item in ItemRow(item: item) }
}
.task { await viewModel.loadItems() }
```

## Repository Pattern

```swift
protocol ItemRepositoryProtocol: Sendable {
    func fetchItems() async throws -> [Item]
    func fetchItem(id: String) async throws -> Item
    func saveItem(_ item: Item) async throws
    func deleteItems(_ items: [Item]) async throws
}

final class RemoteItemRepository: ItemRepositoryProtocol {
    private let client: HTTPClientProtocol
    private let cache: CacheProtocol

    init(client: HTTPClientProtocol, cache: CacheProtocol = InMemoryCache()) { ... }

    func fetchItems() async throws -> [Item] { ... }   // Check cache → fetch → store
    func fetchItem(id: String) async throws -> Item { ... }
    func saveItem(_ item: Item) async throws { ... }    // POST + invalidate cache
    func deleteItems(_ items: [Item]) async throws { ... }  // Parallel delete via TaskGroup
}
```

## HTTPClient Abstraction

```swift
protocol HTTPClientProtocol: Sendable {
    func get<T: Decodable>(_ path: String) async throws -> T
    func post<T: Encodable>(_ path: String, body: T) async throws -> Void
    func delete(_ path: String) async throws
}

final class URLSessionHTTPClient: HTTPClientProtocol {
    private let session: URLSession
    private let baseURL: URL
    private let decoder: JSONDecoder
    private let encoder: JSONEncoder

    init(baseURL:session:decoder:encoder:) { ... }

    func get<T: Decodable>(_ path: String) async throws -> T { ... }
    func post<T: Encodable>(_ path: String, body: T) async throws { ... }
    func delete(_ path: String) async throws { ... }
    private func validate(_ response: URLResponse) throws { ... }
}

enum NetworkError: LocalizedError {
    case invalidResponse
    case unauthorized
    case notFound
    case serverError(Int)
    case unexpectedStatus(Int)

    var errorDescription: String? { ... }  // User-friendly messages
}
```

## Task Cancellation Patterns

### Pattern 1: .task modifier (preferred)

SwiftUI cancels the task automatically when the view disappears:

```swift
.task { await viewModel.loadItems() }            // Cancelled on disappear
.task(id: viewModel.searchQuery) {               // Cancelled + restarted on id change
    try? await Task.sleep(for: .milliseconds(300))  // Debounce
    guard !Task.isCancelled else { return }
    await viewModel.search()
}
```

### Pattern 2: Manual Task management in ViewModel

When a task must be cancellable by user action (not view lifecycle):

```swift
@Observable @MainActor
final class UploadViewModel {
    private var uploadTask: Task<Void, Never>?
    private(set) var state: ViewState<UploadResult> = .idle

    func startUpload(file: Data) { ... }  // Cancel previous → create Task → check isCancelled
    func cancelUpload() { ... }           // Cancel task + reset state
}
```

### Always handle CancellationError explicitly

```swift
// ❌ CancellationError treated as regular error
} catch {
    state = .failed(error)  // Shows "cancelled" to user
}

// ✅ CancellationError handled separately
} catch is CancellationError {
    return  // Silently ignore — state stays as-is
} catch {
    state = .failed(error)
}
```

## ❌ Networking Anti-Patterns

**URLSession in ViewModel:**
```swift
// ❌ Not testable, not reusable
@Observable class BadVM {
    func load() async { ... }  // URLSession.shared directly
}
```

**Fire-and-forget tasks:**
```swift
// ❌ Task leaks if view disappears
func load() { Task { await fetchData() } }

// ✅ Use .task modifier — SwiftUI manages lifecycle
.task { await viewModel.fetchData() }
```

**Raw URLError shown to user:**
```swift
// ❌ "The Internet connection appears to be offline."
state = .failed(urlError)

// ✅ Map to user-friendly errors
state = .failed(NetworkError.from(urlError))
```
