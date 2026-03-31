# Fixing Unsymbolicated Crash Reports in Sentry

When Sentry crash reports show raw hex addresses (e.g., `0x1003a4f8c`) instead of human-readable function names, file names, and line numbers, the issue is that Sentry does not have the **dSYM** (debug symbol) files needed to symbolicate the crash logs.

## What Are dSYMs?

dSYM (Debug Symbol) files are generated during the build process and contain the mapping between compiled machine code addresses and your original source code (function names, file names, line numbers). Without them, crash reports are essentially unreadable hex dumps.

## How to Fix It

### 1. Upload dSYMs to Sentry

The most reliable approach is to automate dSYM uploads as part of your build process.

**Option A: Using sentry-cli in a Build Phase**

Add a Run Script build phase in Xcode (after the "Compile Sources" phase):

```bash
if which sentry-cli >/dev/null 2>&1; then
    export SENTRY_ORG="your-org"
    export SENTRY_PROJECT="your-project"
    export SENTRY_AUTH_TOKEN="your-auth-token"
    ERROR=$(sentry-cli debug-files upload --include-sources "$DWARF_DSYM_FOLDER_PATH" 2>&1 >/dev/null)
    if [ ! $? -eq 0 ]; then
        echo "warning: sentry-cli - $ERROR"
    fi
else
    echo "warning: sentry-cli not installed, skipping dSYM upload"
fi
```

**Option B: Using the Sentry Fastlane Plugin**

```ruby
lane :upload_symbols do
  sentry_upload_dsym(
    org_slug: 'your-org',
    project_slug: 'your-project',
    auth_token: ENV['SENTRY_AUTH_TOKEN'],
    dsym_path: lane_context[SharedValues::DSYM_OUTPUT_PATH]
  )
end
```

**Option C: Using SPM Plugin (Sentry SDK 8.x+)**

If you use Swift Package Manager, the Sentry SDK includes a build tool plugin that can handle uploads automatically. Enable it in your target's build settings.

### 2. Ensure dSYMs Are Generated

Verify your Xcode build settings are correct:

- **Debug Information Format** (`DEBUG_INFORMATION_FORMAT`): Set to `dwarf-with-dsym` for your Release (and ideally Archive) configuration. The default for Debug is `dwarf` (no dSYM), which is fine for local development.
- **Strip Style**: Ensure symbols are not fully stripped before the dSYM is generated.

To check or change this:
1. Select your target in Xcode.
2. Go to **Build Settings**.
3. Search for "Debug Information Format".
4. Set the Release configuration to **DWARF with dSYM File**.

### 3. Handle Bitcode (Legacy, pre-Xcode 16)

If your project used Bitcode (deprecated since Xcode 14 and removed in Xcode 16), Apple would recompile your binary on their servers, generating new dSYMs that differ from your local ones. In that case, you needed to download the App Store-generated dSYMs:

- From **Xcode**: Window > Organizer > select your archive > "Download Debug Symbols"
- From **App Store Connect**: Go to your app > Activity > select the build > "Download dSYM"
- Via **fastlane**: `download_dsyms(app_identifier: "com.your.app")`

Then upload those downloaded dSYMs to Sentry.

### 4. Manually Upload Existing dSYMs

If you have existing unsymbolicated crashes, you can retroactively upload dSYMs:

```bash
# Find dSYMs from a specific archive
sentry-cli debug-files upload --include-sources ~/Library/Developer/Xcode/Archives/

# Or upload a specific dSYM file
sentry-cli debug-files upload --include-sources /path/to/YourApp.app.dSYM
```

### 5. Verify dSYM Upload

Check that Sentry has received and processed your dSYMs:

```bash
# List uploaded debug files
sentry-cli debug-files list

# Check if a specific dSYM UUID is present
sentry-cli debug-files check "YOUR-DSYM-UUID"
```

You can find the expected UUID from your binary:

```bash
dwarfdump --uuid /path/to/YourApp.app.dSYM
```

### 6. CI/CD Integration

For CI/CD pipelines (e.g., GitHub Actions, Bitrise, CircleCI), add the dSYM upload step after your archive/build step:

```bash
# Install sentry-cli
brew install getsentry/tools/sentry-cli

# Upload dSYMs from the build output
sentry-cli debug-files upload --include-sources "$BUILT_PRODUCTS_DIR"
```

## Common Pitfalls

- **Mismatched UUIDs**: The dSYM UUID must exactly match the binary UUID. Rebuilding without uploading new dSYMs will break symbolication.
- **Missing framework dSYMs**: If you use third-party frameworks, you also need their dSYMs. Most popular SDKs distribute them or upload to Sentry automatically.
- **Auth token permissions**: The Sentry auth token needs the `project:releases` and `org:read` scopes.
- **Build configuration mismatch**: Make sure `dwarf-with-dsym` is set on the configuration you actually ship (usually Release), not just Debug.

## Summary

The fix boils down to three things:
1. Make sure Xcode generates dSYM files (`DWARF with dSYM File` build setting).
2. Upload those dSYMs to Sentry (ideally automated via a build phase or CI step).
3. Ensure the uploaded dSYM UUIDs match the deployed binary.

Once dSYMs are properly uploaded, Sentry will retroactively symbolicate any existing crash reports that match those UUIDs, and all future crashes will show full function names, file paths, and line numbers.
