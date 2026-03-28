# Performance Diagnostics & Verification

## Why Performance Evidence Matters

Every architectural recommendation in this skill has a measurable performance impact. Never claim "this is faster" without showing HOW to verify it. This reference teaches the diagnostic tools needed to prove (or disprove) that a refactoring improved performance.

## Tool 1: Self._printChanges() — View Redraw Debugging

The most important diagnostic for SwiftUI. Shows exactly WHY a view re-evaluated its body.

```swift
struct ItemListView: View {
    let viewModel: ItemListViewModel

    var body: some View {
        let _ = Self._printChanges()  // Add this line temporarily
        List(viewModel.filteredItems) { item in
            ItemRow(item: item)
        }
    }
}
```

**Reading the output:**

```
// ObservableObject — ANY @Published change triggers redraw:
ItemListView: @self, @identity, _viewModel changed.

// @Observable — only READ properties trigger redraw:
ItemListView: @self changed.

// No redraw needed (but parent forced it):
ItemListView: @identity changed.

// Binding changed:
SearchBar: _searchText changed.
```

**Use to verify @Observable migration:** Add `Self._printChanges()` BEFORE migration, note the output. Remove ObservableObject, add @Observable. Check output again — you should see fewer and more specific change triggers.

**ALWAYS REMOVE before committing.** This is a debugging tool, not production code.

## Tool 2: Instruments — Time Profiler for Launch Time

Launch time directly impacts user retention. Apple's target: **≤400ms to first frame** on cold launch.

**Measuring pre-main time (dylib loading):**
1. Edit scheme → Run → Arguments → Environment Variables
2. Add: `DYLD_PRINT_STATISTICS = 1`
3. Run app, check console:

```
Total pre-main time: 1.4 seconds (100.0%)
  dylib loading time: 620ms (44.2%)
  rebase/binding time: 135ms (9.6%)
  ObjC setup time:     240ms (17.1%)
  initializer time:    405ms (28.9%)
```

**Impact of DI choices on launch time:**
- Eager singleton registration in `init()` → adds directly to initializer time
- `@Entry` lazy EnvironmentValues → zero launch cost, created on first access
- Third-party DI frameworks (Swinject, Needle) → dylib + initializer overhead

**Reducing dylib loading:** Use static SPM libraries instead of dynamic frameworks when possible. Each dynamic framework adds 5-15ms to dylib loading.

## Tool 3: Instruments — SwiftUI View Body Profile

Identifies which view bodies take the longest to evaluate:

1. Product → Profile (⌘I)
2. Choose "SwiftUI" instrument
3. Record a session
4. Look at "View Body" track — shows evaluation count and duration per view type

**What to look for:**
- Views with >100 body evaluations in a short session → excessive redraws
- Views with >1ms body evaluation time → complex body computation
- Views that re-evaluate when their data hasn't changed → observation bug

## Tool 4: View Count Verification for Lists

Scrolling performance degrades when list cells re-render unnecessarily. Verify with a counter:

```swift
struct ItemRow: View {
    let item: Item
    #if DEBUG
    static var bodyCount = 0
    #endif

    var body: some View {
        #if DEBUG
        let _ = { Self.bodyCount += 1; print("ItemRow body #\(Self.bodyCount): \(item.name)") }()
        #endif
        ...
    }
}
```

**Expected behavior with @Observable:** Changing item #42's name should print `ItemRow body` ONLY for item #42, not all 100 items.

**With ObservableObject:** You'll see all visible cells re-evaluate because the entire `@Published items` array changed notification fires.

## Performance Impact Table

| Pattern | Metric | Impact | How to Verify |
|---------|--------|--------|---------------|
| @Observable over ObservableObject | View redraws | Only views reading changed property redraw | `Self._printChanges()` |
| ViewState enum over 3 booleans | State transitions | 1 property change vs 2-3 | `Self._printChanges()` — 1 trigger vs multiple |
| .task over onAppear+Task | Task lifecycle | Auto-cancellation prevents leaked work | Instruments: check for background Tasks after nav back |
| @State for ViewModel ownership | Object lifecycle | Prevents recreation on parent redraw | Add print in ViewModel.init — should print once |
| Lazy DI (@Entry) over eager | Launch time | 0ms vs 50-500ms per service | `DYLD_PRINT_STATISTICS` + initializer time |
| Static over dynamic frameworks | Launch time | -5-15ms per framework | `DYLD_PRINT_STATISTICS` → dylib loading time |
| Typed [Route] over NavigationPath | Compilation | Compiler catches route errors | Build count — zero runtime route crashes |
| Repository caching | Network calls | Reduces duplicate requests | Charles/Proxyman request count |
| @MainActor on ViewModel | Thread safety | Eliminates purple runtime warnings | Run with Thread Sanitizer enabled |

## Verification Checklist per Refactoring Phase

### After @Observable Migration (Phase 2)
```
□ Self._printChanges() shows reduced/specific triggers
□ ViewModel.init prints only once (not on every parent redraw)
□ List scrolling: only visible changed cells re-render
□ No purple thread warnings in console
□ All existing tests still pass
```

### After ViewState Adoption (Phase 3)
```
□ Self._printChanges() shows single state change per async operation
□ Impossible states eliminated (can't be loading AND error simultaneously)
□ Error → retry → loading → success flow works without stale state
□ Empty state handled (ViewState.idle vs .loaded([]))
```

### After DI Introduction (Phase 4)
```
□ Launch time unchanged or improved (DYLD_PRINT_STATISTICS)
□ Tests can swap dependencies without global state pollution
□ No force unwraps in dependency resolution
□ App extensions (widgets, intents) can access services
```

## ❌ Performance Anti-Patterns

**Formatting dates/numbers in View body:**
```swift
// ❌ Creates new formatter on EVERY body evaluation
var body: some View {
    let formatter = DateFormatter()
    formatter.dateStyle = .medium
    Text(formatter.string(from: item.date))
}

// ✅ Use SwiftUI's built-in formatting
var body: some View {
    Text(item.date, format: .dateTime.month().day().year())
}
```

**Expensive computed properties without caching:**
```swift
// ❌ O(n) filter on every body evaluation
@Observable class ViewModel {
    var items: [Item] = []
    var searchQuery = ""

    var filteredItems: [Item] {
        items.filter { $0.name.localizedCaseInsensitiveContains(searchQuery) }
    }
}

// For large datasets (1000+), cache with didSet:
@Observable class ViewModel {
    var items: [Item] = [] { didSet { updateFiltered() } }
    var searchQuery = "" { didSet { updateFiltered() } }
    private(set) var filteredItems: [Item] = []

    private func updateFiltered() { ... }
}
```

**GeometryReader in scrollable lists:**
```swift
// ❌ GeometryReader forces layout recalculation for every cell
List(items) { item in
    GeometryReader { geo in  // Kills scroll performance
        ItemRow(item: item, width: geo.size.width)
    }
}

// ✅ Use .containerRelativeFrame or fixed sizes
List(items) { item in
    ItemRow(item: item)
        .containerRelativeFrame(.horizontal)  // iOS 17+
}
```
