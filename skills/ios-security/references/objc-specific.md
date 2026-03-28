# Objective-C Runtime Attack Surface

## How to Use This Reference

Read this file when auditing codebases containing Objective-C files (`.m`, `.mm`, `.h` with ObjC syntax). Pure Swift types that do not inherit from `NSObject` are immune to these attacks. Mixed codebases require checking both Swift and ObjC attack surfaces per file.

## Why ObjC Has a Unique Attack Surface

Objective-C's dynamic dispatch via `objc_msgSend` enables runtime method replacement, property access bypassing visibility, and unsafe deserialization — none of which exist in pure Swift's static dispatch model.

---

## R1: Method Swizzling Vulnerability

**Problem**: Any Objective-C method can be replaced at runtime using `method_exchangeImplementations()`. On jailbroken devices, attackers swizzle security methods to bypass authentication, disable logging, or intercept data.

**Detection**: This is an architectural risk, not a code pattern to fix. Mitigations include:

1. Implement security-critical logic as C functions, not ObjC methods
2. Use Swift value types for security state (not swizzlable)
3. For L2/R apps: detect common swizzling frameworks (Cydia Substrate, libhooker)

```objc
// ❌ VULNERABLE: ObjC method — swizzlable at runtime
- (BOOL)isAuthenticated {
    return self.sessionToken != nil && ![self.sessionToken isEqualToString:@""];
}
```

```swift
// ✅ MITIGATION: Pure Swift — not dispatched via objc_msgSend
struct AuthState {
    private let token: String?
    var isAuthenticated: Bool { token?.isEmpty == false }
}
```

```c
// ✅ MITIGATION: C function — not in the ObjC method table
static BOOL _isAuthenticated(SecurityManager *mgr) {
    return mgr->_sessionToken != nil && mgr->_sessionToken.length > 0;
}
```

**Detection for swizzling in the codebase itself**: Search for `method_exchangeImplementations`, `class_replaceMethod`, `method_setImplementation`, `class_addMethod` — these may indicate either defensive swizzling (e.g., crash reporting) or potential misuse.

---

## R2: KVO/KVC Access Control Bypass

**Problem**: Key-Value Coding allows reading any property by name, bypassing access control. `[object valueForKey:@"_privateProperty"]` reads "private" ivars.

**Detection**: Search for `valueForKey:` and `setValue:forKey:` with string keys prefixed by underscore (accessing private ivars). Also check that security-critical classes override `+accessInstanceVariablesDirectly`.

```objc
// ❌ VULNERABILITY: KVC reads "private" security state
NSString *secret = [securityManager valueForKey:@"_internalSecret"];
BOOL auth = [[authManager valueForKey:@"_isLoggedIn"] boolValue];
```

```objc
// ✅ MITIGATION: Block direct ivar access via KVC
+ (BOOL)accessInstanceVariablesDirectly {
    return NO;  // KVC cannot access ivars directly
}

- (id)valueForUndefinedKey:(NSString *)key {
    return nil;  // Silently deny access to unknown keys
}
```

---

## R3: Insecure Deserialization (NSCoding vs NSSecureCoding)

**Problem**: `NSKeyedUnarchiver.unarchiveObject(withFile:)` deserializes without type verification. Crafted archives can instantiate arbitrary classes, triggering unexpected `initWithCoder:` implementations.

**Detection**: Search for `unarchiveObjectWithFile:`, `unarchiveObjectWithData:`, `unarchiveTopLevelObjectWithData:error:`. The secure replacement requires `NSSecureCoding` protocol adoption.

**The false-security trap**: Setting `supportsSecureCoding = YES` but still using `decodeObjectForKey:` (without class parameter) provides NO protection.

```objc
// ❌ CRITICAL: Insecure deserialization — no type verification
id obj = [NSKeyedUnarchiver unarchiveObjectWithFile:path];
```

```objc
// ❌ HIGH: False security — typed static property but untyped decode
+ (BOOL)supportsSecureCoding { return YES; }
- (instancetype)initWithCoder:(NSCoder *)coder {
    self = [super init];
    _name = [coder decodeObjectForKey:@"name"];  // NO CLASS CHECK
    return self;
}
```

```objc
// ✅ FIX: Secure deserialization with type enforcement
NSError *error;
UserProfile *profile = [NSKeyedUnarchiver unarchivedObjectOfClass:[UserProfile class]
                                                         fromData:data
                                                            error:&error];

// ✅ FIX: Typed decode in initWithCoder:
- (instancetype)initWithCoder:(NSCoder *)coder {
    self = [super init];
    _name = [coder decodeObjectOfClass:[NSString class] forKey:@"name"];
    return self;
}
```

---

## R4: Format String Vulnerabilities

**Problem**: Passing user-controlled input directly as a format string to `NSLog`, `[NSString stringWithFormat:]`, `[NSString initWithFormat:]`, or `[NSPredicate predicateWithFormat:]` enables format string attacks. `%x` reads stack memory, `%@` can crash the app with invalid object pointers.

**Detection**: Search for format functions where the first (format) argument is a variable, not a string literal.

```objc
// ❌ HIGH: User input controls format string
NSLog(userInput);                                    // Stack leak with %x%x%x
NSString *msg = [NSString stringWithFormat:userInput]; // Crash with %@
[NSString initWithFormat:userInput];
```

```objc
// ✅ FIX: Always use a format specifier
NSLog(@"%@", userInput);
NSString *msg = [NSString stringWithFormat:@"%@", userInput];
```

**NSPredicate injection** is a related but distinct issue:
```objc
// ❌ HIGH: Predicate format injection
NSPredicate *pred = [NSPredicate predicateWithFormat:
    [NSString stringWithFormat:@"name == '%@'", userInput]];
// Input: "' OR 1=1 OR name == '" bypasses filter

// ✅ FIX: Use argument substitution
NSPredicate *pred = [NSPredicate predicateWithFormat:@"name == %@", userInput];
```

---

## R5: Associated Objects Data Leakage

**Problem**: `objc_setAssociatedObject` attaches arbitrary data to any ObjC object at runtime. This can be used to shadow security-critical properties or leak data between components.

**Detection**: Search for `objc_setAssociatedObject` and `objc_getAssociatedObject`. Verify no security-sensitive data is stored via association (which lacks the protection of proper Keychain or encryption).

```objc
// ❌ MEDIUM: Sensitive data attached via associated object — no encryption, accessible to any code
objc_setAssociatedObject(user, &kTokenKey, authToken, OBJC_ASSOCIATION_RETAIN_NONATOMIC);
```

```objc
// ✅ FIX: Store sensitive data in Keychain, not as associated objects
[SAMKeychain setPassword:authToken forService:@"auth" account:user.identifier];
```

---

## R6: Category Method Override Collisions

**Problem**: When two categories define the same method, the winner is undefined at link time. A malicious or careless third-party SDK category can silently override security-critical methods.

**Detection**: Search for category methods that share names with base class methods or other category methods, particularly on security-relevant classes (e.g., `NSURLSession`, `NSData`, `NSString`).

```objc
// ❌ MEDIUM: Category overrides base class method — undefined behavior
@implementation NSData (SecurityUtils)
- (NSString *)base64EncodedStringWithOptions:(NSDataBase64EncodingOptions)options {
    // This silently replaces the system implementation
    return [self customEncode];
}
@end
```

```objc
// ✅ FIX: Use prefixed method names in categories
@implementation NSData (SecurityUtils)
- (NSString *)myapp_secureBase64EncodedString {
    return [self base64EncodedStringWithOptions:0];
}
@end
```

---

## ObjC Runtime Detection Summary

| Attack | API to Search | Severity | Swift Immune? |
|--------|--------------|----------|---------------|
| Method swizzling | `method_exchangeImplementations`, `class_replaceMethod` | Architectural | Yes (pure Swift) |
| KVC bypass | `valueForKey:` with `_`-prefixed keys | 🟡 HIGH | Yes (pure Swift) |
| Insecure deserialization | `unarchiveObjectWithFile:`, `unarchiveObjectWithData:` | 🔴 CRITICAL | N/A (API level) |
| Format string | `NSLog(var)`, `stringWithFormat:var` | 🟡 HIGH | Yes |
| Associated objects | `objc_setAssociatedObject` with sensitive data | 🟢 MEDIUM | N/A (runtime API) |
| Category collisions | Duplicate category method names | 🟢 MEDIUM | N/A (ObjC only) |

<detection_checklist>
## ObjC Runtime Detection Checklist

- [ ] Grep for `method_exchangeImplementations`, `class_replaceMethod`, `method_setImplementation`
- [ ] Grep for `valueForKey:@"_` (KVC access to private ivars)
- [ ] Check security-critical classes for `+accessInstanceVariablesDirectly` returning NO
- [ ] Grep for `unarchiveObjectWithFile:`, `unarchiveObjectWithData:`
- [ ] Grep for `NSLog(` followed by a variable (not `NSLog(@"`)
- [ ] Grep for `stringWithFormat:` where format arg is a variable
- [ ] Grep for `predicateWithFormat:` using string interpolation instead of `%@` substitution
- [ ] Grep for `objc_setAssociatedObject` with sensitive data
- [ ] Check for category methods overriding system methods (unprefixed names)
</detection_checklist>
