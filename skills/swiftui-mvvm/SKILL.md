---
name: swiftui-mvvm-architecture
description: "Use this skill when working with SwiftUI ViewModels — creating, refactoring, or testing them. Triggers for: setting up a ViewModel for a SwiftUI screen, extracting logic from a View into a ViewModel, migrating from ObservableObject to @Observable, modeling async state (instead of separate Bool flags like isLoading/hasError), injecting dependencies into ViewModels, writing unit tests for @Observable ViewModels, NavigationStack/Router setup, or any question about SwiftUI app architecture. Also use when a SwiftUI View imports too much business logic, when someone asks how to structure a SwiftUI screen 'the modern way,' or when they ask about @State/@Bindable ownership, ViewState patterns, or why their ViewModel shouldn't import SwiftUI."
metadata:
  version: 1.0.2
---

> **Approach: Production-First Iterative Refactoring** — This skill is built for production enterprise codebases where stability and reviewability matter more than speed. Architecture changes are delivered through iterative refactoring — small, focused PRs (≤200 lines, single concern) tracked in a `refactoring/` directory. Critical safety issues ship first; cosmetic improvements come last.

# SwiftUI MVVM Architecture (iOS 17+)

Enterprise-grade SwiftUI MVVM architecture skill. Opinionated: prescribes @Observable ViewModels, Router navigation, constructor injection, ViewState enum, and Repository-based networking. Adopts a **production-first iterative refactoring** approach — every pattern is chosen for testability, reviewability, and safe incremental adoption in large teams. For non-architectural SwiftUI API guidance (animations, modern API replacements, Liquid Glass), use a general SwiftUI skill instead.

## Architecture Layers

```
View Layer         → SwiftUI Views. Declarative UI only. Owns ViewModel via @State.
ViewModel Layer    → @Observable @MainActor final class. Exposes ViewState<T>.
Repository Layer   → Protocol-based data access. Hides data source details.
Service Layer      → URLSession, persistence. Injected via protocol.
```

## Quick Decision Trees

### "Should this View have a ViewModel?"

```
Is there business logic, networking, or complex state?
├── YES → Create @Observable ViewModel
└── NO → Is it a reusable UI component (button, card, cell)?
    ├── YES → Plain struct with data parameters, NO ViewModel
    └── NO → No ViewModel needed unless it simplifies testing
```

### "How should I own this ViewModel?"

```
Does THIS view create the ViewModel?
├── YES → @State private var viewModel = MyViewModel()
└── NO → Does the view need $ bindings to ViewModel properties?
    ├── YES → @Bindable var viewModel: MyViewModel
    └── NO → let viewModel: MyViewModel (plain property)
```

### "Where do dependencies come from?"

```
ViewModel always receives dependencies via constructor:
  init(repository: ItemRepositoryProtocol)

How does the View get the dependency to pass?
├── Shared service (used across many screens)
│   └── Register via @Entry in EnvironmentValues
│       View reads @Environment(\.repo), passes to VM init
├── Screen-specific dependency (passed by parent)
│   └── View receives it as init parameter, passes to VM init
└── Outside view hierarchy (background service, deep utility)
    └── @Injected property wrapper (legacy/convenience only)
```

## Workflows

> **Default workflow**: Analyze & Refactor (below). New screen creation applies the same patterns but from a clean slate. In production enterprise codebases, most work is iterative modernization — not greenfield.

### Workflow: Analyze & Refactor Existing Codebase

**When:** First encounter with a legacy SwiftUI codebase — the most common enterprise scenario.

1. Scan for anti-patterns using the detection checklist (`references/anti-patterns.md`)
2. Create `refactoring/` directory with per-feature plan files (`references/refactoring-workflow.md`)
3. Write each issue with **full description** (Location, Severity, Problem, Fix) — titles alone get forgotten
4. Categorize issues by severity: 🔴 Critical → 🟡 High → 🟢 Medium
5. Plan Phase 1 PR: fix critical safety issues only (≤200 lines per PR)
6. Execute one PR at a time. New findings go to `refactoring/discovered.md` with full descriptions, NOT into current PR
7. After completing each fix: mark the task `- [x]` in the feature file and update `refactoring/README.md` progress table
8. Proceed through phases: Critical → @Observable migration → ViewState → Architecture

### Workflow: Create a New Screen

**When:** Building a new feature screen from scratch. Apply enterprise patterns from the start so no refactoring is needed later.

1. Define the data model and repository protocol (`references/networking.md`)
2. Create ViewModel: `@Observable @MainActor final class` with `ViewState<T>` (`references/mvvm-observable.md`)
3. Add `// MARK: -` sections: Properties, Init, Actions, Computed Properties
4. Create the screen View with `@State private var viewModel`
5. Wire data loading via `.task { await viewModel.load() }`
6. Add navigation route to Router enum (`references/navigation.md`)
7. Register dependencies in `@Environment` or `@Injected` (`references/dependency-injection.md`)
8. Create test file with mock repository (`references/testing.md`)

### Workflow: Migrate ViewModel from ObservableObject

**When:** Modernizing existing code from Combine-based observation to @Observable.

1. Add `Self._printChanges()` to the View body — note current redraw triggers
2. Replace `ObservableObject` conformance with `@Observable` macro
3. Remove all `@Published` — plain `var` properties are auto-tracked
4. Replace `@StateObject` with `@State` in the owning View
5. Replace `@ObservedObject` with plain `let` (or `@Bindable` if `$` bindings needed)
6. Replace `@EnvironmentObject` with `@Environment(Type.self)`
7. Add `@MainActor` to the ViewModel class declaration
8. Verify with `Self._printChanges()` — confirm fewer/more specific redraw triggers
9. Run existing tests — all must pass
10. Remove `Self._printChanges()` before committing

## Code Generation Rules

<critical_rules>
Whether generating new code or refactoring existing code, every output must be **production-ready and PR-shippable** — small, focused, and testable. ALWAYS:

1. Mark ViewModels as `@Observable @MainActor final class`
2. Use `private(set) var` for state properties modified only by the ViewModel
3. Use `ViewState<T>` enum for async data — never separate boolean flags
4. Inject dependencies via constructor with protocol types
5. Use `.task { }` for initial data loading
6. Keep View bodies pure — no `Task { }` inside body, no business logic
7. Use typed `enum Route: Hashable` for navigation
8. Add `// MARK: -` sections: Properties, Init, Actions, Computed Properties
9. Import only `Foundation` (and domain modules) in ViewModels — never `SwiftUI`
10. Keep every generated file ≤ 400 lines. Extract subviews into dedicated files. Split ViewModel logic into extensions (`MyVM+Search.swift`) or child ViewModels when approaching that limit. For legacy files, log a split task in the feature's `refactoring/` plan instead of forcing it mid-refactor.
11. Before modifying a View or ViewModel, output a brief `<thought>` analyzing its current state and redraw triggers.
</critical_rules>

When generating tests, ALWAYS:

1. Use protocol mocks with `var stubbed*` and `var *CallCount` tracking
2. Test through public interface, never test private methods
3. Mark test classes/structs `@MainActor` when testing `@MainActor` ViewModels
4. Use `await fulfillment(of:)` for async tests — NEVER `wait(for:)` (deadlocks)
5. Include memory leak detection with `addTeardownBlock { [weak sut] in XCTAssertNil(sut) }`

## Fallback Strategies & Loop Breakers

<fallback_strategies>
When refactoring legacy code, you may encounter stubborn Swift compiler errors. If you fail to fix the same error twice, break the loop:

1. **@State vs @Bindable Generics:** If the compiler complains about property wrapper bindings (`$`), ensure you use `@Bindable` in subviews for `@Observable` types. Why: `@State` creates ownership (single source of truth), while `@Bindable` enables two-way bindings without ownership — the compiler enforces this distinction. If unresolved, temporarily use plain `let` and closure callbacks to unblock compilation.
2. **NavigationStack Path Issues:** If the compiler complains about `Hashable` routes or `navigationDestination` types, ensure your `enum Route` is perfectly `Hashable` and avoid passing complex models (prefer passing IDs). Why: NavigationStack serializes the path for state restoration, so every route case must be deterministically hashable.
3. **Revert and Restart:** If a View refactor spirals into 50+ compiler errors related to ambiguous type inference, stop. Propose reverting the changes and breaking the problem into two smaller phases (e.g. migrate properties first, then extract subviews). Why: SwiftUI's type inference cascades — a single change can destabilize unrelated code, and small PRs are far easier to review and debug.
</fallback_strategies>

## Confidence Checks

Before finalizing generated or refactored code, verify ALL:

```
□ No duplicate functionality — searched codebase for existing implementations
□ Architecture adherence — follows patterns already established in the project
□ Naming conventions — matches existing project naming style
□ Import check — ViewModel imports only Foundation, NOT SwiftUI
□ @MainActor — present on all ViewModel class declarations
□ ViewState — used for all async data, no separate isLoading/error booleans
□ DI — dependencies injected via protocol, not accessed via singletons
□ Task management — .task modifier for lifecycle, explicit cancellation handling
□ CancellationError — handled silently, never shown to user
□ Tests — corresponding test file exists or is created alongside
□ PR scope — changes within defined scope, new findings go to `refactoring/discovered.md`
□ File size — new files ≤ 400 lines; existing oversized files have a split task logged in `refactoring/`
```

## Companion Skills

> **Before generating async ViewModel, Task, or actor code:** determine the project's concurrency approach. If unclear from context, ask the user.

| Project's concurrency stack | Companion skill | Apply when |
|---|---|---|
| `async/await`, actors, Swift 6, `@MainActor` | `skills/swift-concurrency/SKILL.md` | Writing async ViewModel methods, Task creation, actor-isolated state |
| `DispatchQueue`, `OperationQueue` (legacy or hybrid) | `skills/gcd-operationqueue/SKILL.md` | Writing queue-based networking, background work, thread-safe state |

**If unclear, ask:** "Does this project use Swift Concurrency (async/await) or GCD for async operations?"

## References

| Reference | When to Read |
|-----------|-------------|
| `references/rules.md` | Do's and Don'ts quick reference: priority rules and critical anti-patterns |
| `references/mvvm-observable.md` | Creating ViewModels, @State/@Bindable ownership rules, migration mapping |
| `references/navigation.md` | Router pattern, deep linking, TabView setup, sheets |
| `references/dependency-injection.md` | @Environment, @Injected wrapper, constructor injection, testing DI |
| `references/networking.md` | ViewState enum, Repository pattern, HTTPClient, task cancellation |
| `references/anti-patterns.md` | Code review detection checklist, severity-ranked violations |
| `references/testing.md` | ViewModel unit tests, async patterns, mocks, memory leak detection |
| `references/performance.md` | Self._printChanges(), Instruments, launch time, verification evidence |
| `references/file-organization.md` | File size guidelines, extension splitting, child ViewModels, subview extraction |
| `references/refactoring-workflow.md` | `refactoring/` directory protocol, per-feature plans, PR sizing, phase ordering |
