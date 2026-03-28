# iOS Security Audit

Enterprise-grade security auditing skill for iOS codebases aligned with OWASP MASVS v2.1.0. Detects vulnerabilities across storage, cryptography, networking, platform integration, and code quality in both Swift and Objective-C.

## Benchmark Results

Tested on **17 scenarios** with **37 discriminating assertions**.

### Results Summary

| Model | With Skill | Without Skill | Delta | A/B Quality |
| --- | --- | --- | --- | --- |
| **Sonnet 4.6** | 37/37 (100%) | 26/37 (70.3%) | **+29.7%** | **9W 15T 0L** (avg 9.3 vs 8.9) |
| **GPT-5.4** | 100% | 73.6% | **+26.4%** | **23/24 wins**, 1 tie (avg 8.5 vs 7.0) |

> A/B Quality: blind judge scores each response 0–10 and picks the better one without knowing which used the skill. Position (A/B) is randomized across evals to prevent bias.

### Results (Sonnet 4.6)

| Metric | Value |
| --- | --- |
| With Skill | 37/37 (100%) |
| Without Skill | 26/37 (70.3%) |
| Delta | **+29.7%** |
| A/B Quality | **9W 15T 0L** (avg 9.3 vs 8.9) |

**Interpretation:** Sonnet 4.6 without the skill misses 11 of 37 discriminating assertions — concentrated on exact MASVS and MASWE mappings, L2-vs-L1 requirement boundaries, formal audit-report formatting, HIPAA and PCI citation detail, Apple-specific privacy-manifest terminology, and structured audit finding formats. The skill's advantage grows with complexity, as confirmed by 9 A/B wins with zero losses.

### Results (GPT-5.4)

| Difficulty | With Skill | Without Skill | Delta | A/B Quality |
| --- | --- | --- | --- | --- |
| Simple | 23/23 (100%) | 21/23 (91.3%) | **+8.7%** | **7/8 wins**, 1 tie (avg 8.1 vs 6.8) |
| Medium | 30/30 (100%) | 23/30 (76.7%) | **+23.3%** | **8/8 wins** (avg 8.6 vs 7.0) |
| Complex | 38/38 (100%) | 23/38 (60.5%) | **+39.5%** | **8/8 wins** (avg 8.9 vs 7.2) |
| **Total** | **91/91 (100%)** | **67/91 (73.6%)** | **+26.4%** | **23/24 wins**, 1 tie (avg 8.5 vs 7.0) |

**Interpretation:** The baseline handled simple scenarios reasonably (91.3%) but missed skill-specific details on medium and complex prompts. The gain is concentrated in complex scenarios (+39.5%), where the skill supplies precise implementation and compliance language rather than generic security advice.

### Key Discriminating Assertions (missed without skill)

| Topic | Assertion | Why It Matters |
| --- | --- | --- |
| appstore | `NSPrivacyAccessedAPITypes` must declare API usage reasons | Privacy manifest completeness |
| appstore | `NSPrivacyTrackingDomains` for tracking domains | App Store privacy enforcement |
| audit-process | Maps finding to `MASVS-STORAGE-1` | Audit traceability to MASVS control |
| audit-process | Includes MASWE ID such as `MASWE-0005` | Vulnerability taxonomy precision |
| compliance | Missing biometric auth with server binding for L2 | Correct L2 control boundary |

### Topic Breakdown

| Topic | Simple | Medium | Complex |
| --- | --- | --- | --- |
| storage | **+33%** | 0% | **+75%** |
| crypto | 0% | **+25%** | **+40%** |
| network | 0% | **+50%** | 0% |
| platform | 0% | **+25%** | **+60%** |
| objc | 0% | **+25%** | **+40%** |
| compliance | **+33%** | **+25%** | **+20%** |
| appstore | 0% | **+25%** | **+40%** |
| audit-process | 0% | 0% | **+40%** |

> Raw data:
> `ios-security-audit-workspace/iteration-1/benchmark-gpt-5-4-tiered.json`
> `ios-security-audit-workspace/iteration-1/benchmark-opus-4-5-tiered.json`

### Benchmark Cost Estimate

| Step | Formula | Tokens |
| --- | --- | --- |
| Eval runs (with_skill) | 24 × 35k | 840k |
| Eval runs (without_skill) | 24 × 12k | 288k |
| Grading (48 runs × 5k) | 48 × 5k | 240k |
| **Total** | | **~1.4M** |
| **Est. cost (Opus 4.5)** | ~$30/1M | **~$41** |
| **Est. cost (Sonnet 4.6)** | ~$5.4/1M | **~$8** |

> Token estimates based on sampled timing.json files. Blended rate ~$30/1M for Opus ($15 input + $75 output, ~80/20 ratio); ~$5.4/1M for Sonnet 4.6 ($3 input + $15 output, ~80/20 ratio).

---

## What This Skill Changes

| Without Skill | With Skill |
| --- | --- |
| Ad-hoc security reviews with inconsistent coverage | Structured audit against 24 MASVS controls |
| Missed hardcoded secrets and insecure storage | Pattern-first detection of CRITICAL vulnerabilities |
| No compliance mapping for regulated apps | HIPAA, PCI DSS, GDPR, SOC 2 requirement mapping |
| Generic security advice | Concrete vulnerable/secure code pairs with MASVS traceability |
| Same checklist for all apps | L1/L2/R testing profile-aware severity classification |

## Install

```bash
npx skills add git@git.epam.com:epm-ease/research/agent-skills.git --skill ios-security-audit
```

Verify by asking your AI assistant to "run a security audit on this iOS project".

## Testing From a Feature Branch

To test a skill before it's merged:

```bash
# 1. Clone the repo (or use an existing clone)
git clone https://github.com/anthropics/agent-skills.git
cd agent-skills
git checkout skill/iOS-security-audit  # or your feature branch

# 2. Copy the skill into your target project
cp -r skills/ios/ios-security-audit /path/to/your-ios-project/.claude/skills/

# 3. Add the skill to your project's CLAUDE.md (or .cursorrules, .github/copilot-instructions.md)
# Add this line to the skills section:
# - **ios-security-audit** — Read `skills/ios/ios-security-audit/SKILL.md` for full instructions.
```

For Claude Code, you can also symlink instead of copying:

```bash
mkdir -p /path/to/your-ios-project/.claude/skills/
ln -s "$(pwd)/skills/ios/ios-security-audit" /path/to/your-ios-project/.claude/skills/ios-security-audit
```

This way your local changes are immediately reflected without re-copying. Remove the symlink after testing.

## When to Use

- Reviewing iOS code for security vulnerabilities
- Pre-release security gate checks
- Auditing Keychain usage and data storage patterns
- Checking ATS configuration and certificate pinning
- Detecting hardcoded secrets, weak cryptography, or insecure randomness
- Reviewing Objective-C runtime attack surface
- Mapping compliance requirements (HIPAA, PCI DSS, GDPR, SOC 2)
- Validating WebView security and URL scheme handlers
