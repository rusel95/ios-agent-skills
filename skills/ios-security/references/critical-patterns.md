# Critical Detection Patterns & Fixes

## How to Use This Reference

Read this file at the start of every security audit. Each pattern here is high-confidence with low false-positive rates. Scan the entire codebase for these patterns before moving to contextual analysis. Every match is a finding unless explicitly justified.

## Severity

All patterns in this file are **🔴 CRITICAL** — directly exploitable vulnerabilities that must be flagged immediately.

<critical_anti_patterns>

## C1: Hardcoded Secrets and API Keys

**Problem**: String literals containing credentials are extractable from compiled binaries via the `strings` command. They persist in version control history even after removal.
**MASVS**: MASVS-STORAGE-1 | MASWE-0005, MASWE-0013

**Detection**: Search for string literals assigned to variables named `apiKey`, `secret`, `password`, `PRIVATE_KEY`, `client_secret`, `api_secret`, `accessToken`, `authToken`, `bearerToken`. Also search for `Bearer ` prefix in string literals.

```swift
// ❌ CRITICAL: Extractable from binary, visible in VCS history
let apiKey = "sk-proj-abc123def456"
let secret = "MyS3cretP@ssw0rd"
let headers = ["Authorization": "Bearer eyJhbGciOiJIUzI1NiIs..."]
```

```swift
// ✅ FIX: Load from Keychain or secure configuration
let apiKey = try KeychainManager.retrieve(key: "apiKey")

// Or from server-side configuration at runtime
let config = try await ConfigService.fetchSecureConfig()
```

```objc
// ❌ CRITICAL: Hardcoded in Objective-C
static NSString *const kAPISecret = @"sk-live-abc123";
#define API_KEY @"AIzaSyA..."
```

```objc
// ✅ FIX: Retrieve from Keychain
NSString *apiKey = [SAMKeychain passwordForService:@"MyApp" account:@"apiKey"];
```

---

## C2: Sensitive Data in UserDefaults

**Problem**: UserDefaults persists as plaintext `.plist` in `Library/Preferences/` — readable via device backups, forensic tools, or jailbroken device file system access.
**MASVS**: MASVS-STORAGE-1 | MASWE-0005

**Detection**: Search for `UserDefaults.standard.set(` or `[[NSUserDefaults standardUserDefaults] setObject:` where the key contains: password, token, secret, credential, sessionId, authToken, accessToken, refreshToken, pin, ssn, creditCard, cardNumber.

```swift
// ❌ CRITICAL: Auth token stored in plaintext plist
UserDefaults.standard.set(authToken, forKey: "userAuthToken")
UserDefaults.standard.set(password, forKey: "savedPassword")
UserDefaults.standard.set(sessionId, forKey: "currentSession")
```

```swift
// ✅ FIX: Store in Keychain with appropriate accessibility
let query: [String: Any] = [
    kSecClass as String: kSecClassGenericPassword,
    kSecAttrAccount as String: "authToken",
    kSecValueData as String: token.data(using: .utf8)!,
    kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlockedThisDeviceOnly
]
let status = SecItemAdd(query as CFDictionary, nil)
```

```objc
// ❌ CRITICAL: Objective-C equivalent
[[NSUserDefaults standardUserDefaults] setObject:authToken forKey:@"authToken"];
```

**False positive guidance**: `UserDefaults` for non-sensitive preferences (theme, onboarding state, feature flags) is safe. Only flag when key names suggest sensitive data.

---

## C3: Globally Disabled App Transport Security

**Problem**: `NSAllowsArbitraryLoads = true` disables ATS globally, allowing plaintext HTTP connections to any server. NowSecure found 80% of the 200 most popular free iOS apps opted out of ATS.
**MASVS**: MASVS-NETWORK-1 | MASWE-0050

**Detection**: Search Info.plist files for `NSAllowsArbitraryLoads` set to `true` or `YES`. Check both XML plist format and build-generated plists.

```xml
<!-- ❌ CRITICAL: All network traffic allowed over HTTP -->
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSAllowsArbitraryLoads</key>
    <true/>
</dict>
```

```xml
<!-- ✅ FIX: ATS enabled globally, exceptions only where justified -->
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSExceptionDomains</key>
    <dict>
        <key>legacy-api.example.com</key>
        <dict>
            <key>NSExceptionAllowsInsecureHTTPLoads</key>
            <true/>
            <key>NSExceptionMinimumTLSVersion</key>
            <string>TLSv1.2</string>
        </dict>
    </dict>
</dict>
```

**Note**: `NSAllowsArbitraryLoadsForMedia` and `NSAllowsArbitraryLoadsInWebContent` are separate ATS exemptions — flag as HIGH, not CRITICAL, since they have narrower scope.

---

## C4: Hardcoded Cryptographic Keys

**Problem**: Encryption keys embedded in source code provide no security — they are extractable from the binary. The key is effectively public.
**MASVS**: MASVS-CRYPTO-2 | MASWE-0013

**Detection**: Search for byte array literals (`[UInt8]`, `Data(bytes:)`) or string-to-data conversions used as key parameters in `CCCrypt`, `AES.GCM.seal`, `SymmetricKey(data:)`, or similar encryption calls.

```swift
// ❌ CRITICAL: Key embedded in source code
let key = "MySecretKey12345".data(using: .utf8)!
let symmetricKey = SymmetricKey(data: key)

// ❌ CRITICAL: Byte array key
let keyBytes: [UInt8] = [0x2b, 0x7e, 0x15, 0x16, 0x28, 0xae, 0xd2, 0xa6,
                          0xab, 0xf7, 0x15, 0x88, 0x09, 0xcf, 0x4f, 0x3c]
```

```swift
// ✅ FIX: Use Secure Enclave for key storage (preferred)
let privateKey = try SecureEnclave.P256.Signing.PrivateKey()

// Or derive key from high-entropy material using HKDF
let symmetricKey = HKDF<SHA256>.deriveKey(
    inputKeyMaterial: SymmetricKey(data: highEntropySecret),
    salt: salt,
    outputByteCount: 32
)
// Note: For user passwords, use PBKDF2 via CommonCrypto (see ObjC fix below),
// NOT HKDF — HKDF is designed for high-entropy input, not passwords.
```

```objc
// ❌ CRITICAL: Password used directly as key
char keyPtr[kCCKeySizeAES128];
[password getCString:keyPtr maxLength:sizeof(keyPtr) encoding:NSUTF8StringEncoding];
```

```objc
// ✅ FIX: Use PBKDF2 key derivation
CCKeyDerivationPBKDF(kCCPBKDF2, password.UTF8String, password.length,
    salt, saltLen, kCCPRFHmacAlgSHA256, 100000,
    derivedKey, kCCKeySizeAES256);
```

---

## C5: Insecure Deserialization (NSKeyedUnarchiver)

**Problem**: `NSKeyedUnarchiver.unarchiveObject(withFile:)` and `unarchiveObject(with:)` perform deserialization without type verification — vulnerable to object substitution attacks where crafted archives instantiate unexpected classes.
**MASVS**: MASVS-CODE-4 | MASWE-0058

**Detection**: Search for `unarchiveObject(withFile:`, `unarchiveObject(with:`, `unarchiveTopLevelObjectWithData:`. Also detect the false-security pattern: `supportsSecureCoding = true` combined with `decodeObject(forKey:` (without type parameter).

```swift
// ❌ CRITICAL: No type verification during deserialization
let data = try Data(contentsOf: archiveURL)
let object = NSKeyedUnarchiver.unarchiveObject(with: data)

// ❌ CRITICAL: False security — supportsSecureCoding set but decodeObject lacks type
class UserProfile: NSObject, NSSecureCoding {
    static var supportsSecureCoding: Bool { true }
    required init?(coder: NSCoder) {
        self.name = coder.decodeObject(forKey: "name") as? String ?? ""
        // BAD: decodeObject(forKey:) without ofClass: parameter
    }
}
```

```swift
// ✅ FIX: Secure deserialization with type verification
let object = try NSKeyedUnarchiver.unarchivedObject(
    ofClass: UserProfile.self,
    from: data
)

// ✅ FIX: Use typed decode in NSSecureCoding
required init?(coder: NSCoder) {
    self.name = coder.decodeObject(of: NSString.self, forKey: "name") as String? ?? ""
}
```

```objc
// ❌ CRITICAL: Insecure unarchiving
id obj = [NSKeyedUnarchiver unarchiveObjectWithFile:path];

// ✅ FIX: Secure unarchiving with class verification
NSError *error;
UserProfile *profile = [NSKeyedUnarchiver unarchivedObjectOfClass:[UserProfile class]
                                                         fromData:data
                                                            error:&error];
```

---

## C6: Hardcoded or Zero Initialization Vectors

**Problem**: Using zero-filled or hardcoded IVs/nonces eliminates the randomization that makes each encryption unique. Identical plaintext produces identical ciphertext, enabling pattern analysis.
**MASVS**: MASVS-CRYPTO-1 | MASWE-0022

**Detection**: Search for `Data(repeating: 0, count:` near encryption calls, string literals converted to data and used as IV parameters, or `nil` passed as the IV argument to `CCCrypt`.

```swift
// ❌ CRITICAL: Zero IV — identical plaintext produces identical ciphertext
let iv = Data(repeating: 0, count: 16)
let sealedBox = try AES.GCM.seal(plaintext, using: key, nonce: AES.GCM.Nonce(data: iv))

// ❌ CRITICAL: Hardcoded IV string
let iv = "1234567890123456".data(using: .utf8)!
```

```swift
// ✅ FIX: Let CryptoKit generate a random nonce (default behavior)
let sealedBox = try AES.GCM.seal(plaintext, using: key)
// nonce is automatically generated and included in sealedBox.combined

// Or generate explicitly
let nonce = AES.GCM.Nonce()
let sealedBox = try AES.GCM.seal(plaintext, using: key, nonce: nonce)
```

```objc
// ❌ CRITICAL: nil IV with non-ECB mode
CCCrypt(kCCEncrypt, kCCAlgorithmAES, kCCOptionPKCS7Padding,
    keyData, kCCKeySizeAES256, NULL, /* nil IV */
    plainData, dataLength, outData, outLength, &bytesWritten);
```

```objc
// ✅ FIX: Generate random IV
uint8_t iv[kCCBlockSizeAES128];
SecRandomCopyBytes(kSecRandomDefault, sizeof(iv), iv);
CCCrypt(kCCEncrypt, kCCAlgorithmAES, kCCOptionPKCS7Padding,
    keyData, kCCKeySizeAES256, iv,
    plainData, dataLength, outData, outLength, &bytesWritten);
// Prepend IV to ciphertext for decryption
```

</critical_anti_patterns>

<detection_checklist>
## CRITICAL Detection Checklist

- [ ] Grep for string literals assigned to vars named `apiKey`, `secret`, `password`, `PRIVATE_KEY`, `client_secret`, `Bearer `
- [ ] Grep for `UserDefaults.standard.set` and `NSUserDefaults.*setObject` — check key names for sensitive data indicators
- [ ] Check all Info.plist files for `NSAllowsArbitraryLoads` = `true`
- [ ] Grep for byte arrays or string-to-data conversions near `CCCrypt`, `SymmetricKey`, `AES.GCM`
- [ ] Grep for `unarchiveObject(withFile:`, `unarchiveObject(with:`, `unarchiveTopLevelObjectWithData:`
- [ ] Grep for `decodeObject(forKey:` without `ofClass:` parameter (false NSSecureCoding)
- [ ] Grep for `Data(repeating: 0, count:` near encryption contexts
- [ ] Grep for `nil` or `NULL` IV parameters in `CCCrypt` calls
</detection_checklist>
