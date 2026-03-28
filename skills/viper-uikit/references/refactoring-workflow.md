# Enterprise Refactoring & Tech-Debt Tracker

## Purpose

A `refactoring/` directory at the project root. One file per feature/flow/screen, plus an overview `README.md`. GitHub checkbox syntax (`- [ ]` / `- [x]`). **Every task MUST carry a rich description** — Location, Severity, Problem, Fix — so anyone can pick it up months later.

## Why Not "Fix Everything at Once"

Single mega-PR: unreviewable (2000+ lines), unrevertable, blocks team, unmeasurable.

## Task Description Requirements

| Field | Example |
| --- | --- |
| **Title** | `Force-unwrapped deps in ProfileViewModel` |
| **Location** | `ProfileViewModel.swift:14` |
| **Severity** | 🔴 Critical / 🟡 High / 🟢 Medium |
| **Problem** | 2-4 sentences: what's wrong, what breaks |
| **Fix** | Concrete steps |

Optional: Dependencies, Blocker, PR link, Found during, Branch, Verification.

---

## Directory Structure

```text
refactoring/
├── README.md                ← overview dashboard (always up to date)
├── order-flow.md            ← one feature / flow / screen
├── profile-screen.md
├── cross-cutting.md         ← work that spans multiple features (DI, base classes)
└── discovered.md            ← triage inbox for new findings
```

**Rules:**

- One file per feature, flow, or screen that needs refactoring
- File name = kebab-case feature name
- `cross-cutting.md` for infrastructure work (DI setup, Coordinator base class, shared ViewModels)
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

Each feature file follows this structure. Categories within each feature are ordered by severity — fix crashes before extracting ViewModels:

```markdown
# Feature: [Order Flow]

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

## ViewModel Extraction
- [ ] **VM1: [Title]**
  - ...

## Coordinator Introduction
- [ ] **CO1: [Title]**
  - ...

## Combine Bindings
- [ ] **CB1: [Title]**
  - ...

## DI & Testing
- [ ] **DT1: [Title]**
  - ...
```

Not every feature needs all categories — include only those with actual findings. The category ordering is fixed: **Critical → ViewModel Extraction → Coordinator → Combine → DI & Testing**.

---

## Cross-cutting File Template

```markdown
# Cross-cutting Concerns

> Work that spans multiple features or is infrastructure-level.

- [ ] **X1: Create Coordinator base protocol and AppCoordinator**
  - **Location**: New files: `Coordinator.swift`, `AppCoordinator.swift`
  - **Severity**: 🟡 High
  - **Problem**: No centralized navigation. ViewControllers create and push each other directly.
  - **Fix**: Protocol with start()/childCoordinators. AppCoordinator owns the window.

- [ ] **X2: Add DI container with factory protocol**
  - ...

- [ ] **X3: Create BaseViewModel with Combine cancellables**
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
3. `cross-cutting.md` for infrastructure tasks (DI, Coordinator base, shared types)
4. `discovered.md` (empty template)

### Step 2: Plan one PR

Before writing any code, define the scope. Each PR targets tasks within **one feature file**:

```markdown
## Next PR Scope

**Feature file**: order-flow.md
**PR Title**: Extract OrderListViewModel from OrderListViewController
**Files to change**: OrderListViewController.swift, OrderListViewModel.swift (new)
**Max lines changed**: ~200
**Risk**: Medium (active feature, needs regression test)

### Changes:
1. Create OrderListViewModel with fetchOrders(), deleteOrder()
2. Move business logic out of VC into VM
3. VC observes VM via Combine $orders sink

### Verification:
- [ ] VC only does UIKit — no URLSession, no JSON decoding
- [ ] VM has no import UIKit
- [ ] Existing manual test: orders load, delete, pull-to-refresh
- [ ] deinit prints confirm no retain cycles

### NOT in this PR:
- Coordinator introduction (different category)
- DI changes (cross-cutting)
- Tests (different category)
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

## PR Size Guidelines

| Change Type | Max Lines |
| --- | --- |
| ViewModel extraction | 200 |
| ViewState adoption | 100 |
| Coordinator for one flow | 250 |
| Combine bindings for one screen | 150 |
| New feature screen | 300 |
| DI infrastructure | 200 |
| Bug fix | 50 |

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
- [ ] New/changed ViewModel has corresponding test file
- [ ] `[weak self]` in every `sink` closure stored in `cancellables`
- [ ] `.receive(on: DispatchQueue.main)` before UI updates in Combine chains
- [ ] No `import UIKit` in ViewModel files
- [ ] Feature file updated — task marked `[x]`
- [ ] `README.md` progress table current
- [ ] New discoveries logged in `discovered.md` (not fixed in this PR)
```

## When to Deviate

**Acceptable**: critical production bug (fix now, add to plan retroactively), blocker dependency discovered (reorder), team re-prioritisation, feature larger than expected (subdivide it).

**Never**: expanding PR scope mid-implementation, skipping the plan update step, fixing "just one more thing" in an unrelated area.

---

## Concrete Example

Below is a realistic feature file for the `refactoring/` directory:

```markdown
# Feature: Order Flow

> **Context**: OrderListViewController is 800+ lines with inline networking,
> manual UITableView updates, hardcoded navigation pushes, and zero tests.
> Combine bindings exist but leak due to missing [weak self].
> **Created**: 2025-01-15 | **Status**: In Progress

---

## Critical Safety Issues

- [x] **C1: Retain cycle in OrderListViewController Combine binding**
  - **Location**: `OrderListViewController.swift:47`
  - **Severity**: 🔴 Critical
  - **Problem**: `viewModel.$orders.sink { orders in self.renderOrders(orders) }` captures
    `self` strongly. The VC is never deallocated when popped from the nav stack, leaking
    memory on every navigation cycle. Instruments confirms 12 leaked instances after 5
    minutes of use.
  - **Fix**: Add `[weak self]` to sink closure, add `.receive(on: DispatchQueue.main)`.
    Add `deinit { print("OrderListVC deallocated") }` to verify fix.
  - **PR**: !142
  - **Verification**: Instruments Leaks, navigate in/out 10 times, 0 leaked instances.

- [ ] **C2: Force-unwrapped service in CartViewModel**
  - **Location**: `CartViewModel.swift:8`
  - **Severity**: 🔴 Critical
  - **Problem**: `var cartService: CartServiceProtocol!` — IUO. Crashes from deep link
    if VC is instantiated without setting the property. 23 crash reports this month.
  - **Fix**: Constructor injection: `private let cartService: CartServiceProtocol`.
    Update Coordinator to pass dependency.

## ViewModel Extraction

- [ ] **VM1: Extract OrderListViewModel from 800-line ViewController**
  - **Location**: `OrderListViewController.swift:1-800`
  - **Severity**: 🟡 High
  - **Problem**: VC contains networking, JSON parsing, filtering, and sorting logic
    mixed with UITableView management. Can't unit test any business logic. Changes to
    API response format require touching the same file as UI layout changes.
  - **Fix**: Create `OrderListViewModel` with `fetchOrders()`, `deleteOrder(at:)`,
    `@Published var orders: [Order]`, `@Published var state: ViewState<[Order]>`.
    VC subscribes via Combine sink.
```
