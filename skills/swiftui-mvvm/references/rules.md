# SwiftUI MVVM Architecture — Rules Quick Reference

## Do's — Always Follow

1. **Mark all ViewModels `@Observable @MainActor final class`** — eliminates thread-safety bugs, enables compiler optimizations, enforces composition over inheritance.
2. **Use `ViewState<T>` enum for async data** — prevents impossible states (loading AND error simultaneously). Never use separate `isLoading` + `error` + `data` booleans.
3. **Use `.task { }` for initial data loading** — SwiftUI manages lifecycle, auto-cancels on disappear. Never use `onAppear { Task { } }`.
4. **Inject dependencies via constructor with protocol types** — enables testing, prevents singleton coupling. `init(repository: ItemRepositoryProtocol)`.
5. **Use `private(set) var` for ViewModel state** — View can read but not write. Enforces unidirectional data flow. `@testable import` grants write access for tests.
6. **Use typed `enum Route: Hashable` for navigation** — compile-time safety, inspectable paths, Codable state restoration. Never string-based routing.
7. **Handle `CancellationError` silently** — never show "cancelled" to the user. Catch it separately and return without modifying state.
8. **Keep new files ≤ 400 lines** — split large Views into subview files; split large ViewModels by extension files (`VM+Feature.swift`) or child ViewModels. For existing files over 400 lines, add a split task to the feature's `refactoring/` plan rather than forcing it into an unrelated PR. See `references/file-organization.md`.

## Don'ts — Critical Anti-Patterns

### Never: Task { } in View body or onAppear

```swift
// ❌ Unmanaged task, no cancellation, runs on every reappear
.onAppear { Task { await viewModel.load() } }

// ✅ Managed lifecycle, auto-cancel on disappear
.task { await viewModel.load() }
```

### Never: @StateObject / @ObservedObject with @Observable class

```swift
// ❌ Mixing Combine wrappers with Observation framework
@StateObject var viewModel = MyViewModel()  // WRONG for @Observable

// ✅ Use @State for @Observable classes
@State private var viewModel = MyViewModel()
```

### Never: Force-unwrapped dependencies

```swift
// ❌ Runtime crash when not registered
var service: NetworkService!

// ✅ Constructor injection with protocol
private let service: NetworkServiceProtocol
init(service: NetworkServiceProtocol) { self.service = service }
```

### Never: Import SwiftUI in ViewModel

```swift
// ❌ Couples ViewModel to platform, breaks unit testing
import SwiftUI
@Observable class BadVM { var icon: Image = Image(systemName: "star") }

// ✅ Platform-agnostic types only
import Foundation
@Observable class GoodVM { var iconName: String = "star" }
```

### Never: NavigationStack inside NavigationStack

Causes unpredictable behavior, duplicate toolbars, broken back buttons. Each TabView tab gets its own NavigationStack — never wrap TabView itself in one.
