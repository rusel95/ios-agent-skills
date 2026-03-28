# Router/Wireframe — Navigation Patterns

## How to Use This Reference

Read this when creating or reviewing Router code, handling navigation between modules, or integrating deep linking.

---

## Core Responsibility

Router knows HOW to navigate. Presenter knows WHEN. Router:
- Holds `weak var viewController: UIViewController?` — UIKit owns the VC
- Obtains nav controller via `viewController?.navigationController`
- Performs push, present, dismiss
- Creates destination modules via their Builders
- Is the right place for `UIApplication.shared.open()` and `UIActivityViewController`

## Basic Router

```swift
class OrderListRouter: OrderListRouterInput {
    weak var viewController: UIViewController?

    func navigateToOrderDetail(orderId: String) {
        let detailVC = OrderDetailModule.build(orderId: orderId)
        viewController?.navigationController?.pushViewController(detailVC, animated: true)
    }

    func presentAddOrder(delegate: AddOrderModuleOutput?) {
        let addVC = AddOrderModule.build(output: delegate)
        let nav = UINavigationController(rootViewController: addVC)
        viewController?.present(nav, animated: true)
    }

    func dismissAddOrder() {
        viewController?.dismiss(animated: true)
    }
}
```

## The "Who Dismisses?" Rule

**The PRESENTING module's Router dismisses.** The presented module notifies via delegate that it wants to close. The presenting module's Router performs the actual dismissal.

```swift
// ✅ CORRECT
class ListPresenter: AddModuleOutput {
    func addModuleDidCancel() {
        router.dismissAddModule()
    }
    func addModule(didSave item: Item) {
        interactor.refreshList()
        router.dismissAddModule()
    }
}
class ListRouter {
    func dismissAddModule() {
        viewController?.dismiss(animated: true)
    }
}

// ❌ WRONG — presented module dismisses itself
class AddPresenter {
    func didTapCancel() {
        // Bad: presenting module can't react to dismissal
        view?.dismiss(animated: true)
    }
}
```

## Navigation Safety Guards

Prevent double-navigation and stack corruption:

```swift
class BaseRouter {
    weak var viewController: UIViewController?
    private var isNavigating = false

    func safePush(_ vc: UIViewController) {
        guard !isNavigating,
              let nav = viewController?.navigationController,
              nav.topViewController === viewController else { return }
        isNavigating = true
        nav.pushViewController(vc, animated: true)
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) { [weak self] in
            self?.isNavigating = false
        }
    }

    func safePresent(_ vc: UIViewController) {
        guard viewController?.presentedViewController == nil else { return }
        viewController?.present(vc, animated: true)
    }
}
```

## Passing Data Between Modules

**Forward data (A → B):** Pass through Router → Builder → Presenter.

```swift
class PostListRouter {
    func showDetail(postId: Int) {
        let detailVC = PostDetailModule.build(postId: postId)
        viewController?.navigationController?.pushViewController(detailVC, animated: true)
    }
}
```

**Backward data (B → A):** Use delegate protocol.

```swift
protocol ItemPickerModuleOutput: AnyObject {
    func itemPicker(didSelect item: Item)
    func itemPickerDidCancel()
}

// Parent Presenter implements the output protocol
class OrderPresenter: ItemPickerModuleOutput {
    func itemPicker(didSelect item: Item) {
        view?.updateSelectedItem(item.name)
    }
    func itemPickerDidCancel() {
        router.dismissItemPicker()
    }
}
```

## Deep Linking

Deep linking should NOT be handled by individual module Routers. Use a centralized handler:

```swift
class DeepLinkHandler {
    private let window: UIWindow

    func handle(url: URL) {
        guard let intent = NavigationIntent(url: url) else { return }

        switch intent {
        case .orderDetail(let id):
            let rootNav = window.rootViewController as? UINavigationController
            // Pop to root, then push order list, then push detail
            rootNav?.popToRootViewController(animated: false)
            let listVC = OrderListModule.build()
            rootNav?.pushViewController(listVC, animated: false)
            let detailVC = OrderDetailModule.build(orderId: id)
            rootNav?.pushViewController(detailVC, animated: true)
        }
    }
}
```

## Edge Cases

- **iOS 13+ modal `.automatic`**: `viewWillAppear` of presenting VC NOT called on swipe-dismiss. Force `.fullScreen` or implement `UIAdaptivePresentationControllerDelegate`.
- **Interactive pop gesture**: Router not notified when user swipes back. Use `UINavigationControllerDelegate.didShow` to sync state.
- **iPad SplitView**: Use `show(_:sender:)` instead of `pushViewController` for adaptive layout.
- **Tab bar children**: Each Router references its own VC. Navigation resolved through `viewController?.navigationController`.
