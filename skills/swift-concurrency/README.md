# Swift Concurrency

Enterprise-grade skill for Swift Concurrency on Apple platforms. Prevents the most dangerous production crash patterns — cooperative pool deadlocks, continuation misuse, actor reentrancy corruption, and Sendable violations — through actionable rules, decision trees, and detection checklists. Covers Swift 6.2 Approachable Concurrency, enterprise migration strategies, and security-specific concurrency patterns.

## What This Skill Changes

| Without Skill | With Skill |
| --- | --- |
| AI uses `DispatchSemaphore.wait()` in async contexts (deadlocks cooperative pool) | Continuation-based bridging with `withCheckedThrowingContinuation`, cooperative pool awareness |
| AI uses `@unchecked Sendable` to silence compiler (hides data races) | `sending` parameter, `Mutex<State>`, actor wrapping — compiler-verified safety |
| AI assumes actor state unchanged after `await` (reentrancy bugs) | Re-check-after-await pattern, in-flight Task coalescing for deduplication |
| AI creates `Task {}` inside `@MainActor` expecting background execution | Understands `Task.init` inherits caller isolation; uses `@concurrent` or `nonisolated` for background |
| AI forgets `continuation.finish()` in AsyncStream (resource leaks) | `onTermination` handler pattern, backpressure policy selection, `withDiscardingTaskGroup` for services |
| AI uses `MainActor.run {}` for isolation (runtime-only, unverifiable) | Static `@MainActor` annotation — compiler-verified at every call site |
| AI ignores Swift 6.2 caller-side isolation change (silent main-thread hangs) | Explicit `@concurrent` for CPU-intensive work, awareness of `nonisolated(nonsending)` default |
| AI generates async tests with timing dependencies (flaky CI) | `withMainSerialExecutor` for determinism, `Clock` injection, `AsyncStream.makeStream` for control |
| AI leaves security-critical code vulnerable to TOCTOU at `await` points | Transaction-style actor methods, token refresh serialization, Keychain actor wrapping |

## Install

```bash
npx skills add git@git.epam.com:epm-ease/research/agent-skills.git --skill swift-concurrency
```

Verify installation by asking your AI agent to review async/await code — it should detect cooperative pool blocking, check continuation safety, warn about actor reentrancy, and reference Swift 6.2 behavioral changes.

## When to Use

- Writing or reviewing async/await, actor, or TaskGroup code
- Diagnosing data races, deadlocks, or continuation crashes
- Migrating a codebase to `SWIFT_STRICT_CONCURRENCY=complete` or Swift 6 mode
- Adopting Swift 6.2 Approachable Concurrency (`@concurrent`, `nonisolated(nonsending)`)
- Implementing Sendable conformance or using `sending` parameters
- Using AsyncStream, AsyncSequence, or AsyncChannel correctly
- Fixing concurrency-related security issues (TOCTOU, token races, Keychain access)
- Setting up Thread Sanitizer and `LIBDISPATCH_COOPERATIVE_POOL_STRICT` in CI
- Creating deterministic async tests with Clock injection
- Establishing Swift Concurrency standards across a team

## Available Workflows

Ask your AI agent to run any of these workflows:

| Workflow | What It Does |
| --- | --- |
| **Audit Existing Codebase** | Scans for crash patterns, Sendable violations, actor reentrancy, AsyncStream leaks, and security issues. Creates a severity-ranked refactoring plan. |
| **Migrate Module to Strict Concurrency** | Bottom-up migration to `SWIFT_STRICT_CONCURRENCY=complete` or Swift 6 mode. Audits third-party SDKs, fixes global state, enables per-target flags. |
| **Create New Concurrent Feature** | Guides isolation model selection, concurrency structure, Sendable compliance, cancellation, and deterministic testing from scratch. |
| **Fix Production Crash** | Classifies crash type (continuation, deadlock, watchdog, reentrancy), reproduces with targeted test, applies fix with TSan verification. |

## Benchmark Results

Tested on **21 scenarios** with **40 discriminating assertions**.

### Results Summary

| Model | With Skill | Without Skill | Delta | A/B Quality |
| --- | --- | --- | --- | --- |
| **Sonnet 4.6** | 40/40 (100%) | 27/40 (67.5%) | **+32.5%** | **15W 9T 0L** (avg 8.9 vs 8.5) |
| **GPT-5.4** | 38/40 (95.0%) | 32/40 (80.0%) | **+15.0%** | **21W 0T 0L** (avg 9.0 vs 7.6) |
| **Gemini 3.1 Pro** | 40/40 (100%) | 18/40 (45.0%) | **+55.0%** | **21W** 0T 0L (avg 9.2 vs 7.3) |

> A/B Quality: blind judge scores each response 0–10 and picks the better one without knowing which used the skill. Position (A/B) is randomized across evals to prevent bias.

### Results (Sonnet 4.6)

| Metric | Value |
| --- | --- |
| With Skill | 40/40 (100%) |
| Without Skill | 27/40 (67.5%) |
| Delta | **+32.5%** |
| A/B Quality | **15W 9T 0L** (avg 8.9 vs 8.5) |

**Interpretation:** Sonnet 4.6 without the skill misses 13 of 40 assertions that it consistently passes with the skill. The +32.5% delta reflects the skill's value on assertions that actually matter — cooperative-pool sizing, `withDiscardingTaskGroup`, `sending` parameter, cancellation handler constraints, and security-specific concurrency patterns. A/B confirms with 15 wins and zero losses.

### Results (GPT-5.4)

| Metric | Value |
| --- | --- |
| With Skill | 38/40 (95.0%) |
| Without Skill | 32/40 (80.0%) |
| Delta | **+15.0%** |
| A/B | **21W 0T 0L** (avg 9.0 vs 7.6) |

**Interpretation:** GPT-5.4 has a solid Swift Concurrency baseline at 80.0% without the skill, rising to 95.0% with it — a +15% delta. The recovered gaps concentrate in cooperative-pool awareness: GPT-5.4 without the skill consistently misses `LIBDISPATCH_COOPERATIVE_POOL_STRICT=1` as a CI testing tool, the CPU-core-count cap on the cooperative pool, `Clock` protocol injection for testable sleeps, and security-specific concurrency patterns (actor coalescing for auth, RFC 6749 single-use refresh token rotation). Blind A/B strongly favors the skill at 21W 0T 0L — no losses — with average quality 9.0 vs 7.6.

### Key Discriminating Assertions — GPT-5.4

| Topic | Assertion | Why It Matters |
| --- | --- | --- |
| cooperative-pool | Cooperative pool is capped at CPU-core count (4-10 threads on iPhones) | Explains why blocked async work deadlocks faster on device than simulator. |
| cooperative-pool | `LIBDISPATCH_COOPERATIVE_POOL_STRICT=1` exposes cooperative pool blocking in tests | Makes pool exhaustion reproducible in CI before it hits production. |
| cooperative-pool | `Clock` protocol injection for testable `sleep` durations | Lets retry/backoff logic run deterministically in tests. |
| migration | `LIBDISPATCH_COOPERATIVE_POOL_STRICT=1` for exposing blocking during migration | Surfaces regressions as tests fail, not as watchdog crashes. |
| security-concurrency | Convert `BiometricAuthManager` to actor with Task coalescing | Prevents concurrent authentication races at the security boundary. |
| security-concurrency | OAuth token rotation (RFC 6749) requires single-use refresh tokens | Prevents replay attacks during concurrent refresh races. |

> Raw data:
> `workspaces/ios/swift-concurrency/iteration-6/benchmark-gpt-5-4.json`

## Author

[Ruslan Popesku](https://git.epam.com/Ruslan_Popesku)
