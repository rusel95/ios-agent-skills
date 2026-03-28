# MVVM with @Observable (iOS 17+)

## The Problem @Observable Solves

With `ObservableObject`, changing ANY `@Published` property triggers re-evaluation of EVERY observing view — even views that don't read the changed property. In a list of 100 items, updating item #42's title re-renders all 100 cells.

`@Observable` switches to access-tracked observation: SwiftUI records which properties each view's `body` actually reads, and only invalidates views that read the changed property.

**Verify with `Self._printChanges()`:**
```swift
// Add to any View's body to see what triggers redraws:
let _ = Self._printChanges()
```

With ObservableObject: `ContentView: @self, @identity, _viewModel changed.` (fires for ANY property)
With @Observable: `ContentView: @self changed.` (fires only for READ properties)

## Migration Mapping

> Combine itself is NOT legacy — it remains a supported framework for reactive streams, publishers, and operators. This table covers only the **ObservableObject-based observation pattern** that the Observation framework (`@Observable`) replaces for SwiftUI state management.

| ObservableObject Pattern (pre-iOS 17) | Observation Framework (iOS 17+) | Notes |
|---|---|---|
| `ObservableObject` protocol | `@Observable` macro | Remove protocol conformance |
| `@Published var` | `var` (plain stored property) | Remove all @Published |
| `@StateObject` | `@State` | 1:1 replacement |
| `@ObservedObject` | plain `let` / `var` | No wrapper needed |
| `@EnvironmentObject` | `@Environment(Type.self)` | Different syntax |
| `.environmentObject(obj)` | `.environment(obj)` | Shorter modifier |

## ViewModel Template

Every ViewModel follows this structure:

```swift
import Foundation

@Observable @MainActor
final class ItemListViewModel {
    // MARK: - State
    private(set) var state: ViewState<[Item]> = .idle
    var searchQuery = ""  // Writable — View binds directly

    // MARK: - Dependencies
    private let repository: ItemRepositoryProtocol

    // MARK: - Init
    init(repository: ItemRepositoryProtocol) { ... }

    // MARK: - Actions
    func loadItems() async { ... }
    func deleteItem(at offsets: IndexSet) async { ... }

    // MARK: - Computed Properties
    var filteredItems: [Item] { ... }
}
```

**Why `@MainActor`**: ViewModels mutate state that drives UI. Without `@MainActor`, every state mutation needs `await MainActor.run { }`. With it, Swift guarantees all property access happens on the main thread. This eliminates an entire class of thread-safety bugs.

**Why `final class`**: Prevents subclassing. ViewModels should be composed, not inherited. Also enables compiler optimizations (static dispatch).

**Why `private(set)`**: The View can READ `state` to render UI but cannot WRITE it directly. Only the ViewModel's methods modify state. This enforces unidirectional data flow. For testing, `@testable import` grants write access.

## View Ownership Rules

### Rule 1: The creating view uses @State

```swift
struct ItemListScreen: View {
    @State private var viewModel: ItemListViewModel

    init(repository: ItemRepositoryProtocol) {
        _viewModel = State(initialValue: ItemListViewModel(repository: repository))
    }

    var body: some View { ... }
}
```

### Rule 2: Receiving views use plain properties

```swift
struct ItemListContent: View {
    let viewModel: ItemListViewModel  // No wrapper — just a reference
    var body: some View { ... }
}
```

### Rule 3: @Bindable when you need $ bindings on a received ViewModel

```swift
struct SearchBar: View {
    @Bindable var viewModel: ItemListViewModel  // Enables $viewModel.searchQuery
    var body: some View { ... }  // Can use $viewModel.searchQuery
}
```

### Rule 4: @Bindable for @Environment objects needing bindings

```swift
struct EditorView: View {
    @Environment(Document.self) private var document

    var body: some View {
        @Bindable var document = document  // Local @Bindable at top of body
        TextEditor(text: $document.content)
    }
}
```

## The @State Lifecycle Trap

**Problem**: `@State` initializes eagerly. Every time SwiftUI re-creates the View struct, the initializer runs — even though SwiftUI discards the duplicate and restores the cached instance.

```swift
// ❌ DANGEROUS: Heavy work in init runs multiple times
@Observable final class BadViewModel {
    init() {
        loadFromUserDefaults()       // Called on every parent redraw!
        registerForNotifications()   // Multiple registrations!
    }
}

// ✅ SAFE: Lightweight init + deferred work
@Observable @MainActor final class SafeViewModel {
    var items: [Item] = []
    init() {}  // No side effects
    func bootstrap() async { ... }  // Heavy work here, called once via .task
}

// Wire: .task { await viewModel.bootstrap() }
```

## Observation Tracking Gotchas

### Properties read outside `body` are NOT tracked

```swift
// ❌ NOT TRACKED: property read in onAppear closure
var body: some View {
    Text("Hello")
        .onAppear {
            print(viewModel.count)  // This read is NOT tracked
        }
}

// ✅ TRACKED: property read directly in body
var body: some View {
    Text("Count: \(viewModel.count)")  // This IS tracked
}
```

### Computed properties work correctly with @Observable

```swift
@Observable class Model {
    var firstName = ""
    var lastName = ""
    var fullName: String { "\(firstName) \(lastName)" }  // Tracked through its dependencies
}
// Reading fullName in body tracks firstName AND lastName
```

### Nested @Observable objects propagate changes

Unlike `ObservableObject`, nested `@Observable` objects work:

```swift
@Observable class Parent {
    var child = Child()  // Changes to child.name trigger Parent observers
}

@Observable class Child {
    var name = ""
}
```

## ❌ Anti-Patterns to Detect

**Separate boolean flags instead of ViewState enum:**
```swift
// ❌ Three separate state variables = impossible states (isLoading AND hasError)
@Observable class BadVM {
    var isLoading = false
    var error: Error?
    var items: [Item] = []
}

// ✅ Single ViewState enum = exactly one state at a time
@Observable class GoodVM {
    var state: ViewState<[Item]> = .idle
}
```

**ViewModel knowing about SwiftUI types:**
```swift
// ❌ Importing SwiftUI in ViewModel
import SwiftUI
@Observable class BadVM {
    var icon: Image = Image(systemName: "star")  // SwiftUI type!
    var tintColor: Color = .blue                  // SwiftUI type!
}

// ✅ Platform-agnostic types
import Foundation
@Observable class GoodVM {
    var iconName: String = "star"        // View maps to Image(systemName:)
    var isHighlighted: Bool = false      // View decides the color
}
```

**View doing business logic:**
```swift
// ❌ Business logic in View
Button("Save") {
    Task {
        let validated = item.name.count > 3 && item.price > 0
        if validated { try? await URLSession.shared.upload(item.encoded()) }
    }
}

// ✅ View delegates to ViewModel
Button("Save") { Task { await viewModel.saveItem() } }
```
