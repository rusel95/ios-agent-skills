# iOS Accessibility Skill

Production-grade accessibility skill for iOS codebases. Corrects the systematic accessibility failures that AI coding assistants produce — hardcoded fonts, `onTapGesture` instead of `Button`, missing labels, no system preference checks — and enforces accessible output from the start.

## Benchmark Results

Tested on **36 scenarios** with **115 discriminating assertions** across 12 topics.

### Results Summary

| Model | With Skill | Without Skill | Delta | A/B Quality |
| --- | --- | --- | --- | --- |
| **Sonnet 4.6** | 94/115 (81.7%) | 94/115 (81.7%) | **+0.0%** | **27W 5T 4L** (avg 8.5 vs 7.9) |
| **GPT-5.4** | 113/115 (98.3%) | 101/115 (87.8%) | **+10.4%** | **31W 1T 4L** (avg 9.2 vs 8.5) |
| **Gemini 3.1 Pro** | 115/115 (100%) | 85/115 (73.9%) | **+26.1%** | **36W** 0T 0L (avg 9.0 vs 7.2) |

> Delta = percentage point improvement in discriminating assertion pass rate (with skill vs without skill). A/B Quality: blind judge scores each response 0–10. "—" = not yet benchmarked.
> **Note on GPT-5.4:** Strict regrading of the regenerated GPT-5.4 responses gives 113/115 (98.3%) with the skill vs 101/115 (87.8%) without (+10.4%). The recovered gaps are concentrated in WCAG 2.2 mapping, UIKit accessibility structures, custom-action return values, and system-preference edge cases. Two with-skill misses remain: an explicit `.foregroundColor` deprecation callout and a direct 7:1 Increase Contrast statement. Blind A/B also favors the skill clearly at 31W 1T 4L with average quality 9.2 vs 8.5.

### Results (Sonnet 4.6)

| Metric | Value |
| --- | --- |
| With Skill | **94/115 (81.7%)** |
| Without Skill | 94/115 (81.7%) |
| Delta | **+0.0%** |
| A/B Quality | **27W 5T 4L** (avg 8.5 vs 7.9) |

**Interpretation:** Sonnet 4.6 already has strong iOS accessibility knowledge — the baseline passes 81.7% of assertions. The assertion delta is 0%: the skill produces 3 topic wins (color-contrast, swiftui-controls, voiceover-grouping) offset by 3 regressions (motion-preferences, uikit-controls, wcag-mapping). However, the A/B quality scoring shows the skill consistently produces better responses (27 wins, 4 losses) — the advantage is in depth, WCAG 2.2 coverage, and edge-case examples rather than missing core knowledge.

### Topic Breakdown

| Topic | With Skill | Without Skill | Delta | Assertions |
| --- | --- | --- | --- | --- |
| voiceover-labels | 100.0% | 100.0% | 0.0% | 10 |
| voiceover-traits | 100.0% | 100.0% | 0.0% | 9 |
| motion-preferences | 90.0% | 100.0% | **-10.0%** | 10 |
| swiftui-controls | 90.0% | 80.0% | **+10.0%** | 10 |
| uikit-controls | 80.0% | 90.0% | **-10.0%** | 10 |
| voiceover-grouping | 88.9% | 77.8% | **+11.1%** | 9 |
| voiceover-actions | 80.0% | 80.0% | 0.0% | 10 |
| system-preferences | 77.8% | 77.8% | 0.0% | 9 |
| dynamic-type | 70.0% | 70.0% | 0.0% | 10 |
| color-contrast | 70.0% | 60.0% | **+10.0%** | 10 |
| testing | 88.9% | 88.9% | 0.0% | 9 |
| wcag-mapping | 44.4% | 55.6% | **-11.1%** | 9 |

### Key Discriminating Assertions (21 — missed WITHOUT skill, all passed WITH)

| ID | Topic | Assertion | Why It Matters |
| --- | --- | --- | --- |
| VL2.2 | voiceover-labels | Hides individual star images from VoiceOver | Stars should not be separate VO stops |
| VL3.4 | voiceover-labels | Custom action closures return Bool | Correct API signature |
| VT3.1 | voiceover-traits | Replace onTapGesture in custom stepper | Element invisible to all AT |
| VG1.3 | voiceover-grouping | .ignore + custom label for natural sentences | .combine produces awkward pauses |
| VA2.3 | voiceover-actions | Announcements lost if VO speaking | Critical timing gotcha |
| VA3.4 | voiceover-actions | accessibilityPerformEscape for dismiss | Two-finger Z gesture |
| DT1.3 | dynamic-type | 25%+ of users change text size | Motivates compliance |
| DT2.3 | dynamic-type | numberOfLines = 0 for text wrapping | UIKit anti-pattern |
| DT3.3 | dynamic-type | @ScaledMetric for icon dimensions | Non-text scaling |
| CC3.3 | color-contrast | Test contrast for both light AND dark | Independent verification |
| MP1.2 | motion-preferences | Replace with crossfade, not remove all animation | UX principle |
| MP3.1 | motion-preferences | reduceTransparency → solid background | Material replacement |
| MP3.5 | motion-preferences | accessibilityIgnoresInvertColors for photos | Smart Invert |
| SC1.1 | swiftui-controls | onTapGesture invisible to VO/Switch Control | #1 AI failure |
| SC2.2 | swiftui-controls | .isToggle trait for custom toggles | iOS 17+ semantics |
| SC3.3 | swiftui-controls | textContentType for autofill | WCAG 1.3.5 |
| WC2.1 | wcag-mapping | WCAG 2.5.7 Dragging (new in 2.2) | AI trained on older WCAG |
| WC2.3 | wcag-mapping | Target size 24pt WCAG / 44pt Apple HIG | WCAG 2.5.8 |
| WC3.3 | wcag-mapping | Criteria that DON'T apply to native iOS | Avoids web-only auditing |
| SP3.2 | system-preferences | accessibilityIgnoresInvertColors cascades to subviews | Parent cascade behavior |
| SP3.4 | system-preferences | .dynamicTypeSize cap + Large Content Viewer | Combined fallback pattern |

### Benchmark Cost Estimate

| Step | Formula | Tokens |
| --- | --- | --- |
| Eval runs (with_skill) | 36 × 35k | 1,260k |
| Eval runs (without_skill) | 36 × 12k | 432k |
| Grading (72 runs × 5k) | 72 × 5k | 360k |
| **Total** | | **~2.1M** |
| **Est. cost (Sonnet 4.6)** | ~$5.4/1M | **~$11** |

---

## What This Skill Changes

| Without Skill | With Skill |
| --- | --- |
| onTapGesture for interactive elements (invisible to VoiceOver) | Button with accessibilityLabel for all interactive elements |
| Hardcoded font sizes (.system(size:)) | Dynamic Type text styles that scale |
| Hardcoded colors (.black, .white) | Semantic colors adapting to dark mode |
| No accessibility on custom controls | Labels, values, traits, and adjustable actions |
| No system preference checks | Reduce motion, contrast, transparency, color |
| Generic WCAG advice | iOS-specific API mapping for each criterion |

## What It Does

- Intercepts 11 documented AI failure patterns before they reach production
- Generates VoiceOver-compatible SwiftUI and UIKit code by default
- Enforces Dynamic Type, semantic colors, and proper element grouping
- Maps iOS APIs to WCAG 2.2 AA success criteria
- Provides accessibility review workflows with severity-ranked findings
- Covers enterprise compliance (ADA, EAA, Section 508, VPAT)

## When It Triggers

- Creating new iOS views or screens
- Reviewing existing code for accessibility
- Adding VoiceOver, Dynamic Type, or contrast support
- Auditing WCAG compliance
- Preparing apps for enterprise or government deployment
- Any mention of "make this accessible", "VoiceOver", "a11y"

## Coverage

| Area | SwiftUI | UIKit |
|---|---|---|
| VoiceOver (labels, traits, grouping, actions, rotors) | Full | Full |
| Dynamic Type (text styles, layout adaptation) | Full | Full |
| Color & Contrast (WCAG ratios, dark mode, color blindness) | Full | Full |
| Motion & Animation (reduce motion, flash safety) | Full | Full |
| Alternative Input (Switch Control, Voice Control, Keyboard) | Full | Full |
| iOS 17/18/26 new APIs | Full | Partial |
| WCAG 2.2 AA mapping | Full | Full |
| Testing (Xcode audit, XCTest, CI) | Full | Full |
| Compliance (ADA, EAA, Section 508, VPAT) | Full | Full |

## Structure

```
ios-accessibility/
├── SKILL.md                           — Decision trees, workflows, critical rules
└── references/
    ├── rules.md                       — Priority rules and do's/don'ts
    ├── ai-failure-patterns.md         — 11 AI failure patterns with code pairs
    ├── voiceover-patterns.md          — Labels, hints, traits, grouping, actions
    ├── swiftui-patterns.md            — All SwiftUI accessibility modifiers
    ├── uikit-patterns.md              — UIKit elements, containers, traits
    ├── dynamic-type.md                — UIFontMetrics, @ScaledMetric, layout
    ├── color-visual.md                — Contrast, color blindness, dark mode
    ├── motion-input.md                — Reduce motion, Switch/Voice Control
    ├── wcag-ios-mapping.md            — WCAG 2.2 → iOS API mapping
    ├── testing.md                     — Xcode audit, XCTest, VoiceOver, CI
    ├── ios-new-features.md            — iOS 17/18/26 new APIs
    └── compliance.md                  — Legal, VPAT, enterprise requirements
```

## Companion Skills

| Skill | Use When |
|---|---|
| `swiftui-mvvm` | ViewModels managing accessibility state |
| `ios-security` | Biometric auth with VoiceOver feedback |
| `ios-testing` | XCTest accessibility audit integration |
| `swift-concurrency` | VoiceOver notifications from async contexts |
