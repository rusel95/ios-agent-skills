# Migration Patterns

## How to Use This Reference

Read this when migrating existing code TO VIPER (from MVC/MVVM) or FROM VIPER to SwiftUI.

---

## MVC → VIPER Migration

### Phase Order

1. **Extract Services** — Move networking/persistence out of VCs into injectable service protocols
2. **Extract Interactors** — Move business logic into Interactors that use the new services
3. **Extract Presenters** — Move formatting and state mapping from VCs into Presenters
4. **Reduce VCs to Views** — VCs only do UIKit rendering and event forwarding
5. **Add Routers** — Replace segues and direct VC instantiation with Router navigation
6. **Wire Builders** — Create module factories that assemble everything

### Per-Screen Extraction Steps

```
1. Identify all state in the VC → moves to Interactor (business) or Presenter (presentation)
2. Identify all networking/persistence → moves to injected Service
3. Create module contract protocols (forces you to define boundaries)
4. Extract Interactor first (easiest to test in isolation)
5. Extract Presenter (verify zero UIKit imports)
6. Reduce VC to passive View
7. Create Router (extract navigation code)
8. Create Builder (wire everything)
9. Run existing tests — must pass
10. Add new tests for Interactor and Presenter
```

### MVVM → VIPER Migration

When MVVM ViewModels have grown too large or multiple screens share business logic:

```
ViewModel business logic → Interactor
ViewModel formatting/state → Presenter
ViewModel navigation closures → Router (via Presenter signaling)
Coordinator → can stay as-is, just delegates to VIPER Routers for intra-module nav
```

---

## VIPER → SwiftUI Migration

### Adapter Pattern (Recommended)

SwiftUI Views are structs — they can't conform to VIPER ViewInput protocols (which are `AnyObject`-constrained). Use an ObservableObject adapter:

```swift
final class OrderViewAdapter: ObservableObject, OrderListViewInput {
    @Published var viewState: ViewState<[OrderCellViewModel]> = .idle
    @Published var isRefreshing = false
    private let presenter: OrderListPresenterInput

    init(presenter: OrderListPresenterInput) {
        self.presenter = presenter
    }

    // MARK: - ViewInput
    func render(state: ViewState<[OrderCellViewModel]>) {
        self.viewState = state
    }

    func endRefreshing() {
        isRefreshing = false
    }

    // MARK: - Forward user actions to Presenter
    func onAppear() { presenter.viewDidLoad() }
    func onRefresh() { isRefreshing = true; presenter.didPullToRefresh() }
    func onSelectOrder(at index: Int) { presenter.didSelectOrder(at: index) }
}
```

### SwiftUI View

```swift
struct OrderListSwiftUIView: View {
    @ObservedObject var adapter: OrderViewAdapter

    var body: some View {
        Group {
            switch adapter.viewState {
            case .idle: EmptyView()
            case .loading: ProgressView()
            case .loaded(let items): OrderListContent(items: items, onSelect: adapter.onSelectOrder)
            case .empty: ContentUnavailableView("No Orders", systemImage: "cart")
            case .error(let error): ErrorView(error: error, onRetry: adapter.onAppear)
            }
        }
        .onAppear { adapter.onAppear() }
        .refreshable { adapter.onRefresh() }
    }
}
```

### Module Builder with UIHostingController

```swift
enum OrderListModule {
    static func build() -> UIViewController {
        let interactor = OrderListInteractor(service: OrderService())
        let presenter = OrderListPresenter()
        let router = OrderListRouter()
        let adapter = OrderViewAdapter(presenter: presenter)

        presenter.view = adapter  // adapter IS the ViewInput
        presenter.interactor = interactor
        presenter.router = router
        interactor.output = presenter

        let hostingController = UIHostingController(
            rootView: OrderListSwiftUIView(adapter: adapter)
        )
        router.viewController = hostingController
        return hostingController
    }
}
```

### Migration Rules

1. **Keep Interactor and Entity layers UNCHANGED.** Only View, Router, and Builder change.
2. **UIKit UINavigationController remains the navigation host.** Both UIKit VCs and UIHostingControllers push/present onto it.
3. **NEVER use NavigationLink inside UIHostingController pushed onto UINavigationController.** Creates nested nav controllers → corruption. Use UIKit navigation exclusively from Router.
4. **Presenter changes minimally** — if switching from delegates to Combine, Presenter may adopt @Published.

### Migration Priority

1. Static/display-only screens (About, Legal) — simplest, migrate first
2. Simple forms (Settings, Profile Edit)
3. List screens with simple cells
4. Detail screens
5. Complex screens with custom UIKit components — migrate LAST

### Migration Checklist Per Module

```
[ ] Verify Interactor has zero UIKit imports
[ ] Verify Presenter has zero UIKit imports
[ ] Create ViewAdapter (ObservableObject conforming to ViewInput)
[ ] Create SwiftUI View with @ObservedObject adapter
[ ] Update Module Builder to use UIHostingController
[ ] Update Router to handle UIHostingController
[ ] Run existing Interactor/Presenter tests — must pass without changes
[ ] Test memory management — no retain cycles with adapter
[ ] Verify VoiceOver and Dynamic Type still work
```
