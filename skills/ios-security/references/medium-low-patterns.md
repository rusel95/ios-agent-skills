# Medium & Low Severity Patterns

## How to Use This Reference

Read this file during full security audits after CRITICAL and HIGH patterns are addressed. These findings strengthen defense-in-depth and reflect best practices. MEDIUM issues are relevant for L2 apps; LOW issues are modernization recommendations.

---

## 🟢 MEDIUM — Defense-in-Depth

### M1: Missing Jailbreak Detection (L2/R Apps)

**Problem**: On jailbroken devices, the app sandbox is compromised. Keychain items can be dumped, network traffic intercepted without pinning bypass, and runtime hooks injected.
**MASVS**: MASVS-RESILIENCE-1 | MASWE-0092

**Detection**: For apps handling financial, health, or payment data — search for jailbreak detection logic. If absent, flag as MEDIUM.

**Expected implementation checks**:
- File system: `/Applications/Cydia.app`, `/Library/MobileSubstrate/`, `/usr/sbin/sshd`
- URL schemes: `cydia://`, `sileo://`
- Sandbox integrity: write test outside sandbox
- Dynamic library inspection: `_dyld_image_count()` enumeration
- Fork behavior: `fork()` succeeds on jailbroken devices

```swift
// ✅ REFERENCE: Layered jailbreak detection
func isDeviceCompromised() -> Bool {
    let suspiciousPaths = [
        "/Applications/Cydia.app",
        "/Library/MobileSubstrate/MobileSubstrate.dylib",
        "/usr/sbin/sshd",
        "/etc/apt",
        "/usr/bin/ssh"
    ]
    // Layer 1: File system checks
    for path in suspiciousPaths {
        if FileManager.default.fileExists(atPath: path) { return true }
    }
    // Layer 2: Sandbox integrity
    let testPath = "/private/jailbreak_test_\(UUID().uuidString)"
    do {
        try "test".write(toFile: testPath, atomically: true, encoding: .utf8)
        try FileManager.default.removeItem(atPath: testPath)
        return true  // Write succeeded — sandbox is broken
    } catch { /* Expected on non-jailbroken */ }
    // Layer 3: URL scheme check
    if let url = URL(string: "cydia://"),
       UIApplication.shared.canOpenURL(url) { return true }
    return false
}
```

> **Note**: `canOpenURL("cydia://")` always returns `false` unless `cydia` is listed in
> `LSApplicationQueriesSchemes` in Info.plist. Adding `cydia` to the allowlist is
> inadvisable for App Store apps, so this detection layer is unreliable. Prefer file system
> checks (Layer 1) and sandbox integrity (Layer 2) as primary detection mechanisms.

**Context**: Only flag for L2/R apps. General-purpose apps do not require jailbreak detection.

---

### M2: Missing Screenshot Prevention

**Problem**: iOS captures a screenshot when apps enter background (visible in app switcher). Sensitive data on screen is captured in the snapshot.
**MASVS**: MASVS-STORAGE-2 | MASWE-0003

**Detection**: For apps displaying sensitive data — search for `applicationWillResignActive`, `sceneWillResignActive`, or `willResignActiveNotification` handlers that apply blur/overlay. If absent, flag.

```swift
// ✅ REFERENCE: Blur overlay on background
func sceneWillResignActive(_ scene: UIScene) {
    let blurEffect = UIBlurEffect(style: .light)
    let blurView = UIVisualEffectView(effect: blurEffect)
    blurView.tag = 999
    blurView.frame = window?.bounds ?? .zero
    window?.addSubview(blurView)
}

func sceneDidBecomeActive(_ scene: UIScene) {
    window?.viewWithTag(999)?.removeFromSuperview()
}
```

---

### M3: Pasteboard Without Expiration

**Problem**: `UIPasteboard.general` shares data across apps and devices (Universal Clipboard since iOS 10). Sensitive data copied to pasteboard is accessible to other apps.
**MASVS**: MASVS-STORAGE-2 | MASWE-0003

**Detection**: Search for `UIPasteboard.general.string =` or `UIPasteboard.general.setItems(` without `.localOnly` and `.expirationDate` options.

```swift
// ❌ MEDIUM: Data shared across apps and devices indefinitely
UIPasteboard.general.string = sensitiveText
```

```swift
// ✅ FIX: Local-only with expiration (iOS 10+)
UIPasteboard.general.setItems(
    [[UTType.utf8PlainText.identifier: sensitiveText]],
    options: [.localOnly: true, .expirationDate: Date().addingTimeInterval(60)])
```

---

### M4: URL Scheme Handlers Without Input Validation

**Problem**: Custom URL schemes are not authenticated — any app can invoke them. Without validation, malicious apps can inject parameters to trigger unintended behavior.
**MASVS**: MASVS-PLATFORM-1 | MASWE-0076

**Detection**: Search for `application(_:open:options:)` handlers. Verify they validate source application, whitelist allowed paths, and sanitize parameters.

```swift
// ❌ MEDIUM: No validation of URL scheme parameters
func application(_ app: UIApplication, open url: URL, options: [UIApplication.OpenURLOptionsKey: Any]) -> Bool {
    let action = url.host
    performAction(action!)  // Unvalidated deep link
    return true
}
```

```swift
// ✅ FIX: Validate source, whitelist paths, sanitize parameters
func application(_ app: UIApplication, open url: URL, options: [UIApplication.OpenURLOptionsKey: Any]) -> Bool {
    guard let host = url.host, allowedHosts.contains(host) else { return false }
    guard let components = URLComponents(url: url, resolvingAgainstBaseURL: false),
          let params = components.queryItems else { return false }
    // Validate and sanitize each parameter
    return handleValidatedDeepLink(host: host, params: params)
}
```

**Note**: Prefer Universal Links over custom URL schemes — they provide cryptographic domain verification.

---

### M5: Sensitive Files Without Backup Exclusion

**Problem**: Files in the app's Documents and Library directories are included in iCloud/iTunes backups by default. Sensitive files can be extracted from backups.
**MASVS**: MASVS-STORAGE-2 | MASWE-0003

**Detection**: Search for file write operations creating sensitive data files. Verify `isExcludedFromBackup = true` is set via `URLResourceValues`.

```swift
// ❌ MEDIUM: Sensitive file included in backups
try sensitiveData.write(to: fileURL)
```

```swift
// ✅ FIX: Exclude from backup after writing
try sensitiveData.write(to: fileURL)
var resourceValues = URLResourceValues()
resourceValues.isExcludedFromBackup = true
try fileURL.setResourceValues(resourceValues)
```

**Note**: Atomic file write operations can reset the backup exclusion flag — re-apply after modifications.

---

### M6: Biometric Auth Without Server-Side Binding

**Problem**: `LAContext.evaluatePolicy` returns a local boolean — easily bypassed on jailbroken devices by hooking the completion handler. Without server-side cryptographic binding, biometric auth is decorative.
**MASVS**: MASVS-AUTH-2 | MASWE-0036

**Detection**: Search for `LAContext().evaluatePolicy(` without a corresponding Keychain operation using `kSecAccessControlBiometryCurrentSet` or `SecAccessControlCreateWithFlags` with `.biometryCurrentSet`.

```swift
// ❌ MEDIUM: Bypassable local-only check
let context = LAContext()
context.evaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, localizedReason: "Authenticate") { success, _ in
    if success { self.unlockApp() }  // Hook to always return true
}
```

```swift
// ✅ FIX: Bind biometric to Keychain access control
let access = SecAccessControlCreateWithFlags(nil,
    kSecAttrAccessibleWhenUnlockedThisDeviceOnly,
    [.biometryCurrentSet, .privateKeyUsage], nil)!
// Store credential in Keychain with biometric access control
let query: [String: Any] = [
    kSecClass as String: kSecClassGenericPassword,
    kSecAttrAccount as String: "authCredential",
    kSecValueData as String: credential,
    kSecAttrAccessControl as String: access
]
```

---

### M7: Custom Keyboard Not Blocked on Sensitive Fields

**Problem**: Third-party keyboard extensions can capture and transmit keystrokes. Sensitive input fields should force the system keyboard.
**MASVS**: MASVS-PLATFORM-3 | MASWE-0082

**Detection**: Search for text fields handling passwords, credit cards, SSNs. Verify `isSecureTextEntry = true` or that `textContentType` is set to `.password` or `.oneTimeCode`.

```swift
// ❌ MEDIUM: Third-party keyboard can capture password input
let passwordField = UITextField()
passwordField.placeholder = "Password"
```

```swift
// ✅ FIX: Force system keyboard
passwordField.isSecureTextEntry = true  // Also masks input
```

---

### M8: WKWebView With JavaScript Loading Untrusted Content

**Problem**: WKWebView with JavaScript enabled loading untrusted URLs can execute malicious scripts in the app's context, especially if a JavaScript bridge is registered.
**MASVS**: MASVS-PLATFORM-2 | MASWE-0082

**Detection**: Search for `WKWebView` with `javaScriptEnabled = true` (or default, which is enabled) loading URLs not in a hardcoded allowlist. Flag if `WKUserContentController.add(_:name:)` is used without command whitelisting.

```swift
// ❌ MEDIUM: JS bridge exposed to untrusted content
let controller = WKUserContentController()
controller.add(self, name: "nativeHandler")  // Bridge to native code
let config = WKWebViewConfiguration()
config.userContentController = controller
let webView = WKWebView(frame: .zero, configuration: config)
webView.load(URLRequest(url: userProvidedURL))  // Untrusted URL
```

```swift
// ✅ FIX: Validate URL against allowlist, use nonPersistent store
guard allowedDomains.contains(url.host ?? "") else { return }
let config = WKWebViewConfiguration()
config.websiteDataStore = .nonPersistent()
let allowJS = trustedDomains.contains(url.host ?? "")
if #available(iOS 14.0, *) {
    let prefs = WKWebpagePreferences()
    prefs.allowsContentJavaScript = allowJS
    config.defaultWebpagePreferences = prefs
} else {
    config.preferences.javaScriptEnabled = allowJS  // Deprecated in iOS 14, needed for iOS 13
}
```

---

## 🔵 LOW — Best Practices & Modernization

### L1: CommonCrypto Where CryptoKit Is Available

**Detection**: CommonCrypto imports (`import CommonCrypto`) in projects targeting iOS 13+.
**Recommendation**: Migrate to CryptoKit for type-safe, Swift-native crypto with Secure Enclave support.

### L2: arc4random for Token Generation

**Detection**: `arc4random()` or `arc4random_uniform()` used for generating authentication tokens or cryptographic nonces.
**Recommendation**: Use `SecRandomCopyBytes` for cryptographic randomness.

### L3: Debug Logging Not Gated

**Detection**: `print()` or `debugPrint()` calls outside `#if DEBUG` blocks.
**Recommendation**: Wrap debug-only logging in compilation flags.

### L4: Missing Privacy Manifest

**Detection**: Absence of `PrivacyInfo.xcprivacy` in the app bundle. NowSecure found 42% of iOS apps missing their privacy manifest in 2025.
**Recommendation**: Create `PrivacyInfo.xcprivacy` declaring API usage reasons for required reason APIs (UserDefaults, file timestamps, disk space, etc.).

### L5: Overly Broad Entitlements

**Detection**: Entitlements file (`.entitlements`) with capabilities not used by the app (e.g., `com.apple.developer.associated-domains` without Universal Links).
**Recommendation**: Remove unused entitlements to minimize attack surface.

### L6: Missing Rate Limiting on Authentication

**Detection**: Login/authentication endpoints called without local retry limiting.
**Recommendation**: Implement exponential backoff and maximum attempt tracking.

<detection_checklist>
## MEDIUM/LOW Detection Checklist

- [ ] L2/R apps: Check for jailbreak detection implementation
- [ ] Check for `sceneWillResignActive` / `applicationWillResignActive` blur overlay (apps with sensitive UI)
- [ ] Grep for `UIPasteboard.general` writes without `.localOnly` and `.expirationDate`
- [ ] Check `application(_:open:options:)` handlers for input validation
- [ ] Check file writes for `isExcludedFromBackup` on sensitive data files
- [ ] Check `LAContext.evaluatePolicy` for corresponding Keychain access control binding
- [ ] Check password/credit card fields for `isSecureTextEntry`
- [ ] Check WKWebView JS bridge usage with untrusted URLs
- [ ] Check for `import CommonCrypto` in iOS 13+ projects
- [ ] Check for `PrivacyInfo.xcprivacy` presence
</detection_checklist>
