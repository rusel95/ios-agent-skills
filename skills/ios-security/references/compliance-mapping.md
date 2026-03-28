# Compliance Mapping — HIPAA, PCI DSS, GDPR, SOC 2

## How to Use This Reference

Read this file when auditing L2/regulated apps — financial services, healthcare, government, PCI-regulated, or GDPR-subject applications. Each section maps regulatory requirements to concrete iOS implementation checks.

---

## HIPAA — Health Insurance Portability and Accountability Act

**Applies to**: Apps handling Protected Health Information (PHI) — patient records, lab results, prescriptions, health metrics. HealthKit data constituting PHI requires full safeguards.

**Penalties**: Up to $50,000 per violation, capped at $1.5 million annually per type.

### HIPAA → iOS Control Mapping

| HIPAA Requirement | iOS Implementation | Detection |
|---|---|---|
| Encryption at rest (§164.312(a)(2)(iv)) | `NSFileProtectionComplete` on all PHI files; Keychain for credentials | Check `NSPersistentStoreFileProtectionKey`, file protection API calls |
| Encryption in transit (§164.312(e)(1)) | TLS 1.2+ with certificate pinning | ATS config + pinning delegate |
| Access controls (§164.312(a)(1)) | Biometric + passcode auth with Keychain binding | `LAContext` with `kSecAccessControlBiometryCurrentSet` |
| Audit trails (§164.312(b)) | Log all PHI access with timestamp, user ID, action | Search for audit logging around PHI data access |
| Automatic logoff (§164.312(a)(2)(iii)) | Session timeout after inactivity | Timer-based session invalidation |
| Remote wipe (§164.310(d)(2)(iii)) | MDM integration or remote session invalidation | Server-controlled token revocation |
| Minimum necessary (§164.502(b)) | Data minimization — request only needed PHI fields | API response filtering |

### HIPAA-Specific Checks

```swift
// ❌ HIPAA VIOLATION: PHI stored without encryption
let healthRecord = HealthRecord(patient: "John", diagnosis: "...")
try JSONEncoder().encode(healthRecord).write(to: documentURL)

// ✅ FIX: Use Data Protection + encrypted Core Data
// Core Data store with complete file protection
let storeDesc = NSPersistentStoreDescription()
storeDesc.setOption(FileProtectionType.complete as NSObject,
                     forKey: NSPersistentStoreFileProtectionKey)
```

```swift
// ❌ HIPAA VIOLATION: PHI in push notification
UNMutableNotificationContent().body = "Lab results: \(patientName) - \(result)"

// ✅ FIX: Generic notification — detail in-app only
UNMutableNotificationContent().body = "New lab results available"
```

**Audit trail requirement**: For every PHI read/write, log:
- Timestamp (ISO 8601)
- User identifier (authenticated)
- Action (read/create/update/delete)
- Resource identifier (record ID)
- Success/failure status

---

## PCI DSS v4.0.1 — Payment Card Industry Data Security Standard

**Applies to**: Apps processing, storing, or transmitting cardholder data (PANs, CVVs, expiration dates). Apple Pay tokenization provides significant PCI scope reduction.

### PCI DSS → iOS Control Mapping

| PCI DSS Requirement | iOS Implementation | Detection |
|---|---|---|
| Never store SAD post-auth (3.3) | No CVV/CVC storage; PANs tokenized or truncated | Search for variables named `cvv`, `cvc`, `cardNumber` in persistence code |
| Encrypt stored PANs (3.5) | Keychain with AES-256 for any stored card data | Verify Keychain usage, not UserDefaults or files |
| TLS 1.2+ (4.1) | ATS enabled, `tlsMinimumSupportedProtocolVersion = .TLSv12` | ATS config + URLSession config |
| Strong crypto (3.6) | AES-256 via CryptoKit, no DES/3DES/RC4 | Crypto algorithm audit |
| Screen capture prevention (custom) | Blur overlay on background, screenshot notification | `sceneWillResignActive` handler |
| Anti-debugging (custom) | `ptrace(PT_DENY_ATTACH)`, debugger detection | Resilience control checks |
| Code obfuscation (custom) | Symbol renaming, string encryption | Check for SwiftShield or similar tooling |

### PCI-Specific Checks

```swift
// ❌ PCI VIOLATION: Full PAN stored in Keychain
let query: [String: Any] = [
    kSecValueData as String: fullCardNumber.data(using: .utf8)!
]

// ✅ FIX: Store only token or truncated PAN
let tokenizedPAN = try await paymentGateway.tokenize(cardNumber)
// Store only the token reference
```

```swift
// ❌ PCI VIOLATION: CVV stored beyond transaction
UserDefaults.standard.set(cvv, forKey: "savedCVV")

// ✅ FIX: CVV must NEVER be stored — use in-memory only during transaction
```

**PCI DSS 4.0 shift**: Moves from annual audit to continuous monitoring. Recommend automated security scanning in CI/CD pipeline.

---

## GDPR — General Data Protection Regulation

**Applies to**: Apps processing personal data of EU/EEA residents — regardless of where the company is based.

### GDPR → iOS Control Mapping

| GDPR Requirement | iOS Implementation | Detection |
|---|---|---|
| Data minimization (Art. 5(1)(c)) | Collect only necessary data; Apple's App Store Review 5.1 | Audit data collection vs stated purpose |
| Right to erasure (Art. 17) | User-facing data deletion in-app | Search for account/data deletion UI and API |
| Consent management (Art. 7) | Explicit consent dialogs with timestamp logging | Search for consent UI and persistence |
| Consent withdrawal (Art. 7(3)) | Easy opt-out mechanism | Search for consent revocation UI |
| Data portability (Art. 20) | Export user data in machine-readable format | Search for data export functionality |
| Privacy by design (Art. 25) | Data Protection API, encryption, minimal permissions | Architecture-level review |

### GDPR-Specific Checks

```swift
// ❌ GDPR ISSUE: No consent timestamp or version tracking
UserDefaults.standard.set(true, forKey: "gdprConsented")

// ✅ FIX: Record consent with metadata
struct ConsentRecord: Codable {
    let timestamp: Date
    let policyVersion: String
    let consentedCategories: [String]
    let ipCountry: String?  // For jurisdiction determination
}
```

**ATT vs GDPR**: Apple's App Tracking Transparency framework is separate from GDPR consent. Both must be implemented independently. ATT covers tracking across apps/websites; GDPR covers all personal data processing.

**Privacy manifest compliance**: NowSecure found 97% of apps missing required manifests for third-party SDKs in 2025. Check every SDK dependency for `PrivacyInfo.xcprivacy`.

---

## SOC 2 Type II

**Applies to**: B2B SaaS, enterprise apps, apps handling customer data where clients require SOC 2 compliance.

### SOC 2 → iOS Control Mapping

| SOC 2 Principle | iOS Implementation | Detection |
|---|---|---|
| Security — Access control | MFA, biometric auth, session management | Authentication flow review |
| Security — Encryption | AES-256 at rest, TLS in transit | Crypto + network audit |
| Security — Logging | Comprehensive audit trail | Logging implementation review |
| Availability — Error handling | Graceful degradation, offline support | Error handling patterns |
| Confidentiality — Data protection | Keychain, Data Protection API | Storage audit |
| Processing integrity — Input validation | Server-side validation, input sanitization | Input handling review |
| Privacy — Data lifecycle | Retention policies, deletion support | Data management review |

### SOC 2-Specific Checks

- [ ] MFA enforcement for sensitive operations
- [ ] Session timeout and re-authentication
- [ ] Audit logging for all data access (Attributable, timestamped)
- [ ] Encryption for all sensitive data at rest and in transit
- [ ] Access reviews — are permissions role-based?
- [ ] Change management — are code changes tracked and reviewed?

---

## FDA 21 CFR Part 11 — Electronic Records

**Applies to**: FDA-regulated apps (clinical trials, medical device companion apps, pharmaceutical manufacturing).

### FDA → iOS Control Mapping

| FDA Requirement | iOS Implementation | Detection |
|---|---|---|
| Electronic signatures (§11.100) | Two-factor identification (password + biometric) | Auth flow with dual factor |
| Audit trails (§11.10(e)) | ALCOA-compliant logging | Audit log implementation |
| Record integrity (§11.10(a)) | Tamper-evident storage, checksums | Data integrity verification |
| Access controls (§11.10(d)) | Role-based permissions | Authorization implementation |
| System validation (§11.10(a)) | Documented testing, IQ/OQ/PQ | Test coverage and documentation |

**ALCOA framework for audit trails**: Attributable, Legible, Contemporaneous, Original, Accurate.

```swift
// ✅ REFERENCE: ALCOA-compliant audit entry
struct AuditEntry: Codable {
    let id: UUID
    let timestamp: Date              // Contemporaneous
    let userId: String               // Attributable
    let action: AuditAction          // Legible
    let resourceType: String
    let resourceId: String
    let previousValue: String?       // Original (tracks changes)
    let newValue: String?
    let checksum: String             // Accurate (integrity verification)
}
```

---

## Compliance Quick Reference

| Regulation | Key iOS Control | Most Common Gap |
|---|---|---|
| HIPAA | `NSFileProtectionComplete` + audit trails | PHI in push notifications / missing audit logging |
| PCI DSS | Never store SAD; tokenize PANs | CVV stored locally; full PAN in UserDefaults |
| GDPR | Consent records + data deletion | Missing consent timestamps; no data export |
| SOC 2 | MFA + comprehensive logging | Incomplete audit trails; missing session timeout |
| FDA 21 CFR Part 11 | ALCOA audit trails + dual-factor signatures | Non-validated audit logging; single-factor auth |
