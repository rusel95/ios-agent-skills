# iOS Security Audit — Rules Quick Reference

## Do's — Always Follow

1. **Start with CRITICAL patterns** — Scan for hardcoded secrets, UserDefaults misuse, and disabled ATS before deeper analysis. These are high-confidence, low-false-positive findings.
2. **Report the MASVS control** — Every finding must map to a MASVS control and, where available, a MASWE weakness ID for traceability.
3. **Provide both vulnerable and secure code** — Every finding includes the problematic code and a concrete, copy-pasteable fix.
4. **Detect language per file** — Apply Objective-C runtime checks only to `.m`/`.mm` files. Apply Swift-specific patterns to `.swift` files. Never mix detection strategies.
5. **Cross-reference Info.plist with code** — ATS exceptions, URL schemes, and entitlements must be validated against actual code behavior.
6. **Consider the testing profile** — L1 issues are always relevant. L2 and R issues only apply when the app handles sensitive/regulated data.
7. **Flag false positives explicitly** — If a pattern matches but context makes it safe (e.g., `UserDefaults` for non-sensitive preferences), note it as informational rather than a finding.

## Don'ts — Avoid These Audit Mistakes

### Never: Flag non-sensitive UserDefaults usage

```swift
// ✅ This is SAFE — user preference, not sensitive data
UserDefaults.standard.set(true, forKey: "hasSeenOnboarding")
```

Only flag UserDefaults when keys suggest sensitive data (password, token, secret, credential, session, auth).

### Never: Flag SHA-1/MD5 used for non-security checksums

```swift
// ✅ Acceptable — file integrity check, not cryptographic security
let checksum = Insecure.MD5.hash(data: fileData)
```

Flag only when used for password hashing, signature verification, or HMAC.

### Never: Demand L2 controls for L1 apps

Certificate pinning, jailbreak detection, and encryption at rest are L2/R requirements. Flag as informational for general-purpose apps, not as findings.
