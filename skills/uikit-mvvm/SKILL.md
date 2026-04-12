---
name: mvvm-uikit-architecture
description: "Use for hands-on UIKit MVVM questions: setting up Combine bindings between UIViewController and ViewModel (@Published + sink), extracting business logic from massive ViewControllers step by step, testing ViewModels with XCTestExpectation + Combine publishers, fixing [weak self] retain cycles in sink closures, migrating DispatchQueue/GCD completion handlers to Combine, or replacing reloadData() with DiffableDataSource. Also covers Coordinator navigation patterns, constructor injection, ViewState enum, and incremental MVC-to-MVVM refactoring. Trigger on any UIKit architecture decision — even when the user doesn't mention 'MVVM' explicitly."
metadata:
  version: 1.0.4
---

> **Approach: Production-First Iterative Refactoring** — This skill is built for production enterprise codebases where stability and reviewability matter more than speed. Architecture changes are delivered through iterative refactoring — small, focused PRs (≤200 lines, single concern) tracked in a `refactoring/` directory. Critical safety issues ship first; cosmetic improvements come last.

# UIKit MVVM Architecture (iOS 13+)

Enterprise-grade UIKit MVVM architecture skill. Opinionated: prescribes Combine-bound ViewModels, Coordinator navigation, constructor injection via factories, ViewState enum, DiffableDataSource, and programmatic Auto Layout. Adopts a **production-first iterative refactoring** approach — every pattern is chosen for testability, reviewability, and safe incremental adoption in large teams. UIKit MVVM remains the dominant production architecture for large-scale iOS apps.

## Architecture Layers

```text
View/ViewController  → UIViewController + UIView. Binds to ViewModel via Combine/closures/GCD. Renders state.
ViewModel Layer      → Zero UIKit imports. Exposes ViewState<T>. Uses @Published (Combine) or closures (GCD).
Coordinator Layer    → Manages navigation flow. Creates ViewModels + VCs. Owns UINavigationController.
Repository Layer     → Protocol-based data access. Hides data source details.
Service Layer        → URLSession, persistence. Injected via protocol. May use GCD or async/await.
```

## Quick Decision Trees

### "Should this ViewController have a ViewModel?"

```
Is there business logic, networking, or complex state?
├── YES → Create a ViewModel (see "Which binding mechanism" below for Combine vs closures)
└── NO → Is it a container/flow controller (tab bar, navigation)?
    ├── YES → Coordinator manages it, no ViewModel needed
    └── NO → No ViewModel needed unless it simplifies testing
```

### "Which binding mechanism should I use?"

```text
Is this a legacy codebase with heavy GCD / completion handlers?
├── YES → Is the goal to extract ViewModels first (keep GCD)?
│   ├── YES → Closures / Bindable<T> + GCD in service layer
│   │   └── Upgrade to Combine later (see migration-patterns.md)
│   └── NO → Adopt Combine during extraction
│       └── @Published + sink (production standard)
└── NO → What is the minimum iOS target?
    ├── iOS 13+ → Combine: @Published + sink
    │   └── One-shot events? → PassthroughSubject
    └── < iOS 13 → Closures / Bindable<T> wrapper
```

### "Where do dependencies come from?"

```
ViewModel always receives dependencies via constructor:
  init(service: NetworkServiceProtocol)

Who creates the ViewModel?
├── Coordinator (recommended)
│   └── Coordinator owns factory, creates VM with deps, passes to VC init
├── VC creates it (simpler apps)
│   └── VC receives deps via init, passes to VM init
└── DI Container (large apps, 20+ screens)
    └── Container resolves protocols, coordinator pulls from container
```

### "How should I handle navigation?"

```
Is there more than one navigation flow (auth + main, tabs)?
├── YES → Coordinator pattern with parent/child hierarchy
│   └── AppCoordinator → AuthCoordinator / MainCoordinator → TabCoordinator
└── NO → Single Coordinator wrapping UINavigationController
    └── ViewModel signals navigation via closures, never UIKit imports
```

## Workflows

> **Default workflow**: Analyze & Refactor (below). New screen creation applies the same patterns but from a clean slate. In production enterprise codebases, most work is iterative modernization — not greenfield.

### Workflow: Analyze & Refactor Existing MVC Codebase

**When:** First encounter with a legacy UIKit MVC codebase — the most common enterprise scenario.

1. Scan for anti-patterns using the detection checklist (`references/anti-patterns.md`)
2. Create `refactoring/` directory with per-feature plan files (`references/refactoring-workflow.md`)
3. Write each issue with **full description** (Location, Severity, Problem, Fix) — titles alone get forgotten
4. Categorize issues by severity: 🔴 Critical → 🟡 High → 🟢 Medium
5. Plan Phase 1 PR: fix critical safety issues only (≤200 lines per PR)
6. Execute one PR at a time. New findings go to `refactoring/discovered.md` with full descriptions, NOT into current PR
7. After completing each fix: mark the task `- [x]` and update the Progress table
8. Proceed through phases: Critical → ViewModel extraction → Coordinator → Combine bindings → DI

### Workflow: Create a New Screen

**When:** Building a new feature screen from scratch. Apply enterprise patterns from the start.

1. Define the data model and repository protocol (`references/testing.md` for mock pattern)
2. Create ViewModel: plain class with `private(set) var state: ViewState<T>` — zero UIKit imports (use `@Published` + Combine or closures per the binding mechanism decision tree)
3. Add `// MARK: -` sections: Properties, Init, Actions, Computed Properties
4. Create the ViewController with constructor injection: `init(viewModel: MyViewModel)`
5. Wire Combine bindings in `setupBindings()` called from `viewDidLoad`
6. Build UI programmatically with Auto Layout (`references/layout-approaches.md`)
7. Add Coordinator route and factory method (`references/coordinator-navigation.md`)
8. Create test file with mock repository (`references/testing.md`)

### Workflow: Extract ViewModel from Massive ViewController

**When:** Refactoring an existing MVC screen to MVVM incrementally.

1. Identify all state properties in the VC (data, loading flags, error state)
2. Create ViewModel class — move state properties to `@Published private(set) var`
3. Move business logic methods from VC to VM (networking, validation, formatting)
4. Add Combine `@Published` to VM state, `Set<AnyCancellable>` to VC
5. Replace direct state access in VC with `viewModel.$property.sink` bindings
6. Remove all `import UIKit` from ViewModel — compiler will flag violations
7. Write tests for the ViewModel (now possible since VM has no UIKit dependency)
8. Verify VC only does: bind, render, forward user actions to VM

### Workflow: Introduce Coordinators to Existing MVVM

**When:** Navigation is scattered across ViewControllers. Adding Coordinators incrementally.

1. Start with one flow (e.g., auth flow or a tab's navigation stack)
2. Create Coordinator protocol and AppCoordinator (`references/coordinator-navigation.md`)
3. Move VC creation from VCs/Storyboard segues to Coordinator's factory methods
4. Replace `performSegue` / `pushViewController` calls with ViewModel navigation closures
5. Wire Coordinator as `UINavigationControllerDelegate` for back-button cleanup
6. Add child coordinator lifecycle management (didFinish delegate pattern)
7. Test Coordinator with mock `UINavigationController` (`references/testing.md`)

## Code Generation Rules

<critical_rules>
Whether generating new code or refactoring existing code, every output must be **production-ready and PR-shippable** — small, focused, and testable. ALWAYS:

1. ViewModels import only `Foundation` and `Combine` — never `UIKit`
2. Use `@Published private(set) var` for state properties modified only by the ViewModel
3. Use `ViewState<T>` enum for async data — never separate boolean flags
4. Inject dependencies via constructor with protocol types
5. Bind in `viewDidLoad` using `setupBindings()` — store in `Set<AnyCancellable>`
6. Always `[weak self]` in `sink` closures when stored in `cancellables`
7. Always `.receive(on: DispatchQueue.main)` before UI updates in sink
8. Add `// MARK: -` sections: Properties, Init, Lifecycle, Bindings, Actions
9. Use programmatic Auto Layout — `translatesAutoresizingMaskIntoConstraints = false`
10. Keep every generated file ≤ 400 lines. Extract child VCs or ViewModel extensions when approaching that limit.
11. Before modifying a ViewController, output a brief `<thought>` analyzing its current dependencies and retain cycles.
</critical_rules>

When generating tests, ALWAYS:

1. Use protocol mocks with `var stubbed*` and `var *CallCount` tracking
2. Test through public interface, never test private methods
3. Use `XCTestExpectation` + `sink` + `dropFirst()` for Combine publisher tests
4. Use `await fulfillment(of:)` for async tests — NEVER `wait(for:)` in async contexts. When you write async test code in a response, the **actual code example must call `await fulfillment(of: [expectation], timeout: 2.0)`**, not `wait(for: [expectation], timeout: 2.0)`. Mentioning the modern API only in a note while the code uses `wait(for:)` still hangs the test — it's the classic cooperative-pool deadlock. In XCTestCase this is a synchronous blocking call that cannot pump the queue, so the expectation never fulfills:

```swift
// ❌ WRONG — deadlocks in async test function
func test_load_updates_items() async {
    let exp = expectation(description: "items updated")
    let cancellable = sut.$items.dropFirst().sink { _ in exp.fulfill() }
    await sut.load()
    wait(for: [exp], timeout: 2.0)  // cooperative-pool deadlock
    _ = cancellable
}

// ✅ CORRECT — releases the cooperative thread via await
func test_load_updates_items() async {
    let exp = expectation(description: "items updated")
    let cancellable = sut.$items.dropFirst().sink { _ in exp.fulfill() }
    await sut.load()
    await fulfillment(of: [exp], timeout: 2.0)
    _ = cancellable
}
```
5. Include memory leak detection with `addTeardownBlock { [weak sut] in XCTAssertNil(sut) }`

## Fallback Strategies & Loop Breakers

<fallback_strategies>
When refactoring legacy code, you may encounter stubborn Swift compiler errors. If you fail to fix the same error twice, break the loop:

1. **Combine Type Erasure:** If you get generic type mismatch errors with Combine `AnyPublisher`, append `.eraseToAnyPublisher()` to the pipeline or fall back to closures instead of fighting the type system. Why: Combine's generic types nest deeply (e.g., `Publishers.Map<Publishers.Filter<...>, Output>`), and type erasure is the standard solution.
2. **DiffableDataSource Generics:** If the compiler complains about `Hashable` conformance or type differences in `NSDiffableDataSourceSnapshot`, verify your `CellViewModel` uses a unique `UUID` instead of complex nested generic models. Why: DiffableDataSource compares items by hash — nested models with mutable state produce inconsistent hashes and silent data corruption.
3. **Revert and Restart:** If a ViewController refactor spirals into 50+ compiler errors, stop. Propose reverting the changes and breaking the problem into two smaller phases (e.g., extract networking first, then migrate state). Why: UIKit's implicit dependencies cascade — changing one property often breaks unrelated outlets, delegates, and data sources.
</fallback_strategies>

## Confidence Checks

Before finalizing generated or refactored code, verify ALL:

```
□ No duplicate functionality — searched codebase for existing implementations
□ Architecture adherence — follows patterns already established in the project
□ Naming conventions — matches existing project naming style
□ Import check — ViewModel imports only Foundation + Combine, NOT UIKit
□ ViewState — used for all async data, no separate isLoading/error booleans
□ Combine bindings — [weak self] in every sink, .receive(on: .main) before UI updates
□ DI — dependencies injected via protocol, not accessed via singletons
□ Coordinator — navigation handled by Coordinator, not by VC pushing other VCs
□ Memory management — deinit cancels Tasks, no retain cycles in closures
□ Tests — corresponding test file exists or is created alongside
□ PR scope — changes within defined scope, new findings go to `refactoring/discovered.md`
□ File size — new files ≤ 400 lines; existing oversized files have a split task logged
```

## Companion Skills

> **Before generating async ViewModel or migrating completion handlers:** determine the project's concurrency approach. If unclear from context, ask the user.

| Project's concurrency stack | Companion skill | Apply when |
|---|---|---|
| `async/await`, actors, Swift 6 (migrating or greenfield) | `skills/ios/epam-swift-concurrency/SKILL.md` | Migrating completion handlers, writing async ViewModel methods, actor-based state |
| `DispatchQueue`, `OperationQueue` (staying or auditing existing) | `skills/ios/epam-gcd-operationqueue/SKILL.md` | Reviewing existing queue code, writing queue-based concurrency, thread-safe collections |
| Mixed (GCD stays, new code gets async/await) | Both skills | Apply GCD rules to existing code, concurrency rules to new code |

**If unclear, ask:** "Is the team migrating to Swift Concurrency or keeping GCD/OperationQueue?"

## References

| Reference | When to Read |
|-----------|-------------|
| `references/rules.md` | Do's and Don'ts quick reference: priority rules and critical anti-patterns |
| `references/binding-mechanisms.md` | Combine @Published + sink, closures, async/await, Input/Output pattern, decision matrix |
| `references/coordinator-navigation.md` | Coordinator protocol, hierarchy, memory management, back button handling, deep linking |
| `references/viewcontroller-lifecycle.md` | VC lifecycle, ViewState enum, DiffableDataSource, VC containment, keyboard handling |
| `references/dependency-injection.md` | Constructor injection, Factory pattern, Storyboard DI, Container/Resolver, @Injected wrapper |
| `references/layout-approaches.md` | Programmatic Auto Layout, UIStackView, XIBs, Storyboards, decision criteria |
| `references/testing.md` | Testing Combine publishers, async ViewModels, mocking, memory leak detection, Coordinator tests |
| `references/anti-patterns.md` | Code review detection checklist, severity-ranked UIKit MVVM violations |
| `references/migration-patterns.md` | MVC → MVVM, UIKit → SwiftUI, Combine adoption strategies |
| `references/refactoring-workflow.md` | `refactoring/` directory protocol, per-feature plans, PR sizing, phase ordering |
| `references/file-organization.md` | File size guidelines, ViewModel extension splits, child ViewControllers and subclassing views |
