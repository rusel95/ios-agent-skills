#!/usr/bin/env python3
"""
Grades all ios-logging eval runs against assertions.
Reads each response.md and checks if assertions are met.
Outputs grading.json per run + aggregate benchmark.json + benchmark.md.

Topic-based evals, 27 scenarios, Sonnet 4.6.
"""
import json, os, re, sys
from pathlib import Path

WORKSPACE = Path(__file__).parent / "iteration-2"
EVALS_PATH = Path(__file__).parent.parent / "evals.json"

def load_evals():
    with open(EVALS_PATH) as f:
        return json.load(f)

def read_response(eval_name, variant):
    path = WORKSPACE / eval_name / variant / "outputs" / "response.md"
    if path.exists():
        return path.read_text()
    return ""

def check_assertion(response_text, assertion_id, assertion_text):
    """Check if an assertion is satisfied by the response text.
    Returns (passed: bool, evidence: str) with matched keywords."""
    r = response_text.lower().replace("*", "").replace("`", "")

    def kw_check(required_groups, label=""):
        """Check that at least one keyword from each group is found.
        Returns (passed, evidence_str)."""
        matched = []
        missed = []
        for group in required_groups:
            found = [kw for kw in group if kw in r]
            if found:
                matched.append(found[0])
            else:
                missed.append(group[0] if group else "?")
        passed = len(missed) == 0
        if passed:
            return True, f"Matched: {matched}"
        else:
            return False, f"Matched: {matched}, Missing group containing: {missed}"

    checks = {
        # 1. Task error swallowing
        "TE1.1": lambda: kw_check([
            ["@discardableresult", "discardable", "task {} swallow", "task swallow", "silently discard", "error is silently", "silently ignored"]
        ]),
        "TE1.2": lambda: kw_check([
            ["try? erases", "try? destroys", "diagnostic information", "error type", "all information lost", "all context lost", "destroys the error", "discards the error"]
        ]),
        "TE1.3": lambda: kw_check([
            ["logger.error", "logger.", "os.logger", "os_log", "import os"],
            ["privacy:", "privacy annotation", ".public", ".private"]
        ]),
        "TE1.4": lambda: kw_check([
            ["errorreporter", "recordnonfatal", "sentry", "crashlytics", "crash report", "crash sdk"]
        ]),

        # 2. Combine pipeline death
        "CP2.1": lambda: kw_check([
            ["kills the", "terminates the", "pipeline permanently", "stops publishing", "failure type to never", "permanently dead", "permanently terminat"]
        ]),
        "CP2.2": lambda: kw_check([
            ["inside flatmap", "within flatmap", "error handling inside", "catch inside", "inside the flatmap", "move .catch", "move the .catch", "move error"]
        ]),
        "CP2.3": lambda: kw_check([
            ["errorreporter", "recordnonfatal", "sentry", "crashlytics", "crash report", "error report"]
        ]),

        # 3. Audit ViewModel
        "AV3.1": lambda: kw_check([
            ["loadorders"],
            ["placeorder"],
            ["deleteorder", "all three", "all 3"]
        ]),
        "AV3.2": lambda: kw_check([
            ["confirmation email", "sendemail", "sendconfirmation"],
            ["still runs", "still executes", "even if", "regardless", "logic error", "stale"]
        ]),
        "AV3.3": lambda: kw_check([
            ["print(", "print is not", "invisible in production", "stdout", "not part of", "not visible"]
        ]),
        "AV3.4": lambda: kw_check([
            ["logger.", "os.logger"],
            ["privacy:", ".public", ".private", "privacy annotation"]
        ]),
        "AV3.5": lambda: kw_check([
            ["errorreporter", "recordnonfatal", "sentry", "crashlytics", "crash report", "sentrysdK.capture"]
        ]),

        # 4. Print replacement
        "PR4.1": lambda: kw_check([
            ["os.logger", "import os", "logger(subsystem"]
        ]),
        "PR4.2": lambda: kw_check([
            ["bundle.main.bundleidentifier"],
            ["category", "networking", "auth"]
        ]),
        "PR4.3": lambda: kw_check([
            ["privacy annotation", "privacy:", ".private", "redacted", "<private>"]
        ]),
        "PR4.4": lambda: kw_check([
            [".debug", "debug level", "debug messages"],
            ["zero cost", "free", "no cost", "optimized away", "no overhead", "no performance", "not persisted"]
        ]),

        # 5. Privacy annotations
        "PA5.1": lambda: kw_check([
            ["authtoken", "token"],
            ["should not", "don't log", "never log", "must not", "remove", "shouldn't", ".sensitive"]
        ]),
        "PA5.2": lambda: (True, "Matched: [mask: .hash]") if ("mask: .hash" in r or "mask:.hash" in r or "private(mask:" in r) else (False, "Missing: mask: .hash pattern"),
        "PA5.3": lambda: kw_check([
            ["<private>", "redacted", "without annotation"],
            ["production", "log"]
        ]),

        # 6. Crash SDK selection
        "CS6.1": lambda: kw_check([
            ["8 non-fatal", "eight non-fatal", "8 exception"],
            ["crashlytics"]
        ]),
        "CS6.2": lambda: kw_check([
            ["signal handler", "conflict", "both for fatal", "both for crash"]
        ]),
        "CS6.3": lambda: kw_check([
            ["protocol", "abstraction", "errorreporter", "wrapper", "abstract"]
        ]),

        # 7. URLSession status codes
        "US7.1": lambda: kw_check([
            ["4xx", "5xx", "statuscode", "status code", "http error"],
            ["doesn't throw", "does not throw", "not throw", "won't throw", "no error", "no exception"]
        ]),
        "US7.2": lambda: kw_check([
            ["breadcrumb", "addbreadcrumb"]
        ]),
        "US7.3": lambda: kw_check([
            ["logger.", "os.logger"],
            ["privacy:", ".public", "privacy annotation"]
        ]),
        "US7.4": lambda: kw_check([
            ["errorreporter", "recordnonfatal", "sentrysdK.capture", "crashlytics", "record(error"]
        ]),

        # 8. Dual SDK conflicts
        "DC8.1": lambda: kw_check([
            ["signal handler", "sigabrt", "sigsegv", "sigbus"],
            ["conflict", "last registered", "only one", "overwrite", "replaces"]
        ]),
        "DC8.2": lambda: kw_check([
            ["enablecrashhandler", "disable crash", "crash handler", "enablecrashhandling"],
            ["false", "disable"]
        ]),
        "DC8.3": lambda: kw_check([
            ["metrickit"],
            ["oom", "watchdog", "out-of-process", "out of process"]
        ]),

        # 9. Centralized error handling
        "CE9.1": lambda: kw_check([
            ["errorhandler", "error handler", "errorhandling"],
            ["observableobject", "observable", "environment"]
        ]),
        "CE9.2": lambda: kw_check([
            ["categorizederror", "categorized", "error categor"],
            ["retryable", "nonretryable", "requireslogout", "logout"]
        ]),
        "CE9.3": lambda: kw_check([
            ["error boundar", "swiftui lacks", "no error boundar", "no built-in error", "unlike react"]
        ]),

        # 10. Retry with backoff
        "RB10.1": lambda: kw_check([
            ["after all retries", "all retries exhausted", "only after", "final failure", "last attempt", "exhausted"],
            ["report", "crash", "sentry", "nonfatal", "recordnonfatal"]
        ]),
        "RB10.2": lambda: kw_check([
            ["breadcrumb", "addbreadcrumb"],
            ["retry", "attempt"]
        ]),
        "RB10.3": lambda: kw_check([
            [".warning", "logger.networking.warning", "logger.warning"],
            ["retry", "attempt", "intermediate"]
        ]),
        "RB10.4": lambda: kw_check([
            ["jitter"],
            ["random", "double.random", ".random(in"]
        ]),

        # 11. App extensions
        "AE11.1": lambda: kw_check([
            ["separate process", "own process", "sandboxed process", "different process"]
        ]),
        "AE11.2": lambda: kw_check([
            ["initialize separately", "init separately", "own initialization", "initialize crash", "sentrysdK.start", "sdk.start"],
            ["extension", "widget"]
        ]),
        "AE11.3": lambda: kw_check([
            ["dsym", "dsyms"],
            ["extension", "each target", "each extension", "all target"]
        ]),
        "AE11.4": lambda: kw_check([
            ["autosessiontracking", "session tracking", "enableautosessiontracking"],
            ["disable", "false"]
        ]),

        # 12. MetricKit purpose
        "MK12.1": lambda: kw_check([
            ["out-of-process", "out of process", "separate process", "system process", "outside the app"]
        ]),
        "MK12.2": lambda: kw_check([
            ["oom", "out of memory", "watchdog"],
            ["miss", "catch", "detect", "invisible", "can't"]
        ]),
        "MK12.3": lambda: kw_check([
            ["share with app developer", "opt-in", "opt in"]
        ]),
        "MK12.4": lambda: kw_check([
            ["use both", "alongside", "complement", "in addition", "together"]
        ]),

        # 13. PII/GDPR compliance
        "PG13.1": lambda: kw_check([
            ["http bod", "request bod", "response bod", "auth header", "url path"],
            ["leak", "contain", "expos", "risk"]
        ]),
        "PG13.2": lambda: kw_check([
            ["privacyinfo", "privacy manifest", ".xcprivacy", "may 2024"]
        ]),
        "PG13.3": lambda: kw_check([
            ["att", "app tracking transparency"],
            ["not require", "doesn't require", "does not require", "not tracking", "not considered"]
        ]),
        "PG13.4": lambda: (True, "Matched: [mask: .hash]") if ("mask: .hash" in r or "mask:.hash" in r or "private(mask:" in r) else (False, "Missing: mask: .hash pattern"),

        # 14. CancellationError
        "CR14.1": lambda: kw_check([
            ["cancellationerror", "cancellation error"],
            ["view disappear", "normal", "lifecycle", "expected", "not a failure", "not an error"]
        ]),
        "CR14.2": lambda: kw_check([
            ["catch is cancellationerror", "catch _ is cancellationerror", "is cancellationerror", "case is cancellation"]
        ]),
        "CR14.3": lambda: kw_check([
            ["cancellation"],
            ["should not", "don't report", "not report", "skip", "ignore", "noise", "shouldn't"]
        ]),

        # 15. Core Data save
        "CD15.1": lambda: kw_check([
            ["try?"],
            ["validation", "merge conflict", "constraint", "core data"]
        ]),
        "CD15.2": lambda: kw_check([
            ["nserror", "as nserror"],
            ["userinfo", "detailederror", "detailedErrors"]
        ]),
        "CD15.3": lambda: kw_check([
            ["rollback"]
        ]),

        # 16. HIPAA logging strategy
        "HL16.1": lambda: kw_check([
            ["hipaa", "health", "phi", "protected health", "medical"]
        ]),
        "HL16.2": lambda: kw_check([
            ["privacyinfo", "privacy manifest", ".xcprivacy", "may 2024"]
        ]),
        "HL16.3": lambda: kw_check([
            ["redactor", "@redacted", "property wrapper", "redaction"],
            ["model", "string", "pii", "mask"]
        ]),
        "HL16.4": lambda: kw_check([
            ["metrickit"]
        ]),

        # 17. Background task errors
        "BT17.1": lambda: kw_check([
            ["task {", "task{"],
            ["do/catch", "do {", "do{", "error handling", "try"]
        ]),
        "BT17.2": lambda: kw_check([
            ["expirationhandler", "expiration handler", "expiration"]
        ]),
        "BT17.3": lambda: kw_check([
            ["sigkill", "watchdog", "metrickit", "os kill", "system kill"]
        ]),

        # 18. ObjC bridge edge case
        "OB18.1": lambda: kw_check([
            ["nsexception", "objective-c exception", "objc exception"],
            ["not caught", "won't catch", "doesn't catch", "cannot catch", "will not catch", "never execute", "never catch", "will never", "do/catch will not"]
        ]),
        "OB18.2": lambda: (True, f"Matched: {sum(1 for x in ['out-of-bounds', 'out of bounds', 'kvo', 'unrecognized selector', 'nsrangeexception'] if x in r)} of 5 triggers") if sum(1 for x in ["out-of-bounds", "out of bounds", "kvo", "unrecognized selector", "nsrangeexception"] if x in r) >= 2 else (False, "Fewer than 2 NSException triggers listed"),
        "OB18.3": lambda: kw_check([
            ["bridge", "objc bridge", "swift-objc", "swift to objc"],
            ["non-nil", "return value", "nserror", "catch block never", "silently lost", "error is lost"]
        ]),

        # 19. Breadcrumbs usage
        "BC19.1": lambda: kw_check([
            ["breadcrumb"],
            ["timestamp", "buffer", "attach", "event", "trail"]
        ]),
        "BC19.2": lambda: kw_check([
            ["breadcrumb"],
            ["migration", "payment", "auth", "checkout", "database", "risky"]
        ]),
        "BC19.3": lambda: kw_check([
            ["crashlytics"],
            ["plain string", "string only", "no structured", "limited", "no data", "log("]
        ]),

        # 20. dSYM setup
        "DS20.1": lambda: kw_check([
            ["dsym", "debug symbol"]
        ]),
        "DS20.2": lambda: kw_check([
            ["dwarf with dsym", "dwarf with dsym file", "debug information format"]
        ]),
        "DS20.3": lambda: kw_check([
            ["dsym"],
            ["all target", "each target", "extension", "widget", "every target"]
        ]),

        # 21. SwiftUI .task modifier
        "ST21.1": lambda: kw_check([
            [".task"],
            ["non-throwing", "doesn't throw", "does not throw", "async -> void", "async->void", "no throws", "void"]
        ]),
        "ST21.2": lambda: kw_check([
            ["error state", "showerror", "errorstate", "errorMessage", "loading forever", "indefinite", "spinner"]
        ]),
        "ST21.3": lambda: kw_check([
            ["cancellationerror", "cancellation"],
            ["separate", "distinguish", "filter", "ignore", "not a failure"]
        ]),

        # 22. Operational PII leaks
        "OL22.1": lambda: kw_check([
            ["header", "authorization", "bearer"],
            ["token", "secret", "credential", "pii", "sensitive"]
        ]),
        "OL22.2": lambda: kw_check([
            ["body", "httpbody"],
            ["pii", "personal", "user data", "password", "sensitive"]
        ]),
        "OL22.3": lambda: kw_check([
            ["url", "path", "status"],
            ["privacy:", ".public", "only log"]
        ]),

        # 23. ErrorReporter protocol
        "ER23.1": lambda: kw_check([
            ["protocol", "errorreporter", "abstraction"]
        ]),
        "ER23.2": lambda: kw_check([
            ["swap", "switch", "replace", "vendor", "migrat"]
        ]),
        "ER23.3": lambda: kw_check([
            ["test", "mock", "testab"]
        ]),

        # 24. Combine error reporting
        "CER24.1": lambda: kw_check([
            [".failure", "receivecompletion", "completion"],
            ["dead", "terminat", "permanently", "stop"]
        ]),
        "CER24.2": lambda: kw_check([
            ["inside flatmap", "within flatmap", ".catch", "trycatch"],
            ["alive", "outer", "keep"]
        ]),
        "CER24.3": lambda: kw_check([
            ["logger", "os.logger"],
            ["errorreporter", "sentry", "crash", "recordnonfatal"]
        ]),

        # 25. MCP connectivity
        "MC25.1": lambda: kw_check([
            ["mcp", "model context protocol"],
            ["sentry", "query", "issue"]
        ]),
        "MC25.2": lambda: kw_check([
            ["claude mcp add", ".mcp.json", "mcp config", "mcp server"]
        ]),
        "MC25.3": lambda: kw_check([
            ["posthog"]
        ]),

        # 26. Notification silent failures
        "NF26.1": lambda: kw_check([
            ["token", "observer", "return value"],
            ["store", "retain", "deallocat", "hold", "discard", "not stored"]
        ]),
        "NF26.2": lambda: kw_check([
            ["string", "typo", "fragile", "raw string"]
        ]),
        "NF26.3": lambda: kw_check([
            ["notification.name", "typed", "constant", "static"]
        ]),

        # 27. Non-fatal vs crash importance
        "NF27.1": lambda: kw_check([
            ["10", "20", "30"],
            ["%", "percent", "session"]
        ]),
        "NF27.2": lambda: kw_check([
            ["non-fatal", "nonfatal", "non fatal"],
            ["primary", "silent", "important", "more", "greater"]
        ]),
        "NF27.3": lambda: kw_check([
            ["8 non-fatal", "eight non-fatal", "8 exception", "8 errors"],
            ["crashlytics"]
        ]),
    }

    checker = checks.get(assertion_id)
    if checker:
        passed, evidence = checker()
        return passed, evidence
    return False, f"No checker defined for {assertion_id}"


def grade_run(eval_entry, variant):
    eval_name = eval_entry["name"]
    response = read_response(eval_name, variant)
    if not response:
        return None

    expectations = []
    for assertion in eval_entry["assertions"]:
        passed, evidence = check_assertion(response, assertion["id"], assertion["text"])
        expectations.append({
            "text": assertion["text"],
            "passed": passed,
            "evidence": evidence
        })

    grading = {
        "eval_id": eval_entry["id"],
        "eval_name": eval_name,
        "variant": variant,
        "expectations": expectations,
        "pass_count": sum(1 for e in expectations if e["passed"]),
        "total": len(expectations)
    }

    # Save grading.json
    out_dir = WORKSPACE / eval_name / variant
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "grading.json"
    with open(out_path, "w") as f:
        json.dump(grading, f, indent=2)

    return grading


def generate_benchmark(all_gradings, evals_data):
    with_skill = [g for g in all_gradings if g and g["variant"] == "with_skill"]
    without_skill = [g for g in all_gradings if g and g["variant"] == "without_skill"]

    ws_pass = sum(g["pass_count"] for g in with_skill)
    ws_total = sum(g["total"] for g in with_skill)
    wo_pass = sum(g["pass_count"] for g in without_skill)
    wo_total = sum(g["total"] for g in without_skill)

    # By topic
    topics = {}
    for ev in evals_data["evals"]:
        topic = ev["topic"]
        if topic not in topics:
            topics[topic] = {"with_skill": {"pass": 0, "total": 0}, "without_skill": {"pass": 0, "total": 0}}

    for g in all_gradings:
        if not g:
            continue
        ev = next((e for e in evals_data["evals"] if e["name"] == g["eval_name"]), None)
        if ev:
            topic = ev["topic"]
            topics[topic][g["variant"]]["pass"] += g["pass_count"]
            topics[topic][g["variant"]]["total"] += g["total"]

    by_topic = {}
    for topic, data in topics.items():
        ws = data["with_skill"]
        wo = data["without_skill"]
        ws_rate = (ws["pass"] / ws["total"] * 100) if ws["total"] > 0 else 0
        wo_rate = (wo["pass"] / wo["total"] * 100) if wo["total"] > 0 else 0
        by_topic[topic] = {
            "with_skill": {**ws, "rate": round(ws_rate, 1)},
            "without_skill": {**wo, "rate": round(wo_rate, 1)},
            "delta": round(ws_rate - wo_rate, 1)
        }

    # Per-eval breakdown
    per_eval = []
    for ev in evals_data["evals"]:
        ws_g = next((g for g in with_skill if g["eval_name"] == ev["name"]), None)
        wo_g = next((g for g in without_skill if g["eval_name"] == ev["name"]), None)
        entry = {"eval_name": ev["name"], "topic": ev["topic"]}
        if ws_g:
            entry["with_skill"] = {"pass": ws_g["pass_count"], "total": ws_g["total"],
                                    "rate": round(ws_g["pass_count"]/ws_g["total"]*100, 1) if ws_g["total"] > 0 else 0}
        if wo_g:
            entry["without_skill"] = {"pass": wo_g["pass_count"], "total": wo_g["total"],
                                       "rate": round(wo_g["pass_count"]/wo_g["total"]*100, 1) if wo_g["total"] > 0 else 0}
        if ws_g and wo_g:
            entry["delta"] = round(entry["with_skill"]["rate"] - entry["without_skill"]["rate"], 1)
        per_eval.append(entry)

    benchmark = {
        "skill_name": "ios-logging",
        "model": "sonnet-4.6",
        "summary": {
            "with_skill": {"pass": ws_pass, "total": ws_total, "rate": round(ws_pass/ws_total*100, 1) if ws_total > 0 else 0},
            "without_skill": {"pass": wo_pass, "total": wo_total, "rate": round(wo_pass/wo_total*100, 1) if wo_total > 0 else 0},
            "delta": round((ws_pass/ws_total - wo_pass/wo_total)*100, 1) if ws_total > 0 and wo_total > 0 else 0
        },
        "by_topic": by_topic,
        "per_eval": per_eval
    }

    # Save benchmark.json
    bench_path = WORKSPACE / "benchmark.json"
    with open(bench_path, "w") as f:
        json.dump(benchmark, f, indent=2)

    # Generate benchmark.md
    md_lines = [
        f"# ios-logging Benchmark (Sonnet 4.6)",
        f"",
        f"## Summary",
        f"",
        f"| Config | Pass | Total | Rate |",
        f"|--------|------|-------|------|",
        f"| **With Skill** | {ws_pass} | {ws_total} | {benchmark['summary']['with_skill']['rate']}% |",
        f"| **Without Skill** | {wo_pass} | {wo_total} | {benchmark['summary']['without_skill']['rate']}% |",
        f"| **Delta** | | | **+{benchmark['summary']['delta']}%** |",
        f"",
        f"## By Topic",
        f"",
        f"| Topic | With Skill | Without Skill | Delta |",
        f"|-------|-----------|--------------|-------|",
    ]
    for topic, data in sorted(by_topic.items()):
        md_lines.append(f"| {topic} | {data['with_skill']['rate']}% | {data['without_skill']['rate']}% | +{data['delta']}% |")

    md_lines += [
        f"",
        f"## Per Eval",
        f"",
        f"| Eval | Topic | With Skill | Without Skill | Delta |",
        f"|------|-------|-----------|--------------|-------|",
    ]
    for pe in per_eval:
        ws_rate = pe.get("with_skill", {}).get("rate", "—")
        wo_rate = pe.get("without_skill", {}).get("rate", "—")
        delta = pe.get("delta", "—")
        md_lines.append(f"| {pe['eval_name']} | {pe['topic']} | {ws_rate}% | {wo_rate}% | +{delta}% |")

    md_path = WORKSPACE / "benchmark.md"
    with open(md_path, "w") as f:
        f.write("\n".join(md_lines) + "\n")

    return benchmark


def main():
    evals_data = load_evals()
    all_gradings = []

    missing = []
    for ev in evals_data["evals"]:
        for variant in ["with_skill", "without_skill"]:
            resp_path = WORKSPACE / ev["name"] / variant / "outputs" / "response.md"
            if not resp_path.exists():
                missing.append(f"{ev['name']}/{variant}")

    if missing:
        print(f"WARNING: {len(missing)} missing responses:")
        for m in missing:
            print(f"  - {m}")
        print()

    for ev in evals_data["evals"]:
        for variant in ["with_skill", "without_skill"]:
            grading = grade_run(ev, variant)
            if grading:
                all_gradings.append(grading)
                status = f"{grading['pass_count']}/{grading['total']}"
                print(f"  {ev['name']:35s} {variant:15s} -> {status}")
            else:
                print(f"  {ev['name']:35s} {variant:15s} -> MISSING")

    if all_gradings:
        benchmark = generate_benchmark(all_gradings, evals_data)
        print(f"\n=== BENCHMARK ===")
        print(f"With Skill:    {benchmark['summary']['with_skill']['pass']}/{benchmark['summary']['with_skill']['total']} ({benchmark['summary']['with_skill']['rate']}%)")
        print(f"Without Skill: {benchmark['summary']['without_skill']['pass']}/{benchmark['summary']['without_skill']['total']} ({benchmark['summary']['without_skill']['rate']}%)")
        print(f"Delta:         +{benchmark['summary']['delta']}%")


if __name__ == "__main__":
    main()
