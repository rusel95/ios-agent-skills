# File Organization & Splitting Patterns

## File Size Guidelines

Smaller files are easier to read, review, and maintain. The thresholds below are **guidelines for new code** — not a hard gate that blocks every PR.

**Trigger thresholds:**

| Lines | Verdict | Action |
|-------|---------|--------|
| ≤ 400 | ✅ Fine | No action needed |
| 400–700 | 🟡 Review | Check for multiple concerns; plan a split if the file is still growing |
| 700–1000 | 🟠 Plan split | Identify logical boundaries and schedule an extraction |
| > 1000 | 🔴 Must address | File is a strong candidate for splitting; prioritise in the next cycle |

> Extension files under 30 lines are too granular — merge back or combine.

### New Code vs Refactoring

**New features** — aim for ≤ 400 lines per file from the start. Splitting at creation time is cheap.

**Refactoring / tech-debt** — do NOT force a file split inside a refactoring PR just to hit a line count. Splitting a 900-line legacy ViewModel is itself a large refactoring; it deserves its own dedicated task in the feature's `refactoring/` plan. Forcing it into an unrelated migration PR creates cascading changes, bloats the diff, and defeats the purpose of small focused PRs.

## Decision Tree: How to Split

```
File exceeds 400 lines (or growing toward it in new code)?
├── It's a ViewModel
│   ├── Has distinct feature groups (search, filtering, CRUD)?
│   │   └── Split by EXTENSION files: `MyVM+Search.swift`
│   ├── Has a child concern with its own lifecycle (form, detail panel)?
│   │   └── Extract CHILD VIEWMODEL: `FormViewModel` owned by parent
│   └── Has reusable business logic (validation, formatting)?
│       └── Extract HELPER / SERVICE class
├── It's a View
│   ├── Has identifiable sub-sections (header, list, footer)?
│   │   └── Extract SUBVIEW files: `MyFeatureHeader.swift`
│   ├── Has a complex row / cell?
│   │   └── Extract ROW VIEW: `ItemRow.swift`
│   └── Has repetitive modifiers or style configurations?
│       └── Extract VIEW MODIFIER or EXTENSION: `MyView+Styling.swift`
```

---

## Splitting ViewModels by Extension

Use Swift file-level extensions to group related functionality while keeping a single ViewModel class.

### File: `ItemListViewModel.swift` (core)

```swift
import Foundation

@Observable @MainActor
final class ItemListViewModel {
    // MARK: - State
    private(set) var state: ViewState<[Item]> = .idle
    private(set) var selectedFilter: ItemFilter = .all
    var searchQuery = ""

    // MARK: - Dependencies
    private let repository: ItemRepositoryProtocol
    private let analytics: AnalyticsServiceProtocol

    // MARK: - Init
    init(repository: ItemRepositoryProtocol, analytics: AnalyticsServiceProtocol) { ... }

    // MARK: - Core Actions
    func loadItems() async { ... }
}
```

### File: `ItemListViewModel+Search.swift`

```swift
extension ItemListViewModel {
    // MARK: - Search & Filtering
    var filteredItems: [Item] { ... }
    func applyFilter(_ items: [Item]) -> [Item] { ... }
    func updateFilter(_ filter: ItemFilter) { ... }
}
```

### File: `ItemListViewModel+CRUD.swift`

```swift
extension ItemListViewModel {
    // MARK: - Create / Update / Delete
    func deleteItems(at offsets: IndexSet) async { ... }
    func toggleFavorite(for item: Item) async { ... }
}
```

### Naming Convention for Extension Files

```
{ClassName}+{FeatureGroup}.swift
```

| File | Purpose |
|------|---------|
| `ProfileViewModel.swift` | Core state, init, dependencies |
| `ProfileViewModel+Validation.swift` | Form validation logic |
| `ProfileViewModel+Avatar.swift` | Avatar upload / crop logic |
| `ProfileViewModel+Settings.swift` | User preferences management |

---

## Child ViewModel Pattern

When a concern has its own distinct lifecycle (modal form, expandable detail panel, filter sidebar), extract a **child ViewModel**.

```swift
// Parent: OrderListViewModel.swift
@Observable @MainActor
final class OrderListViewModel {
    private(set) var state: ViewState<[Order]> = .idle
    private(set) var activeFilter: OrderFilterViewModel  // child VM
    private let repository: OrderRepositoryProtocol

    init(repository: OrderRepositoryProtocol) { ... }
    var filteredOrders: [Order] { activeFilter.apply(to: ...) }
    func loadOrders() async { ... }
}

// Child: OrderFilterViewModel.swift
@Observable @MainActor
final class OrderFilterViewModel {
    var dateRange: DateRange = .lastMonth
    var statusFilter: OrderStatus? = nil
    var minAmount: Decimal? = nil

    func apply(to orders: [Order]) -> [Order] { ... }
    func reset() { ... }
}
```

### Ownership Rules for Child ViewModels

- Parent **creates and owns** child VM via `private(set) var` or `let`
- Child VM is passed to child View as `let` or `@Bindable`
- Child **NEVER** holds a reference to parent — no back-pointers
- Communication flows down (parent → child), events flow up via closures or shared service

---

## Splitting Views into Subviews

Large Views are split into dedicated subview files — one concern per file.

### File: `ItemListScreen.swift` — Screen container

```swift
struct ItemListScreen: View {
    @State private var viewModel: ItemListViewModel

    init(repository: ItemRepositoryProtocol) { ... }

    var body: some View {
        ItemListContent(viewModel: viewModel)
            .searchable(text: $viewModel.searchQuery)
            .task { await viewModel.loadItems() }
            .navigationTitle("Items")
    }
}
```

### File: `ItemListContent.swift` — ViewState switch

```swift
struct ItemListContent: View {
    let viewModel: ItemListViewModel

    var body: some View {
        switch viewModel.state {
        case .idle, .loading: ProgressView()
        case .loaded:         ItemListBody(viewModel: viewModel)
        case .failed(let error): ContentUnavailableView(...)
        }
    }
}
```

### File: `ItemListBody.swift` — The list

```swift
struct ItemListBody: View {
    @Bindable var viewModel: ItemListViewModel

    var body: some View {
        List {
            ForEach(viewModel.filteredItems) { item in
                ItemRow(item: item, onFavorite: { ... })
            }
            .onDelete { offsets in ... }
        }
    }
}
```

### File: `ItemRow.swift` — Reusable row

```swift
struct ItemRow: View {
    let item: Item
    var onFavorite: () -> Void

    var body: some View { ... }
}
```

### Naming Convention for Subviews

```
{FeatureName}{Role}.swift
```

| File | Role |
|------|------|
| `ItemListScreen.swift` | Screen container — owns ViewModel, wires `.task` |
| `ItemListContent.swift` | ViewState switch — routes to correct sub-view |
| `ItemListBody.swift` | Main content layout |
| `ItemListHeader.swift` | Top section / filter bar |
| `ItemRow.swift` | Reusable list row |
| `ItemDetailSheet.swift` | Modal detail |

---

## When NOT to Split

- **File is under 200 lines** — splitting adds navigational overhead with no readability gain
- **All methods are tightly coupled** — splitting would require passing many parameters between extensions
- **It's a simple data-display View** — a 150-line View with a single List is fine as-is
- **A split would yield 1 method per file** — that's fragmentation, not organization
