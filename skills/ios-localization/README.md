# iOS Localization Skill

Production-grade localization skill for iOS codebases. Corrects 30+ AI failure patterns — from missing Slavic plural categories to hardcoded left/right constraints that shatter RTL layouts — and enforces correct localization from the start.

## Benchmark Results

Tested on **36 scenarios** with **103 assertions** across 10 topics.

### Results Summary

| Model | With Skill | Without Skill | Delta | A/B Quality |
| --- | --- | --- | --- | --- |
| **Sonnet 4.6** | 84/103 (81.6%) | 83/103 (80.6%) | **+1.0%** | **10W 21T 5L** (avg 8.9 vs 8.7) |
| **GPT-5.4** | 103/103 (100%) | 99/103 (96.1%) | **+3.9%** | **26W 2T 8L** (avg 9.1 vs 8.9) |
| **Gemini 3.1 Pro** | 103/103 (100%) | 73/103 (70.9%) | **+29.1%** | **36W** 0T 0L (avg 9.0 vs 6.3) |

> Delta = percentage point improvement in discriminating assertion pass rate. A/B Quality: blind judge scores each response 0-10. "—" = not yet collected.
> **Note on GPT-5.4:** Strict regrading of the regenerated GPT-5.4 responses gives 103/103 (100%) with the skill vs 99/103 (96.1%) without (+3.9%). The remaining baseline gaps are the `#bundle` resource macro, same-table `.strings` to `.xcstrings` migration rules, `LocalizedStringKey` interpolation behavior, and CI validation-script usage. Blind A/B also favors the skill, but more modestly, at 26W 2T 8L with average quality 9.1 vs 8.9.
> **Note on Gemini 3.1 Pro:** Achieves 100% with the skill. Without the skill, 30 assertions fail across 10 topics. The largest gaps are package localization (12% baseline — misses bundle: .module, Package.swift defaultLocalization, and LocalizedStringResource API boundary patterns entirely), string-catalogs (45% baseline — fails on hidden-count .stringsdict exception, comment-order churn root cause, and catalog splitting), and accessibility-localization (62% baseline — misses locale-aware percent formatting and dedicated a11y key patterns). Pluralization knowledge is strong (91% baseline).

### Results (Sonnet 4.6)

| Metric | Value |
| --- | --- |
| With Skill | **84/103 (81.6%)** |
| Without Skill | 83/103 (80.6%) |
| Delta | **+1.0%** |
| Discriminating assertions | 2 (WITH wins), 0 (WITHOUT wins) |
| A/B Quality | **10W 21T 5L** (avg 8.9 vs 8.7) |

**Interpretation:** Sonnet 4.6 already has strong iOS localization knowledge — the baseline passes 80.6% of assertions. The skill's discriminating value concentrates in niche Xcode-specific details (comment order randomization bug in .xcstrings) and precise Slavic plural rule boundaries (Polish vs Russian number 21 mapping). The A/B quality scoring shows a modest advantage (10 wins, 5 losses, 21 ties) — responses are broadly similar in quality, with the skill adding edge-case depth.

### Results (Gemini 3.1 Pro)

| Metric | Value |
| --- | --- |
| With Skill | **103/103 (100%)** |
| Without Skill | 73/103 (70.9%) |
| Delta | **+29.1%** |
| Discriminating assertions failed by baseline | 30 |
| A/B Quality | — |

**Topic breakdown (without skill):**

| Topic | Without Skill | With Skill | Delta |
| --- | --- | --- | --- |
| package-localization | 1/8 (12%) | 8/8 (100%) | +88% |
| string-catalogs | 5/11 (45%) | 11/11 (100%) | +55% |
| accessibility-localization | 5/8 (62%) | 8/8 (100%) | +38% |
| localization-testing | 8/11 (73%) | 11/11 (100%) | +27% |
| enterprise-patterns | 6/8 (75%) | 8/8 (100%) | +25% |
| uikit-localization | 9/11 (82%) | 11/11 (100%) | +18% |
| rtl-layout | 9/11 (82%) | 11/11 (100%) | +18% |
| swiftui-localization | 10/12 (83%) | 12/12 (100%) | +17% |
| formatting | 10/12 (83%) | 12/12 (100%) | +17% |
| pluralization | 10/11 (91%) | 11/11 (100%) | +9% |

**Interpretation:** Gemini 3.1 Pro without the skill has the widest baseline gap of any model tested (+29.1% delta). The baseline fails completely on package localization (misses `bundle: .module`, `defaultLocalization` in Package.swift, and the `LocalizedStringResource` API boundary pattern) and has significant gaps in string-catalog niche knowledge (hidden-count `.stringsdict` exception, comment-order churn root cause). Pluralization knowledge is relatively strong. The skill closes all 30 gaps to achieve 100%.

### Key Discriminating Assertions

| ID | Topic | Assertion | Why It Matters |
| --- | --- | --- | --- |
| PL2.2 | pluralization | Number 21 maps to 'one' in Russian but 'many' in Polish | Precise cross-language difference |
| SC2.3 | string-catalogs | Xcode comment order randomization bug causing false diffs | Niche Xcode-specific knowledge |

---

## What This Skill Changes

| Without Skill | With Skill |
| --- | --- |
| Only one/other plural categories (breaks Russian, Polish, Arabic) | All CLDR-required categories per language |
| Concatenated string fragments ("Hello, " + name) | Format strings with positional specifiers |
| Custom dateFormat for user-facing dates | System styles (Date.formatted, .dateStyle) |
| Left/right constraints (breaks Arabic, Hebrew) | Leading/trailing constraints everywhere |
| Hardcoded English accessibility labels | Localized accessibility strings |
| Manual .strings file creation | String Catalogs with auto-extraction |
| Direct .xcstrings editing (breaks on large files) | Python scripts for programmatic operations |

## What It Does

- Intercepts 30 documented AI localization failure patterns
- Enforces CLDR-correct pluralization for all supported languages
- Provides Python scripts for .xcstrings validation, editing, and plural auditing
- Covers String Catalogs, SwiftUI/UIKit APIs, date/number/currency formatting
- Handles RTL layout, accessibility localization, and enterprise patterns
- Maps to CLDR specifications and Apple documentation

## Coverage

| Area | SwiftUI | UIKit |
|---|---|---|
| String Catalogs (.xcstrings) | Full | Full |
| CLDR Pluralization (Slavic, Arabic, CJK) | Full | Full |
| Date/Number/Currency Formatting | Full | Full |
| RTL Layout (Arabic, Hebrew) | Full | Full |
| Accessibility String Localization | Full | Full |
| Swift Package Bundle Management | Full | Full |
| Enterprise (White-label, Modular) | Full | Full |
| Testing (Pseudolanguages, CI) | Full | Full |

## Structure

```text
ios-localization/
├── SKILL.md                           — Decision trees, workflows, 17 critical rules
├── scripts/
│   └── xcstrings_tool.py             — Validate, add keys, audit plurals, fix plurals
└── references/
    ├── rules.md                       — All 30 rules ranked by severity
    ├── ai-failure-patterns.md         — 30 failure patterns with ❌/✅ code pairs
    ├── string-catalogs.md             — .xcstrings format, pitfalls, Xcode 26 features
    ├── pluralization.md               — CLDR categories, Russian vs Polish, test sets
    ├── swiftui-localization.md        — LocalizedStringKey, verbatim, packages
    ├── formatting.md                  — Date, number, currency formatting
    ├── rtl-layout.md                  — Leading/trailing, semantic content, exceptions
    ├── enterprise-patterns.md         — Modular apps, white-label, accessibility
    └── testing.md                     — Pseudolanguages, launch arguments, CI
```

## Companion Skills

| Skill | Use When |
| --- | --- |
| `ios-accessibility` | Accessibility labels need localization |
| `swiftui-mvvm` | Localized ViewModels and state management |
| `ios-testing` | Locale-specific test automation |
| `ios-security` | Format string vulnerabilities in localized strings |
