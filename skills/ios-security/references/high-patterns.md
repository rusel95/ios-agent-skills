# High Severity Detection Patterns & Fixes

## How to Use This Reference

Read this file after completing CRITICAL pattern scans. HIGH findings require more context than CRITICAL ones — a pattern match may need data-flow analysis to confirm exploitability. Each pattern includes false-positive guidance.

## Severity

All patterns in this file are **🟡 HIGH** — significant security risks that require context to confirm.

## H1: Missing Certificate Pinning

**Problem**: Without certificate or public key pinning, a man-in-the-middle attacker with a rogue CA certificate can intercept all TLS traffic. Required for L2 apps.
**MASVS**: MASVS-NETWORK-2 | MASWE-0047

**Detection**: Search for `URLSession` usage where no class implements `urlSession(_:didReceive:completionHandler:)` with `SecTrustEvaluateWithError` or pinned certificate validation. For Alamofire, check for `ServerTrustManager`. For TrustKit, check for `kTSKEnforcePinning: true`.

```swift
// ❌ HIGH: URLSession without pinning delegate
let session = URLSession(configuration: .default)
let (data, _) = try await session.data(from: url)
```

```swift
// ✅ FIX: Public key pinning via URLSessionDelegate
class PinningDelegate: NSObject, URLSessionDelegate {
    let pinnedKeyHashes: Set<String> // Base64-encoded SHA-256 of SubjectPublicKeyInfo

    func urlSession(_ session: URLSession,
                    didReceive challenge: URLAuthenticationChallenge,
                    completionHandler: @escaping (URLSession.AuthChallengeDisposition, URLCredential?) -> Void) {
        guard challenge.protectionSpace.authenticationMethod == NSURLAuthenticationMethodServerTrust,
              let serverTrust = challenge.protectionSpace.serverTrust else {
            completionHandler(.cancelAuthenticationChallenge, nil)
            return
        }

        // Evaluate trust — capture error for diagnostics
        var trustError: CFError?
        guard SecTrustEvaluateWithError(serverTrust, &trustError) else {
            completionHandler(.cancelAuthenticationChallenge, nil)
            return
        }

        // Extract server certificate (iOS 15+ / fallback for iOS 14)
        let serverCert: SecCertificate?
        if #available(iOS 15, *) {
            serverCert = (SecTrustCopyCertificateChain(serverTrust) as? [SecCertificate])?.first
        } else {
            serverCert = SecTrustGetCertificateAtIndex(serverTrust, 0)
        }
        guard let serverCert else {
            completionHandler(.cancelAuthenticationChallenge, nil)
            return
        }

        let serverKeyHash = sha256OfPublicKey(serverCert)
        if pinnedKeyHashes.contains(serverKeyHash) {
            completionHandler(.useCredential, URLCredential(trust: serverTrust))
        } else {
            completionHandler(.cancelAuthenticationChallenge, nil)
        }
    }
}
```

**Context**: Only flag as HIGH for apps handling sensitive data (L2). For L1 apps, flag as informational.

---

## H2: Weak Keychain Accessibility Level

**Problem**: `kSecAttrAccessibleAlways` and `kSecAttrAccessibleAlwaysThisDeviceOnly` are deprecated since iOS 12. Data is accessible even when the device is locked.
**MASVS**: MASVS-STORAGE-1 | MASWE-0005

**Detection**: Search for `kSecAttrAccessibleAlways` or `kSecAttrAccessibleAlwaysThisDeviceOnly` in Keychain query dictionaries.

```swift
// ❌ HIGH: Deprecated — accessible when device is locked
let query: [String: Any] = [
    kSecClass as String: kSecClassGenericPassword,
    kSecAttrAccessible as String: kSecAttrAccessibleAlways  // DEPRECATED
]
```

```swift
// ✅ FIX: Use appropriate accessibility level
// For most sensitive data:
kSecAttrAccessibleWhenPasscodeSetThisDeviceOnly  // Most secure, deleted if passcode removed
// For general sensitive data:
kSecAttrAccessibleWhenUnlockedThisDeviceOnly     // Recommended default
// For background tasks needing credentials:
kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly // Available after first unlock
```

**Accessibility hierarchy** (most → least secure):
1. `kSecAttrAccessibleWhenPasscodeSetThisDeviceOnly`
2. `kSecAttrAccessibleWhenUnlockedThisDeviceOnly`
3. `kSecAttrAccessibleWhenUnlocked`
4. `kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly`
5. `kSecAttrAccessibleAfterFirstUnlock`
6. ~~`kSecAttrAccessibleAlways`~~ (deprecated)
7. ~~`kSecAttrAccessibleAlwaysThisDeviceOnly`~~ (deprecated)

---

## H3: Deprecated Cryptographic Algorithms

**Problem**: MD5, SHA-1, DES, 3DES, and RC4 have known weaknesses. MD5 and SHA-1 are vulnerable to collision attacks. DES has a 56-bit key (brute-forceable). RC4 has statistical biases.
**MASVS**: MASVS-CRYPTO-1 | MASWE-0020

**Detection**: Search for `CC_MD5(`, `CC_SHA1(`, `kCCAlgorithmDES`, `kCCAlgorithm3DES`, `kCCAlgorithmRC4`, `Insecure.MD5`, `Insecure.SHA1`.

```swift
// ❌ HIGH: Deprecated hash for security purpose
let hash = Insecure.MD5.hash(data: passwordData)
let sha1 = Insecure.SHA1.hash(data: tokenData)
```

```swift
// ✅ FIX: Use SHA-256 or stronger
let hash = SHA256.hash(data: passwordData)
// For password-based key derivation, use PBKDF2 via CommonCrypto
// (HKDF is NOT suitable for low-entropy passwords)
```

```objc
// ❌ HIGH: CommonCrypto deprecated algorithms
CC_MD5(data, (CC_LONG)length, digest);
CCCrypt(kCCEncrypt, kCCAlgorithmDES, kCCOptionPKCS7Padding, ...);
CCCrypt(kCCEncrypt, kCCAlgorithm3DES, kCCOptionPKCS7Padding, ...);
```

```objc
// ✅ FIX: Use AES-256 with GCM mode
CCCrypt(kCCEncrypt, kCCAlgorithmAES, kCCOptionPKCS7Padding,
    key, kCCKeySizeAES256, iv, plainData, dataLen, outData, outLen, &written);
```

**False positive**: MD5/SHA-1 for non-security checksums (file deduplication, cache keys) is acceptable — flag as informational.

---

## H4: ECB Mode Encryption

**Problem**: ECB mode encrypts each block independently — identical plaintext blocks produce identical ciphertext blocks, preserving patterns. The ECB penguin is the canonical demonstration.
**MASVS**: MASVS-CRYPTO-1 | MASWE-0020

**Detection**: Search for `kCCOptionECBMode` in `CCCrypt` calls.

```objc
// ❌ HIGH: ECB mode preserves plaintext patterns
CCCrypt(kCCEncrypt, kCCAlgorithmAES,
    kCCOptionPKCS7Padding | kCCOptionECBMode,
    key, kCCKeySizeAES256, NULL,
    plainData, dataLen, outData, outLen, &written);
```

```objc
// ✅ FIX: Use CBC with random IV, or prefer GCM via CryptoKit
uint8_t iv[kCCBlockSizeAES128];
SecRandomCopyBytes(kSecRandomDefault, sizeof(iv), iv);
CCCrypt(kCCEncrypt, kCCAlgorithmAES, kCCOptionPKCS7Padding,
    key, kCCKeySizeAES256, iv,
    plainData, dataLen, outData, outLen, &written);
```

**Note**: `kCCOptionECBMode` is always a finding — there is no legitimate use case for ECB mode on iOS.

---

## H5: Insecure Random Number Generation

**Problem**: `rand()`, `random()`, and `srand()` produce predictable sequences from a seedable PRNG. Using them for tokens, keys, nonces, or session IDs allows prediction attacks.
**MASVS**: MASVS-CRYPTO-1 | MASWE-0027

**Detection**: Search for `rand()`, `random()`, `srand()` in security-related contexts. Also flag `arc4random` when used explicitly for cryptographic key or nonce generation (though `arc4random` uses CSPRNG on Apple platforms).

```swift
// ❌ HIGH: Predictable PRNG for security token
let token = String(format: "%08x", random())
srand(UInt32(time(nil)))
let sessionId = rand()
```

```swift
// ✅ FIX: Cryptographically secure random
var bytes = [UInt8](repeating: 0, count: 32)
let status = SecRandomCopyBytes(kSecRandomDefault, bytes.count, &bytes)
guard status == errSecSuccess else { throw SecurityError.randomGenerationFailed }
let token = Data(bytes).base64EncodedString()
```

**Randomness hierarchy**:
1. `SecRandomCopyBytes` — gold standard for keys, IVs, tokens
2. `arc4random` / `arc4random_uniform` — CSPRNG on Apple platforms, acceptable for general use
3. ~~`rand()` / `random()` / `srand()`~~ — never for security

---

## H6: UIWebView Usage

**Problem**: UIWebView is deprecated since iOS 12 and causes App Store rejection since April 2020. It cannot disable JavaScript, doesn't properly enforce same-origin policy, and runs in-process (web exploits compromise the app directly).
**MASVS**: MASVS-PLATFORM-2 | MASWE-0082

**Detection**: Search for `UIWebView` in source code. Also check binary: `grep -r "UIWebView"` in the compiled app.

```swift
// ❌ HIGH: Deprecated, insecure WebView
let webView = UIWebView(frame: view.bounds)
webView.loadRequest(URLRequest(url: url))
```

```swift
// ✅ FIX: Use WKWebView with secure configuration
let config = WKWebViewConfiguration()
config.websiteDataStore = .nonPersistent()
if #available(iOS 14.0, *) {
    let prefs = WKWebpagePreferences()
    prefs.allowsContentJavaScript = false  // Disable JS unless required
    config.defaultWebpagePreferences = prefs
} else {
    config.preferences.javaScriptEnabled = false  // Deprecated in iOS 14, needed for iOS 13
}

let webView = WKWebView(frame: view.bounds, configuration: config)
```

---

## H7: PII in Log Statements

**Problem**: `NSLog`, `print`, `os_log`, and `debugPrint` persist to the system log, accessible via device console, sysdiagnose, or third-party log aggregation. Sensitive data in logs violates MASVS-STORAGE and privacy regulations.
**MASVS**: MASVS-STORAGE-2 | MASWE-0001

**Detection**: Search for `NSLog(`, `print(`, `os_log(`, `debugPrint(` containing variables with names suggesting sensitive data: password, token, ssn, creditCard, cardNumber, pin, secret, auth, session.

```swift
// ❌ HIGH: Auth token persists in system log
print("User token: \(authToken)")
NSLog("Login with password: %@", password)
os_log("Session: %{public}@", sessionId)
```

```swift
// ✅ FIX: Use os_log with private visibility, or remove entirely
os_log("Login attempted", log: .auth, type: .info)
// For debug-only logging:
#if DEBUG
print("Debug token: \(authToken)")
#endif
```

---

## H8: NSCoding Without Proper NSSecureCoding

**Problem**: Setting `supportsSecureCoding = true` but still using `decodeObject(forKey:)` without the type parameter provides false security. The unarchiver trusts any class that claims secure coding support.
**MASVS**: MASVS-CODE-4 | MASWE-0058

**Detection**: Search for classes implementing `NSSecureCoding` that use `decodeObject(forKey:` without an `ofClass:` or `of:` parameter.

```swift
// ❌ HIGH: False security — missing typed decode
class Profile: NSObject, NSSecureCoding {
    static var supportsSecureCoding: Bool { true }
    required init?(coder: NSCoder) {
        self.name = coder.decodeObject(forKey: "name") as? String ?? ""
    }
}
```

```swift
// ✅ FIX: Typed decoding enforces class verification
required init?(coder: NSCoder) {
    self.name = coder.decodeObject(of: NSString.self, forKey: "name") as String? ?? ""
}
```

---

## H9: Format String Vulnerabilities (Objective-C)

**Problem**: Passing user-controlled strings directly as format arguments to `NSLog`, `NSString stringWithFormat:`, or `NSAlert` allows format string attacks (`%x` leaks stack data, `%n` can write memory in some implementations).
**MASVS**: MASVS-CODE-4 | MASWE-0058

**Detection**: Search for `NSLog(variable)` where the variable is not a format string literal. Search for `[NSString stringWithFormat:variable]` without a literal format.

```objc
// ❌ HIGH: User input as format string — leaks stack data with %x%x%x
NSLog(userInput);
NSString *msg = [NSString stringWithFormat:userInput];
```

```objc
// ✅ FIX: Always use format specifier
NSLog(@"%@", userInput);
NSString *msg = [NSString stringWithFormat:@"%@", userInput];
```

<detection_checklist>
## HIGH Detection Checklist

- [ ] Check for `URLSession` usage without pinning delegate (L2 apps)
- [ ] Grep for `kSecAttrAccessibleAlways` and `kSecAttrAccessibleAlwaysThisDeviceOnly`
- [ ] Grep for `CC_MD5`, `CC_SHA1`, `kCCAlgorithmDES`, `kCCAlgorithm3DES`, `kCCAlgorithmRC4`, `Insecure.MD5`, `Insecure.SHA1`
- [ ] Grep for `kCCOptionECBMode`
- [ ] Grep for `rand()`, `random()`, `srand()` in security contexts
- [ ] Grep for `UIWebView`
- [ ] Grep for `NSLog`, `print`, `os_log` with sensitive variable names
- [ ] Check `NSSecureCoding` implementations for `decodeObject(forKey:` without type
- [ ] Check ObjC files for `NSLog(variable)` without format specifier
</detection_checklist>
