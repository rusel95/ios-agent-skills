---
name: swift-concurrency
description: "Use for any Swift Concurrency question on Apple platforms. Triggers on: actor reentrancy (stale state after await), AsyncStream lifecycle (continuation.finish, onTermination), TaskGroup memory and task throttling (activeProcessorCount), Sendable conformance across actor boundaries (non-Sendable third-party types), SWIFT_STRICT_CONCURRENCY=complete error triage ('Sending X risks causing data races'), Swift 6 / 6.2 migration (nonisolated caller-side isolation, @concurrent), cooperative pool blocking, async/await patterns, and continuation misuse. Also covers @MainActor isolation, structured concurrency, and converting callbacks to async/await. Use whenever the query mentions actor, AsyncStream, TaskGroup, Sendable, nonisolated, withCheckedContinuation, or Swift 6."
metadata:
  version: 1.1.2
---

# Swift Concurrency

Enterprise-grade skill for Swift Concurrency crash prevention, strict concurrency migration, and Swift 6.2 readiness. Opinionated: prescribes structured concurrency over unstructured, actors for shared mutable state, `@MainActor` for UI isolation, `Mutex` for synchronous critical sections, compile-time isolation over runtime hops, and `withCheckedContinuation` over `withUnsafeContinuation`. Every rule in this skill has broken a real production app.

## Concurrency Layers

```text
Application Layer    -> Structured concurrency: TaskGroup, async let, .task modifier
Actor Layer          -> actor for shared mutable state, @MainActor for UI state
Async/Await Layer    -> Cooperative, non-blocking async functions on the cooperative pool
Sendable Layer       -> Compile-time data-race safety at isolation boundary crossings
Compiler Layer       -> SWIFT_STRICT_CONCURRENCY=complete, Swift 6 language mode, TSan
```

## Quick Decision Trees

### "What isolation does this type need?"

```
Does this type own mutable state shared across concurrency domains?
+-- YES -> Does it need to update UI?
|   +-- YES -> @MainActor class/struct
|   +-- NO  -> Is the state complex or involves await points?
|       +-- YES -> actor
|       +-- NO  -> Mutex<State> (Swift 6+, iOS 18+) or NSLock wrapper
+-- NO  -> Is it a value type with only Sendable stored properties?
    +-- YES -> Implicitly Sendable (internal types only; public needs explicit conformance)
    +-- NO  -> Can it be redesigned as a value type?
        +-- YES -> Refactor to struct/enum
        +-- NO  -> Keep non-Sendable, contain within single isolation domain
```

### "async let vs TaskGroup vs Task {}?"

```
How many concurrent operations?
+-- Known at compile time (2-5) -> async let (simplest, heterogeneous return types OK)
+-- Dynamic count (N items)     -> TaskGroup
|   +-- Need results?
|   |   +-- YES -> withThrowingTaskGroup (iterate with for await)
|   |   +-- NO  -> withDiscardingTaskGroup (no result accumulation leak)
|   +-- Unbounded input? -> Throttle: limit addTask to activeProcessorCount
+-- Fire-and-forget from sync context?
    +-- Need caller's isolation -> Task { } (inherits actor context)
    +-- Need background, no isolation -> Task.detached { }
       WARNING: detached strips priority, task-locals, cancellation propagation. Rarely correct.
```

### "Is this safe to call from an async context?"

```
Does the API block the current thread?
+-- YES (semaphore.wait, group.wait, Thread.sleep, sync file I/O, NSLock in long section)
|   -> NEVER in async context. Deadlocks cooperative pool (capped at CPU core count).
|   -> Wrap in DispatchQueue + withCheckedContinuation to move off cooperative pool.
+-- NO  -> Is the work CPU-bound and takes >1ms?
    +-- YES -> Use @concurrent func (Swift 6.2+) or nonisolated func on dedicated queue
    +-- NO  -> Safe in async context
```

## Workflows

### Workflow: Audit Existing Codebase

**When:** First encounter with a codebase, or preparing for Swift 6 migration.

1. Check `SWIFT_STRICT_CONCURRENCY` setting (`references/compiler-flags-ci.md`)
2. Scan for crash patterns: continuation misuse, cooperative pool blocking, TaskGroup without throttling (`references/crash-patterns.md`)
3. Scan for `@unchecked Sendable` usage (`references/sendable-transfer.md`)
4. Check actor isolation: reentrancy bugs, deinit access, split isolation (`references/actor-isolation.md`)
5. Check AsyncStream usage: missing `finish()`, infinite sequences, no backpressure (`references/asyncstream-memory.md`)
6. For security-sensitive code: token refresh, TOCTOU, Keychain (`references/security-concurrency.md`)
7. Create `refactoring/` directory with severity-ranked findings (`references/refactoring-workflow.md`)
8. Execute fixes: 🔴 crash → 🟡 hang → 🟠 data race → 🟢 best practice

### Workflow: Migrate Module to Strict Concurrency

**When:** Enabling `SWIFT_STRICT_CONCURRENCY=complete` or Swift 6 mode.

**The migration is a THREE-STEP progression, not a binary flip.** Do not jump directly to `complete` or to Swift 6 language mode — you will drown in errors. The canonical progression is:

| Step | Setting | What it does |
|:----:|---------|--------------|
| **1. Targeted** | `SWIFT_STRICT_CONCURRENCY=targeted` | Surfaces warnings only in code explicitly marked `Sendable` or in `@preconcurrency` boundaries. Low-noise entry point. Ship this first, fix the surfaced warnings, then advance. |
| **2. Complete** | `SWIFT_STRICT_CONCURRENCY=complete` | Enables all concurrency checks as **warnings**. Work through each module until the warning count is zero. Still compiles and ships while you migrate. |
| **3. Swift 6 language mode** | `SWIFT_VERSION=6.0` | Promotes all concurrency checks from warnings to **errors**. Only switch here AFTER the module is clean under `complete`. This is the final gate. |

Most teams spend weeks in step 2 before advancing to step 3. Enabling step 3 prematurely produces hundreds of errors with no actionable incremental path.

1. Start with leaf modules (no internal dependencies) (`references/migration-strategy.md`)
2. Enable **targeted** on the leaf first to surface obvious Sendable gaps
3. Audit third-party SDKs for Sendable conformance; wrap blockers in actors (`references/migration-strategy.md`)
4. Fix global mutable state: `static var` → actor, Mutex, or `let` (`references/actor-isolation.md`)
5. Advance to **complete** on the leaf, fix each warning module by module
6. Annotate Sendable on public types; use `sending` where applicable (`references/sendable-transfer.md`)
7. Check Swift 6.2 caller-side isolation changes (`references/swift-6-2-changes.md`)
8. Only after **complete** is warning-free on the leaf, advance that leaf to **Swift 6 language mode**
9. Enable per-target in SPM (`references/compiler-flags-ci.md`)
10. Run TSan + `LIBDISPATCH_COOPERATIVE_POOL_STRICT=1` (`references/testing-debugging.md`)
11. One PR per module, bottom-up order

### Workflow: Create New Concurrent Feature

**When:** Building a new feature from scratch with Swift Concurrency.

1. Choose isolation model using Decision Tree 1 (actor vs @MainActor vs Mutex)
2. Choose concurrency structure using Decision Tree 2 (async let vs TaskGroup)
3. Implement with Sendable-clean types (`references/sendable-transfer.md`)
4. Add cancellation handling (`references/advanced-patterns.md`)
5. Use Clock injection for testability (`references/testing-debugging.md`)
6. Write deterministic tests with `withMainSerialExecutor` (`references/testing-debugging.md`)

### Workflow: Fix Production Crash

**When:** Crash report points to continuation, actor, AsyncStream, or TaskGroup.

1. Classify crash type (`references/crash-patterns.md`)
2. Check if release-only (optimized builds strip cooperative pool assertions) -- Rule 9
3. For reentrancy crashes: check state assumptions after await (`references/actor-isolation.md`)
4. For security crashes: token refresh, TOCTOU patterns (`references/security-concurrency.md`)
5. Add targeted test reproducing the crash (`references/testing-debugging.md`)
6. Verify fix with TSan + `LIBDISPATCH_COOPERATIVE_POOL_STRICT=1`

## Code Generation Rules

<critical_rules>
Whether reviewing, generating, or refactoring concurrent code, every output must be **data-race-free, deadlock-free, and production-ready under Swift 6 strict concurrency**. ALWAYS:

1. Never block the cooperative thread pool -- no `semaphore.wait()`, `group.wait()`, `Thread.sleep()`, synchronous file I/O in any async context
2. Resume every continuation exactly once on every code path -- use `withCheckedThrowingContinuation`
3. Re-check actor state after every `await` -- actors are reentrant at suspension points
4. Use `withDiscardingTaskGroup` for fire-and-forget child tasks -- prevents result accumulation memory leaks
5. **AsyncStream must use `onTermination` for EVERY external resource cleanup** — NotificationCenter observers, delegate assignments, timers, KVO, Combine subscribers, or any observer/callback registration made inside the stream's setup closure. `deinit` is not sufficient because an AsyncStream can outlive or be dropped independently of its owner; `onTermination` fires when the stream is finished or its task is cancelled, which is exactly when cleanup must run. Always pair every `addObserver`/`delegate = self`/registration call inside the stream setup with a symmetric removal in `onTermination`. Also call `continuation.finish()` from inside `onTermination` when your stream is an infinite observer pattern
6. Mark public types with explicit `Sendable` conformance -- no automatic inference across module boundaries
7. Limit TaskGroup child task count for unbounded work -- throttle to `ProcessInfo.processInfo.activeProcessorCount`
8. Use `@MainActor` annotation for UI isolation, not `MainActor.run {}`
9. Handle `CancellationError` silently -- never surface "cancelled" to users
10. Inject `Clock` protocol for time-dependent code -- never hardcode `Task.sleep`
11. Check Swift 6.2 caller-side isolation -- `nonisolated async` now inherits caller's actor; use `@concurrent` for explicit background
12. Before generating concurrent code, output a brief `<thought>` analyzing isolation domains, Sendable conformance, and potential reentrancy
</critical_rules>

## Fallback Strategies & Loop Breakers

<fallback_strategies>
When fixing concurrency issues, you may encounter cascading compiler errors. If you fail to fix the same issue twice, break the loop:

1. **Sendable spiral:** Conforming a type to Sendable cascades into 20+ errors across files. Temporarily use `@preconcurrency import` for the offending module and log a migration task in `refactoring/discovered.md`. Why: `@preconcurrency` suppresses Sendable checking at module boundaries while preserving local safety — it's the sanctioned escape hatch, unlike `@unchecked Sendable` which bypasses all checking.
2. **Actor isolation cascade:** Adding `@MainActor` to a class cascades into dozens of async call-site errors. Start by marking individual methods `@MainActor` instead of the whole class. Why: class-level isolation propagates to all methods, forcing every call site to be async — method-level isolation limits the blast radius.
3. **Third-party SDK blocker:** A third-party type is not Sendable and cannot be made so. Wrap it in a dedicated actor that owns the instance and mediates all access. Why: the actor serializes all access, making the non-Sendable type safe without needing to modify the SDK.
4. **TaskGroup OOM:** TaskGroup spawns thousands of child tasks and OOMs. Add a semaphore-based throttle: acquire before `addTask`, release inside the task. Limit to `ProcessInfo.processInfo.activeProcessorCount * 2`. Why: each child task retains its result until the group iterates — unbounded tasks accumulate results in memory.
</fallback_strategies>

## Confidence Checks

Before finalizing generated or refactored concurrent code, verify ALL:

```
[] No cooperative pool blocking -- no semaphore.wait, Thread.sleep, sync I/O in any async function
[] No continuation leaks -- every withChecked*Continuation resumes on every path (success, failure, cancellation)
[] No unchecked Sendable -- every @unchecked Sendable has documented synchronization (Mutex, NSLock, or actor)
[] Actor reentrancy -- state re-checked after every await inside actors
[] AsyncStream cleanup -- finish() called in onTermination, no infinite sequence without cancellation
[] TaskGroup bounded -- child task count limited for unbounded input
[] MainActor correct -- UI state @MainActor-isolated, no MainActor.run anti-pattern
[] Swift 6.2 ready -- nonisolated async caller-isolation understood, @concurrent used where needed
[] Cancellation handled -- withTaskCancellationHandler for long-running ops, CancellationError caught silently
[] Tests deterministic -- Clock injected, withMainSerialExecutor used, no flaky timing dependencies
[] Compiler flags -- SWIFT_STRICT_CONCURRENCY=complete set, TSan enabled in CI
```

## References

> **Start here** for most tasks: `crash-patterns.md`, `actor-isolation.md`, `sendable-transfer.md`. Then consult the specific reference based on your workflow.

| Reference | When to Read |
|-----------|-------------|
| `references/rules.md` | Do's and Don'ts quick reference: priority rules and critical anti-patterns |
| `references/crash-patterns.md` | Production crash patterns: continuation misuse, cooperative pool deadlocks, TaskGroup OOM, watchdog kills, release-only crashes |
| `references/actor-isolation.md` | Task.init inherits isolation, compile-time isolation, nonisolated deinit, isolated deinit (Swift 6.1+), split isolation, assumeIsolated, actors as advanced tools |
| `references/sendable-transfer.md` | sending keyword, region-based isolation, @unchecked Sendable risks, public type inference, @preconcurrency scope |
| `references/asyncstream-memory.md` | Infinite sequence leaks, continuation.finish(), backpressure policies, withDiscardingTaskGroup, Task.detached stripping |
| `references/swift-6-2-changes.md` | Approachable Concurrency: caller isolation, @concurrent, MainActor default, @preconcurrency runtime crashes |
| `references/migration-strategy.md` | Bottom-up module migration, third-party SDK blockers, global singleton conversion, actor hopping overhead |
| `references/security-concurrency.md` | Token refresh serialization, TOCTOU at await, Keychain serialization, sensitive data, actor double-spend |
| `references/compiler-flags-ci.md` | SWIFT_STRICT_CONCURRENCY, SPM per-target flags, Swift 6.2 feature flags, SwiftLint rules, CI pipeline |
| `references/advanced-patterns.md` | Mutex vs actors, async let vs TaskGroup, isolated parameters, withTaskCancellationHandler, .task modifier, task-locals |
| `references/diagnostics-fix-mapping.md` | Compiler error → fix mapping: "Sending risks data races", "non-sendable capture", "static property not safe", isolation errors |
| `references/cancellation-patterns.md` | Cooperative cancellation, withTaskCancellationHandler, CancellationError handling, timeout patterns, SwiftUI .task |
| `references/memory-retain-cycles.md` | Task retain cycles, weak self patterns, async sequence retention, isolated deinit, testing for leaks |
| `references/core-data-concurrency.md` | NSManagedObject not Sendable, DAO pattern, NSManagedObjectID, actor-isolated context, @MainActor conflicts |
| `references/testing-async.md` | Swift Testing async, confirmation(), Clock injection, withMainSerialExecutor, TSan, deterministic tests |
| `references/testing-debugging.md` | withMainSerialExecutor, Clock injection, TSan, Instruments, deterministic tests, timeouts |
| `references/refactoring-workflow.md` | refactoring/ directory protocol, per-feature plans, severity ordering, PR sizing, verification checklist |
