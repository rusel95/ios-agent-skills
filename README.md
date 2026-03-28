<p align="center">
  <img src="assets/banner.png" alt="iOS Agent Skills" width="100%">
</p>

# iOS Agent Skills

Production-tested iOS Agent Skills for Claude Code, Codex, and 40+ AI coding tools.

8 enterprise-grade skills covering architecture, concurrency, testing, and security — built by a Lead iOS Engineer with real production experience.

## Benchmark Results

Every skill is benchmarked against multiple LLMs with discriminating assertions and blind A/B quality scoring.

| Skill | Sonnet 4.6 Delta | GPT-5.4 Delta | Gemini 3.1 Pro Delta | Scenarios | Assertions |
|-------|:-:|:-:|:-:|:-:|:-:|
| **swiftui-mvvm** | +11.1% | +40.8% | +76.0% | 23 | 63 |
| **uikit-mvvm** | +13.7% | +40.8% | +54.9% | 24 | 51 |
| **viper-uikit** | +13.4% | — | — | 16 | 149 |
| **tca-swiftui** | +25.9% | — | — | 20 | 113 |
| **swift-concurrency** | +32.5% | +17.8% | +35.6% | 21 | 40 |
| **gcd-operations** | +47.4% | +4.8% | +16.1% | 13 | 19 |
| **ios-testing** | +44.2% | +30.0% | +33.6% | 27 | 77 |
| **ios-security** | +29.7% | +26.4% | — | 17 | 37 |

> Delta = percentage point improvement in discriminating assertion pass rate (with skill vs without skill). Higher = more value added. "—" = not yet benchmarked for that model.

### Methodology

- **Discriminating assertions**: binary checks that distinguish skill-guided output from baseline. Each assertion targets a specific pattern AI tools consistently miss without the skill.
- **A/B quality scoring**: blind judge scores both outputs 0–10 without knowing which used the skill. Position randomized to prevent bias.
- **Multi-model**: tested across Claude Sonnet 4.6, GPT-5.4, and Gemini 3.1 Pro to ensure skill value isn't model-specific.
- **Tiered difficulty**: simple / medium / complex scenarios. Skills show largest gains on medium and complex tiers.

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
- **Architecture coverage** — the only collection covering VIPER, TCA, GCD, and Security Audit. No major iOS skill author has claimed these domains
- **Benchmarked** — tested against 3 LLMs with 549 discriminating assertions across 161 scenarios

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

## Author

**Ruslan Popesku** — Lead iOS Software Engineer at EPAM
[GitHub](https://github.com/rusel95) · [LinkedIn](https://www.linkedin.com/in/rusel95)

## License

MIT
