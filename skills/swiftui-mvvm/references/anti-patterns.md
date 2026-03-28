# Anti-Patterns Detection & Fixes

## How to Use This Reference

When reviewing existing code, check each section below. For every violation found, add it to the feature's `refactoring/` plan with severity and recommended fix.

## Severity Levels

- **🔴 Critical**: Causes bugs, crashes, or data corruption. Fix immediately.
- **🟡 High**: Performance issues, testability blockers. Fix in next sprint.
- **🟢 Medium**: Code quality, maintainability. Fix opportunistically.

---

<critical_anti_patterns>
## 🔴 Critical Anti-Patterns

### C1: View body contains Task { }

**Problem**: Creates unmanaged tasks that outlive the view. No cancellation. Runs on every body re-evaluation if placed incorrectly.

```swift
// ❌ VIOLATION
var body: some View {
    VStack {
        Text(viewModel.title)
    }
    .onAppear {
        Task { await viewModel.load() }  // New task every appear, no cancel
    }
}

// ✅ FIX
var body: some View {
    VStack {
        Text(viewModel.title)
    }
    .task { await viewModel.load() }  // Managed lifecycle, auto-cancel
}
```

### C2: Force unwrapped dependencies

**Problem**: Runtime crash when dependency not registered.

```swift
// ❌ VIOLATION
class ViewModel {
    var service: NetworkService!  // Implicitly unwrapped
}

// ✅ FIX
@Observable @MainActor
final class ViewModel {
    private let service: NetworkServiceProtocol
    init(service: NetworkServiceProtocol) { self.service = service }
}
```

### C3: @StateObject or @ObservedObject with @Observable class

**Problem**: Using Combine wrappers with Observation framework. Causes double-notification or no notification at all.

```swift
// ❌ VIOLATION — mixing frameworks
@Observable class MyViewModel { var count = 0 }

struct MyView: View {
    @StateObject var viewModel = MyViewModel()  // WRONG wrapper
}

// ✅ FIX
struct MyView: View {
    @State private var viewModel = MyViewModel()  // Correct for @Observable
}
```

### C4: NavigationStack inside NavigationStack

**Problem**: Unpredictable navigation behavior, duplicate toolbars, broken back buttons.

**Detection**: Search for nested `NavigationStack` in view hierarchy, especially inside TabView tabs that are already wrapped.

### C5: Mutating shared state without @MainActor

**Problem**: UI updates from background threads. Purple runtime warnings, potential crashes.

```swift
// ❌ VIOLATION
@Observable class ViewModel {
    var items: [Item] = []

    func load() async {
        let fetched = try await api.fetch()
        items = fetched  // ⚠️ May execute on background thread
    }
}

// ✅ FIX
@Observable @MainActor
final class ViewModel {
    var items: [Item] = []

    func load() async {
        let fetched = try await api.fetch()
        items = fetched  // Guaranteed main thread
    }
}
```
</critical_anti_patterns>

---

## 🟡 High Anti-Patterns

### H1: Oversized File (View or ViewModel > 1000 lines)

**Problem**: Files exceeding 1000 lines are very hard to read, review, and maintain. A ViewModel handling multiple features (user data, cart, analytics, navigation) is a "God ViewModel" — untestable and unmaintainable. An oversized View buries logic and prevents reuse.

**Detection**:
- **> 1000 lines** — high priority, add a dedicated split task to the feature's `refactoring/` plan.
- **400–1000 lines** — review for multiple concerns; plan a split if the file is still growing.
- **≤ 400 lines** — fine as-is.

**Context matters**: For **new features**, aim for ≤ 400 lines from the start. For **refactoring PRs**, do NOT force a split just to hit a number — a file split is its own task. Cascading a split into an unrelated migration PR bloats the diff and defeats small-PR discipline.

**Fix**: See `file-organization.md` for full patterns:
- **ViewModel**: Split by extension files (`VM+Search.swift`, `VM+CRUD.swift`), or extract child ViewModels for sub-features with their own lifecycle.
- **View**: Extract subviews into separate files (`FeatureHeader.swift`, `ItemRow.swift`), one concern per file.
- **Shared logic**: Move reusable business logic to helper/service classes.

### H2: Separate isLoading + error + data booleans

**Problem**: Allows impossible states. Forget to reset `isLoading` on error path.

```swift
// ❌ VIOLATION
@Observable class ViewModel {
    var isLoading = false
    var error: Error?
    var items: [Item]?
    // Can be: isLoading=true AND error=non-nil AND items=non-nil 🤯
}

// ✅ FIX: Single ViewState enum
@Observable class ViewModel {
    var state: ViewState<[Item]> = .idle
}
```

### H3: ViewModel importing SwiftUI

**Problem**: Couples ViewModel to platform. Can't share with macOS/watchOS without SwiftUI import. Can't unit test without UI framework.

**Detection**: Check imports. Only `Foundation`, `Observation`, and domain modules allowed.

### H4: Business logic in View

**Problem**: Untestable. Logic scattered across Views. Duplicated across screens.

**Detection**: Look for `if`/`switch` on data state, calculations, string formatting, date formatting inside View body.

### H5: NavigationLink with destination closure

**Problem**: View is tightly coupled to its destination. Can't test navigation. Can't reuse view in different navigation contexts.

### H6: CancellationError treated as user-visible error

**Problem**: User sees "cancelled" error message when navigating away quickly.

---

## 🟢 Medium Anti-Patterns

### M1: Missing `private(set)` on ViewModel state

**Problem**: View can accidentally mutate ViewModel state, breaking unidirectional data flow.

### M2: Heavy work in @Observable init

**Problem**: Runs multiple times due to @State lifecycle. UserDefaults reads, notification registrations, network calls in init.

### M3: No MARK sections in ViewModel

**Problem**: Hard to navigate. Missing structure for: Properties, Init, Actions, Computed Properties.

### M4: Retain cycles in closures

**Problem**: ViewModel captured strongly in long-lived closures. Memory leak.

**Detection**: Look for `self` in closures stored on properties, notification observers, Combine sinks without `[weak self]`.

### M5: Using NavigationPath instead of typed [Route]

**Problem**: No compile-time safety. Can't inspect path contents. Can't serialize for state restoration without extra work.

### M6: Inline string URLs

**Problem**: Typos, no compile-time checking, duplicated across files.

```swift
// ❌ VIOLATION
let (data, _) = try await session.data(from: URL(string: "https://api.example.com/items")!)

// ✅ FIX: Centralized endpoint enum
enum Endpoint {
    case items
    case item(id: String)

    var path: String {
        switch self {
        case .items: return "/api/items"
        case .item(let id): return "/api/items/\(id)"
        }
    }
}
```

### M7: No sample/factory methods for test data

**Problem**: Test data construction duplicated across test files. Changes to model require updating every test.

---

<detection_checklist>
## Detection Checklist for Code Review

When reviewing a PR or analyzing existing code, check in this order:

1. [ ] **@Observable + @State**: Are ViewModels using `@Observable`? Is ownership via `@State`?
2. [ ] **@MainActor**: Do all ViewModels have `@MainActor`?
3. [ ] **ViewState enum**: Is async state using `ViewState<T>` not separate booleans?
4. [ ] **No Task{} in body/onAppear**: All async work via `.task` modifier?
5. [ ] **DI via constructor**: Dependencies injected, not accessed globally?
6. [ ] **Protocol abstractions**: Can repositories be mocked?
7. [ ] **Navigation via Router**: No direct NavigationLink destinations?
8. [ ] **File size**: New files ≤ 400 lines? Existing files > 1000 lines flagged for splitting? Oversized files have a task in the `refactoring/` directory?
9. [ ] **No SwiftUI import in ViewModel**: Only Foundation + Observation?
10. [ ] **Tests exist**: ViewModel has corresponding test file?
</detection_checklist>
