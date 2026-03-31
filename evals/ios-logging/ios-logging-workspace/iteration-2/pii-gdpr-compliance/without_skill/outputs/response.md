# Logging and GDPR Compliance in iOS Apps

## Core Principle

GDPR treats any data that can identify a person as personal data. Logs often inadvertently capture such data, which means your logging strategy must be designed with privacy in mind from the start.

## Key Areas to Watch

### 1. Avoid Logging Personally Identifiable Information (PII)

Never log data that can directly or indirectly identify a user:

- Email addresses, phone numbers, names
- IP addresses (considered PII under GDPR)
- Device identifiers (IDFA, IDFV) unless absolutely necessary
- Location data
- User IDs that can be traced back to a real person

Instead, use opaque session tokens or anonymized identifiers in your logs.

### 2. Be Careful with Network Request/Response Logging

HTTP interceptors or network logging layers can inadvertently capture:

- Authorization headers containing tokens
- Request bodies with user-submitted personal data
- Response bodies with user profiles or sensitive records

Strip or redact sensitive fields before they reach your logging layer.

### 3. OSLog and System Logs

When using `os.Logger` or `os_log`, be aware that:

- Logs may be collected through device sysdiagnose and shared with Apple or your team during debugging.
- Mark sensitive values with the `private` privacy level so they are redacted in log archives: `logger.info("User logged in: \(userId, privacy: .private)")`
- By default, dynamic string interpolations in `os_log` are private, but explicit annotation makes intent clear.

### 4. Third-Party Analytics and Crash Reporting

Services like Firebase Crashlytics, Sentry, or Datadog can capture log data and transmit it to servers outside the EU:

- Audit what data these SDKs collect automatically.
- Disable automatic PII collection where possible.
- Ensure data processing agreements (DPAs) are in place with each vendor.
- Confirm data residency requirements are met (EU hosting for EU users).

### 5. Log Retention and Deletion

GDPR requires that personal data not be kept longer than necessary:

- Define a retention policy for any logs stored on-device or server-side.
- Ensure logs are automatically purged after the retention period.
- If a user exercises their "right to erasure," you need a process to delete or anonymize their data in logs too.

### 6. User Consent

If your logs contain personal data and are transmitted off-device:

- You may need to obtain user consent before collecting those logs.
- Provide clear information about what is logged and why.
- Allow users to opt out of non-essential logging.

### 7. On-Device Log Files

If you write log files to the app sandbox (e.g., for diagnostics export):

- Encrypt log files at rest.
- Purge them on a schedule.
- If the user can share logs (e.g., via a support feature), inform them of what the file contains before they send it.

### 8. Debug vs. Release Logging Levels

- Use verbose logging only in debug builds.
- In release builds, limit logging to essential operational data and ensure nothing personally identifiable leaks through.
- Use compiler flags or environment checks to gate detailed logging.

## Practical Recommendations

- **Audit your log statements** periodically to catch accidental PII leakage.
- **Use a centralized logging wrapper** so you can apply redaction rules in one place.
- **Implement a redaction utility** that sanitizes known PII patterns (emails, phone numbers) before writing to logs.
- **Document your logging practices** as part of your GDPR data processing records (Article 30 obligation).
- **Test with privacy in mind** -- review log output from real user flows to verify no PII appears.
