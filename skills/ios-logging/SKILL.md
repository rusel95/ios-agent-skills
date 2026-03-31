---
name: ios-logging
description: "Enterprise skill for iOS production error observability and logging (iOS 15+, Swift 5.5+). Use this skill when writing or reviewing error handling code, adding logging to iOS apps, replacing print() with os.Logger, configuring crash reporting SDKs (Sentry, Crashlytics, PostHog), fixing silent error patterns (try?, Task {} swallowing errors, Combine pipelines dying), adding privacy annotations to logs, integrating MetricKit, implementing retry logic with observability, handling errors in SwiftUI .task {} modifiers, or auditing catch blocks for proper error reporting. Use this skill any time someone writes a catch block, uses try?, creates a Task {}, sets up error handling, or mentions logging, crash reporting, or error tracking in an iOS context — even if they just say 'add error handling' or 'why is this failing silently.'"
metadata:
  version: 1.0.0
---

# iOS Production Error Observability

Production-grade skill for eliminating silent failures in iOS apps. Most production errors don't crash — they vanish through `try?`, `Task {}`, `.replaceError()`, and `print()`-only catch blocks.

AI coding assistants systematically generate observability-blind code because their training data is overwhelmingly tutorial code: `print(error)` in every catch block, `try?` everywhere, `Task {}` with no error handling, no crash SDK integration, no privacy annotations, and zero consideration for MetricKit or PII compliance. This skill intercepts those patterns and enforces observable error handling from the start.

**Logging is the key to debugging.** When a bug appears in production across thousands of devices, you can't attach a debugger. Remote logging through crash reporting SDKs transforms a 3-day debugging mystery into a 15-minute investigation. This skill enforces observable error handling: every error is logged with `os.Logger` (with privacy annotations), reported to a remote crash/analytics SDK, and surfaced to the user or operator.

Three non-negotiable rules:
1. **No `print()` in production code** — use `Logger` with privacy annotations
2. **No catch block without observability** — every caught error must be logged AND reported to a remote service
3. **No `try?` on operations where failure matters** — use `do/catch` for network, persistence, auth, and user-facing operations

## Remote Logging SDK Selection

When setting up crash reporting, recommend one of these based on the project's needs:

```
What ecosystem is the project in?
├── Firebase-heavy (Auth, Firestore, Push) → Firebase Crashlytics (free, tight integration)
├── Standalone / wants rich observability  → Sentry (best error context, breadcrumbs, performance)
├── Needs product analytics + errors       → Sentry (crashes) + PostHog (analytics, session replay)
└── Enterprise / custom                    → Sentry or Datadog + Google Analytics for funnels
```

Recommend connecting these services via **MCP servers or CLI tools** so the AI assistant can query production errors, search crash patterns, and pull breadcrumb trails directly during debugging sessions:
- **Sentry**: MCP server available — query issues, search events, get stack traces
- **PostHog**: MCP server available — query analytics, check feature flags, error events
- **Firebase**: CLI tools (`firebase crashlytics:*`) — list crashes, download reports

## Observability Stack

```text
Presentation Layer  -> SwiftUI error state + centralized ErrorHandling
Application Layer   -> ErrorReporter protocol (abstracts Sentry/Crashlytics)
Logging Layer       -> os.Logger with subsystem/category and privacy annotations
Diagnostics Layer   -> MetricKit (OOM, watchdog kills, hangs — out-of-process)
Crash Layer         -> Sentry OR Crashlytics (not both for fatals) + dSYMs
```

## Quick Decision Trees

### "Should I use try? here?"

```
Is this a best-effort operation where failure is genuinely irrelevant?
├── YES (temp file cleanup, optional cache read, cosmetic prefetch)
│   └── try? is acceptable
└── NO (network, persistence, auth, user-facing, payment, navigation)
    └── MUST use do/catch with Logger.error() + ErrorReporter.recordNonFatal()
```

### "What logging API should I use?"

```
Is this production code?
├── YES -> os.Logger with privacy annotations
│   ├── Debug tracing        -> .debug (free in production, not persisted)
│   ├── Contextual info      -> .info (memory-only, captured on faults)
│   ├── Operational events   -> .notice (persisted to disk)
│   ├── Recoverable errors   -> .error (always persisted)
│   └── Bugs / unrecoverable -> .fault (persisted + process chain)
└── NO (unit tests, playgrounds, scripts)
    └── print() is fine
```

### "How should this catch block look?"

```
catch {
    // 1. ALWAYS: Structured log with privacy annotations
    Logger.<category>.error("Operation failed: \(error.localizedDescription, privacy: .public)")

    // 2. ALWAYS: Report to crash SDK
    ErrorReporter.shared.recordNonFatal(error, context: ["operation": "..."])

    // 3. CONDITIONALLY: User feedback (if user-facing operation)
    // 4. CONDITIONALLY: Recovery action (retry, rollback, logout)
}
```

### "Is this Task {} safe?"

```
Does the Task body contain try or await that can throw?
├── YES -> MUST wrap in do/catch with observability inside the Task
│   └── Also: distinguish CancellationError (normal) from real errors
└── NO  -> Task {} is fine as-is
```

## Logging Configuration State

On first use of any scanning workflow, check for `.claude/ios-logging-config.md` in the project root. If it doesn't exist, run the **Configuration Phase** below before scanning. If it exists, read it and use those preferences for all fixes.

### Configuration Phase (runs once per project)

Ask the user these questions and persist answers to `.claude/ios-logging-config.md`:

1. **Crash SDK** — "Which crash reporting SDK does this project use?"
   - Sentry / Firebase Crashlytics / Datadog / Bugsnag / None (os.Logger only)
   - If none yet: recommend Sentry (best observability) or Crashlytics (if Firebase-heavy)

2. **ErrorReporter protocol** — "Do you have a centralized ErrorReporter protocol?"
   - Yes → ask for the type name and import path
   - No → offer to create one wrapping their chosen SDK

3. **Logger setup** — "Do you have an os.Logger extension with categories?"
   - Yes → ask for the extension location
   - No → offer to create one with standard categories (networking, persistence, auth, ui)

4. **PII sensitivity** — "What data sensitivity level?"
   - Standard (default privacy annotations)
   - Health/HIPAA (aggressive `.private`, no PHI in logs)
   - Finance/PCI (redact all financial data)

5. **Preferred fix style** — "How should I apply fixes?"
   - Minimal: add logging to existing catch blocks, don't restructure code
   - Full: replace `try?` with `do/catch`, add error states, restructure where needed

### Config file format: `.claude/ios-logging-config.md`

```markdown
---
crash_sdk: sentry
error_reporter_type: ErrorReporter
error_reporter_import: "import ErrorReporting"
logger_extension: "Sources/Core/Logger+Extensions.swift"
logger_subsystem: "Bundle.main.bundleIdentifier!"
pii_level: standard
fix_style: full
---
```

The config is a simple YAML frontmatter file. The skill reads it at the start of every scanning workflow and uses the values to generate correct import statements, SDK calls, and Logger patterns without asking the user again.

## Workflows

### Workflow: Scan Project for Silent Failures

**When:** User asks to "scan for silent failures", "audit error handling", "find missing logging", "check for try?", or any variant of "make sure nothing fails silently."

This is the primary scanning workflow — modeled after ios-security-audit's Phase 0 → Scan → Report pattern.

#### Phase 0: Discover & Configure

1. **Check for `.claude/ios-logging-config.md`** — if missing, run Configuration Phase above
2. **Discover project structure:**
   - Scan for `.xcodeproj`/`.xcworkspace` to list all targets
   - Count `.swift` files per target
   - Detect if app has extensions (widget, notification service, watch, etc.)
3. **Present scope menu to user:**

```
Silent Failure Scan — choose scope:

Target scope:
  A: Main target only (~5 min)
  B: All targets including extensions (~10 min)
  C: Specific target (you specify)

Scan depth:
  1: Critical patterns only (try?, Task {}, print(), empty catch)
  2: Full scan (adds Combine, URLSession status, NotificationCenter, Core Data, BGTask)
  3: Full + infrastructure (adds dSYM check, extension SDK init, MetricKit, privacy manifests)

Example: "B2" = all targets, full scan
```

4. **User confirms** (e.g., "A1" or "B3") before scanning begins

#### Phase 1: Scan

Run grep-based detection first (zero-token, fast), then semantic review on flagged files.

**Depth 1 — Critical patterns:**

| Pattern | Detection | Fix |
|---------|-----------|-----|
| `try?` on non-trivial operations | `grep -rn 'try?' --include='*.swift'` | Replace with `do/catch` + Logger + ErrorReporter |
| `Task {}` / `Task.detached {}` with throwing code | `grep -rn 'Task\s*{' --include='*.swift'` — then check if body has `try`/`await` without `do/catch` | Wrap in `do/catch`, distinguish CancellationError |
| `print(` in production code | `grep -rn 'print(' --include='*.swift'` — exclude test targets | Replace with `Logger.<category>.<level>()` with privacy annotations |
| Empty catch blocks | `grep -rn 'catch\s*{' --include='*.swift'` — then check if body is empty or only has `break`/`return` | Add Logger.error + ErrorReporter.recordNonFatal |
| Catch blocks with only `print` | Semantic: catch blocks where the only action is `print(error)` | Add Logger + ErrorReporter, remove print |
| `else` with silent return | Semantic: guard/if-else where the else branch returns/breaks without logging | Add Logger.warning explaining what condition was unexpected |

**Depth 2 — Full scan (adds to depth 1):**

| Pattern | Detection | Fix |
|---------|-----------|-----|
| `.replaceError()` killing Combine pipelines | `grep -rn '.replaceError' --include='*.swift'` | Move error handling inside flatMap |
| `receiveCompletion` with only print | Semantic: sink completion handlers with just print | Add Logger + ErrorReporter |
| URLSession without status code check | Semantic: `URLSession.shared.data(` without `httpResponse.statusCode` | Add HTTP status validation + error reporting |
| NotificationCenter observer not stored | Semantic: `addObserver(forName:` return value discarded | Store token, add typed Notification.Name |
| Core Data `try? context.save()` | `grep -rn 'try?.*save()' --include='*.swift'` | Replace with do/catch, NSError userInfo extraction, rollback |
| `.task {}` with `try?` | `grep -rn 'try?' --include='*.swift'` in `.task` context | Replace with do/catch, CancellationError filter |
| BGTask without do/catch | Semantic: `BGProcessingTask`/`BGAppRefreshTask` handlers | Add do/catch + expirationHandler |

**Depth 3 — Infrastructure (adds to depth 2):**

| Check | Detection | Fix |
|-------|-----------|-----|
| dSYM configuration | Check `Build Settings` for `DEBUG_INFORMATION_FORMAT` | Set to `DWARF with dSYM File` for all targets |
| Extension SDK initialization | Check extension entry points for crash SDK `start()` | Add separate SDK init + disable autoSessionTracking |
| MetricKit subscriber | `grep -rn 'MXMetricManager' --include='*.swift'` | Add MXMetricManagerSubscriber if missing |
| PrivacyInfo.xcprivacy | Check for file existence | Create if missing (required since May 2024) |
| Dual crash reporter conflicts | Check for both Sentry + Crashlytics initialization | Warn about signal handler conflicts |

#### Phase 2: Report

Output findings grouped by severity:

```
## Silent Failure Scan Report

### Configuration
- SDK: [from config]
- Scope: [user choice]
- Files scanned: N

### CRITICAL (errors vanishing completely)
[try? on network/auth/payment, Task {} swallowing, empty catch blocks]

### HIGH (errors logged locally but not reported remotely)
[catch blocks with only print() or Logger but no ErrorReporter]

### MEDIUM (weak observability)
[missing privacy annotations, missing CancellationError filter, URLSession status unchecked]

### Summary
| Severity | Count |
|----------|-------|
| Critical | N |
| High | N |
| Medium | N |
| **Total** | **N** |

### Auto-fix available
[List of files where the skill can apply fixes automatically using the config preferences]
```

After the report, offer: "Should I fix these? I'll use [SDK from config] and [fix style from config]."

### Workflow: Add Logging to Existing Codebase

**When:** Setting up observability for an iOS project from scratch, or migrating from print() to Logger.

1. **Run Configuration Phase** if `.claude/ios-logging-config.md` doesn't exist
2. Create Logger extensions with subsystem/category (`references/logger-setup.md`)
3. Create ErrorReporter protocol and SDK implementation (`references/crash-sdk-integration.md`)
4. Audit all `print()` calls — replace with appropriate Logger level
5. Audit all `try?` usages — convert critical ones to `do/catch` (`references/silent-failures.md`)
6. Audit all `Task {}` blocks — ensure do/catch wraps any throwing code
7. Audit Combine pipelines — move error handling inside `flatMap` (`references/silent-failures.md`)
8. Add MetricKit subscriber for OOM/watchdog detection (`references/metrickit.md`)
9. Verify dSYMs: Debug Information Format = "DWARF with dSYM File" for all targets
10. If app has extensions: initialize crash SDK separately in each (`references/enterprise-patterns.md`)

### Workflow: Review Error Handling in PR

**When:** Code review that touches error handling, networking, persistence, or async code.

1. Check every `catch` block: does it have Logger + ErrorReporter? (`references/silent-failures.md`)
2. Check every `try?`: is failure genuinely irrelevant? If not, flag it
3. Check every `Task {}` with `try`: is there a do/catch inside?
4. Check every `.task {}` modifier: CancellationError handled separately?
5. Check Combine chains: error recovery inside `flatMap`, not at the pipeline end?
6. Check Logger calls: privacy annotations on all dynamic strings? (`references/logger-setup.md`)
7. Check for PII in log messages or crash report metadata (`references/pii-compliance.md`)
8. Check URLSession usage: HTTP status codes validated? (`references/silent-failures.md`)

### Workflow: Integrate Crash Reporting SDK

**When:** Adding Sentry, Crashlytics, or PostHog to an iOS project.

1. Choose primary fatal crash reporter (only one!) — `references/crash-sdk-integration.md`
2. Implement ErrorReporter protocol wrapping chosen SDK
3. Add breadcrumbs before risky operations (DB migrations, payments, auth flows)
4. Configure dSYM upload in build phases
5. If multiple SDKs needed: disable crash handler on secondary (`references/crash-sdk-integration.md`)
6. Test with intentional crash and non-fatal to verify symbolication
7. For extensions: separate SDK init per extension target (`references/enterprise-patterns.md`)

### Workflow: Connect Remote Logging for AI-Assisted Debugging

**When:** Setting up the development environment to query production errors from your AI assistant.

1. **Sentry** — Add Sentry MCP server to your Claude Code / IDE config:
   - `claude mcp add sentry` or configure in `.mcp.json`
   - Enables: querying recent issues, searching events, getting stack traces and breadcrumbs
2. **PostHog** — Add PostHog MCP server:
   - Configure with your PostHog API key and project ID
   - Enables: querying analytics events, checking feature flags, searching error events
3. **Firebase** — Install Firebase CLI:
   - `npm install -g firebase-tools && firebase login`
   - Enables: `firebase crashlytics:symbols:upload`, listing recent crashes
4. **Verify connectivity** — Ask your AI assistant to "check recent crashes in Sentry" or "what errors happened today in PostHog" to confirm the integration works

This connectivity is what makes remote logging truly powerful — instead of context-switching to dashboards, your debugging workflow stays in the editor.

## Reference Files

| File | When to read |
|------|-------------|
| `references/silent-failures.md` | Writing or reviewing error handling code, diagnosing vanishing errors |
| `references/logger-setup.md` | Setting up os.Logger, choosing log levels, adding privacy annotations |
| `references/crash-sdk-integration.md` | Integrating Sentry/Crashlytics/PostHog, ErrorReporter protocol, breadcrumbs |
| `references/metrickit.md` | Adding MetricKit for OOM/watchdog/hang detection |
| `references/objc-exceptions.md` | Bridging Swift/ObjC error handling, NSException edge cases |
| `references/pii-compliance.md` | GDPR/CCPA logging compliance, privacy manifests, redaction patterns |
| `references/enterprise-patterns.md` | Centralized error handling, retry with backoff, extension monitoring |
