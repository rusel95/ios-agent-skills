# Adding Error Handling with Crash Reporting to a Network Call

Here is the updated implementation with proper error handling and crash reporting:

```swift
import Foundation

// MARK: - Custom Error Types

enum NetworkError: LocalizedError {
    case invalidResponse
    case httpError(statusCode: Int, data: Data?)
    case decodingFailed(underlying: Error)
    case noData

    var errorDescription: String? {
        switch self {
        case .invalidResponse:
            return "The server returned an invalid response."
        case .httpError(let statusCode, _):
            return "HTTP error with status code \(statusCode)."
        case .decodingFailed(let underlying):
            return "Failed to decode response: \(underlying.localizedDescription)"
        case .noData:
            return "No data received from the server."
        }
    }
}

// MARK: - Crash Reporter Protocol

protocol CrashReporter {
    func log(_ message: String)
    func recordError(_ error: Error, userInfo: [String: Any])
    func addBreadcrumb(_ message: String, category: String, metadata: [String: Any])
}

// MARK: - Updated Network Call

func fetchProducts() async throws -> [Product] {
    crashReporter.addBreadcrumb(
        "Fetching products",
        category: "network",
        metadata: ["url": productsURL.absoluteString]
    )

    let data: Data
    let response: URLResponse

    do {
        (data, response) = try await URLSession.shared.data(from: productsURL)
    } catch let urlError as URLError {
        crashReporter.recordError(urlError, userInfo: [
            "url": productsURL.absoluteString,
            "errorCode": urlError.code.rawValue,
            "errorDomain": urlError.errorCode
        ])
        crashReporter.log("Network request failed: \(urlError.localizedDescription)")
        throw urlError
    } catch {
        crashReporter.recordError(error, userInfo: [
            "url": productsURL.absoluteString
        ])
        throw error
    }

    // Validate HTTP response
    guard let httpResponse = response as? HTTPURLResponse else {
        let error = NetworkError.invalidResponse
        crashReporter.recordError(error, userInfo: [
            "url": productsURL.absoluteString,
            "responseType": String(describing: type(of: response))
        ])
        throw error
    }

    crashReporter.addBreadcrumb(
        "Received HTTP response",
        category: "network",
        metadata: [
            "statusCode": httpResponse.statusCode,
            "url": productsURL.absoluteString,
            "contentLength": httpResponse.expectedContentLength
        ]
    )

    // Check for HTTP error status codes
    guard (200...299).contains(httpResponse.statusCode) else {
        let error = NetworkError.httpError(
            statusCode: httpResponse.statusCode,
            data: data
        )
        crashReporter.recordError(error, userInfo: [
            "url": productsURL.absoluteString,
            "statusCode": httpResponse.statusCode,
            "responseBody": String(data: data, encoding: .utf8) ?? "non-UTF8 body"
        ])
        crashReporter.log("HTTP error \(httpResponse.statusCode) for \(productsURL.absoluteString)")
        throw error
    }

    // Decode the response
    do {
        let products = try JSONDecoder().decode([Product].self, from: data)
        crashReporter.addBreadcrumb(
            "Successfully decoded products",
            category: "network",
            metadata: ["productCount": products.count]
        )
        return products
    } catch {
        crashReporter.recordError(error, userInfo: [
            "url": productsURL.absoluteString,
            "statusCode": httpResponse.statusCode,
            "rawResponse": String(data: data.prefix(1024), encoding: .utf8) ?? "non-UTF8",
            "decodingError": String(describing: error)
        ])
        crashReporter.log("Decoding failed for products response: \(error)")
        throw NetworkError.decodingFailed(underlying: error)
    }
}
```

## What Was Added

1. **Custom `NetworkError` enum** -- Defines specific error cases for invalid responses, HTTP errors, and decoding failures. Conforms to `LocalizedError` for human-readable descriptions.

2. **HTTP status code validation** -- The original code ignored the `response` entirely. Now it casts to `HTTPURLResponse` and verifies the status code is in the 2xx range before attempting to decode.

3. **`URLError` handling** -- Network-level failures (timeout, no connection, DNS failure, etc.) are caught separately so you can attach the specific `URLError.code` to the crash report.

4. **Crash reporter integration** -- A `CrashReporter` protocol abstracts the crash reporting service (Crashlytics, Sentry, Datadog, etc.). Each failure path calls `recordError` with contextual metadata such as the URL, status code, and response body. Breadcrumbs are logged at key stages to provide a trail in crash reports.

5. **Decoding error context** -- When JSON decoding fails, the raw response body (truncated to 1024 bytes) is attached to the crash report. This makes it much easier to diagnose malformed responses from the server.

## Example: Concrete CrashReporter Using Firebase Crashlytics

```swift
import FirebaseCrashlytics

final class FirebaseCrashReporter: CrashReporter {
    func log(_ message: String) {
        Crashlytics.crashlytics().log(message)
    }

    func recordError(_ error: Error, userInfo: [String: Any]) {
        Crashlytics.crashlytics().record(error: error, userInfo: userInfo)
    }

    func addBreadcrumb(_ message: String, category: String, metadata: [String: Any]) {
        Crashlytics.crashlytics().log("\(category): \(message) | \(metadata)")
    }
}
```

## Key Points

- Always check the HTTP status code. A 200-level response is the only indicator that the server processed your request successfully. Status codes like 401, 403, 404, and 500 should be treated as errors.
- Attach as much context as possible to crash reports (URL, status code, response body) so issues are diagnosable without reproduction.
- Truncate response bodies before attaching them to crash reports to avoid excessive memory usage or payload size limits.
- Use breadcrumbs to trace the sequence of events leading up to a failure. This is especially useful when a crash occurs later in the flow.
