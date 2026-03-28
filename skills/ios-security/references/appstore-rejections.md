# App Store Rejection Prevention

## How to Use This Reference

Read this file during pre-release security gates or when the user asks "is this ready for release" or "App Store checklist". These are security-related issues that cause App Store rejection — distinct from security vulnerabilities (which may ship but create risk) because rejections **block release entirely**.

---

## Rejection Categories

### Hard Rejections — Automated (Binary Scan)

Apple's automated tooling catches these before human review. No appeal possible.

#### AS1: UIWebView Binary References

**ITMS-90809**: "UIWebView API Deprecation"
**Status**: Hard reject since April 2020

Apple scans the binary for `UIWebView` class references — including in linked frameworks and pods.

**Detection**:

- Source: grep for `UIWebView` in `.swift`, `.m`, `.h` files
- Binary: `grep -r "UIWebView" YourApp.app/`
- Dependencies: check `Pods/` and `Carthage/` for UIWebView usage

```swift
// ❌ REJECT: Any UIWebView reference in binary
let webView = UIWebView(frame: view.bounds)
```

```swift
// ✅ FIX: Migrate to WKWebView
let webView = WKWebView(frame: view.bounds, configuration: WKWebViewConfiguration())
```

**Common trap**: Your code uses WKWebView, but an old pod still links UIWebView. Update or replace the dependency.

**Cross-ref**: high-patterns.md #H6

---

#### AS2: Missing Privacy Manifest for Required Reason APIs

**Status**: Hard reject since Spring 2024 (phased enforcement)

Apps using "required reason APIs" must include `PrivacyInfo.xcprivacy` declaring usage reasons. Third-party SDKs must also include their own privacy manifests.

**Required reason API categories**:

| API Category | Common Usage |
| ------------ | ------------ |
| `NSPrivacyAccessedAPICategoryFileTimestamp` | `FileManager` file modification dates |
| `NSPrivacyAccessedAPICategorySystemBootTime` | `ProcessInfo.processInfo.systemUptime` |
| `NSPrivacyAccessedAPICategoryDiskSpace` | `FileManager` disk space queries |
| `NSPrivacyAccessedAPICategoryUserDefaults` | `UserDefaults` (all usage) |
| `NSPrivacyAccessedAPICategoryActiveKeyboards` | Keyboard extension checks |

**Detection**:

1. Check for `PrivacyInfo.xcprivacy` in the project
2. Verify each required reason API category used in code is declared
3. Check that each third-party SDK (pods, SPM packages) includes its own privacy manifest

```text
# Quick check for required reason API usage
grep -rn "UserDefaults" --include="*.swift" .
grep -rn "fileModificationDate\|modificationDate\|creationDate" --include="*.swift" .
grep -rn "systemUptime\|ProcessInfo" --include="*.swift" .
grep -rn "volumeAvailableCapacity\|availableCapacity" --include="*.swift" .
```

**Cross-ref**: plist-audit.md #P8

---

#### AS3: Missing Usage Description Keys

**Status**: Hard reject (crash at runtime without description = immediate rejection)

Every protected API requires an `NS*UsageDescription` key in Info.plist. Missing keys cause a runtime crash when the permission dialog would appear — Apple's automated testing catches this.

**Detection**: Cross-reference API usage in code against Info.plist keys:

| API Framework | Required Plist Key |
| ------------- | ------------------ |
| Camera (`AVCaptureDevice`) | `NSCameraUsageDescription` |
| Microphone (`AVAudioSession.record`) | `NSMicrophoneUsageDescription` |
| Photos (`PHPhotoLibrary`) | `NSPhotoLibraryUsageDescription` |
| Location (`CLLocationManager`) | `NSLocationWhenInUseUsageDescription` |
| Contacts (`CNContactStore`) | `NSContactsUsageDescription` |
| Calendars (`EKEventStore`) | `NSCalendarsUsageDescription` |
| Face ID (`LAContext`) | `NSFaceIDUsageDescription` |
| Bluetooth (`CBCentralManager`) | `NSBluetoothAlwaysUsageDescription` |
| Health (`HKHealthStore`) | `NSHealthShareUsageDescription` |
| Motion (`CMMotionManager`) | `NSMotionUsageDescription` |
| Local Network (`NWBrowser`) | `NSLocalNetworkUsageDescription` |
| Tracking (`ATTrackingManager`) | `NSUserTrackingUsageDescription` |

**Cross-ref**: plist-audit.md #P7

---

### Hard Rejections — Human Review

Apple's review team flags these during manual testing.

#### AS4: Non-Functional App or Crash on Launch

Apps that crash during review are immediately rejected. Security-related crash causes:

- Missing Keychain migration after changing accessibility level
- Forced unwrap on Keychain read returning `nil` after first install
- Missing entitlements for required capabilities (push, HealthKit, Apple Pay)
- `fatalError()` or `preconditionFailure()` in production code paths

**Detection**: Search for `fatalError(`, `preconditionFailure(`, `assert(` outside `#if DEBUG` blocks in production code paths.

---

#### AS5: Guideline 5.1.1 — Data Collection and Storage

Apps must accurately describe data collection in App Store Connect privacy labels. Mismatch between declared privacy labels and actual data collection detected in the binary causes rejection.

**Common mismatches**:

- App collects device identifiers but doesn't declare "Device ID" in privacy labels
- App uses analytics SDKs (Firebase, Mixpanel) but doesn't declare "Analytics" data collection
- App shares data with third-party SDKs but doesn't declare "Third-Party Advertising"

**Detection**: Audit third-party SDKs and their data collection against App Store Connect privacy declarations.

---

#### AS6: Guideline 5.1.2 — Data Use and Sharing (ATT)

Apps that access IDFA or track users across apps/websites must use `ATTrackingManager.requestTrackingAuthorization()` and include `NSUserTrackingUsageDescription`.

**Detection**:

```text
grep -rn "ASIdentifierManager\|advertisingIdentifier\|IDFA" --include="*.swift" --include="*.m" .
grep -rn "ATTrackingManager" --include="*.swift" .
```

If advertising identifier usage is found without ATTrackingManager, flag as rejection risk.

---

#### AS7: Insecure HTTP Without Justification

**Guideline 2.1**: Apps that disable ATS globally (`NSAllowsArbitraryLoads = true`) without justified exception domains face rejection. Apple expects HTTPS for all connections.

**Detection**: Same as CRITICAL pattern C3. If `NSAllowsArbitraryLoads = true` exists without specific `NSExceptionDomains` entries, flag as both security CRITICAL and rejection risk.

**Cross-ref**: critical-patterns.md #C3, plist-audit.md #P1

---

### Conditional Rejections — Depends on App Category

#### AS8: Missing Export Compliance (Encryption)

Apps using encryption beyond standard HTTPS must either:

- Set `ITSAppUsesNonExemptEncryption = NO` in Info.plist (if only standard HTTPS)
- Submit an encryption self-classification report

**Detection**: Check Info.plist for `ITSAppUsesNonExemptEncryption`. If absent and the app uses custom encryption (CommonCrypto, CryptoKit beyond basic hashing), flag.

```text
grep -rn "CCCrypt\|SecKeyEncrypt\|CryptoKit\|AES\|ChaCha" --include="*.swift" --include="*.m" .
```

If custom encryption is found and `ITSAppUsesNonExemptEncryption` is not set, the developer will be prompted during submission — not a hard reject, but blocks automated delivery.

---

#### AS9: HealthKit Without Purpose

Apps with HealthKit entitlements must use HealthKit features and explain why. Unused HealthKit entitlements cause rejection.

**Detection**: Check `.entitlements` for `com.apple.developer.healthkit`. If present, verify `HKHealthStore` is used in code.

**Cross-ref**: plist-audit.md #P9

---

## Pre-Submission Checklist

Run this checklist before every App Store submission:

```text
[ ] No UIWebView references in binary or dependencies (AS1)
[ ] PrivacyInfo.xcprivacy present with all required reason APIs declared (AS2)
[ ] All NS*UsageDescription keys present for APIs used (AS3)
[ ] No fatalError/preconditionFailure in production code paths (AS4)
[ ] Privacy labels match actual data collection (AS5)
[ ] ATTrackingManager used if IDFA accessed (AS6)
[ ] ATS not globally disabled, or exceptions justified (AS7)
[ ] ITSAppUsesNonExemptEncryption declared in Info.plist (NO for HTTPS-only, YES + compliance docs for custom crypto) (AS8)
[ ] All entitlements match actual feature usage (AS9)
[ ] App launches and completes core flows without crash
[ ] Test account credentials provided in App Store Connect review notes
```

## Quick Scan Addition

To extend `scripts/quick-scan.sh` with App Store rejection checks, add blocks matching the existing inline style. Example for AS1:

```bash
# === APP STORE REJECTION CHECKS ===
echo ""
echo -e "${YELLOW}--- APP STORE REJECTION CHECKS ---${NC}"
echo ""

# AS1: UIWebView references
echo -n "[AS1] UIWebView binary references: "
MATCHES=$(grep -rn --include="*.swift" --include="*.m" --include="*.h" \
    'UIWebView' "$PROJECT_ROOT" 2>/dev/null || true)
if [ -n "$MATCHES" ]; then
    COUNT=$(echo "$MATCHES" | wc -l | tr -d ' ')
    echo -e "${RED}$COUNT potential finding(s)${NC}"
    echo "$MATCHES"
else
    echo -e "${GREEN}None found${NC}"
fi
echo ""
```

Repeat the same pattern for AS2 (find PrivacyInfo.xcprivacy), AS4 (fatalError outside DEBUG), AS8 (ITSAppUsesNonExemptEncryption).

## Integration With Security Audit

App Store rejection findings should appear in the audit report as a separate section **after** severity-based findings:

```markdown
## App Store Rejection Risks

| # | Issue | Status | Cross-ref |
| - | ----- | ------ | --------- |
| AS1 | UIWebView in dependency X | BLOCKING | H6 |
| AS2 | Missing PrivacyInfo.xcprivacy | BLOCKING | P8 |
| AS7 | ATS globally disabled | BLOCKING | C3 |
```

This section uses **BLOCKING / WARNING / CLEAR** status rather than severity levels — rejection is binary (you ship or you don't).
