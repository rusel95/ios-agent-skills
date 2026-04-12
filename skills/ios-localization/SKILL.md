---
name: ios-localization
description: "Production-grade iOS localization skill covering String Catalogs (.xcstrings), CLDR pluralization, SwiftUI/UIKit localization APIs, RTL layout, date/number/currency formatting, and enterprise patterns (modular apps, white-label, accessibility localization). This skill should be used when creating or editing localized iOS strings, working with .xcstrings or .strings files, implementing pluralization, formatting dates/numbers/currencies for display, building RTL-compatible layouts, localizing accessibility labels, setting up localization in Swift Packages, or reviewing code for localization correctness. Use this skill any time someone is working with iOS localization, i18n, l10n, String Catalogs, plural rules, RTL, date formatting, or translated strings — even if they only say 'add a string' or 'format this date' or 'make this work in Arabic.' Also audit any newly generated user-facing iOS code for localization failures before finalizing — AI coding assistants systematically produce broken localization (hardcoded strings, missing plural categories, wrong date formats, left/right instead of leading/trailing) and this skill corrects those patterns. For .xcstrings files that are too large for direct editing, use the bundled Python scripts in scripts/ to validate, add entries, audit completeness, and fix plural categories programmatically."
metadata:
  version: 1.0.2
---

# iOS Localization

Production-grade localization skill for iOS codebases. AI coding assistants systematically produce broken localization code across 30+ identifiable patterns — from missing Slavic plural categories to hardcoded left/right constraints that shatter RTL layouts. This skill intercepts those patterns and enforces correct localization from the start.

Covers String Catalogs (.xcstrings), CLDR pluralization, SwiftUI/UIKit APIs, date/number/currency formatting, RTL layout, accessibility localization, and enterprise patterns (modular apps, white-label, Swift Packages).

## Why This Skill Exists

AI assistants generate localization code trained predominantly on English-only codebases. The result: only `one`/`other` plurals (breaking Russian, Ukrainian, Polish, Arabic), hardcoded English strings, `String(format:)` without positional specifiers, `dateFormat` strings that break in non-Gregorian calendars, and left/right constraints that break for 400M+ Arabic/Hebrew users. These bugs are silent in English testing and only surface in production.

## Quick Decision Trees

### Which localization API to use?

```
Is the project SwiftUI or UIKit?
├── SwiftUI → String literals in Text/Button/Toggle auto-localize
│   ├── Need to prevent localization? → Text(verbatim: "v2.0")
│   ├── Dynamic key from variable? → Text(LocalizedStringKey(key))
│   ├── In a Swift Package? → Text("key", bundle: .module)
│   └── Passing localized content across APIs? → Use LocalizedStringResource
└── UIKit → Use String(localized:) for iOS 15+, NSLocalizedString for older
    ├── In a Swift Package? → String(localized: "key", bundle: .module)
    └── Passing to another module? → Use LocalizedStringResource
```

### Which string file format?

```
Is the project using Xcode 15+ and targeting iOS 16+?
├── YES → Use String Catalogs (.xcstrings)
│   ├── Need pluralization without visible number? → .stringsdict (exception)
│   └── .xcstrings too large for direct editing? → Use scripts/xcstrings_tool.py
└── NO → Use .strings + .stringsdict
    └── Migrating? → Xcode can convert: right-click .strings → Migrate to String Catalog
```

### How many plural categories does this language need?

```
Language family?
├── English, Spanish, Portuguese, Italian, French, German → one + other (2)
├── Russian, Ukrainian → one + few + many + other (4)
├── Polish → one + few + many + other (4, BUT different rules from Russian!)
├── Arabic → zero + one + two + few + many + other (6)
├── Japanese, Chinese, Korean, Turkish, Thai → other only (1)
└── Unsure → Check CLDR at unicode.org/cldr/charts/latest/supplemental/language_plural_rules.html
```

### Date formatting: parsing or displaying?

```
Is this date from a server/API (parsing)?
├── YES → Fixed format with en_US_POSIX locale. NEVER user-facing styles
│   └── DateFormatter + locale = Locale(identifier: "en_US_POSIX") + dateFormat
└── NO → Displaying to user?
    ├── YES → NEVER use custom dateFormat strings
    │   ├── iOS 15+ → Date.formatted(.dateTime.month().day().year())
    │   ├── Older → DateFormatter with .dateStyle/.timeStyle
    │   └── Custom pattern needed → setLocalizedDateFormatFromTemplate()
    └── NO → Internal logic → Use Date components, not formatted strings
```

### What severity level applies?

```
Does the issue produce wrong output for non-English users?
├── YES → Is it silently wrong (no crash, just wrong text/layout)?
│   ├── YES → 🔴 CRITICAL (missing plurals, wrong date format, concatenated strings)
│   └── NO → 🟡 HIGH (crash on nil forced unwrap from missing key)
└── NO → Does it create localization debt (harder to translate later)?
    ├── YES → 🟡 HIGH (hardcoded strings, missing comments, String not LocalizedStringKey)
    └── NO → 🟢 MEDIUM (non-optimal API, missing verbatim:)
```

## Severity Definitions

- **🔴 CRITICAL** — Wrong output for non-English users. Missing plural categories for Slavic/Arabic languages, concatenated string fragments, hardcoded left/right constraints, `dateFormat` for user-facing dates, currency interpolation without formatter.
- **🟡 HIGH** — Localization debt or broken extraction. Hardcoded user-facing strings, missing translator comments, `String` parameter where `LocalizedStringKey` needed, missing `bundle: .module` in packages, `NSLocalizedString` with interpolation.
- **🟢 MEDIUM** — Non-optimal patterns. Using `NSLocalizedString` on iOS 15+ (should be `String(localized:)`), missing `verbatim:` on non-localizable text, same key for different contexts.

## Core AI Failure Patterns

> For all 30 patterns with code pairs, read `references/ai-failure-patterns.md`

| # | AI Failure | Severity |
|---|-----------|----------|
| F1 | Hardcoded user-facing strings without localization | 🟡 |
| F2 | English text as localization key (ambiguous) | 🟡 |
| F3 | Empty translator comments | 🟡 |
| F4 | Concatenated string fragments instead of format strings | 🔴 |
| F5 | Non-positional format specifiers (%@ not %1$@) | 🔴 |
| F6 | Only one/other plural categories (breaks Slavic/Arabic) | 🔴 |
| F7 | `count == 1 ? singular : plural` instead of stringsdict | 🔴 |
| F8 | Polish plural rules copied from Russian | 🔴 |
| F9 | String variable passed to Text() (skips localization) | 🟡 |
| F10 | Missing `verbatim:` on non-localizable strings | 🟢 |
| F11 | Missing `bundle: .module` in Swift Packages | 🟡 |
| F12 | `NSLocalizedString` with string interpolation | 🟡 |
| F13 | Custom `dateFormat` for user-facing dates | 🔴 |
| F14 | Missing `en_US_POSIX` locale for API date parsing | 🔴 |
| F15 | `YYYY` instead of `yyyy` in date format | 🔴 |
| F16 | Currency interpolation without NumberFormatter | 🔴 |
| F17 | Left/right constraints instead of leading/trailing | 🔴 |
| F18 | `.left` text alignment instead of `.natural` | 🔴 |
| F19 | Fixed-width containers on localized text | 🟡 |
| F20 | Hardcoded English accessibility labels | 🟡 |

## .xcstrings File Handling

String Catalog files are large single-JSON files (often 10K+ lines). AI assistants cannot reliably edit them directly. Use the bundled scripts:

```bash
# Validate .xcstrings for missing plurals, empty translations, stale entries
python3 scripts/xcstrings_tool.py validate path/to/Localizable.xcstrings

# Add a new key with comment
python3 scripts/xcstrings_tool.py add-key path/to/Localizable.xcstrings \
  --key "greeting_format" \
  --comment "Greeting with user name, e.g. 'Hello, Maria!'" \
  --value "Hello, %@!"

# Audit plural completeness for a specific language
python3 scripts/xcstrings_tool.py audit-plurals path/to/Localizable.xcstrings --lang ru

# Export translation status report
python3 scripts/xcstrings_tool.py status path/to/Localizable.xcstrings
```

**Fallback if scripts fail:** Read the .xcstrings as JSON, find the key under `strings.<key>.localizations.<lang>`, and edit the `stringUnit.value` field. Always validate JSON after editing. Never attempt to rewrite the entire file — make surgical edits to specific keys only.

## Workflows

### Workflow: Localize a New Screen

**When:** Creating a new SwiftUI or UIKit screen with user-facing text.

1. Read `references/ai-failure-patterns.md` — internalize patterns to avoid
2. Use `LocalizedStringKey` for all user-facing text in SwiftUI
3. Use `Text(verbatim:)` for non-localizable content (versions, URLs, identifiers)
4. Add meaningful translator comments to every string
5. Use positional format specifiers (%1$@, %2$@) in all format strings
6. For any counted content, use String Catalog plural variations (not conditionals)
7. Check CLDR plural requirements for all supported languages → `references/pluralization.md`
8. Use leading/trailing constraints, `.natural` text alignment
9. Use `Date.formatted()` or `.dateStyle/.timeStyle` for displayed dates
10. Localize all accessibility labels and hints
11. Run confidence checks before finalizing

### Workflow: Review Existing Code for Localization

**When:** User asks "review localization", "check i18n", or any variant.

1. Search for hardcoded user-facing strings (missing localization wrappers)
2. Search for `String(format:` without positional specifiers
3. Search for `count == 1 ?` or `count > 1 ?` — should use stringsdict
4. Search for `.left`/`.right` in constraints and text alignment
5. Search for `dateFormat =` on user-facing DateFormatters (missing en_US_POSIX check)
6. Search for `"\(price)"` or string-interpolated currency values
7. Check .xcstrings plural completeness: `python3 scripts/xcstrings_tool.py audit-plurals`
8. Verify Swift Packages pass `bundle: .module`
9. Verify accessibility labels are localized
10. Report findings using the finding template

### Workflow: Fix .xcstrings Plural Categories

**When:** Adding a new language or auditing plural completeness.

1. Run `python3 scripts/xcstrings_tool.py audit-plurals path/to/file.xcstrings --lang <code>`
2. Read `references/pluralization.md` for the language's required categories
3. For each key with plural variations, verify all required categories are present
4. Use the script to add missing categories or edit manually in Xcode's String Catalog editor
5. Test with verification set: `[0, 1, 2, 3, 4, 5, 10, 11, 12, 14, 20, 21, 22, 25, 100, 101, 111, 1.5]`

### Workflow: Format Dates/Numbers Correctly

**When:** User is displaying or parsing dates, numbers, or currencies.

1. Read `references/formatting.md` for the specific formatting rules
2. Determine if parsing (API) or displaying (user-facing)
3. For API parsing: fixed format + `en_US_POSIX` locale
4. For display: never custom `dateFormat` — use system styles
5. For currencies: always `NumberFormatter` or `.formatted(.currency(code:))`
6. Test with non-Gregorian calendars and Arabic locale

## Finding Report Template

```
### [SEVERITY] [Short title]

**File:** `path/to/file.swift:42`
**Rule:** [Rule number from the 30 rules]
**Issue:** [1-2 sentence description]
**Impact:** [Which languages/locales are affected]
**Fix:**
```swift
// ❌ Current
[broken code]

// ✅ Corrected
[localized replacement]
```
```

<critical_rules>
## Code Generation Rules

Whether generating new code or reviewing existing code, ALWAYS enforce these rules:

1. NEVER hardcode user-facing strings. Every visible string needs `String(localized:)` (UIKit) or auto-localization via `Text()` literal (SwiftUI).
2. NEVER use English text as localization keys. Use semantic dot-notation keys: `"settings.account.delete"` not `"Delete Account"`.
3. ALWAYS provide meaningful translator comments. Include UI context, variable descriptions, and example values. Never `comment: ""`.
4. NEVER concatenate localized string fragments. `"Hello, " + name` prevents word reordering. Use a single format string with placeholders.
5. ALWAYS use positional format specifiers. `"%1$@ invited %2$@"` not `"%@ invited %@"` — translators need to reorder arguments.
6. Implement ALL CLDR-required plural categories. Russian/Ukrainian need `one/few/many/other`. Polish needs the same but with different rules. Arabic needs all six. Check CLDR for every supported language.
7. NEVER use `count == 1 ? singular : plural`. This breaks every language with more than two plural forms. Always use `.stringsdict` or String Catalog plural variations.
8. Use `Text(verbatim:)` for non-localizable strings. Version numbers, URLs, identifiers, debug text, format codes — none of these should enter String Catalogs.
9. In Swift Packages, ALWAYS pass `bundle: .module` to `Text()`, `String(localized:)`, and `NSLocalizedString`.
10. For API date parsing, ALWAYS set `locale = Locale(identifier: "en_US_POSIX")`. Without it, Buddhist calendar users get year 2568, 12-hour time users break HH:mm.
11. NEVER use custom `dateFormat` for user-facing dates. Use `.dateStyle/.timeStyle`, `setLocalizedDateFormatFromTemplate()`, or `Date.formatted()`.
12. Use `yyyy` not `YYYY`, `dd` not `DD` in date format strings. `YYYY` = week-of-year year (wrong near Jan 1). `DD` = day of year (1-366).
13. NEVER interpolate currency values. Use `NumberFormatter` with `.currency` style or `.formatted(.currency(code:))`.
14. ALWAYS use leading/trailing constraints, NEVER left/right. Left/right never flip for RTL languages.
15. Set text alignment to `.natural`, never `.left`. `.natural` auto-adapts to RTL.
16. Localize ALL accessibility labels and hints. `accessibilityLabel("Close")` in English is broken for every other language. Use `String(localized:)` or localized `Text()`.
17. For .xcstrings files too large for direct editing, use `scripts/xcstrings_tool.py` to validate, add entries, and audit programmatically.
18. **Test with the canonical CLDR plural set** — when writing plural tests, use exactly these values: `[0, 1, 2, 3, 4, 5, 10, 11, 12, 14, 20, 21, 22, 25, 100, 101, 111, 1.5]`. This set hits every boundary where Russian/Polish/Arabic categories change (e.g., Russian flips one→few at 2, few→many at 5, then repeats at 11; Polish has different rules at 22; the `1.5` catches fraction plurals). Do NOT improvise the set.
19. **Use one canonical translator comment per key.** Xcode randomizes comment order in `.xcstrings` when the same key is extracted from multiple source locations with different comments — this creates noisy diffs on every build. Fix by extracting the call site to a single helper function or literal, or by overriding the comment in one canonical place.
20. **.strings and .xcstrings CANNOT coexist with the same table name.** When migrating to String Catalogs, either fully migrate (delete the old `.strings` file) or use a different table name. Mixing results in undefined load-order behavior.
21. **`.stringsdict` is still required for hidden-count plurals.** Cases where the plural category depends on a count that is NOT displayed in the UI (e.g., "You have messages" where the count is implicit) cannot be modeled in `.xcstrings` plural variations — use a separate `.stringsdict` file for those specific keys.
22. **For UIKit `NSLocalizedString` with interpolation, ALWAYS use positional specifiers.** `String(format: NSLocalizedString("greeting", comment: ""), name)` requires `%1$@` in the translation, not `%@`. This is the #1 UIKit localization regression — translators CANNOT reorder `%@` placeholders.
23. **Image assets: separate directional from non-directional.** Logos, photos, avatars, and brand marks must NEVER mirror in RTL — they keep their natural orientation. Only directional icons (arrows, back-buttons, chevrons) should flip. Mark directional assets with `imageFlippedForRightToLeftLayoutDirection()` (UIKit) or `flipsForRightToLeftLayoutDirection(true)` (SwiftUI).
24. **SwiftUI String interpolation trap.** `Text("Hello, \(name)")` infers `DefaultStringInterpolation` and produces a non-localized `String`, not a `LocalizedStringKey`. To force localization, use `Text("greeting_\(name)", tableName: nil)` with a key that's extracted, or `Text(String(localized: "greeting_\(name)"))`. Simply interpolating into `Text(...)` loses localization.
25. **Package localization fallback trap.** A missing `bundle: .module` bug appears to work in English because the key matches the fallback value OR because only `Bundle.main` is populated with translations. Always verify by running the app in a non-English language — English-only testing hides this bug completely.
26. **White-label apps: keep semantic keys stable across brands.** Each brand's runtime bundle override should replace only the translated values, never the keys themselves — renaming keys per brand breaks every shared translation and doubles QA cost.
27. **Validate VoiceOver in non-English locales.** Localized accessibility labels are only half the battle — pronunciation, number/percent formatting, and date announcements differ per locale. A value like `0.75` must read as "soixante-quinze pour cent" in French, which requires passing the value to `.formatted(.percent)` not `"\(value * 100)%"`.
</critical_rules>

## String Catalog Enterprise Patterns

**Split catalogs by feature or module** to reduce merge pressure on large teams: `Settings.xcstrings`, `Checkout.xcstrings`, `Auth.xcstrings` instead of one monolithic `Localizable.xcstrings`. Cross-feature duplication is cheap (bytes) — the merge-conflict savings are large.

**Hand-sorting `.xcstrings` JSON as a primary fix is wrong.** Xcode rewrites the file on every build, so sort ordering is not a durable fix. The real fix is one canonical comment per key (rule 19 above) and catalog splitting.

## Testing & QA Tooling

Add these to your localization QA pipeline:

- **`-NSShowNonLocalizedStrings YES`** launch argument — logs every hardcoded (non-localized) string the app displays at runtime. Run the app for 5 minutes with this flag; inspect the console. Every logged string is a missing localization.
- **Xcode Right-to-Left pseudolanguage** — Scheme → Run → Options → Application Language → "Right-to-Left Pseudolanguage". Validates that all `.leading`/`.trailing` constraints flip correctly AND that text mirrors, without needing to add Arabic translations first.
- **Double Length pseudolanguage** — same menu, appends padding to every string. Catches fixed-width containers that truncate in German/Finnish before you ship.
- **CI jobs for RTL and Double Length UI tests** — run the app under both pseudolanguages in CI and capture screenshots for visual diff. This is the only way to catch layout regressions automatically.

<fallback_strategies>
## Fallback Strategies & Loop Breakers

**If .xcstrings file is too large to read/edit directly:**
Use `scripts/xcstrings_tool.py` for programmatic operations. If the script fails, read the file as JSON, navigate to the specific key path (`strings.<key>.localizations.<lang>.stringUnit.value`), make a surgical edit, and validate JSON after. Never attempt to rewrite the full file.

**If unsure which CLDR plural categories a language needs:**
Check `references/pluralization.md` for common languages. For others, query unicode.org/cldr/charts/latest/supplemental/language_plural_rules.html. When in doubt, include all six categories — extra categories are harmless, missing ones produce wrong output.

**If String Catalog extraction misses a key:**
Verify the string is a literal in a localization-aware API (`Text()`, `String(localized:)`, `NSLocalizedString`). Variables passed as `String` type won't be extracted. Wrap in `LocalizedStringKey(variable)` or `String(localized: .init(stringLiteral: variable))`.

**If merge conflicts in .xcstrings:**
Both sides likely added different keys to the same JSON object. Resolution: accept either side, then manually re-add the other side's keys. Or split strings across multiple catalogs to reduce conflict frequency.

**If date parsing fails silently in testing but works locally:**
Check if the test device/simulator uses a non-Gregorian calendar or 12-hour time. Set `locale = Locale(identifier: "en_US_POSIX")` on the DateFormatter used for parsing.
</fallback_strategies>

## Confidence Checks

Before finalizing generated or reviewed code, verify ALL:

```
[ ] No hardcoded user-facing strings — all use localization APIs
[ ] Localization keys are semantic (dot-notation), not English text
[ ] Every localized string has a meaningful translator comment
[ ] No string concatenation — all use format strings with placeholders
[ ] All format specifiers are positional (%1$@, %2$@)
[ ] Plural forms cover all CLDR-required categories for each supported language
[ ] No count == 1 ternaries — all use stringsdict or String Catalog plurals
[ ] Non-localizable strings use Text(verbatim:) in SwiftUI
[ ] Swift Package strings pass bundle: .module
[ ] API date parsing uses en_US_POSIX locale
[ ] User-facing dates use system styles (not custom dateFormat)
[ ] Date formats use yyyy (not YYYY) and dd (not DD)
[ ] Currency values use NumberFormatter or .formatted(.currency(code:))
[ ] All constraints use leading/trailing (not left/right)
[ ] Text alignment uses .natural (not .left)
[ ] All accessibility labels and hints are localized
[ ] .xcstrings validated with scripts/xcstrings_tool.py
```

## Companion Skills

| Finding type | Companion skill | Apply when |
|---|---|---|
| Accessibility labels need localization | `skills/ios/epam-ios-accessibility/SKILL.md` | VoiceOver labels and hints must be localized |
| SwiftUI architecture for localized ViewModels | `skills/ios/epam-swiftui-mvvm-architecture/SKILL.md` | Managing localized state in ViewModels |
| Testing localization | `skills/ios/epam-ios-testing/SKILL.md` | XCTest with pseudolanguages, locale-specific tests |
| Security of localized content | `skills/ios/epam-ios-security-audit/SKILL.md` | Format string vulnerabilities in localized strings |

## References

| Reference | When to Read |
|-----------|-------------|
| `references/rules.md` | Do's and Don'ts quick reference: all 30 rules ranked by severity |
| `references/ai-failure-patterns.md` | Every code generation/review — all failure patterns with ❌/✅ code pairs |
| `references/string-catalogs.md` | Working with .xcstrings — format, pitfalls, migration, Xcode 26 features |
| `references/pluralization.md` | Plural rules — CLDR categories per language, Russian vs Polish differences, test sets |
| `references/swiftui-localization.md` | SwiftUI-specific — LocalizedStringKey, verbatim, interpolation, packages |
| `references/formatting.md` | Date, number, currency formatting — parsing vs display, locale traps |
| `references/rtl-layout.md` | RTL layout — leading/trailing, semantic content attribute, exceptions |
| `references/enterprise-patterns.md` | Modular apps, white-label, accessibility localization, bundle management |
| `references/testing.md` | Testing — pseudolanguages, NSShowNonLocalizedStrings, automated checks |
