# Memory Management — Ownership Chain & Retain Cycles

## How to Use This Reference

Read this when debugging memory leaks, reviewing VIPER wiring, or creating deallocation tests. VIPER's most common production bugs are retain cycles from incorrect reference directions.

---

## The Canonical Ownership Chain

```text
UIKit Nav Stack ──strong──> UIViewController (View)
View ──strong──> Presenter
Presenter ──weak──> View          ← AnyObject protocol required
Presenter ──strong──> Interactor
Presenter ──strong──> Router
Interactor ──weak──> Presenter    ← AnyObject protocol (output)
Router ──weak──> ViewController   ← UIKit owns it
Builder ──transient──> all        ← creates, wires, releases
```

## Deallocation Chain

When a UIViewController is popped/dismissed:
1. UIKit releases VC from nav stack
2. View's strong ref to Presenter released → Presenter's retain count drops
3. Presenter's strong refs to Interactor and Router released → they dealloc
4. Interactor's weak ref to Presenter already nil → clean
5. All components deallocate cleanly

**If ANY bidirectional reference is strong, this chain BREAKS and nothing deallocates.**

## Protocol Constraint Requirement

Protocols used for `weak var` references MUST be constrained to `AnyObject`:

```swift
// ✅ CORRECT — can be weak
protocol InteractorOutputProtocol: AnyObject {
    func didFetchData(_ data: [Item])
}
class Interactor {
    weak var output: InteractorOutputProtocol?
}

// ❌ WRONG — can't be weak, defaults to strong → RETAIN CYCLE
protocol InteractorOutputProtocol {  // no AnyObject
    func didFetchData(_ data: [Item])
}
class Interactor {
    var output: InteractorOutputProtocol?  // compiler won't allow weak
}
```

## Closure-Based Retain Cycles

Always `[weak self]` in Interactor callbacks:

```swift
// ❌ WRONG — closure captures self strongly
func findUpcomingItems() {
    dataManager.todoItems { todoItems in
        self.output?.foundUpcomingItems(self.process(todoItems))
    }
}

// ✅ CORRECT
func findUpcomingItems() {
    dataManager.todoItems { [weak self] todoItems in
        guard let self = self else { return }
        self.output?.foundUpcomingItems(self.process(todoItems))
    }
}
```

## The Dismissed-Module-With-Pending-Callback Bug

User navigates to Module A. Interactor starts network request. User navigates BACK before request completes.

**With `[weak self]`:** Interactor deallocated. Callback fires, `self` is nil, guard-let exits. No crash. Clean.

**Without `[weak self]`:** Interactor stays alive (retained by closure). Calls `output?.foundItems(...)`. If output (Presenter) also alive because Interactor retains it strongly → Presenter tries to update View that no longer exists → crash or phantom updates + memory leak.

## Development Verification

Add `deinit` to EVERY VIPER component during development:

```swift
deinit {
    #if DEBUG
    print("[VIPER] \(String(describing: type(of: self))) deallocated")
    #endif
}
```

Navigate away. If you don't see deinit logs for ALL components → retain cycle.

## Debugging Tools

1. **Xcode Debug Memory Graph** (most powerful): Shows reference graph between objects. Filter by module name.
2. **Instruments > Allocations**: Filter by module name prefix. Navigate away — persistent count should drop.
3. **Instruments > Leaks**: Shows retain cycle graph.
4. **Zombie Objects** (scheme diagnostic): Catches EXC_BAD_ACCESS from unowned references.

## Test for Leaks

```swift
func test_module_doesNotLeakMemory() {
    var view: OrderListViewController? = OrderListModule.build() as? OrderListViewController
    weak var weakView = view
    weak var weakPresenter = view?.presenter as? OrderListPresenter
    weak var weakInteractor = weakPresenter?.interactor as? OrderListInteractor

    view = nil

    XCTAssertNil(weakView, "View leaked!")
    XCTAssertNil(weakPresenter, "Presenter leaked!")
    XCTAssertNil(weakInteractor, "Interactor leaked!")
}
```

## Common Leak Sources

| Leak Source | Detection | Fix |
|------------|-----------|-----|
| Presenter→View is strong | View never deinits | Change to `weak var view` |
| Interactor→Presenter is strong | Presenter never deinits | Change output to `weak var` |
| Router→VC is strong | VC never deinits | Change to `weak var viewController` |
| Missing AnyObject on protocol | Compiler allows strong-only | Add `: AnyObject` to protocol |
| Closure captures self strongly | Interactor/Presenter never deinits | Add `[weak self]` |
| Timer/NotificationCenter | Component stays alive | Remove observer in deinit |
| Combine sink without `[weak self]` | VC/Presenter never deinits | Add `[weak self]` to sink |
