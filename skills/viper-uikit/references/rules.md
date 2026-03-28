# VIPER Architecture — Rules Quick Reference

## Do's — Always Follow

1. **Presenter imports Foundation only — never UIKit.** This is the #1 VIPER rule. If Presenter references UIColor, UIImage, UIFont, UIViewController — it's wrong. Presenter decides WHAT to display, View decides HOW.
2. **View is passive — "as dumb as possible."** View waits for Presenter to give it content. It never asks for data. It forwards lifecycle events (`viewDidLoad` → `presenter.viewDidLoad()`), renders ViewModels, and reports user actions.
3. **Interactor = single use case.** NOT "all business logic for this screen." One Interactor might handle "fetch upcoming items and assign relative due dates." A second handles "mark item complete and update badge count."
4. **Interactor never passes Entities to Presenter.** Map entities to plain response structs before crossing the boundary. "Simple data structures that have no behavior."
5. **All back-references are `weak var` with `AnyObject`-constrained protocols.** Presenter→View, Interactor→Presenter (output), Router→ViewController. If any becomes strong, the module leaks.
6. **Use `ViewState<T>` enum for async data.** Prevents impossible states (loading AND error simultaneously). Never use separate `isLoading` + `error` + `data` booleans.
7. **Builder wires everything before VC enters lifecycle.** All references connected before returning the VC from the factory. Presenter must be set when `viewDidLoad` fires.
8. **Router holds `weak var viewController: UIViewController?`** — obtains nav controller via `.navigationController` property. Never store a strong ref to UINavigationController.
9. **Dependencies injected into Interactor via constructor with protocol types.** Enables testing, prevents singleton coupling.
10. **Always `[weak self]` in Interactor callbacks.** Module may be dismissed during async work. Without weak capture, the dismissed module stays alive.
11. **Pick one main-thread dispatch boundary and stick to it.** Either Interactor always dispatches output to main, OR Presenter always dispatches to main before calling View. Don't mix.
12. **Keep new files <= 400 lines.** Split via extensions. For existing oversized files, log a split task in `refactoring/`.

## Don'ts — Critical Anti-Patterns

### Never: UIKit in Presenter

```swift
// ❌ Couples Presenter to platform, breaks testability
import UIKit
class ProfilePresenter {
    func userLoaded(_ user: User) {
        let color: UIColor = user.isPremium ? .systemGold : .label
        view?.configure(name: user.name, color: color)
    }
}

// ✅ Presenter provides semantic data, View decides rendering
import Foundation
struct ProfileViewModel {
    let name: String
    let isPremium: Bool  // View maps this to UIColor
}
class ProfilePresenter {
    func userLoaded(_ user: User) {
        view?.display(ProfileViewModel(name: user.displayName, isPremium: user.tier == .premium))
    }
}
```

### Never: Business logic in Presenter

```swift
// ❌ God Presenter doing Interactor's job
class OrderPresenter {
    func placeOrder(items: [CartItem]) {
        let subtotal = items.reduce(0) { $0 + $1.price * Double($1.quantity) }
        let tax = subtotal * 0.08875  // business rule in Presenter!
        let discount = subtotal > 100 ? subtotal * 0.1 : 0  // also business rule!
    }
}

// ✅ Business logic in Interactor, Presenter only formats
class OrderInteractor {
    func placeOrder(items: [CartItem]) {
        let total = calculator.calculate(items: items)
        // ...
    }
}
class OrderPresenter: OrderInteractorOutput {
    func orderCalculated(total: Decimal) {
        view?.showTotal(formatCurrency(total))
    }
}
```

### Never: Strong back-references (retain cycle)

```swift
// ❌ RETAIN CYCLE — module never deallocates
class MyPresenter {
    var view: MyViewProtocol!  // STRONG → cycle with View's strong ref to Presenter
}

// ✅ Weak reference with AnyObject-constrained protocol
protocol MyViewProtocol: AnyObject { ... }
class MyPresenter {
    weak var view: MyViewProtocol?  // WEAK → clean deallocation
}
```

### Never: View bypassing Presenter

```swift
// ❌ View talks to Interactor directly
class ProductVC: UIViewController {
    var interactor: ProductInteractor?
    func loadProducts() { interactor?.fetchProducts() }
}

// ✅ View only talks to Presenter
class ProductVC: UIViewController {
    var presenter: ProductPresenterProtocol!
    override func viewDidLoad() {
        super.viewDidLoad()
        presenter.viewDidLoad()
    }
}
```

### Never: Networking in Interactor body

```swift
// ❌ URLSession directly in Interactor — untestable
class UserInteractor {
    func fetchUser(id: String) {
        URLSession.shared.dataTask(with: url) { ... }.resume()
    }
}

// ✅ Service injected via protocol
class UserInteractor {
    private let userService: UserServiceProtocol
    init(userService: UserServiceProtocol) { self.userService = userService }
    func fetchUser(id: String) {
        userService.fetchUser(id: id) { [weak self] result in ... }
    }
}
```

### Never: Segues in VIPER

Segues make it impossible to keep module boundaries clean. Router handles ALL navigation programmatically. "The danger with segues is they make it very difficult to keep the separation between screens intact."

### Never: Force-unwrapped dependencies

```swift
// ❌ Runtime crash when not wired
var service: NetworkService!

// ✅ Constructor injection
private let service: NetworkServiceProtocol
init(service: NetworkServiceProtocol) { self.service = service }
```
