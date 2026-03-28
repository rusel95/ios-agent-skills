---
name: viper-uikit-architecture
description: "Production-first enterprise skill for UIKit VIPER architecture (iOS 13+). This skill should be used when building new VIPER modules, refactoring legacy MVC/MVVM codebases to VIPER through phased PRs, decomposing god ViewControllers into View-Interactor-Presenter-Entity-Router layers, implementing Router/Wireframe navigation, testing Presenters and Interactors in isolation, fixing retain cycles in VIPER module wiring, migrating VIPER Views to SwiftUI via UIHostingController, or setting up module assembly with dependency injection. Use this skill any time someone works with VIPER architecture, passive Views, single-use-case Interactors, UIKit-free Presenters, or module protocol contracts — even if they don't explicitly mention 'VIPER.'"
metadata:
  version: 1.0.0
---

> **Approach: Production-First Iterative Refactoring** — This skill is built for production enterprise codebases where stability and reviewability matter more than speed. Architecture changes are delivered through iterative refactoring — small, focused PRs (<=200 lines, single concern) tracked in a `refactoring/` directory. AI tools consistently generate VIPER code with retain cycles, UIKit in Presenters, business logic in Presenters instead of Interactors, and strong references where weak ones are required. Every rule here exists to prevent those mistakes.

# UIKit VIPER Architecture (iOS 13+)

Enterprise-grade UIKit VIPER architecture skill. Opinionated: prescribes passive Views (UIViewController IS the View), single-use-case Interactors, UIKit-free Presenters, protocol-isolated module boundaries, enum-based Builders with constructor injection, and optional Coordinator integration for multi-flow apps. VIPER's value is testability at scale — each layer is independently testable behind protocols. The tradeoff is boilerplate (5-15 files per module), which means code generation and consistent conventions are essential.

## Architecture Layers

```text
View (UIViewController) → Passive. Renders what Presenter says. Forwards user actions. Zero decisions.
Presenter              → Traffic cop. Translates Interactor data → ViewModels. Decides WHEN to navigate.
                         Imports Foundation ONLY — never UIKit.
Interactor             → Single use case. Business logic, data orchestration. Independent of UI.
                         Talks to Services/DataManagers via injected protocols.
Entity                 → Plain data structs (PONSOs). No behavior beyond computed properties.
Router/Wireframe       → HOW to navigate. Holds weak ref to ViewController. Performs push/present/dismiss.
Builder/Module         → Factory that assembles all components and wires references. Transient — creates and releases.
```

### Ownership Chain (memorize this — most VIPER bugs are reference direction errors)

```text
UIKit Nav Stack ──strong──> UIViewController (View)
View ──strong──> Presenter
Presenter ──weak──> View          ← MUST be weak (AnyObject protocol)
Presenter ──strong──> Interactor
Presenter ──strong──> Router
Interactor ──weak──> Presenter    ← MUST be weak (output protocol: AnyObject)
Router ──weak──> ViewController   ← MUST be weak (UIKit owns the VC)
Builder ──transient──> all        ← creates, wires, returns VC, releases
```

**If ANY `weak` becomes `strong`, the module NEVER deallocates.** Add `deinit { print("deallocated") }` to every VIPER component during development.

## Quick Decision Trees

### "Where does this code belong?"

```
Is it about HOW something looks on screen (layout, animation, UIKit delegates)?
├── YES → VIEW
Is it about WHAT data to fetch, filter, sort, validate, combine?
├── YES → INTERACTOR (use case / business logic)
Is it about HOW to FORMAT data for display, or WHICH view state to show?
├── YES → PRESENTER (date formatting, string composition, ViewState mapping)
Is it about HOW to navigate to another screen?
├── YES → ROUTER (push, present, dismiss, transitions)
Is it a plain data container?
├── YES → ENTITY (struct, no logic beyond computed properties)
Is it about HOW to talk to a network/database?
└── YES → SERVICE / DATA MANAGER (external to VIPER, injected into Interactor)
```

### "Should this screen use full VIPER?"

```
Is it a complex feature (Feed, Search, Editor, Checkout)?
├── YES → Full VIPER module (all 5 layers + Builder)
Is it a simple form (Login, Settings edit)?
├── YES → VIPER-lite (skip Interactor if no API/business rules, Presenter talks to Service directly)
Is it static content (About, Legal)?
├── YES → Plain ViewController or MVVM — VIPER is overkill
Is it a reusable UI component (Cell, Widget)?
├── YES → Custom UIView, NOT a VIPER module
Is it a background service (API, Storage)?
└── YES → Service class injected into Interactors — NOT a VIPER module
```

### "How should child module communicate results back?"

```
One-time result return (picker, form)?
├── Simple result → Closure callback on Builder
├── Complex/multiple → Delegate protocol (ModuleOutput)
Ongoing state sync between modules?
├── Known consumer → Shared service with delegate/closure
├── Unknown/multiple → NotificationCenter (app-wide only)
Forward-only data (navigating to detail)?
└── Pass via Router → Builder → Presenter (IDs or DTOs)
```

### "Who dismisses?"

```
The PRESENTING module's Router dismisses.
Presented module notifies via delegate → presenting Presenter receives → presenting Router dismisses.
The presented module NEVER calls dismiss on itself — presenting module must react to closure.
```

## Workflows

> **Default workflow**: Analyze & Refactor (below). New module creation applies the same patterns from a clean slate. In production enterprise codebases, most work is iterative modernization — not greenfield.

### Workflow: Analyze & Refactor Existing MVC Codebase to VIPER

**When:** First encounter with a legacy UIKit MVC or poorly-structured codebase. The most common enterprise scenario.

1. Scan for anti-patterns using the detection checklist (`references/anti-patterns.md`)
2. Create `refactoring/` directory with per-feature plan files (`references/refactoring-workflow.md`)
3. Write each issue with **full description** (Location, Severity, Problem, Fix) — titles alone get forgotten
4. Categorize issues by severity: Critical → High → Medium
5. Plan Phase 1 PR: fix critical safety issues only (retain cycles, crashes) — <=200 lines per PR
6. Execute one PR at a time. New findings go to `refactoring/discovered.md` with full descriptions
7. After completing each fix: mark the task `- [x]` and update the Progress table
8. Proceed through phases: Critical fixes → Extract Interactors → Extract Presenters → Add Routers → Wire Builders → Add Tests

### Workflow: Create a New VIPER Module

**When:** Building a new feature screen from scratch. Apply all patterns from the start.

1. Define the module contract — all 6 protocols in `{Module}Contract.swift` (`references/module-contracts.md`)
2. Create Entity structs in the shared domain layer (NOT inside the module folder)
3. Create Interactor with injected service protocol — implements use-case logic (`references/interactor-patterns.md`)
4. Create Presenter: imports Foundation only, translates Interactor output to ViewModels, decides ViewState (`references/presenter-patterns.md`)
5. Create ViewController (View): passive, binds to Presenter, forwards lifecycle events (`references/view-patterns.md`)
6. Create Router: weak ref to VC, performs UIKit navigation (`references/router-navigation.md`)
7. Create Builder (enum-based factory): assembles all components, wires references, returns VC (`references/module-assembly.md`)
8. Write tests: Interactor (highest priority), then Presenter, then Router (`references/testing.md`)

### Workflow: Extract VIPER Module from Massive ViewController

**When:** Incrementally migrating one screen from MVC to VIPER.

1. Identify all state and business logic in the VC — these move to Interactor
2. Identify all formatting, view state decisions — these move to Presenter
3. Create the module contract protocols first (forces you to define boundaries)
4. Extract Interactor: move networking/validation/filtering logic, inject services via protocol
5. Extract Presenter: move formatting and state mapping, add `weak var view` protocol ref
6. Reduce VC to passive View: only lifecycle forwarding, UI rendering, user action forwarding
7. Create Router: extract all navigation code from VC (push, present, segue replacements)
8. Create Builder: wire everything, replace old VC instantiation with `Module.build()`
9. Verify: `deinit` fires on ALL components when navigating away, zero UIKit in Presenter

### Workflow: Introduce Coordinators to VIPER

**When:** Multi-flow navigation (auth + main, tabs) or deep linking requirements exceed per-module Routers.

1. Define Coordinator protocol: `start()`, `childCoordinators: [Coordinator]` (`references/coordinator-integration.md`)
2. Start with one flow (e.g., auth flow) — don't coordinate everything at once
3. Coordinators manage FLOWS (multi-screen sequences). Routers manage SINGLE transitions
4. VIPER Router delegates "cross-flow" navigation to its parent Coordinator
5. Module Builder receives coordinator-provided dependencies
6. Wire `UINavigationControllerDelegate` for back-button cleanup of child coordinators

## Code Generation Rules

<critical_rules>
Whether generating new code or refactoring existing code, every output must be **production-ready and PR-shippable** — small, focused, and testable. ALWAYS:

1. Presenter imports ONLY Foundation — never UIKit. This is the single most violated rule in VIPER.
2. View protocol methods express content at a higher abstraction than UIKit widgets: `showUserProfile(viewModel:)`, NOT `setLabelText(_:)`
3. View is passive: forwards lifecycle events to Presenter, renders what Presenter says, makes zero decisions
4. Interactor represents a SINGLE USE CASE — not "all business logic for this screen"
5. Interactor NEVER passes Entities to Presenter — map to plain response structs first
6. All back-references use `weak var` with `AnyObject`-constrained protocols: Presenter→View, Interactor→Presenter(output), Router→VC
7. Use `ViewState<T>` enum for async data — never separate boolean flags
8. Builder/Module assembles all components and wires references BEFORE VC enters view lifecycle
9. Router holds `weak var viewController: UIViewController?` — UIKit owns the VC
10. Dependencies injected into Interactor via constructor with protocol types — never singletons
11. Always `[weak self]` in Interactor callbacks/closures — module may be dismissed during async work
12. All UI updates dispatch to main queue — pick one consistent boundary (Interactor output or Presenter→View)
13. Keep every generated file <= 400 lines. Split via extensions or child VCs when approaching.
14. Before modifying a VIPER module, output a brief `<thought>` analyzing ownership chain and retain cycle risks.
</critical_rules>

When generating tests, ALWAYS:

1. Test Interactor first (pure business logic, no UI), then Presenter, then Router
2. Use protocol mocks with `var stubbed*` and `var *CallCount` tracking
3. Include memory leak detection: `addTeardownBlock { [weak sut] in XCTAssertNil(sut) }`
4. Test the full communication chain: View action → Presenter → Interactor → Presenter callback → View display
5. Router tests need strong VC reference in the test (Router holds weak ref, so VC would dealloc otherwise)

## Fallback Strategies & Loop Breakers

<fallback_strategies>
When refactoring legacy code to VIPER, you may encounter stubborn issues. If you fail to fix the same error twice, break the loop:

1. **Retain cycle won't break:** Verify ALL 3 weak references (Presenter→View, Interactor→Presenter, Router→VC). Check protocol has `AnyObject` constraint. Use Xcode Debug Memory Graph. Why: missing even one `weak` creates an invisible retain cycle — the module never deallocates, leaking memory on every navigation.
2. **Module never deallocates:** Add `deinit` to ALL 5 components. Navigate away. Missing log = that component is retained. Walk the reference chain from that component.
3. **Massive protocol file (30+ methods):** Split into role-based protocols: `ViewEventHandler`, `ItemActions`, `SearchHandler`. Presenter conforms to all; mocks only to what they test. Why: one monolithic protocol forces mocks to stub 30+ methods even when testing one behavior.
4. **Storyboard segue entanglement:** Don't try to incrementally replace segues. Replace ALL navigation for one flow at once with Router + Builder. Why: half-segue/half-Router creates two navigation systems that fight each other, making bugs nearly impossible to reproduce.
5. **UITabBarController timing:** `viewDidLoad` fires BEFORE init completes for tab children. Wire Presenter in Builder before returning VC, NOT in viewDidLoad. Why: if Presenter wiring happens in viewDidLoad, the Presenter receives lifecycle events before it has its dependencies set.
6. **Revert threshold:** If extracting a VIPER module from MVC creates 50+ compiler errors, stop. Revert and break into two smaller phases (e.g., extract networking first into Service, THEN extract Interactor).
</fallback_strategies>

## Confidence Checks

Before finalizing generated or refactored VIPER code, verify ALL:

```
[ ] Presenter does NOT import UIKit — only Foundation (and Combine if using publishers)
[ ] All cross-layer references use protocols, not concrete types
[ ] View only communicates with Presenter (never Interactor/Router directly)
[ ] Business logic in Interactor, presentation logic in Presenter — not mixed
[ ] Networking/persistence in injected services, not raw in Interactor
[ ] Router holds weak reference to VC
[ ] Interactor holds weak reference to Presenter (output)
[ ] Presenter holds weak reference to View
[ ] All weak-referenced protocols constrained to AnyObject
[ ] All Interactor callbacks dispatch to main thread before reaching View
[ ] ViewState<T> used for async data — no separate boolean flags
[ ] Module Builder creates all components before VC enters lifecycle
[ ] Dependencies injected via constructor with protocol types
[ ] Entities shared across modules live outside module folders
[ ] deinit added to all components during development
[ ] Tests exist for Interactor and Presenter
[ ] File size — new files <= 400 lines
[ ] PR scope — changes within defined scope, discoveries logged in refactoring/discovered.md
```

## Companion Skills

> **Before generating async Interactor or migrating completion handlers:** determine the project's concurrency approach. If unclear from context, ask the user.

| Project's concurrency stack | Companion skill | Apply when |
|---|---|---|
| `async/await`, actors, Swift 6 | `skills/ios/swift-concurrency/SKILL.md` | Migrating completion handlers, writing async Interactors, actor-based state |
| `DispatchQueue`, `OperationQueue` | `skills/ios/gcd-operationqueue/SKILL.md` | Reviewing existing queue code, thread-safe Interactor state |
| Mixed (GCD stays, new code gets async/await) | Both skills | Apply GCD rules to existing code, concurrency rules to new code |
| Comprehensive testing beyond VIPER | `skills/ios/ios-testing/SKILL.md` | See `references/viper-testing.md` for VIPER-specific patterns |
| Security audit | `skills/ios/ios-security-audit/SKILL.md` | Auditing Keychain usage, network security in VIPER apps |

## References

> **Core references** (read for every VIPER task): `rules.md`, `module-contracts.md`, `memory-management.md`. Then consult the specific reference based on which layer you're working with.

| Reference | When to Read |
|-----------|-------------|
| **Understanding VIPER** | |
| `rules.md` | Do's and Don'ts quick reference: priority rules and critical anti-patterns |
| `module-contracts.md` | Protocol design: 6 protocols per module, naming conventions, AnyObject constraints |
| `memory-management.md` | Ownership chain, retain cycle debugging, closure captures, deallocation verification |
| `anti-patterns.md` | AI-specific mistakes, severity-ranked violations, detection checklist |
| **Building Modules** | |
| `view-patterns.md` | Passive View rules, lifecycle forwarding, UITableView/UICollectionView data flow |
| `presenter-patterns.md` | UIKit-free Presenter, ViewState mapping, Entity→ViewModel translation |
| `interactor-patterns.md` | Single use case, service injection, Entity boundaries, async/Combine patterns |
| `router-navigation.md` | Weak VC reference, push/present/dismiss, deep linking, Coordinator delegation |
| `module-assembly.md` | Builder/Factory patterns, dependency injection, wiring order, storyboard vs programmatic |
| **Testing & Migration** | |
| `testing.md` | Interactor/Presenter/Router testing, mock patterns, memory leak assertions, snapshot testing |
| `coordinator-integration.md` | When Routers aren't enough, Coordinator hierarchy, VIPER+Coordinator wiring |
| `migration-patterns.md` | MVC→VIPER extraction, VIPER→SwiftUI migration via UIHostingController adapter |
| **Enterprise** | |
| `enterprise-patterns.md` | Error propagation chain, ViewState management, analytics decoration, thread safety |
| `refactoring-workflow.md` | `refactoring/` directory protocol, per-feature plans, PR sizing, phase ordering |
