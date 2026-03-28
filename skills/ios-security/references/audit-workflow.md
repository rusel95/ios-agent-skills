# Security Audit Report & Remediation Tracker

This reference covers two phases:

1. **Audit Report** — generating the findings report after scanning the codebase
2. **Remediation Tracker** — structured directory for tracking fixes across PRs

---

## Phase 1: Audit Report

## Report Structure

After completing all scans (CRITICAL → HIGH → MEDIUM/LOW), compile findings into a single report with these sections:

```markdown
# Security Audit Report

**App**: [App Name]
**Testing Profile**: L1 / L2 / R
**Audit Date**: YYYY-MM-DD
**Standard**: OWASP MASVS v2.1.0
**Auditor**: [AI model / human / team]

## Executive Summary

- **Total findings**: X (Y CRITICAL, Z HIGH, W MEDIUM, V LOW)
- **Release recommendation**: BLOCK / CONDITIONAL / PASS
- **Top 3 risks**: [ordered list]
- **MASVS coverage**: [categories audited / total]

## Findings by Severity

### 🔴 CRITICAL

#### [C1] [Short title]
- **File**: `path/to/file.swift:42`
- **MASVS**: MASVS-[CATEGORY]-[N] | MASWE-[NNNN]
- **Issue**: [1-2 sentence description]
- **Risk**: [What an attacker can achieve]
- **Fix**:
  ```swift
  // ✅ Secure replacement code
  ```

[Repeat for each CRITICAL finding]

### 🟡 HIGH

[Same format]

### 🟢 MEDIUM

[Same format]

### 🔵 LOW

[Same format — can use abbreviated format without full code fix]

## Informational

[Items that matched detection patterns but are safe in context — e.g., MD5 for checksums, UserDefaults for non-sensitive preferences. Document why they are safe to prevent re-flagging in future audits.]

## MASVS Coverage Matrix

> **Required in every audit report.** Fill in actual finding counts per severity.

Status icons: ✅ zero findings | ✅ L1 zero L1 findings (RESILIENCE: L2/R not applicable) | ⚠️ HIGH or MEDIUM present, no CRITICAL | 🔴 CRITICAL present

| Category | Controls | CRITICAL | HIGH | MEDIUM | LOW | Status |
| -------- | -------- | -------- | ---- | ------ | --- | ------ |
| STORAGE | 2/2 | 0 | 0 | 0 | 0 | ✅ |
| CRYPTO | 2/2 | 0 | 0 | 0 | 0 | ✅ |
| AUTH | 3/3 | 0 | 0 | 0 | 0 | ✅ |
| NETWORK | 2/2 | 0 | 0 | 0 | 0 | ✅ |
| PLATFORM | 3/3 | 0 | 0 | 0 | 0 | ✅ |
| CODE | 4/4 | 0 | 0 | 0 | 0 | ✅ |
| RESILIENCE | 4/4 | 0 | 0 | 0 | 0 | ✅ L1 |
| PRIVACY | 4/4 | 0 | 0 | 0 | 0 | ✅ |

**Status rules:**

- Any CRITICAL > 0 → 🔴
- No CRITICAL but any HIGH or MEDIUM > 0 → ⚠️
- All zeros, RESILIENCE for L1 app → ✅ L1
- All zeros → ✅

## Recommendations

1. [Most impactful recommendation]
2. [Second most impactful]
3. [Third most impactful]

## Next Steps

- [ ] Create `security-audit/` remediation tracker (see Phase 2)
- [ ] Schedule CRITICAL fixes for immediate sprint
- [ ] Risk-accept or schedule HIGH findings

```

## Report Rules

1. **Order findings by severity** — CRITICAL first, LOW last
2. **Number findings sequentially per report** — Use report-local IDs (e.g., [C1], [H1]) and cite the pattern reference ID where applicable: `[C1] (Pattern C4): Hardcoded crypto key in CryptoManager.swift`. Pattern IDs (C1-C6, H1-H9, M1-M8) are fixed in reference files; report IDs are sequential per audit.
3. **Every finding gets a MASVS mapping** — no unmapped findings
4. **Document false positives as Informational** — prevents re-flagging
5. **Include the executive summary** — stakeholders read this, not individual findings
6. **Release recommendation**:
   - **BLOCK** — any CRITICAL finding present
   - **CONDITIONAL** — HIGH findings requiring risk acceptance
   - **PASS** — no CRITICAL/HIGH, only defense-in-depth gaps

## Cost Optimization for Large Codebases

Full security audits on large codebases consume significant tokens. Use a tiered model strategy:

| Phase | Recommended Model | Why |
|-------|------------------|-----|
| Pattern scanning (CRITICAL/HIGH) | **Sonnet** | Grep-based detection with context — string matching, regex patterns, simple context checks. |
| Contextual analysis | **Sonnet** | Data-flow reasoning, false-positive filtering, cross-file analysis. |
| Report compilation | **Sonnet** | Template filling, formatting, aggregation. |
| Compliance mapping (L2) | **Sonnet** | Requires understanding regulatory requirements against implementation. |
| Fix code generation | **Sonnet / Opus** | Secure replacement code must be correct — use the most capable model available. |

**Practical approach for large projects (500+ Swift files):**

1. Run `scripts/quick-scan.sh` first (zero token cost — local grep)
2. Feed quick-scan output to **Sonnet** for triage and CRITICAL/HIGH report
3. Use **Sonnet** for contextual HIGH findings requiring data-flow analysis
4. Use **Sonnet/Opus** for fix generation and compliance mapping

This reduces audit cost by 60-80% compared to using the most capable model for all phases.

---

## Phase 2: Remediation Tracker

## Purpose

A `security-audit/` directory at the project root. One file per audit scope (feature, module, or full app), plus an overview `README.md`. GitHub checkbox syntax (`- [ ]` / `- [x]`). **Every finding MUST carry a rich description** — File, Line, Severity, MASVS, Issue, Risk, Fix — so anyone can remediate months later without re-auditing.

## Why Not "Fix Everything at Once"

Single mega-PR that fixes all security findings: unreviewable (security fixes often change auth flows, crypto, and storage simultaneously), unrevertable (one fix may break another), blocks feature delivery, impossible to verify each fix independently. Ship CRITICAL fixes first, then HIGH, then defense-in-depth.

## Finding Description Requirements

| Field | Example |
| --- | --- |
| **Title** | `S1: Auth token stored in UserDefaults` |
| **File** | `AuthManager.swift:23` |
| **Severity** | 🔴 Critical / 🟡 High / 🟢 Medium / 🔵 Low |
| **MASVS** | MASVS-STORAGE-1 \| MASWE-0005 |
| **Issue** | 2-4 sentences: what's wrong, what's exposed |
| **Risk** | What an attacker can achieve |
| **Fix** | Concrete steps with secure code |

Optional: Compliance (HIPAA/PCI/GDPR), Dependencies, PR link, Verification steps, Testing profile (L1/L2/R).

---

## Directory Structure

```text
security-audit/
├── README.md                  ← overview dashboard (always up to date)
├── storage-findings.md        ← MASVS-STORAGE findings
├── crypto-findings.md         ← MASVS-CRYPTO findings
├── network-findings.md        ← MASVS-NETWORK findings
├── platform-findings.md       ← MASVS-PLATFORM + MASVS-CODE findings
├── compliance-gaps.md         ← regulatory requirement gaps (L2 apps)
├── cross-cutting.md           ← findings spanning multiple categories
└── discovered.md              ← triage inbox for findings discovered during remediation
```

**Rules:**

- One file per MASVS category or logical grouping
- File name = kebab-case scope name
- `compliance-gaps.md` only for L2/regulated apps — omit for L1
- `discovered.md` for new findings found during fix implementation — triage regularly
- `README.md` is the only file stakeholders need to read for status

---

## README.md Template

When creating an audit tracker for a project, create `security-audit/` with this `README.md`:

```markdown
# Security Audit Plan

**App**: [App Name]
**Testing Profile**: L1 / L2 / R
**Audit Date**: YYYY-MM-DD
**Standard**: OWASP MASVS v2.1.0
**Last Updated**: YYYY-MM-DD

| Scope | File | CRITICAL | HIGH | MEDIUM | LOW | Done | Status |
|-------|------|----------|------|--------|-----|------|--------|
| Storage | [storage-findings.md](storage-findings.md) | 0 | 0 | 0 | 0 | 0 | Planned |
| Crypto | [crypto-findings.md](crypto-findings.md) | 0 | 0 | 0 | 0 | 0 | Planned |
| Network | [network-findings.md](network-findings.md) | 0 | 0 | 0 | 0 | 0 | Planned |
| Platform & Code | [platform-findings.md](platform-findings.md) | 0 | 0 | 0 | 0 | 0 | Planned |
| Compliance | [compliance-gaps.md](compliance-gaps.md) | 0 | 0 | 0 | 0 | 0 | Planned |
| **Total** | | **0** | **0** | **0** | **0** | **0** | **0%** |

## Blocking Release

[List any CRITICAL findings that must be fixed before release]

## Discovered (needs triage)

See [discovered.md](discovered.md) for findings discovered during remediation.
```

---

## Finding File Template

Each scope file follows this structure. Findings are ordered by severity — fix CRITICAL before HIGH:

```markdown
# Scope: Storage Security

> **Context**: Audit of data storage patterns against MASVS-STORAGE-1 and MASVS-STORAGE-2.
> **Audited**: YYYY-MM-DD | **Status**: In Progress

---

## 🔴 CRITICAL

- [ ] **S1: Auth token stored in UserDefaults**
  - **File**: `AuthManager.swift:23`
  - **Severity**: 🔴 Critical
  - **MASVS**: MASVS-STORAGE-1 | MASWE-0005
  - **Issue**: `UserDefaults.standard.set(authToken, forKey: "token")` stores the
    authentication token as plaintext in `Library/Preferences/`. Extractable via
    device backup or jailbroken file system access.
  - **Risk**: Account takeover — attacker obtains valid auth token from backup.
  - **Fix**: Migrate to Keychain with `kSecAttrAccessibleWhenUnlockedThisDeviceOnly`.
  - **Compliance**: HIPAA §164.312(a)(2)(iv), PCI DSS 3.5

## 🟡 HIGH

- [ ] **S2: PII logged in production**
  - **File**: `LoginService.swift:45`
  - **Severity**: 🟡 High
  - **MASVS**: MASVS-STORAGE-2 | MASWE-0001
  - **Issue**: `print("User email: \(email)")` persists to system log.
  - **Risk**: PII exposure via device console or sysdiagnose.
  - **Fix**: Remove or wrap in `#if DEBUG`.

## 🟢 MEDIUM

- [ ] **S3: Missing screenshot prevention**
  - ...

## 🔵 LOW

- [ ] **S4: Debug logging not gated**
  - ...
```

---

## Cross-cutting File Template

```markdown
# Cross-cutting Security Concerns

> Findings that span multiple MASVS categories or require architectural changes.

- [ ] **X1: No privacy manifest (PrivacyInfo.xcprivacy)**
  - **Severity**: 🔵 Low
  - **MASVS**: MASVS-PRIVACY-1
  - **Issue**: App uses UserDefaults and file timestamp APIs without declaring
    required reason APIs in a privacy manifest.
  - **Fix**: Create `PrivacyInfo.xcprivacy` with appropriate API usage reasons.

- [ ] **X2: Mixed ObjC/Swift with no runtime protection strategy**
  - ...
```

---

## Discovered File Template

```markdown
# Discovered During Remediation

> New issues found while fixing other findings.
> Add here immediately — do NOT fix in-flight.
> Triage regularly: move items to the appropriate scope file.

- [ ] **D1: [Title]**
  - **Found during**: [which finding fix]
  - **File**: `File.swift:line`
  - **Severity**: 🟡 High
  - **MASVS**: MASVS-[CATEGORY]-[N]
  - **Issue**: ...
  - **Fix**: ...
  - **Assign to**: [scope file name]
```

---

## Step-by-Step Protocol

### Step 1: Create the security-audit/ directory

After completing a full audit, propose creating the `security-audit/` directory:

1. `README.md` with the overview dashboard
2. One scope file per MASVS category with findings
3. `compliance-gaps.md` for L2/regulated apps
4. `cross-cutting.md` for architectural findings
5. `discovered.md` (empty template)

### Step 2: Plan one remediation PR

Before writing any code, define the scope. Each PR targets findings within **one scope file** and **one severity level**:

```markdown
## Next PR Scope

**Scope file**: storage-findings.md
**PR Title**: Fix plaintext credential storage in AuthManager and SessionService
**Findings**: S1, S2
**Files to change**: AuthManager.swift, SessionService.swift
**Max lines changed**: ~80
**Risk**: Medium (changes auth token storage — test all auth flows)

### Changes:
1. Migrate auth token from UserDefaults to Keychain
2. Remove email from print statement in LoginService

### Verification:
- [ ] Login → verify token stored in Keychain (not UserDefaults)
- [ ] Kill app → relaunch → verify session persists
- [ ] Check device console — no PII in logs
- [ ] Run quick-scan.sh — no new CRITICAL findings

### NOT in this PR:
- Network pinning (different scope)
- Crypto migration (different category)
```

### Step 3: Execute the PR

Apply ONLY the changes listed in the PR scope. If you discover new issues:

- **DO NOT fix them now**
- Add them to `security-audit/discovered.md` with a full description
- Continue with the original scope

### Step 4: Update the tracker

After each PR:

1. Mark findings done in the scope file: `- [ ]` → `- [x]`
2. Update the `README.md` progress table (counts and status)
3. Triage `discovered.md` — move items to the right scope file
4. If a scope is fully remediated, mark it Completed in `README.md`

---

## Remediation Priority Order

Fix findings in this order to maximize security impact per PR:

| Priority | What | Why |
| --- | --- | --- |
| 1 | 🔴 CRITICAL — all scopes | Directly exploitable, blocks release |
| 2 | 🟡 HIGH — Storage & Crypto | Data exposure and weak crypto are most impactful |
| 3 | 🟡 HIGH — Network & Platform | MitM and WebView risks |
| 4 | 🟢 MEDIUM — L2 controls | Defense-in-depth for regulated apps |
| 5 | 🔵 LOW — Best practices | Modernization and hygiene |

---

## PR Size Guidelines

| Change Type | Max Lines |
| --- | --- |
| UserDefaults → Keychain migration | 80 |
| Certificate pinning implementation | 150 |
| ATS configuration fix | 20 |
| NSKeyedUnarchiver → secure deserialization | 100 |
| Crypto algorithm upgrade (one module) | 120 |
| Jailbreak detection implementation | 200 |
| Privacy manifest creation | 50 |
| Biometric auth Keychain binding | 150 |
| Screenshot prevention | 40 |
| URL scheme input validation | 80 |

## Rules

- New findings go to `discovered.md` with full description, NOT into current PR
- Mark findings `- [x]` immediately after completing
- Update `README.md` progress table after every PR
- Triage `discovered.md` at least weekly — move items to scope files
- **Never**: expand PR scope mid-implementation, skip tracker update, fix "one more thing" in unrelated scope
- **Security-specific**: never combine a storage fix with a crypto migration in the same PR — if the combined change breaks authentication, you can't tell which change caused it

## PR Verification Checklist

Before submitting each remediation PR, verify:

```markdown
- [ ] Changes match the defined scope — no extras
- [ ] No new build warnings introduced
- [ ] All existing tests pass
- [ ] App launches and core flows work (login, data access, network calls)
- [ ] Run quick-scan.sh — no new CRITICAL or HIGH findings introduced
- [ ] Secure code follows current API (no deprecated replacements)
- [ ] Keychain operations handle errSecDuplicateItem and errSecItemNotFound
- [ ] No hardcoded keys, tokens, or credentials in the fix
- [ ] Scope file updated — finding marked [x]
- [ ] README.md progress table current
- [ ] New discoveries logged in discovered.md (not fixed in this PR)
```

## When to Deviate

**Acceptable**: CRITICAL production vulnerability (fix immediately, add to tracker retroactively), blocked by dependency (reorder), regulatory deadline (prioritize compliance gaps), finding turns out to be a false positive (remove from tracker with note).

**Never**: expanding PR scope mid-implementation, skipping the tracker update step, fixing "just one more thing" in an unrelated scope, marking a finding done without verification.
