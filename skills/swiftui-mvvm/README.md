# SwiftUI MVVM Architecture

Enterprise-grade SwiftUI MVVM architecture with @Observable (iOS 17+). Takes a **production-first iterative refactoring** approach — modernizing legacy codebases through small, reviewable PRs while also ensuring new features meet enterprise standards from day one.

## What This Skill Changes

| Without Skill | With Skill |
| --- | --- |
| `ObservableObject` + `@Published` | `@Observable @MainActor final class` |
| `isLoading` + `error` + `data` booleans | `ViewState<T>` enum (no impossible states) |
| `onAppear { Task { } }` | `.task { }` (managed lifecycle, auto-cancel) |
| `URLSession.shared` in ViewModel | Protocol-based Repository + HTTPClient injection |
| `NavigationLink("Details") { DetailView() }` | Typed `enum Route` + `AppRouter` |
| No tests | Mock pattern + async testing + memory leak detection |
| "Fix everything at once" PRs | Phased `refactoring/` directory with ≤200-line PRs |

## Install

```bash
npx skills add git@git.epam.com:epm-ease/research/agent-skills.git --skill swiftui-mvvm-architecture
```

Verify installation by asking your AI agent to refactor a SwiftUI view — it should follow @Observable ViewModel + Router patterns and reference the `refactoring/` directory.

## When to Use

- **Refactoring legacy SwiftUI code** — iterative, phased PRs tracked in a `refactoring/` directory
- Migrating from ObservableObject to @Observable
- Writing ViewModel unit tests (async patterns)
- Diagnosing unnecessary view redraws or performance issues

## Pain Points This Skill Solves

Models without this skill commonly make these mistakes:

| Pain Point | What Goes Wrong | Impact |
| ---------- | --------------- | ------ |
| `@StateObject` + `@Observable` mixing | Uses `@StateObject` for `@Observable` classes | Crashes, undefined behavior |
| `onAppear { Task { } }` | Unmanaged tasks, no cancellation on disappear | Memory leaks, duplicate requests |
| `wait(for:)` in tests | Deadlocks on `@MainActor` test classes | Tests hang forever |
| Separate `isLoading`/`error` booleans | Allows impossible states (loading AND error) | UI bugs, race conditions |

## Benchmark Results

Tested on **23 scenarios** with **63 discriminating assertions**.

### Results Summary

| Model | With Skill | Without Skill | Delta | A/B Quality |
| --- | --- | --- | --- | --- |
| **Sonnet 4.6** | 63/63 (100%) | 56/63 (88.9%) | **+11.1%** | **9W 15T 0L** (avg 9.2 vs 8.8) |
| **GPT-5.4** | 100% | 59.2% | **+40.8%** | **24/24 wins** (avg 8.5 vs 7.5) |
| **Gemini 3.1 Pro** | 98.6% | 22.5% | **+76.0%** | **24/24 wins** (avg 8.8 vs 6.5) |

> A/B Quality: blind judge scores each response 0–10 and picks the better one without knowing which used the skill. Position (A/B) is randomized across evals to prevent bias.

### Results (Sonnet 4.6)

| Metric | Value |
| --- | --- |
| With Skill | 63/63 (100%) |
| Without Skill | 56/63 (88.9%) |
| Delta | **+11.1%** |
| A/B Quality | **9W 15T 0L** (avg 9.2 vs 8.8) |

**Interpretation:** Sonnet 4.6 without the skill misses 7 of 63 discriminating assertions — concentrated on `@Bindable` usage, `.task(id:)` for reactive reloads, Observation-native environment injection, navigation state ownership, and focused `@Observable` model splitting. A/B confirms with 9 wins, 15 ties, and zero losses.

### Results (GPT-5.4)

| Difficulty | With Skill | Without Skill | Delta | A/B Quality |
| --- | --- | --- | --- | --- |
| Simple | 22/22 (100%) | 22/22 (100%) | **0%** | **8/8 wins** (avg 8.5 vs 7.4) |
| Medium | 23/23 (100%) | 11/23 (47.8%) | **+52.2%** | **8/8 wins** (avg 8.4 vs 7.4) |
| Complex | 26/26 (100%) | 9/26 (34.6%) | **+65.4%** | **8/8 wins** (avg 8.6 vs 7.7) |
| **Total** | **71/71 (100%)** | **42/71 (59.2%)** | **+40.8%** | **24/24 wins** (avg 8.5 vs 7.5) |

### Results (Gemini 3.1 Pro)

| Difficulty | With Skill | Without Skill | Delta | A/B Quality |
| --- | --- | --- | --- | --- |
| Simple | 21/22 (95.5%) | 7/22 (31.8%) | **+63.6%** | **8/8 wins** (avg 8.4 vs 6.6) |
| Medium | 23/23 (100%) | 4/23 (17.4%) | **+82.6%** | **8/8 wins** (avg 8.9 vs 6.5) |
| Complex | 26/26 (100%) | 5/26 (19.2%) | **+80.8%** | **8/8 wins** (avg 9.0 vs 6.4) |
| **Total** | **70/71 (98.6%)** | **16/71 (22.5%)** | **+76.0%** | **24/24 wins** (avg 8.8 vs 6.5) |

### Key Discriminating Assertions — GPT-5.4

| Topic | Assertion | Why It Matters |
| --- | --- | --- |
| observable-viewmodel | `@Bindable` is the correct wrapper for `$` bindings | Distinguishes read-only model passing from true two-way binding |
| observable-viewmodel | ViewModels should import `Foundation`, not `SwiftUI`, and must be `@MainActor` | Preserves testability and keeps state mutation on the correct actor |
| task-lifecycle | `.task(id:)` is required for reactive reloads | Keeps data loading tied to changing inputs like filters |
| task-lifecycle | `CancellationError` must be handled silently in ViewModel tasks | Prevents user-facing "Cancelled" error states during normal view lifecycle changes |
| navigation | Navigation booleans belong in the View layer, not the ViewModel | Keeps presentation state out of business logic and improves testability |
| dependency-injection | `@EnvironmentObject` is wrong for `@Observable` | Avoids mixing Combine DI with Observation-native environment APIs |
| dependency-injection | `@Entry` enables environment-backed protocol injection | Makes shared services testable without changing ViewModel code |
| performance | Split large `@Observable` types into focused ViewModels | Reduces redraw scope and keeps observation granular |
| performance | Separate `@State` app-level models are not shared state | Catches a subtle but severe architecture bug in large SwiftUI apps |

### Key Discriminating Assertions — Gemini 3.1 Pro (54 total)

Gemini 3.1 Pro without-skill baseline defaults entirely to Combine-era patterns. With skill, it scores 98.6% — evidence that the skill content is clear and complete. The 54 gaps (without skill) span all 8 topics:

| Topic | ID | Assertion | Why It Matters |
| --- | --- | --- | --- |
| anti-patterns | AP1.1–1.3, AP2.1–2.3, AP3.1–3.3 | `@StateObject` + `@Observable` is Critical; causes no updates, crashes | Most critical Observation correctness error |
| observable-viewmodel | OV1.2–1.3, OV2.1–2.3, OV3.1, 3.3–3.4 | `@ObservedObject` wrong for `@Observable`; must use `@State`/`@Bindable`; `@MainActor` required | Core `@Observable` adoption rules |
| dependency-injection | DI1.2, DI2.1–2.3, DI3.1–3.3 | `@EnvironmentObject` wrong for `@Observable`; use `@Environment(\.key)` and `@Entry` | Observation-native DI replacing Combine patterns |
| navigation | NA1.2, NA2.1–2.3, NA3.1–3.3 | Navigation booleans in ViewModel is a violation; outer `NavigationStack` wrapping `TabView` is wrong | View-layer navigation ownership |
| task-lifecycle | TL1.1, TL1.3, TL2.2, TL3.2–3.3 | `.task {}` for managed lifecycle; `.task(id:)` for reactive reloads; `CancellationError` guard | Correct task management tied to view lifecycle |
| viewstate | VS1.2–1.3, VS2.1, VS3.1–3.3 | `ViewState<T>` enum; direct URLSession in ViewModel; force-`try!` crash | Production-safe state modeling |
| testing | TE1.2, TE2.1, TE2.3, TE3.2–3.3 | `@MainActor` on test class; memory leak detection; `if case` pattern matching | Correct async test setup and leak detection |
| performance | PE1.2–1.3, PE2.1–2.3, PE3.2–3.3 | Remove `.printChanges()`; split focused ViewModels; separate `@State` models are not shared | Performance analysis and architecture correctness |

> Raw data:
> `swiftui-mvvm-architecture-workspace/iteration-1/benchmark-gpt-5-4-tiered.json`
>
> `swiftui-mvvm-architecture-workspace/iteration-1/benchmark-gemini-3-1-pro-tiered.json`

## Author

[Ruslan Popesku](https://git.epam.com/Ruslan_Popesku)
