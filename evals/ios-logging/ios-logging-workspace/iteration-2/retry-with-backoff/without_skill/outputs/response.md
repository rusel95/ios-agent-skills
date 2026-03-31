# Retry Mechanism with Exponential Backoff, Jitter, and Observability

Below is a complete implementation of a retry mechanism for network requests in Swift, featuring exponential backoff with jitter and structured logging for observability.

## RetryConfiguration

```swift
import Foundation
import os.log

struct RetryConfiguration {
    let maxRetries: Int
    let baseDelay: TimeInterval
    let maxDelay: TimeInterval
    let jitterFactor: Double
    let retryableStatusCodes: Set<Int>
    let retryableErrors: Set<URLError.Code>

    init(
        maxRetries: Int = 3,
        baseDelay: TimeInterval = 1.0,
        maxDelay: TimeInterval = 30.0,
        jitterFactor: Double = 0.5,
        retryableStatusCodes: Set<Int> = [408, 429, 500, 502, 503, 504],
        retryableErrors: Set<URLError.Code> = [
            .timedOut,
            .networkConnectionLost,
            .notConnectedToInternet,
            .cannotConnectToHost
        ]
    ) {
        self.maxRetries = maxRetries
        self.baseDelay = baseDelay
        self.maxDelay = maxDelay
        self.jitterFactor = jitterFactor
        self.retryableStatusCodes = retryableStatusCodes
        self.retryableErrors = retryableErrors
    }
}
```

## RetryNetworkClient

```swift
final class RetryNetworkClient {
    private let session: URLSession
    private let configuration: RetryConfiguration
    private let logger = Logger(subsystem: Bundle.main.bundleIdentifier ?? "com.app", category: "NetworkRetry")
    private let signposter = OSSignposter(subsystem: Bundle.main.bundleIdentifier ?? "com.app", category: "NetworkRetry")

    init(session: URLSession = .shared, configuration: RetryConfiguration = RetryConfiguration()) {
        self.session = session
        self.configuration = configuration
    }

    func data(for request: URLRequest) async throws -> (Data, URLResponse) {
        let requestID = UUID().uuidString.prefix(8)
        let url = request.url?.absoluteString ?? "unknown"

        let intervalState = signposter.beginInterval("RetryRequest", id: signposter.makeSignpostID(), "\(url)")

        logger.info("[\(requestID)] Starting request: \(request.httpMethod ?? "GET") \(url)")

        var lastError: Error?
        var lastResponse: HTTPURLResponse?

        for attempt in 0...configuration.maxRetries {
            if attempt > 0 {
                let delay = calculateDelay(forAttempt: attempt)
                logger.notice("[\(requestID)] Retry \(attempt)/\(self.configuration.maxRetries) after \(String(format: "%.2f", delay))s delay. Reason: \(self.describeFailure(error: lastError, response: lastResponse))")

                signposter.emitEvent("RetryDelay", "\(delay)s before attempt \(attempt)")

                try await Task.sleep(nanoseconds: UInt64(delay * 1_000_000_000))
            }

            do {
                logger.debug("[\(requestID)] Attempt \(attempt + 1)/\(self.configuration.maxRetries + 1)")

                let (data, response) = try await session.data(for: request)

                guard let httpResponse = response as? HTTPURLResponse else {
                    logger.error("[\(requestID)] Response is not HTTPURLResponse")
                    throw URLError(.badServerResponse)
                }

                lastResponse = httpResponse

                if configuration.retryableStatusCodes.contains(httpResponse.statusCode) && attempt < configuration.maxRetries {
                    let retryAfter = parseRetryAfterHeader(httpResponse)
                    if let retryAfter {
                        logger.info("[\(requestID)] Server requested Retry-After: \(retryAfter)s")
                    }
                    logger.warning("[\(requestID)] Retryable status code \(httpResponse.statusCode) on attempt \(attempt + 1)")
                    lastError = URLError(.init(rawValue: httpResponse.statusCode))
                    continue
                }

                logger.info("[\(requestID)] Request succeeded on attempt \(attempt + 1) with status \(httpResponse.statusCode)")
                signposter.endInterval("RetryRequest", intervalState, "Success on attempt \(attempt + 1)")

                return (data, response)

            } catch let error as URLError where configuration.retryableErrors.contains(error.code) && attempt < configuration.maxRetries {
                lastError = error
                logger.warning("[\(requestID)] Retryable error on attempt \(attempt + 1): \(error.localizedDescription) (code: \(error.code.rawValue))")
                continue

            } catch {
                logger.error("[\(requestID)] Non-retryable error on attempt \(attempt + 1): \(error.localizedDescription)")
                signposter.endInterval("RetryRequest", intervalState, "Failed: non-retryable error")
                throw error
            }
        }

        logger.error("[\(requestID)] All \(self.configuration.maxRetries + 1) attempts exhausted for \(url)")
        signposter.endInterval("RetryRequest", intervalState, "Failed: max retries exceeded")

        throw lastError ?? URLError(.unknown)
    }

    // MARK: - Exponential Backoff with Jitter

    private func calculateDelay(forAttempt attempt: Int) -> TimeInterval {
        // Exponential: baseDelay * 2^(attempt-1)
        let exponentialDelay = configuration.baseDelay * pow(2.0, Double(attempt - 1))

        // Cap at maxDelay
        let cappedDelay = min(exponentialDelay, configuration.maxDelay)

        // Full jitter: random value between 0 and cappedDelay
        // This decorrelates retries from multiple clients hitting the same server
        let jitter = Double.random(in: 0...(cappedDelay * configuration.jitterFactor))
        let finalDelay = cappedDelay * (1.0 - configuration.jitterFactor) + jitter

        logger.debug("Backoff calculation: base=\(self.configuration.baseDelay), exponential=\(exponentialDelay), capped=\(cappedDelay), jittered=\(finalDelay)")

        return finalDelay
    }

    // MARK: - Helpers

    private func parseRetryAfterHeader(_ response: HTTPURLResponse) -> TimeInterval? {
        guard let retryAfterString = response.value(forHTTPHeaderField: "Retry-After") else {
            return nil
        }
        return TimeInterval(retryAfterString)
    }

    private func describeFailure(error: Error?, response: HTTPURLResponse?) -> String {
        if let response {
            return "HTTP \(response.statusCode)"
        }
        if let urlError = error as? URLError {
            return "URLError \(urlError.code.rawValue): \(urlError.localizedDescription)"
        }
        return error?.localizedDescription ?? "Unknown error"
    }
}
```

## Usage

```swift
let client = RetryNetworkClient(
    configuration: RetryConfiguration(
        maxRetries: 3,
        baseDelay: 1.0,
        maxDelay: 30.0,
        jitterFactor: 0.5,
        retryableStatusCodes: [408, 429, 500, 502, 503, 504]
    )
)

let request = URLRequest(url: URL(string: "https://api.example.com/data")!)
let (data, response) = try await client.data(for: request)
```

## Key Design Decisions

### Exponential Backoff with Jitter

The delay formula works as follows:

1. **Exponential growth**: `baseDelay * 2^(attempt - 1)` produces delays of 1s, 2s, 4s, 8s, etc.
2. **Cap**: The delay is clamped to `maxDelay` to prevent unreasonably long waits.
3. **Jitter**: A random component is mixed in so that multiple clients retrying simultaneously do not all hit the server at the same instant (the "thundering herd" problem). The `jitterFactor` of 0.5 means the final delay ranges between 50% and 100% of the capped exponential value.

### Observability

The implementation uses Apple's unified logging framework (`os.log`) at appropriate levels:

- **`.info`** for request lifecycle events (start, success, retry-after headers).
- **`.notice`** for retry decisions, including the computed delay and the reason for retrying.
- **`.warning`** for retryable failures (transient errors and server errors).
- **`.error`** for terminal failures (non-retryable errors and exhaustion of all attempts).
- **`.debug`** for internal details like per-attempt markers and backoff calculations.

`OSSignposter` is used to create Instruments-visible intervals around the entire retry sequence. This allows profiling in Instruments with the `os_signpost` instrument to see exactly how long retried requests take end-to-end, including all delay time.

### Retryable Conditions

The client distinguishes between transient and permanent failures:

- **Retryable HTTP status codes**: 408 (Request Timeout), 429 (Too Many Requests), 500, 502, 503, 504 -- these are server-side issues that may resolve on retry.
- **Retryable URLError codes**: timeout, connection lost, not connected, cannot connect -- these are network-layer issues that may be transient.
- **Non-retryable errors**: Everything else (4xx client errors, decoding errors, cancelled requests) fails immediately without wasting retry budget.

### Retry-After Header

The implementation reads the `Retry-After` HTTP header when present (commonly returned with 429 responses). While the current code logs this value, you could extend it to use the server-suggested delay instead of the calculated backoff when it is larger.
