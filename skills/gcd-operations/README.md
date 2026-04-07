# GCD & OperationQueue Concurrency

Enterprise-grade concurrency skill for Grand Central Dispatch and OperationQueue on Apple platforms (iOS, macOS, watchOS, tvOS, visionOS). Prevents the most dangerous concurrency bugs — deadlocks, thread explosion, and data races — through actionable patterns and detection checklists.

## Benchmark Results

Tested on **24 scenarios** with **62 discriminating assertions**.

### Results Summary

| Model | With Skill | Without Skill | Delta | A/B Quality |
| --- | --- | --- | --- | --- |
| **Sonnet 4.6** | 62/62 (100%) | 58/62 (93.5%) | **+6.5%** | **15W 9T 0L** (avg 8.6 vs 8.1) |
| **GPT-5.4** | 60/62 (96.8%) | 55/62 (88.7%) | **+8.1%** | **18W 1T 5L** (avg 8.6 vs 7.8) |
| **Gemini 3.1 Pro** | 19/19 (100%) | 5/19 (26.3%) | **+74.0%** | **12W** 0T 1L (avg 8.8 vs 7.1) |

> A/B Quality: blind judge scores each response 0–10 and picks the better one without knowing which used the skill. Position (A/B) is randomized across evals to prevent bias.

### Results (Sonnet 4.6)

| Metric | Value |
| --- | --- |
| With Skill | 62/62 (100%) |
| Without Skill | 58/62 (93.5%) |
| Delta | **+6.5%** |
| A/B Quality | **15W 9T 0L** (avg 8.6 vs 8.1) |

**Interpretation:** Sonnet 4.6 has a strong GCD baseline (93.5%) — it knows most patterns. The skill adds the 4 assertions it misses: WWDC 2017-706 queue architecture guidance, `.background` halting in Low Power Mode, `dispatchPrecondition` removed in release builds, and specific lock selection rationale. A/B confirms with 15 wins and zero losses.

### Results (GPT-5.4)

| Metric | Value |
| --- | --- |
| With Skill | 60/62 (96.8%) |
| Without Skill | 55/62 (88.7%) |
| Delta | **+8.1%** |
| A/B | **18W 1T 5L** (avg 8.6 vs 7.8) |

**Interpretation:** On the refreshed strict regrade, GPT-5.4 is a strong GCD baseline at 88.7% without the skill and rises to 96.8% with it. The recovered gaps are concrete implementation details: tracing TSan call paths back to the racing access sites, balanced `DispatchGroup` cleanup on early returns, global-queue barrier misuse, missing KVO notifications in `AsyncOperation`, and unsafe stored `os_unfair_lock` usage. Two with-skill misses remain: it still does not explicitly call out the original missing `isCancelled` check in `operation-queue-complex`, and it discusses blocking I/O without directly stating that `Data(contentsOf:)` worsens thread explosion. Blind A/B also favors the skill at 18W 1T 5L with higher average quality (8.6 vs 7.8).

> Raw data:
> `workspaces/ios/gcd-operationqueue/iteration-2/benchmark-gpt-5-4.json`
> `gcd-operationqueue-workspace/benchmark-sonnet-4-6.json`

### Benchmark Cost Estimate

| Step | Formula | Tokens |
| --- | --- | --- |
| Eval runs (with_skill) | 24 × 35k | 840k |
| Eval runs (without_skill) | 24 × 12k | 288k |
| Grading (48 runs × 5k) | 48 × 5k | 240k |
| **Total** | | **~1.4M** |
| **Est. cost (Sonnet 4.6)** | ~$5.4/1M | **~$8** |

> Token estimates based on sampled timing.json files. Blended rate ~$5.4/1M for Sonnet 4.6 ($3 input + $15 output, ~80/20 ratio).

### Key Discriminating Assertions (GPT-5.4 — missed without skill)

GPT-5.4 now misses 7 of 62 assertions without the skill; 6 of those are recovered by the skill, which lifts the score to 96.8%.

| Topic | Assertion | Why It Matters |
| --- | --- | --- |
| debugging | Traces the call paths - NetworkManager callback vs ProductCell configure | Connects TSan output back to the concrete racing read/write sites. |
| dispatch-primitives | Identifies deinit must call `timer?.cancel()` not just set to nil | Prevents leaked dispatch sources and callbacks firing after teardown. |
| dispatch-primitives | Identifies barrier on global queue is silently ignored | Catches a synchronization bug that looks correct but provides no protection. |
| dispatch-primitives | Identifies weak self guard returns without `leave()` - causes hang | Prevents `DispatchGroup` deadlocks from unbalanced enter/leave paths. |
| operation-queue | CRITICAL: Identifies missing KVO notifications (`willChangeValue`/`didChangeValue`) | `AsyncOperation` correctness depends on KVO for `isExecuting` and `isFinished`. |
| thread-safety | Identifies `os_unfair_lock` as stored property causes memory corruption | Prevents a Swift-specific lock storage bug that can corrupt memory. |


## What This Skill Changes

| Without Skill | With Skill |
| --- | --- |
| AI scatters `DispatchQueue.global().async` throughout codebase | 3-4 well-defined queue subsystems with target queue hierarchies (WWDC 2017-706) |
| AI uses `DispatchQueue.main.sync` causing deadlocks | `async` by default, `dispatchPrecondition` at API boundaries |
| AI stores `os_unfair_lock` as Swift property (memory corruption) | `OSAllocatedUnfairLock` (iOS 16+) or `NSLock` (any iOS) — safe by construction |
| AI uses `DispatchSemaphore` as a mutex (no priority donation) | Lock selection hierarchy: NSLock for general, barrier for R/W, semaphore only for rate-limiting |
| AI uses barriers on global queues (silently ignored) | Custom concurrent queues with explicit barrier for reader-writer pattern |
| AI creates `AsyncOperation` without KVO or thread-safe state | Complete AsyncOperation base class with KVO, barrier-protected state, cancel-before-start handling |
| AI leaves `DispatchGroup.enter()` without `defer { group.leave() }` | Balanced enter/leave with `defer` on every code path |
| AI mixes `DispatchSemaphore.wait()` with Swift Concurrency (deadlock) | Clear migration mapping: what to migrate vs keep as GCD |
| AI generates concurrent code without Thread Sanitizer verification | TSan in CI, `dispatchPrecondition` at boundaries, stress tests with `concurrentPerform` |

## Install

```bash
npx skills add git@git.epam.com:epm-ease/research/agent-skills.git --skill gcd-operationqueue --copy
```

Verify installation by asking your AI agent to review concurrent code — it should detect deadlock patterns, recommend proper lock selection, and reference `dispatchPrecondition`.

## When to Use

- Reviewing or writing GCD/OperationQueue concurrent code
- Fixing deadlocks, data races, or thread explosion issues
- Implementing thread-safe collections or caches
- Creating AsyncOperation subclasses for OperationQueue
- Selecting the right lock type (NSLock, OSAllocatedUnfairLock, barriers)
- Using DispatchGroup, DispatchWorkItem, or DispatchSemaphore correctly
- Setting up DispatchSource timers or DispatchIO file operations
- Debugging concurrency issues with Thread Sanitizer and Instruments
- Migrating specific GCD patterns to Swift Concurrency
- Establishing concurrency standards across a team

## Author

[Ruslan Popesku](https://git.epam.com/Ruslan_Popesku)
