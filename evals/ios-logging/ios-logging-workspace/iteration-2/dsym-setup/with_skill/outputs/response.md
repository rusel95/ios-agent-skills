# Fixing Unsymbolicated Crash Reports in Sentry (Hex Addresses Instead of Function Names)

The problem is that your dSYM files are not reaching Sentry. dSYM files contain the debug symbol mapping between memory addresses (like `0x1003a4f8c`) and human-readable function names, file names, and line numbers. Without them, Sentry cannot symbolicate crash reports. Here is the complete fix.

## Step 1: Enable dSYM Generation in Xcode Build Settings

By default, some build configurations (especially Release) may use plain DWARF without generating a dSYM bundle. You must change this for every target that produces executable code.

1. In Xcode, select your **project** (not a target) in the navigator.
2. Go to **Build Settings** and search for `Debug Information Format`.
3. Set the value to **"DWARF with dSYM File"** for **all configurations** (Debug and Release).
4. Repeat for **every target**: the main app, any app extensions (widgets, notification service extensions, share extensions), watch apps, and embedded frameworks.

The build setting key is `DEBUG_INFORMATION_FORMAT` and the value must be `dwarf-with-dsym`.

If you have extensions or widgets, each one is a separate binary with its own dSYM. Missing any target means that crashes originating in that target will remain unsymbolicated.

## Step 2: Add the Sentry dSYM Upload Script to Build Phases

Sentry provides a build phase script that automatically finds and uploads dSYM files after each build.

1. Select your **main app target** in Xcode.
2. Go to **Build Phases**.
3. Click **+** and choose **New Run Script Phase**.
4. Name it something like "Upload dSYMs to Sentry".
5. Place it **after** the "Compile Sources" and "Link Binary" phases.
6. Set the script contents. If you installed Sentry via SPM:

```bash
# Sentry CLI dSYM upload script
if which sentry-cli >/dev/null 2>&1; then
    export SENTRY_ORG="your-org-slug"
    export SENTRY_PROJECT="your-project-slug"
    export SENTRY_AUTH_TOKEN="your-auth-token"
    ERROR=$(sentry-cli upload-dif "$DWARF_DSYM_FOLDER_PATH" 2>&1 >/dev/null)
    if [ ! $? -eq 0 ]; then
        echo "warning: sentry-cli upload-dif failed: $ERROR"
    fi
else
    echo "warning: sentry-cli not installed, skipping dSYM upload"
fi
```

If you installed Sentry via CocoaPods, the upload script path is typically:
```bash
"${PODS_ROOT}/Sentry/Scripts/sentry-upload-dsyms.sh"
```

7. **Repeat for each extension target** that has its own build phases. Each extension produces its own dSYM that must be uploaded separately.

## Step 3: Install sentry-cli (If Not Already Present)

```bash
brew install getsentry/tools/sentry-cli
```

Or via npm:
```bash
npm install -g @sentry/cli
```

Authenticate it:
```bash
sentry-cli login
```

## Step 4: Upload Existing dSYMs for Past Releases

If you have already shipped builds without uploading dSYMs, you can retroactively upload them. Find the dSYMs in your Xcode archive:

```bash
# List recent archives
ls ~/Library/Developer/Xcode/Archives/

# Upload dSYMs from a specific archive
sentry-cli upload-dif ~/Library/Developer/Xcode/Archives/2026-03-30/YourApp.xcarchive/dSYMs/
```

This will immediately symbolicate any pending crash reports in Sentry that match those build UUIDs.

## Step 5: Verify the Setup

1. **Build your app** (Archive or regular build).
2. Check the Xcode build log for the sentry-cli upload output -- it should confirm files were uploaded.
3. In the **Sentry dashboard**, go to **Settings > Project > Debug Files** and confirm your dSYMs appear with the correct UUIDs.
4. **Trigger a test crash** to verify end-to-end symbolication:

```swift
// Temporary test -- remove after verification
SentrySDK.crash()
```

5. After the crash report appears in Sentry, confirm it shows function names, file names, and line numbers instead of hex addresses.

## Important Notes

- **Bitcode is deprecated since Xcode 14.** You do not need to download dSYMs from App Store Connect. The locally generated dSYMs from your archive are authoritative.
- **Never run multiple fatal crash reporters simultaneously.** If you also use Firebase Crashlytics, pick one for fatal crash reporting and disable the crash handler on the other (e.g., `options.enableCrashHandler = false` on Sentry if Crashlytics handles fatals). Signal handler conflicts (`SIGABRT`, `SIGSEGV`, etc.) mean only the last registered handler receives the signal.
- **App extensions run in separate processes.** Each extension (widgets, notification service, share extension) needs its own crash SDK initialization and its own dSYM upload in its build phases.
- **CI/CD pipelines** should include the dSYM upload step as part of the archive/release workflow so that every production build automatically has its symbols available in Sentry.
