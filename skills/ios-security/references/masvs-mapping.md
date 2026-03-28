# MASVS v2.1.0 Control → Detection Pattern Mapping

## How to Use This Reference

Use this file to look up which detection patterns apply to a specific MASVS control, or to verify audit coverage. Each control lists the corresponding checks, reference files, and MASWE weakness IDs.

## MASVS Structure

MASVS v2.1.0 defines 24 controls across 8 categories. Testing profiles determine rigor:
- **MAS-L1** (standard): Baseline security for all apps
- **MAS-L2** (defense-in-depth): Financial, healthcare, government, PCI-regulated apps
- **MAS-R** (resilience): Apps requiring tamper protection

---

## MASVS-STORAGE — Data Storage

### MASVS-STORAGE-1: Secure Storage of Sensitive Data
**Profile**: L1 (unencrypted sandbox OK) / L2 (Keychain-managed encryption required)
**MASWE**: MASWE-0005 (Insecure Data Storage)

| Check | Severity | Pattern File |
|-------|----------|-------------|
| Sensitive data in UserDefaults | 🔴 CRITICAL | critical-patterns.md #C2 |
| Weak Keychain accessibility | 🟡 HIGH | high-patterns.md #H2 |
| Hardcoded secrets in source | 🔴 CRITICAL | critical-patterns.md #C1 |
| Missing file protection (L2) | 🟢 MEDIUM | compliance-mapping.md (HIPAA) |

### MASVS-STORAGE-2: Data Leakage Prevention
**Profile**: L1 / L2
**MASWE**: MASWE-0001 (Sensitive Data in Logs), MASWE-0003 (Data Leakage)

| Check | Severity | Pattern File |
|-------|----------|-------------|
| PII in log statements | 🟡 HIGH | high-patterns.md #H7 |
| Missing screenshot prevention | 🟢 MEDIUM | medium-low-patterns.md #M2 |
| Pasteboard without expiration | 🟢 MEDIUM | medium-low-patterns.md #M3 |
| Backup exclusion for sensitive files | 🟢 MEDIUM | medium-low-patterns.md #M5 |

---

## MASVS-CRYPTO — Cryptography

### MASVS-CRYPTO-1: Algorithm and Configuration Correctness
**Profile**: L1 / L2
**MASWE**: MASWE-0020 (Weak Crypto), MASWE-0022 (Improper IV), MASWE-0027 (Weak Randomness)

| Check | Severity | Pattern File |
|-------|----------|-------------|
| Deprecated algorithms (MD5/SHA1/DES/3DES/RC4) | 🟡 HIGH | high-patterns.md #H3 |
| ECB mode encryption | 🟡 HIGH | high-patterns.md #H4 |
| Hardcoded/zero IVs | 🔴 CRITICAL | critical-patterns.md #C6 |
| Insecure randomness (rand/random/srand) | 🟡 HIGH | high-patterns.md #H5 |

### MASVS-CRYPTO-2: Key Management
**Profile**: L1 / L2
**MASWE**: MASWE-0013 (Hardcoded Keys)

| Check | Severity | Pattern File |
|-------|----------|-------------|
| Hardcoded cryptographic keys | 🔴 CRITICAL | critical-patterns.md #C4 |
| Password used directly as key | 🔴 CRITICAL | critical-patterns.md #C4 |
| Missing Secure Enclave for L2 keys | 🟢 MEDIUM | critical-patterns.md #C4 (fix section) |

---

## MASVS-AUTH — Authentication and Authorization

### MASVS-AUTH-1: Authentication Protocol Security
**Profile**: L1 / L2

| Check | Severity | Pattern File |
|-------|----------|-------------|
| Missing rate limiting on auth | 🔵 LOW | medium-low-patterns.md #L6 |
| Hardcoded credentials | 🔴 CRITICAL | critical-patterns.md #C1 |

### MASVS-AUTH-2: Local Authentication
**Profile**: L1 / L2
**MASWE**: MASWE-0036 (Biometric Bypass)

| Check | Severity | Pattern File |
|-------|----------|-------------|
| Biometric without server binding | 🟢 MEDIUM | medium-low-patterns.md #M6 |

### MASVS-AUTH-3: Step-Up Authentication
**Profile**: L2

| Check | Severity | Pattern File |
|-------|----------|-------------|
| Missing re-auth for sensitive ops | 🟢 MEDIUM | Contextual check |

---

## MASVS-NETWORK — Network Communication

### MASVS-NETWORK-1: Traffic Security
**Profile**: L1 / L2
**MASWE**: MASWE-0050 (Cleartext Traffic)

| Check | Severity | Pattern File |
|-------|----------|-------------|
| Globally disabled ATS | 🔴 CRITICAL | critical-patterns.md #C3 |
| Partial ATS exceptions | 🟡 HIGH | plist-audit.md #P2 |
| TLS below 1.2 | 🟡 HIGH | plist-audit.md #P3 |

### MASVS-NETWORK-2: Identity Pinning
**Profile**: L2
**MASWE**: MASWE-0047 (Missing Pinning)

| Check | Severity | Pattern File |
|-------|----------|-------------|
| Missing certificate pinning | 🟡 HIGH | high-patterns.md #H1 |

---

## MASVS-PLATFORM — Platform Interaction

### MASVS-PLATFORM-1: IPC Security
**Profile**: L1 / L2
**MASWE**: MASWE-0076 (URL Scheme Injection)

| Check | Severity | Pattern File |
|-------|----------|-------------|
| URL scheme without validation | 🟢 MEDIUM | medium-low-patterns.md #M4 |
| Universal Links vs URL schemes | 🟢 MEDIUM | plist-audit.md #P5 |

### MASVS-PLATFORM-2: WebView Security
**Profile**: L1 / L2
**MASWE**: MASWE-0082 (WebView Misconfiguration)

| Check | Severity | Pattern File |
|-------|----------|-------------|
| UIWebView usage | 🟡 HIGH | high-patterns.md #H6 |
| WKWebView JS bridge + untrusted content | 🟢 MEDIUM | medium-low-patterns.md #M8 |

### MASVS-PLATFORM-3: UI Security
**Profile**: L1 / L2
**MASWE**: MASWE-0082

| Check | Severity | Pattern File |
|-------|----------|-------------|
| Missing custom keyboard blocking | 🟢 MEDIUM | medium-low-patterns.md #M7 |

---

## MASVS-CODE — Code Quality

### MASVS-CODE-1: Platform Version Security
**Profile**: L1

| Check | Severity | Pattern File |
|-------|----------|-------------|
| Minimum deployment target check | 🔵 LOW | Contextual |

### MASVS-CODE-2: App Update Mechanism
**Profile**: L1

| Check | Severity | Pattern File |
|-------|----------|-------------|
| Force update mechanism | 🔵 LOW | Contextual |

### MASVS-CODE-3: Third-Party Dependencies
**Profile**: L1 / L2

| Check | Severity | Pattern File |
|-------|----------|-------------|
| Outdated dependencies with known CVEs | 🟡 HIGH | Check Podfile.lock / Package.resolved |

### MASVS-CODE-4: Input Validation and Serialization
**Profile**: L1 / L2
**MASWE**: MASWE-0058 (Insecure Deserialization)

| Check | Severity | Pattern File |
|-------|----------|-------------|
| Insecure deserialization | 🔴 CRITICAL | critical-patterns.md #C5 |
| NSCoding without NSSecureCoding | 🟡 HIGH | high-patterns.md #H8 |
| Format string vulnerability | 🟡 HIGH | high-patterns.md #H9, objc-specific.md #R4 |

---

## MASVS-RESILIENCE — Resilience Against Reverse Engineering

### MASVS-RESILIENCE-1: Platform Integrity Verification
**Profile**: R
**MASWE**: MASWE-0092 (Missing Integrity Checks)

| Check | Severity | Pattern File |
|-------|----------|-------------|
| Missing jailbreak detection | 🟢 MEDIUM | medium-low-patterns.md #M1 |

### MASVS-RESILIENCE-2: Anti-Tampering
**Profile**: R

| Check | Severity | Pattern File |
|-------|----------|-------------|
| Code signing verification | 🟢 MEDIUM | Contextual |

### MASVS-RESILIENCE-3: Anti-Static Analysis
**Profile**: R

| Check | Severity | Pattern File |
|-------|----------|-------------|
| String obfuscation | 🔵 LOW | Contextual (SwiftShield, Swift Confidential) |
| Symbol stripping | 🔵 LOW | Build settings check |

### MASVS-RESILIENCE-4: Anti-Dynamic Analysis
**Profile**: R

| Check | Severity | Pattern File |
|-------|----------|-------------|
| Debugger detection | 🟢 MEDIUM | ptrace + sysctl checks |
| Frida detection | 🟢 MEDIUM | dylib enumeration + port check |

---

## MASVS-PRIVACY — Privacy Controls (Added v2.1.0)

### MASVS-PRIVACY-1: Data Minimization
**Profile**: L1 / L2

| Check | Severity | Pattern File |
|-------|----------|-------------|
| Privacy manifest presence | 🔵 LOW | plist-audit.md #P8 |
| Overly broad permissions | 🔵 LOW | plist-audit.md #P9 |

### MASVS-PRIVACY-2: Transparency
**Profile**: L1 / L2

| Check | Severity | Pattern File |
|-------|----------|-------------|
| Usage description completeness | 🟢 MEDIUM | plist-audit.md #P7 |

### MASVS-PRIVACY-3: User Control
**Profile**: L1 / L2

| Check | Severity | Pattern File |
|-------|----------|-------------|
| Consent management | 🟢 MEDIUM | compliance-mapping.md (GDPR) |
| Data deletion capability | 🟢 MEDIUM | compliance-mapping.md (GDPR) |

### MASVS-PRIVACY-4: Data Lifecycle
**Profile**: L1 / L2

| Check | Severity | Pattern File |
|-------|----------|-------------|
| Data retention policies | 🟢 MEDIUM | Contextual |

---

## Coverage Summary

| Category | Controls | CRITICAL | HIGH | MEDIUM | LOW |
|----------|----------|----------|------|--------|-----|
| STORAGE | 2 | 2 | 2 | 3 | 0 |
| CRYPTO | 2 | 2 | 3 | 1 | 0 |
| AUTH | 3 | 1 | 0 | 2 | 1 |
| NETWORK | 2 | 1 | 3 | 0 | 0 |
| PLATFORM | 3 | 0 | 1 | 4 | 0 |
| CODE | 4 | 1 | 3 | 0 | 2 |
| RESILIENCE | 4 | 0 | 0 | 4 | 2 |
| PRIVACY | 4 | 0 | 0 | 3 | 2 |
| **Total** | **24** | **7** | **12** | **17** | **7** |
