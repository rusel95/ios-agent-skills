# Coordinator Integration with VIPER

## How to Use This Reference

Read this when VIPER Routers aren't enough for your navigation needs — multi-flow apps, deep linking, or complex tab/modal combinations.

---

## When to Add Coordinators

```
Simple app (<10 screens): VIPER Routers handle everything
Medium app: VIPER Routers + AppRouter for deep linking
Large app with complex flows: VIPER Routers + Coordinators + AppRouter
```

**Coordinators manage FLOWS** (multi-screen sequences like auth, onboarding, checkout). **Routers manage SINGLE transitions** (push detail, present modal).

## Coordinator Protocol

```swift
protocol Coordinator: AnyObject {
    var childCoordinators: [Coordinator] { get set }
    var navigationController: UINavigationController { get }
    func start()
}

extension Coordinator {
    func addChild(_ coordinator: Coordinator) {
        childCoordinators.append(coordinator)
    }

    func removeChild(_ coordinator: Coordinator) {
        childCoordinators.removeAll { $0 === coordinator }
    }
}
```

## Coordinator Hierarchy

```text
AppCoordinator (owns window)
├── AuthCoordinator (login, signup, forgot password)
│   └── LoginModule, SignupModule, ForgotPasswordModule
├── MainCoordinator (tab bar)
│   ├── HomeCoordinator (home tab)
│   │   └── HomeModule, DetailModule, SettingsModule
│   └── ProfileCoordinator (profile tab)
│       └── ProfileModule, EditProfileModule
└── OnboardingCoordinator (first launch)
    └── WelcomeModule, PermissionsModule
```

## How VIPER Routers Delegate to Coordinators

Router handles intra-module navigation (push detail). For cross-flow navigation (e.g., "user must log in"), Router delegates to Coordinator:

```swift
class HomeRouter: HomeRouterInput {
    weak var viewController: UIViewController?
    weak var coordinator: HomeCoordinatorDelegate?

    func navigateToDetail(itemId: String) {
        // Intra-flow — Router handles
        let detailVC = ItemDetailModule.build(itemId: itemId)
        viewController?.navigationController?.pushViewController(detailVC, animated: true)
    }

    func requestAuthentication() {
        // Cross-flow — delegate to Coordinator
        coordinator?.homeModuleRequiresAuthentication()
    }
}
```

## Coordinator as Module Delegate

Coordinators implement module output protocols to receive results:

```swift
class CheckoutCoordinator: Coordinator, CartModuleOutput, PaymentModuleOutput {
    var childCoordinators: [Coordinator] = []
    let navigationController: UINavigationController

    func start() {
        let cartVC = CartModule.build(output: self)
        navigationController.pushViewController(cartVC, animated: true)
    }

    // CartModuleOutput
    func cartDidRequestCheckout(items: [CartItem]) {
        let paymentVC = PaymentModule.build(items: items, output: self)
        navigationController.pushViewController(paymentVC, animated: true)
    }

    // PaymentModuleOutput
    func paymentDidComplete(orderId: String) {
        let confirmVC = ConfirmationModule.build(orderId: orderId)
        navigationController.pushViewController(confirmVC, animated: true)
    }

    func paymentDidCancel() {
        navigationController.popViewController(animated: true)
    }
}
```

## Child Coordinator Lifecycle

Remove child coordinators when their flow completes:

```swift
class MainCoordinator: Coordinator {
    func showAuth() {
        let authCoordinator = AuthCoordinator(navigationController: navigationController)
        authCoordinator.onFinish = { [weak self] in
            self?.removeChild(authCoordinator)
            self?.showHome()
        }
        addChild(authCoordinator)
        authCoordinator.start()
    }
}
```

**Back button cleanup:** Use `UINavigationControllerDelegate` to detect pop:

```swift
extension MainCoordinator: UINavigationControllerDelegate {
    func navigationController(_ nav: UINavigationController, didShow vc: UIViewController, animated: Bool) {
        guard let fromVC = nav.transitionCoordinator?.viewController(forKey: .from),
              !nav.viewControllers.contains(fromVC) else { return }
        // fromVC was popped — clean up its coordinator if needed
        cleanupCoordinator(for: fromVC)
    }
}
```

## Module Builder Receives Coordinator Dependencies

```swift
enum ProfileModule {
    static func build(
        coordinator: ProfileCoordinatorDelegate?,
        container: DependencyContainer
    ) -> UIViewController {
        let view = ProfileViewController()
        let interactor = ProfileInteractor(
            userService: container.resolve(UserServiceProtocol.self)
        )
        let presenter = ProfilePresenter()
        let router = ProfileRouter()
        router.coordinator = coordinator  // weak ref

        // ... wire everything
        return view
    }
}
```
