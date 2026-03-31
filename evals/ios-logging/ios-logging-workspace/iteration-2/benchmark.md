# ios-logging Benchmark (Sonnet 4.6)

## Summary

| Config | Pass | Total | Rate |
|--------|------|-------|------|
| **With Skill** | 89 | 91 | 97.8% |
| **Without Skill** | 58 | 91 | 63.7% |
| **Delta** | | | **+34.1%** |

## By Topic

| Topic | With Skill | Without Skill | Delta |
|-------|-----------|--------------|-------|
| app-extensions | 100.0% | 75.0% | +25.0% |
| audit-viewmodel | 100.0% | 60.0% | +40.0% |
| background-tasks | 100.0% | 100.0% | +0.0% |
| breadcrumbs | 100.0% | 66.7% | +33.3% |
| cancellation-error | 100.0% | 100.0% | +0.0% |
| centralized-error-handling | 100.0% | 0.0% | +100.0% |
| combine-error-reporting | 100.0% | 66.7% | +33.3% |
| combine-pipeline-death | 100.0% | 33.3% | +66.7% |
| core-data-silent-failures | 100.0% | 66.7% | +33.3% |
| crash-sdk-selection | 83.3% | 33.3% | +50.0% |
| dsym-configuration | 100.0% | 66.7% | +33.3% |
| dual-sdk-conflicts | 100.0% | 66.7% | +33.3% |
| error-reporter-protocol | 100.0% | 100.0% | +0.0% |
| mcp-connectivity | 66.7% | 66.7% | +0.0% |
| metrickit | 100.0% | 50.0% | +50.0% |
| notification-silent-failures | 100.0% | 100.0% | +0.0% |
| objc-bridge-edge-case | 100.0% | 100.0% | +0.0% |
| operational-pii-leaks | 100.0% | 100.0% | +0.0% |
| pii-compliance | 100.0% | 37.5% | +62.5% |
| print-replacement | 100.0% | 100.0% | +0.0% |
| privacy-annotations | 100.0% | 66.7% | +33.3% |
| retry-with-backoff | 100.0% | 50.0% | +50.0% |
| swiftui-task-modifier | 100.0% | 66.7% | +33.3% |
| task-error-swallowing | 100.0% | 50.0% | +50.0% |
| urlsession-status-codes | 100.0% | 50.0% | +50.0% |

## Per Eval

| Eval | Topic | With Skill | Without Skill | Delta |
|------|-------|-----------|--------------|-------|
| task-error-swallowing | task-error-swallowing | 100.0% | 50.0% | +50.0% |
| combine-pipeline-death | combine-pipeline-death | 100.0% | 33.3% | +66.7% |
| audit-viewmodel | audit-viewmodel | 100.0% | 60.0% | +40.0% |
| print-replacement | print-replacement | 100.0% | 100.0% | +0.0% |
| privacy-annotations | privacy-annotations | 100.0% | 66.7% | +33.3% |
| crash-sdk-selection | crash-sdk-selection | 100.0% | 0.0% | +100.0% |
| urlsession-status-codes | urlsession-status-codes | 100.0% | 50.0% | +50.0% |
| dual-sdk-conflicts | dual-sdk-conflicts | 100.0% | 66.7% | +33.3% |
| centralized-error-handling | centralized-error-handling | 100.0% | 0.0% | +100.0% |
| retry-with-backoff | retry-with-backoff | 100.0% | 50.0% | +50.0% |
| app-extensions | app-extensions | 100.0% | 75.0% | +25.0% |
| metrickit-purpose | metrickit | 100.0% | 50.0% | +50.0% |
| pii-gdpr-compliance | pii-compliance | 100.0% | 25.0% | +75.0% |
| cancellation-error | cancellation-error | 100.0% | 100.0% | +0.0% |
| core-data-save | core-data-silent-failures | 100.0% | 66.7% | +33.3% |
| hipaa-logging-strategy | pii-compliance | 100.0% | 50.0% | +50.0% |
| background-task-errors | background-tasks | 100.0% | 100.0% | +0.0% |
| objc-bridge-edge-case | objc-bridge-edge-case | 100.0% | 100.0% | +0.0% |
| breadcrumbs-usage | breadcrumbs | 100.0% | 66.7% | +33.3% |
| dsym-setup | dsym-configuration | 100.0% | 66.7% | +33.3% |
| swiftui-task-modifier | swiftui-task-modifier | 100.0% | 66.7% | +33.3% |
| operational-pii-leaks | operational-pii-leaks | 100.0% | 100.0% | +0.0% |
| error-reporter-protocol | error-reporter-protocol | 100.0% | 100.0% | +0.0% |
| combine-error-reporting | combine-error-reporting | 100.0% | 66.7% | +33.3% |
| mcp-connectivity | mcp-connectivity | 66.7% | 66.7% | +0.0% |
| notification-silent-failures | notification-silent-failures | 100.0% | 100.0% | +0.0% |
| non-fatal-vs-crash | crash-sdk-selection | 66.7% | 66.7% | +0.0% |
