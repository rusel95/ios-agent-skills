# Navigation Architecture (iOS 17+)

## The Problem with Ad-Hoc Navigation

Without centralized navigation, every view knows about its destination. Adding deep linking requires touching every screen. Testing navigation paths is impossible. Refactoring one screen's route breaks its parent.

## Enum-Based Routing with @Observable Router

### Route Definition

```swift
enum Route: Hashable {
    case itemList
    case itemDetail(Item)
    case settings
    case profile(userId: String)
}
```

**Use typed arrays `[Route]` over `NavigationPath`** — you get compile-time safety, `Codable` state restoration, and can inspect/modify the path. Use `NavigationPath` only when you need heterogeneous navigation types in a single stack.

### Router

```swift
@Observable @MainActor
final class AppRouter {
    var routes: [Route] = []
    var presentedSheet: SheetDestination?
    var presentedAlert: AlertDestination?

    enum SheetDestination: Identifiable { case addItem, editItem(Item), filter(FilterOptions); var id: String { ... } }
    enum AlertDestination: Identifiable { case deleteConfirmation(Item), error(String); var id: String { ... } }

    // MARK: - Navigation Actions
    func navigate(to route: Route) { ... }
    func pop() { ... }
    func popToRoot() { ... }
    func replaceAll(with route: Route) { ... }

    // MARK: - Sheet Actions
    func presentSheet(_ sheet: SheetDestination) { ... }
    func dismissSheet() { ... }
}
```

### Wiring in the App Root

```swift
@main
struct MyApp: App {
    @State private var router = AppRouter()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(router)
        }
    }
}

struct RootView: View {
    @Environment(AppRouter.self) private var router

    var body: some View {
        @Bindable var router = router

        NavigationStack(path: $router.routes) {
            HomeScreen()
                .navigationDestination(for: Route.self) { route in
                    destinationView(for: route)
                }
        }
        .sheet(item: $router.presentedSheet) { sheet in ... }
        .alert(item: $router.presentedAlert) { alert in ... }
    }

    @ViewBuilder
    private func destinationView(for route: Route) -> some View { ... }  // switch route
    @ViewBuilder
    private func sheetView(for sheet: AppRouter.SheetDestination) -> some View { ... }
}
```

## TabView: Each Tab Gets Its Own NavigationStack

**NEVER wrap TabView in NavigationStack. NEVER nest NavigationStack inside another.**

```swift
@Observable @MainActor
final class TabRouter {
    var selectedTab: Tab = .home
    var homeRoutes: [HomeRoute] = []
    var searchRoutes: [SearchRoute] = []
    var profileRoutes: [ProfileRoute] = []

    enum Tab: Hashable { case home, search, profile }

    func switchTab(to tab: Tab) { ... }  // Same tab = pop to root, different = switch
}

struct MainTabView: View {
    @Environment(TabRouter.self) private var tabRouter

    var body: some View {
        @Bindable var tabRouter = tabRouter

        TabView(selection: $tabRouter.selectedTab) {
            Tab("Home", ...) { NavigationStack(path: $tabRouter.homeRoutes) { ... } }
            Tab("Search", ...) { NavigationStack(path: $tabRouter.searchRoutes) { ... } }
        }
    }
}
```

## Deep Linking

Routes should be `Codable` for state restoration and parseable from URLs:

```swift
extension Route: Codable {}  // Works if all associated values are Codable

struct DeepLinkParser {
    static func parse(_ url: URL) -> [Route]? { ... }  // URLComponents → switch host → [Route]
}

// In RootView:
.onOpenURL { url in
    if let routes = DeepLinkParser.parse(url) { router.routes = routes }
}
```

## State Restoration with SceneStorage

```swift
struct RootView: View {
    @SceneStorage("navigation") private var navigationData: Data?
    @Environment(AppRouter.self) private var router

    var body: some View {
        // ... NavigationStack setup ...
        .task { /* Decode navigationData → router.routes */ }
        .onChange(of: router.routes) { /* Encode → navigationData */ }
    }
}
```

## ❌ Navigation Anti-Patterns

**NavigationLink with destination closure (coupling):**
```swift
// ❌ View knows about its destination
NavigationLink("Details") {
    ItemDetailView(item: item)  // Tight coupling
}

// ✅ Value-based navigation via Router
Button("Details") {
    router.navigate(to: .itemDetail(item))
}
```

**NavigationStack inside NavigationStack:**
```swift
// ❌ Causes unpredictable behavior, duplicate toolbars
NavigationStack {
    NavigationStack {  // NEVER DO THIS
        ContentView()
    }
}
```

**String-based routing:**
```swift
// ❌ No compile-time safety, easy to typo
router.navigate(to: "item-detail-\(item.id)")

// ✅ Typed enum — compiler catches errors
router.navigate(to: .itemDetail(item))
```
