# Anti-Patterns Detection & Fixes

## How to Use

When reviewing existing VIPER code or AI-generated VIPER code, check each section below. For every violation found, add it to the feature's `refactoring/` plan with severity and recommended fix.

## Severity Levels

- **🔴 Critical**: Retain cycles, crashes, memory leaks. Fix immediately.
- **🟡 High**: Testability blockers, architecture violations. Fix in next sprint.
- **🟢 Medium**: Code quality, maintainability. Fix opportunistically.

---

<critical_anti_patterns>
## 🔴 Critical

### C1: UIKit in Presenter

**Problem**: Presenter imports UIKit — references UIColor, UIImage, UIFont, UIViewController. Breaks testability and platform independence. AI tools do this constantly.

```swift
// ❌ import UIKit in Presenter
// ✅ import Foundation only. Use semantic ViewModels.
```

### C2: Strong back-references (retain cycle)

**Problem**: Presenter→View, Interactor→Presenter, or Router→VC is strong. Module NEVER deallocates. Most common production VIPER bug.

**Detection**: Add `deinit` logs to all components. Navigate away. Missing logs = leak.

### C3: Missing AnyObject on weak-reference protocols

**Problem**: Protocol not constrained to AnyObject. Swift defaults to strong reference. Silent retain cycle.

```swift
// ❌ protocol ViewInput { }  → can't be weak
// ✅ protocol ViewInput: AnyObject { }  → weak var view: ViewInput?
```

### C4: God Presenter — business logic in Presenter

**Problem**: Presenter does filtering, sorting, validation, calculations. These are Interactor responsibilities. Test: "If the business rule changes, should the Presenter change?" If yes → wrong layer.

```swift
// ❌ Presenter calculating tax, applying discounts
// ✅ Interactor owns business rules, Presenter only formats results
```

### C5: Missing [weak self] in Interactor closures

**Problem**: Network callback captures self strongly. Module dismissed during request → Interactor stays alive → Presenter tries to update deallocated View.

### C6: UI updates from background thread

**Problem**: Interactor callback fires on background thread. Presenter forwards to View without dispatching to main. Purple warnings, crashes.

**Fix**: Pick one boundary and always dispatch: either Interactor output always dispatches to main, or Presenter always dispatches before calling View.

### C7: View bypassing Presenter

**Problem**: View talks directly to Interactor or Router. Breaks the communication chain. VIPER law: View ↔ Presenter only.

### C8: Force-unwrapped dependencies

**Problem**: `var service: NetworkService!` — crash if not wired. Use constructor injection.

### C9: Networking code directly in Interactor

**Problem**: URLSession.shared.dataTask inside Interactor — untestable. Services are external dependencies injected via protocol.
</critical_anti_patterns>

---

## 🟡 High

### H1: Massive protocol files (30+ methods)

**Problem**: Single protocol with 30+ methods. Impossible to mock partially. **Fix**: Split into role-based protocols.

### H2: Concrete types between layers (no protocols)

**Problem**: `var view: LoginViewController` instead of `weak var view: LoginViewInput?`. Untestable.

### H3: Entities passed directly to View

**Problem**: Interactor returns domain entities to Presenter, Presenter passes them to View. Leaks domain model into UI layer. **Fix**: Map to ViewModels at the Presenter boundary.

### H4: Router holding strong references

**Problem**: Router stores `var view: ProfileViewController` strongly instead of `weak var viewController: UIViewController?`.

### H5: No module Builder/Factory

**Problem**: Components created ad-hoc in ViewControllers or AppDelegate. Wiring scattered, inconsistent, easy to miss weak references.

### H6: Segues in VIPER

**Problem**: Storyboard segues bypass Router entirely. Makes module boundaries impossible to maintain.

### H7: Singleton abuse

**Problem**: Interactor accesses `ServiceManager.shared` instead of injected protocol. Hidden dependency, untestable.

### H8: Module state after backgrounding

**Problem**: No refresh on `UIApplication.willEnterForegroundNotification`. Stale data after app resume.

### H9: Presenter as ViewState source of truth for business data

**Problem**: Presenter caches domain data (order lists, user profiles) instead of just presentation state. Interactor should own business state; Presenter only holds current ViewState and ephemeral UI state (selected index, pagination cursor).

---

## 🟢 Medium

- **M1**: Missing `deinit` logs during development — can't verify deallocation
- **M2**: No `// MARK: -` sections in VIPER files
- **M3**: Interactor methods not returning via Output protocol (using closures instead) — inconsistent
- **M4**: View making formatting decisions (date formatting in VC instead of Presenter)
- **M5**: Fat ViewModels with computed properties — should be plain data
- **M6**: Module files scattered across project — should be in `Modules/{ModuleName}/` folder
- **M7**: Manual `reloadData()` instead of DiffableDataSource (iOS 13+)

---

<detection_checklist>
## Detection Checklist

1. [ ] **Presenter UIKit-free**: imports only Foundation (+ Combine if needed)?
2. [ ] **Ownership chain correct**: Presenter→View weak, Interactor→Presenter weak, Router→VC weak?
3. [ ] **AnyObject constraints**: all weak-referenced protocols constrained to AnyObject?
4. [ ] **View passive**: only forwards events, renders ViewModels, makes zero decisions?
5. [ ] **Business logic in Interactor**: not in Presenter or View?
6. [ ] **Entities stay in Interactor**: Presenter receives plain response structs?
7. [ ] **No direct layer bypass**: View only talks to Presenter, never Interactor/Router?
8. [ ] **[weak self] in all closures**: Interactor callbacks, Combine sinks, GCD blocks?
9. [ ] **Main thread UI**: all View updates dispatched to main?
10. [ ] **Protocol abstractions**: all cross-layer references use protocols?
11. [ ] **DI via constructor**: no singletons or service locators?
12. [ ] **Builder wires before lifecycle**: all refs set before viewDidLoad?
13. [ ] **Router weak VC**: `weak var viewController: UIViewController?`?
14. [ ] **No segues**: Router handles all navigation programmatically?
15. [ ] **deinit fires**: all 5 components log deallocation on navigation?
16. [ ] **File size**: new <= 400 lines, existing > 1000 flagged?
17. [ ] **Tests exist**: Interactor and Presenter test files present?
</detection_checklist>
