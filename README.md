<p align="center">
  <img src="assets/banner.png" alt="iOS Agent Skills" width="100%">
</p>

<p align="center">
  <a href="https://github.com/rusel95/ios-agent-skills"><img src="https://visitor-badge.laobi.icu/badge?page_id=rusel95.ios-agent-skills&left_color=gray&right_color=blue&left_text=visitors" alt="visitors"/></a>
  <a href="https://github.com/rusel95/ios-agent-skills"><img src="https://img.shields.io/github/stars/rusel95/ios-agent-skills?style=flat-square&color=yellow" alt="stars"/></a>
  <img src="https://img.shields.io/badge/skills-10-purple?style=flat-square" alt="skills"/>
  <img src="https://img.shields.io/badge/models_tested-3-teal?style=flat-square" alt="models"/>
  <img src="https://img.shields.io/badge/assertions-800-orange?style=flat-square" alt="assertions"/>
  <img src="https://img.shields.io/badge/scenarios-245-green?style=flat-square" alt="scenarios"/>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-brightgreen?style=flat-square" alt="license"/></a>
</p>

# iOS Agent Skills

**The first and most comprehensively benchmarked iOS skill marketplace** for Claude Code, Codex, and 40+ AI coding tools.

10 enterprise-grade skills covering architecture, concurrency, testing, security, accessibility, and localization — every skill benchmarked with discriminating assertions and blind A/B quality scoring across multiple LLMs. No other iOS skill collection has this level of rigorous, reproducible evaluation — 800 assertions across 245 scenarios, tested on Claude Sonnet 4.6, GPT-5.4, and Gemini 3.1 Pro.

## Benchmark Results

Every skill is benchmarked against multiple LLMs with discriminating assertions and blind A/B quality scoring.

| Skill | Sonnet 4.6 delta | Sonnet 4.6 A/B | GPT-5.4 delta | Gemini 3.1 Pro delta |
|-------|:-:|:-:|:-:|:-:|
| **swiftui-mvvm** | ![](https://img.shields.io/badge/+11.1%25-555?style=flat-square&logo=swift&logoColor=white) | 9W 15T 0L · 9.2↑8.8 (+0.4) | ![](https://img.shields.io/badge/+40.8%25-555?style=flat-square&logo=swift&logoColor=white) | ![](https://img.shields.io/badge/+76.0%25-007AFF?style=flat-square&logo=swift&logoColor=white) |
| **uikit-mvvm** | ![](https://img.shields.io/badge/+13.7%25-555?style=flat-square&logo=swift&logoColor=white) | 20W 2T 2L · 9.1↑8.2 (+0.9) | ![](https://img.shields.io/badge/+40.8%25-555?style=flat-square&logo=swift&logoColor=white) | ![](https://img.shields.io/badge/+54.9%25-34C759?style=flat-square&logo=swift&logoColor=white) |
| **gcd-operations** | ![](https://img.shields.io/badge/+47.4%25-5AC8FA?style=flat-square&logo=swift&logoColor=white) | 15W 9T 0L · 8.6↑8.1 (+0.5) | ![](https://img.shields.io/badge/+4.8%25-555?style=flat-square&logo=swift&logoColor=white) | ![](https://img.shields.io/badge/+16.1%25-555?style=flat-square&logo=swift&logoColor=white) |
| **ios-testing** | ![](https://img.shields.io/badge/+44.2%25-FFD60A?style=flat-square&logo=swift&logoColor=black) | 23W 7T 0L · 8.9↑8.0 (+0.9) | ![](https://img.shields.io/badge/+30.0%25-555?style=flat-square&logo=swift&logoColor=white) | ![](https://img.shields.io/badge/+33.6%25-555?style=flat-square&logo=swift&logoColor=white) |
| **swift-concurrency** | ![](https://img.shields.io/badge/+32.5%25-555?style=flat-square&logo=swift&logoColor=white) | 15W 9T 0L · 8.9↑8.5 (+0.4) | ![](https://img.shields.io/badge/+17.8%25-555?style=flat-square&logo=swift&logoColor=white) | ![](https://img.shields.io/badge/+35.6%25-FF2D55?style=flat-square&logo=swift&logoColor=white) |
| **ios-security** | ![](https://img.shields.io/badge/+29.7%25-FF3B30?style=flat-square&logo=swift&logoColor=white) | 9W 15T 0L · 9.3↑8.9 (+0.4) | ![](https://img.shields.io/badge/+26.4%25-555?style=flat-square&logo=swift&logoColor=white) | — |
| **tca-swiftui** | ![](https://img.shields.io/badge/+25.9%25-AF52DE?style=flat-square&logo=swift&logoColor=white) | 14W 2T 4L · 8.7↑7.8 (+0.9) | — | — |
| **ios-logging** | ![](https://img.shields.io/badge/+34.1%25-8E8E93?style=flat-square&logo=swift&logoColor=white) | 25W 0T 2L · 8.6↑7.4 (+1.2) | — | — |
| **ios-accessibility** | ![](https://img.shields.io/badge/+18.3%25-00C7BE?style=flat-square&logo=swift&logoColor=white) | 21W 15T 0L · 8.8↑7.9 (+0.9) | — | — |
| **viper-uikit** | ![](https://img.shields.io/badge/+13.4%25-FF9500?style=flat-square&logo=swift&logoColor=white) | 15W 1T 0L · 9.4↑8.2 (+1.2) | — | — |
| **ios-localization** | ![](https://img.shields.io/badge/+1.9%25-555?style=flat-square&logo=swift&logoColor=white) | 27W 0T 9L · 8.4↑7.6 (+0.8) | — | — |

> Delta = assertion pass rate improvement (with skill vs without). Colored badge = best result for that skill. A/B: blind judge scores both responses 0–10 without knowing which used the skill; position randomized. **W = skill wins · T = tie · L = baseline wins.**

See [BENCHMARKING.md](BENCHMARKING.md) for full methodology.

## Skills

| Skill | Domain | iOS Target |
|-------|--------|------------|
| **swiftui-mvvm** | SwiftUI + @Observable MVVM | iOS 17+ |
| **uikit-mvvm** | UIKit + Combine MVVM | iOS 13+ |
| **viper-uikit** | VIPER Architecture | iOS 13+ |
| **tca-swiftui** | The Composable Architecture | iOS 16+ |
| **swift-concurrency** | async/await, Actors, Swift 6 | iOS 13+ |
| **gcd-operations** | GCD & OperationQueue | iOS 13+ |
| **ios-testing** | Testing across all architectures | iOS 13+ |
| **ios-security** | OWASP MASVS Security Audit | iOS 13+ |
| **ios-accessibility** | VoiceOver, Dynamic Type, WCAG 2.2 | iOS 13+ |
| **ios-logging** | Production Error Observability & Logging | iOS 15+ |
| **ios-localization** | String Catalogs, CLDR Plurals, RTL, Formatting | iOS 13+ |

## Install

### Claude Code Plugin (recommended)

```bash
claude plugin add rusel95/ios-agent-skills
```

Install individual skills:

```bash
claude plugin add rusel95/ios-agent-skills --skill swiftui-mvvm
claude plugin add rusel95/ios-agent-skills --skill swift-concurrency
```

### Agent Skills CLI

```bash
npx skills add rusel95/ios-agent-skills --skill swiftui-mvvm
```

### Manual

Clone and copy the `skills/` directory into your project.

## What Makes These Different

- **Production-first** — every pattern comes from real enterprise codebases, not tutorials
- **Iterative refactoring** — small, reviewable PRs (≤200 lines) instead of "rewrite everything" approaches
- **Anti-pattern prevention** — AI tools consistently generate broken patterns (retain cycles in VIPER, outdated TCA APIs, unsafe GCD). These skills prevent that
- **Architecture coverage** — the only collection covering VIPER, TCA, GCD, Security Audit, Accessibility, and Localization. No other iOS skill marketplace covers these domains
- **Rigorously benchmarked** — the most comprehensively evaluated iOS skill collection available: 800 discriminating assertions across 245 scenarios, tested against 3 LLMs with blind A/B quality scoring. Every skill ships with reproducible eval data

## Skill Details

### swiftui-mvvm
@Observable ViewModels, ViewState enum, Router navigation, constructor injection, Repository-based networking. Phased migration from ObservableObject. **+40.8% on GPT-5.4, +76.0% on Gemini.**

### uikit-mvvm
Combine-bound ViewModels, Coordinator navigation, DiffableDataSource, programmatic Auto Layout. GCD-to-Combine migration paths. **+40.8% on GPT-5.4, +54.9% on Gemini.**

### viper-uikit
Passive Views, single-use-case Interactors, UIKit-free Presenters, protocol-isolated module boundaries. Prevents the retain cycles AI tools consistently generate. **+13.4% on Sonnet 4.6** (149 assertions).

### tca-swiftui
@Reducer macro, @ObservableState, Effect API, @DependencyClient. Prevents outdated pre-1.7 TCA patterns (WithViewStore, Environment, IfLetStore). **+25.9% on Sonnet 4.6** (113 assertions).

### swift-concurrency
async/await, actor isolation, Sendable, TaskGroup, AsyncStream. Swift 6.2 readiness, strict concurrency migration, crash pattern prevention. **+32.5% on Sonnet, +35.6% on Gemini.**

### gcd-operations
DispatchQueue, OperationQueue, locks, barriers, DispatchSource. Thread explosion prevention, deadlock diagnosis, GCD-to-Swift-Concurrency migration. **+47.4% on Sonnet 4.6.**

### ios-testing
Swift Testing (@Test/@Suite/#expect), XCTest, async testing, architecture-specific patterns (MVVM/VIPER/TCA), snapshot testing, integration testing. **+44.2% on Sonnet, +30% on GPT-5.4.**

### ios-security
OWASP MASVS v2.1.0 audit (24 controls, 8 categories). Keychain, ATS, certificate pinning, WebView, biometric auth, compliance mapping (HIPAA, PCI DSS, GDPR). **+29.7% on Sonnet, +26.4% on GPT-5.4.**

### ios-logging
Production error observability: `os.Logger` with privacy annotations, crash SDK integration (Sentry/Crashlytics), MetricKit for OOM/watchdog detection, silent failure pattern elimination (`try?`, `Task {}`, Combine `.replaceError()`), PII compliance, centralized error handling, retry with backoff, app extension monitoring, MCP connectivity for AI-assisted debugging. **25W 0T 2L** blind A/B (8.6↑7.4), **+34.1% on Sonnet 4.6** (91 assertions, 27 scenarios).

### ios-accessibility
VoiceOver, Dynamic Type, color contrast, motion preferences, Switch Control, Voice Control, WCAG 2.2 AA mapping. Corrects 11 documented AI failure patterns (onTapGesture, hardcoded fonts, missing labels, trait assignment). **+18.3% on Sonnet 4.6** (115 assertions, 100% with-skill, 21 discriminating wins).

### ios-localization
String Catalogs (.xcstrings), CLDR pluralization (Russian, Polish, Arabic), SwiftUI/UIKit localization APIs, date/number/currency formatting, RTL layout, accessibility localization, enterprise patterns (modular apps, white-label). Corrects 30 documented AI localization failures. Includes Python scripts for .xcstrings validation and plural auditing. **+1.9% on Sonnet 4.6** (103 assertions; 27W 0L 9T A/B — skill value is in depth and edge cases, not core knowledge gaps).

## Author

**Ruslan Popesku** — Lead iOS Software Engineer
[GitHub](https://github.com/rusel95) · [LinkedIn](https://www.linkedin.com/in/rusel95)

## License

MIT
