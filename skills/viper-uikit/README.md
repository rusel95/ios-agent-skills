# VIPER UIKit Architecture Skill

Enterprise-grade UIKit VIPER architecture skill for production iOS codebases (iOS 13+).

## What This Skill Does

Guides AI coding assistants through VIPER (View-Interactor-Presenter-Entity-Router) architecture for UIKit applications, preventing the most common AI-generated mistakes: retain cycles from incorrect reference directions, UIKit imports in Presenters, business logic in Presenters instead of Interactors, and strong references where weak ones are required.

**Covers:**
- Building new VIPER modules with correct ownership chains and protocol contracts
- Refactoring legacy MVC/MVVM codebases to VIPER through phased, reviewable PRs
- Decomposing god ViewControllers into properly separated VIPER layers
- Implementing Router/Wireframe navigation with weak reference safety
- Testing Presenters and Interactors in isolation with mock protocols
- Debugging and fixing retain cycles in VIPER module wiring
- Integrating Coordinators for multi-flow navigation in large apps
- Migrating VIPER Views to SwiftUI via UIHostingController adapter pattern
- Module assembly with dependency injection (enum-based Builders)
- Enterprise concerns: error propagation chains, ViewState management, thread dispatching

## When to Use

- Creating new VIPER modules for UIKit apps
- Refactoring MVC or MVVM screens to VIPER architecture
- Reviewing VIPER code for anti-patterns (especially retain cycles and layer violations)
- Fixing memory leaks in VIPER module wiring
- Setting up module Builders/Factories with dependency injection
- Implementing Router navigation patterns
- Testing VIPER Presenters and Interactors
- Migrating VIPER Views to SwiftUI incrementally
- Adding Coordinator pattern on top of VIPER Routers

## Structure

```
viper-uikit-architecture/
├── SKILL.md                              # Main skill: architecture layers, decision trees, workflows, rules
├── README.md                             # This file
└── references/
    ├── rules.md                          # Do's and Don'ts quick reference
    ├── module-contracts.md               # 6 protocols per module, naming conventions, AnyObject constraints
    ├── view-patterns.md                  # Passive View rules, lifecycle forwarding, UITableView data flow
    ├── presenter-patterns.md             # UIKit-free Presenter, ViewState mapping, Entity→ViewModel translation
    ├── interactor-patterns.md            # Single use case, service injection, Entity boundaries, async patterns
    ├── router-navigation.md              # Weak VC reference, push/present/dismiss, deep linking
    ├── module-assembly.md                # Builder/Factory patterns, DI, wiring order
    ├── memory-management.md              # Ownership chain, retain cycle debugging, deallocation verification
    ├── testing.md                        # Interactor/Presenter/Router testing, mock patterns, leak assertions
    ├── anti-patterns.md                  # AI-specific mistakes, severity-ranked violations, detection checklist
    ├── coordinator-integration.md        # When Routers aren't enough, Coordinator hierarchy, wiring
    ├── migration-patterns.md             # MVC→VIPER extraction, VIPER→SwiftUI via UIHostingController
    ├── enterprise-patterns.md            # Error propagation, ViewState, analytics decoration, thread safety
    └── refactoring-workflow.md           # refactoring/ directory protocol, per-feature plans, PR sizing
```

## Benchmark Results

Tested on **16 scenarios** with **149 assertions**.

### Results Summary

| Model | With Skill | Without Skill | Delta |
| --- | --- | --- | --- |
| **Sonnet 4.6** | 147/149 (98.7%) | 127/149 (85.2%) | **+13.4%** |

### Per-Scenario Breakdown

| # | Scenario | With Skill | Without Skill | Delta |
| --- | --- | --- | --- | --- |
| 1 | Greenfield product-list module | 17/17 | 17/17 | +0 |
| 2 | Profile MVC→VIPER refactor | 12/13 | 9/13 | **+3** |
| 3 | Presenter unit tests (checkout) | 11/12 | 10/12 | +1 |
| 4 | Inter-module communication | 9/9 | 8/9 | +1 |
| 5 | Code review anti-patterns | 11/11 | 10/11 | +1 |
| 6 | async/await integration | 9/9 | 9/9 | +0 |
| 7 | Retain cycle detection & fix | 10/10 | 9/10 | +1 |
| 8 | SwiftUI migration (UIHostingController) | 11/11 | 11/11 | +0 |
| 9 | Complex navigation (TabBar, modal, multi-step) | 9/9 | 9/9 | +0 |
| 10 | Interactor unit tests (cart) | 12/12 | 11/12 | +1 |
| 11 | Builder assembly + UITabBarController timing | 6/6 | 2/6 | **+4** |
| 12 | Thread-safety dispatching boundary | 5/5 | 3/5 | +2 |
| 13 | ViewState enum design | 6/6 | 6/6 | +0 |
| 14 | God Interactor decomposition | 7/7 | 5/7 | +2 |
| 15 | Entities domain layer design | 6/6 | 4/6 | +2 |
| 16 | Error propagation chain | 6/6 | 4/6 | +2 |

### Key Discriminating Assertions (Skill wins)

| Scenario | Assertion | Why Baseline Fails |
| --- | --- | --- |
| Profile refactor | Presenter does NOT import UIKit | Baseline imports UIKit for formatting |
| Profile refactor | Uses ViewState enum instead of separate booleans | Baseline uses `isLoading`/`error` flags |
| Profile refactor | Entities defined outside module folder | Baseline puts entities inside module |
| Presenter tests | Memory leak detection via `addTeardownBlock` + `weak` | Baseline skips leak detection entirely |
| Module communication | ItemPicker dismissal by PRESENTING Router | Baseline lets ItemPicker dismiss itself |
| Code review | Identifies Router→Presenter as retain cycle | Baseline misses Router holding Presenter ref |
| Retain cycles | Explains all three cycles broken after fixes | Baseline explains fix but not full chain |
| Interactor tests | Presenter mock held weakly with leak detection | Baseline skips weak reference pattern |
| Builder + TabBar | Builder wires ALL references before returning VC | Baseline defers wiring to `viewDidLoad` |
| Builder + TabBar | Builder is enum-based with static `build()` | Baseline uses class-based Builder |
| Builder + TabBar | `build()` accepts dependencies as parameters | Baseline stores deps as Builder properties |
| Builder + TabBar | Router's VC typed as `UIViewController?` | Baseline uses concrete VC subclass type |
| Thread dispatching | `DispatchQueue.main.async` at Interactor OUTPUT boundary | Baseline dispatches inside Presenter |
| Thread dispatching | `@MainActor` Presenter as acceptable alternative | Baseline doesn't mention @MainActor option |
| God Interactor | Presenter holds multiple Interactor refs (one per use case) | Baseline keeps single god Interactor |
| God Interactor | Presenter conforms to all output protocols | Baseline uses single massive output protocol |
| Entities | Interactors map to response structs, not raw Entities | Baseline passes raw Entities to Presenter |
| Entities | Presenter maps to ViewModels — entities never reach View | Baseline leaks entities to View layer |
| Error propagation | Interactor uses result type, not raw service errors | Baseline passes CartError to Presenter |
| Error propagation | Error cases exhaustively handled, no wildcard catch-all | Baseline uses generic catch-all |

### By Category

| Category | Evals | With Skill | Without Skill | Delta |
| --- | --- | --- | --- | --- |
| Creation (evals 1, 6, 8, 9, 11, 13) | 6 | 58/58 (100%) | 54/58 (93.1%) | **+6.9%** |
| Review & Debug (evals 5, 7, 12) | 3 | 26/26 (100%) | 22/26 (84.6%) | **+15.4%** |
| Testing (evals 3, 10) | 2 | 23/24 (95.8%) | 21/24 (87.5%) | **+8.3%** |
| Refactoring (evals 2, 14) | 2 | 19/20 (95.0%) | 14/20 (70.0%) | **+25.0%** |
| Architecture (evals 4, 15, 16) | 3 | 21/21 (100%) | 16/21 (76.2%) | **+23.8%** |

**Interpretation:** The skill's value is strongest on refactoring (+25.0%) and architecture design (+23.8%) — scenarios requiring knowledge of VIPER-specific patterns like Router→Builder delegation, entity layering, and error boundary transformation. Creation scenarios show a smaller gap (+6.9%) because Sonnet 4.6 already produces reasonable basic VIPER modules without the skill. The biggest single-eval gap is eval 11 (Builder + UITabBarController timing, +4 assertions) — a niche but critical gotcha that models consistently miss.

## Source Material

- objc.io "Architecting iOS Apps with VIPER" (original Mutual Mobile article)
- Rambler&Co VIPER guidelines and Typhoon DI patterns
- TheSwiftDev VIPER ownership chain analysis
- CheesecakeLabs VIPER implementation guides
- ZIKViper Router/Wireframe distinction
- Infinum iOS templates (GitHub issue #31 — UIKit in Presenter fix)
- Vadim Bulavin's DI patterns for VIPER
- mutualmobile/VIPER-TODO GitHub issues
- Point-Free swift-snapshot-testing for View layer
- Multiple production post-mortems on VIPER retain cycles
