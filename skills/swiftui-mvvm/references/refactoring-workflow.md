# Enterprise Refactoring & Tech-Debt Tracker

## Purpose

A `refactoring/` directory at the project root. One file per feature/flow/screen, plus an overview `README.md`. GitHub checkbox syntax (`- [ ]` / `- [x]`).

Short titles get forgotten in a week. **Every task MUST carry a rich description** — the "what", "where", "why it matters", and "how to fix" — so any team member (or your future self) can pick it up months later without archaeology.

## The Problem with "Fix Everything at Once"

A single PR that migrates @Observable, restructures navigation, introduces DI, and adds tests is:
- **Unreviewable**: 2000+ line diffs get rubber-stamped, not reviewed
- **Unrevertable**: If one change introduces a regression, you can't revert without losing everything
- **Unblockable**: Blocks the entire team while one person refactors
- **Unmeasurable**: You can't measure which change improved what

Enterprise refactoring requires **small, focused, independently-shippable PRs** with a living plan that tracks everything.

---

## Task Description Requirements

Every task — whether tech-debt, refactoring, or discovered issue — MUST include the fields below. A checkbox with only a title is **not acceptable**.

### Required Fields

| Field | Why | Example |
|-------|-----|---------|
| **Title** | Scannable one-liner for the plan overview | `Force-unwrapped dependencies in ProfileViewModel` |
| **Location** | Exact file(s) and line(s) so the next person finds it instantly | `ProfileViewModel.swift:14`, `ProfileView.swift:8` |
| **Severity** | Prioritisation — 🔴 Critical / 🟡 High / 🟢 Medium | `🔴 Critical` |
| **Problem** | 2-4 sentences: what is wrong and what bad outcome it causes | "The `networkService` property is implicitly unwrapped (`!`). If the DI container fails to register it — or registration order changes — the app crashes on launch with no actionable error message. This has caused 2 Crashlytics incidents in the last month." |
| **Fix** | Concrete steps or code pointer | "Replace IUO with constructor injection. Accept `NetworkServiceProtocol` in `init`. Remove the `!` property. Update `ProfileScreenFactory` to pass the dependency." |

### Optional Fields (add when applicable)

| Field | When |
|-------|------|
| **Dependencies** | Task depends on another task being completed first |
| **Blocker** | Something external prevents starting |
| **PR** | Link when submitted |
| **Found during** | Which task uncovered this (for "Discovered" items) |
| **Assigned** | Team member handling it |
| **Branch** | WIP branch name |
| **Verification** | How to confirm the fix works |

---

## Directory Structure

```text
refactoring/
├── README.md               ← overview dashboard (always up to date)
├── profile-screen.md       ← one feature / flow / screen
├── cart-checkout.md
├── order-flow.md
├── cross-cutting.md        ← work that spans multiple features (DI, Router)
└── discovered.md           ← triage inbox for new findings
```

**Rules:**

- One file per feature, flow, or screen that needs refactoring
- File name = kebab-case feature name
- `cross-cutting.md` for infrastructure work (DI setup, Router, shared utilities)
- `discovered.md` for new findings not yet assigned to a feature — triage regularly
- `README.md` is the only file stakeholders need to read for status

---

## README.md Template

When created for a new project, you **MUST** create a `refactoring/` directory with this `README.md`:

```markdown
# Refactoring Plan

Last Updated: YYYY-MM-DD

| Feature / Scope | File | Total | Done | Status |
|-----------------|------|-------|------|--------|
| [Feature Name] | [feature-name.md](feature-name.md) | 0 | 0 | Planned |
| Cross-cutting | [cross-cutting.md](cross-cutting.md) | 0 | 0 | Planned |
| **Total** | | **0** | **0** | **0%** |

## Discovered (needs triage)

See [discovered.md](discovered.md) for new findings not yet assigned to a feature.
```

---

## Feature File Template

Each feature file follows this structure. Categories within each feature are ordered by severity — fix crashes before migrations:

```markdown
# Feature: [Profile Screen]

> **Context**: Brief description of why this feature needs refactoring.
> What's broken, what the user impact is, what triggered this work.
> **Created**: YYYY-MM-DD | **Status**: In Progress

---

## Critical Safety Issues
- [ ] **C1: [Title]**
  - **Location**: `File.swift:line`
  - **Severity**: 🔴 Critical
  - **Problem**: ...
  - **Fix**: ...

## @Observable Migration
- [ ] **M1: [Title]**
  - ...

## ViewState Adoption
- [ ] **V1: [Title]**
  - ...

## Architecture (DI, Navigation, Repository)
- [ ] **A1: [Title]**
  - ...

## Testing
- [ ] **T1: [Title]**
  - ...
```

Not every feature needs all categories — include only those with actual findings. The category ordering is fixed: **Critical → @Observable → ViewState → Architecture → Testing**.

---

## Cross-cutting File Template

```markdown
# Cross-cutting Concerns

> Work that spans multiple features or is infrastructure-level.

- [ ] **X1: Introduce AppRouter for centralized navigation**
  - **Location**: `ContentView.swift:12-45`, scattered NavigationLink across 8 views
  - **Severity**: 🟢 Medium
  - **Problem**: Navigation is scattered across views. Can't test or deep-link.
  - **Fix**: @Observable AppRouter with typed Route enum.

- [ ] **X2: Add @Injected DI infrastructure**
  - ...

- [ ] **X3: Create ViewState<T> enum in shared utilities**
  - ...
```

---

## Discovered File Template

```markdown
# Discovered During Refactoring

> New issues found while working on other tasks.
> Add here immediately — do NOT fix in-flight.
> Triage regularly: move items to the appropriate feature file or cross-cutting.md.

- [ ] **D1: [Title]**
  - **Found during**: [which task / feature]
  - **Location**: `File.swift:line`
  - **Severity**: 🟡 High
  - **Problem**: ...
  - **Fix**: ...
  - **Assign to**: [feature file name or cross-cutting]
```

---

## Step-by-Step Protocol

### Step 1: Create the refactoring/ directory

On first analysis of a codebase, propose creating the `refactoring/` directory. Scan the codebase and create:

1. `README.md` with the overview table
2. One feature file per feature/flow/screen that needs work
3. `cross-cutting.md` for infrastructure tasks (DI, Router, shared types)
4. `discovered.md` (empty template)

### Step 2: Plan one PR

Before writing any code, define the scope. Each PR targets tasks within **one feature file**:

```markdown
## Next PR Scope

**Feature file**: cart-checkout.md
**PR Title**: Migrate CartViewModel to @Observable
**Files to change**: CartViewModel.swift, CartView.swift, CartBadge.swift
**Max lines changed**: ~150
**Risk**: Low (isolated feature, no shared state)

### Changes:
1. CartViewModel: ObservableObject → @Observable, remove @Published
2. CartView: @StateObject → @State
3. CartBadge: @ObservedObject → @Bindable (needs $ binding for badge count)

### Verification:
- [ ] Add `Self._printChanges()` before and after — confirm reduced redraws
- [ ] Run existing tests — all pass
- [ ] Manual test: add/remove items, verify badge updates
- [ ] Remove `Self._printChanges()` before merge

### NOT in this PR:
- ViewState enum migration (different category)
- DI changes (cross-cutting)
- New tests (different category)
```

### Step 3: Execute the PR

Apply ONLY the changes listed in the PR scope. If you discover new issues during implementation:

- **DO NOT fix them now**
- Add them to `refactoring/discovered.md` with a **full description**
- Continue with the original scope

### Step 4: Update the plan

After each PR:

1. Mark the task done in the feature file: `- [ ]` → `- [x]`
2. Update the `README.md` progress table
3. Triage `discovered.md` — move items to the right feature file
4. If a feature is fully done, mark it Completed in `README.md`

---

## Writing Good Task Descriptions

A task description must be understandable **6 months later** by someone with no prior context.

### Bad — Titles Without Context

```markdown
- [ ] **Fix CartViewModel state issue**
  - Has some boolean state problems. Should probably use ViewState.
```

Six months later: "What state issue? Which booleans? What breaks? Is this still relevant?"

### Good — Full Context

```markdown
- [ ] **V2: CartViewModel — introduce ViewState for checkout flow**
  - **Location**: `CartViewModel.swift:8-12`
  - **Severity**: 🟡 High
  - **Problem**: Checkout uses `isProcessing`, `checkoutError`, and
    `orderConfirmation` as three independent variables. A race condition
    exists where `isProcessing = false` is set before `orderConfirmation`
    is populated, causing a brief flash of the empty cart before the
    confirmation screen appears.
  - **Fix**: Introduce `var checkoutState: ViewState<OrderConfirmation> = .idle`.
    Transition directly from `.loading` → `.loaded(confirmation)`.
```

Six months later: crystal clear. File, line, exact symptom, exact fix.

---

## PR Size Guidelines

| Change Type | Max Lines | Example |
| ----------- | --------- | ------- |
| Single ViewModel migration | 150 | ObservableObject → @Observable |
| ViewState enum adoption | 100 | Replace 3 booleans with ViewState |
| New feature screen | 300 | ViewModel + View + basic test |
| DI infrastructure setup | 200 | @Injected wrapper + first 2 keys |
| Router introduction | 250 | Router + Route enum + RootView wiring |
| Bug fix | 50 | Single focused fix |
| File split (View or ViewModel) | 0 net | Extract extensions / subviews — dedicated PR, not mid-refactor |

If a PR exceeds these limits, split it. If a file exceeds 1000 lines, log a dedicated split task in the plan — see `file-organization.md`. Do NOT force a file split inside an unrelated refactoring PR.

## Rules

- New findings go to `discovered.md` with full description, NOT into current PR
- Mark tasks `- [x]` immediately after completing
- Update `README.md` progress table after every PR
- Triage `discovered.md` at least weekly — move items to feature files
- **Never**: expand PR scope mid-implementation, skip plan update, fix "one more thing" in unrelated area

## PR Verification Checklist

Before submitting each PR, verify:

```markdown
- [ ] Changes match the defined scope — no extras
- [ ] No new warnings introduced (build + analyze)
- [ ] All existing tests pass
- [ ] `Self._printChanges()` confirms reduced re-evaluations (for @Observable PRs)
- [ ] New/changed ViewModel has corresponding test file
- [ ] `@MainActor` present on ViewModel class declarations
- [ ] No `import SwiftUI` in ViewModel files
- [ ] Feature file updated — task marked `[x]`
- [ ] `README.md` progress table current
- [ ] New discoveries logged in `discovered.md` (not fixed in this PR)
```

## When to Deviate from the Plan

**Acceptable**: critical production bug (fix now, add to plan retroactively), blocker dependency discovered (reorder), team re-prioritisation, feature larger than expected (subdivide it).

**Never**: expanding PR scope mid-implementation, skipping the plan update step, fixing "just one more thing" in an unrelated area.

---

## Concrete Example

Below is a realistic feature file for the `refactoring/` directory:

```markdown
# Feature: Cart & Checkout

> **Context**: Cart screen uses legacy ObservableObject with 6 @Published properties,
> causing full-view re-evaluation on every change. Checkout has impossible states from
> 3 independent boolean flags. CartBadge silently breaks tracking after migration.
> **Created**: 2025-01-20 | **Status**: In Progress

---

## Critical Safety Issues

- [x] **C1: Missing @MainActor on CartViewModel**
  - **Location**: `CartViewModel.swift:1`
  - **Severity**: 🔴 Critical
  - **Problem**: `CartViewModel` mutates `@Published var items` from the result
    of `await api.fetchCart()`, which resumes on a background thread. This
    causes purple "Publishing changes from background threads" warnings in
    Xcode and intermittent UI glitches where the cart badge shows stale data
    for 1-2 seconds.
  - **Fix**: Add `@MainActor` to the class declaration. Wrap test assertions
    in `@MainActor` or use `await MainActor.run { }`.
  - **PR**: #143 (merged 2025-01-17)

## @Observable Migration

- [ ] **M1: Migrate CartViewModel to @Observable**
  - **Location**: `CartViewModel.swift`, `CartView.swift`, `CartBadge.swift`
  - **Severity**: 🟡 High
  - **Problem**: Same over-invalidation issue. `CartBadge` uses
    `@ObservedObject var viewModel` which will silently break with @Observable.
  - **Fix**: ObservableObject → @Observable. `CartBadge` needs `@Bindable`
    for `$viewModel.promoCode` in TextField.
  - **Assigned**: @ruslan

## ViewState Adoption

- [ ] **V1: Introduce ViewState for checkout flow**
  - **Location**: `CartViewModel.swift:8-12`
  - **Severity**: 🟡 High
  - **Problem**: `isProcessing`, `checkoutError`, `orderConfirmation` as 3
    independent variables. Race: `isProcessing = false` set before
    `orderConfirmation` is populated, causing brief cart flash.
  - **Fix**: `var checkoutState: ViewState<OrderConfirmation> = .idle`.
  - **Dependencies**: M1 should be merged first (cleaner diff).
```
