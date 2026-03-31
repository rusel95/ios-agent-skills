# Proper Error Handling with Crash Reporting for Network Calls

The original code has a critical silent failure pattern: **URLSession does not throw for HTTP errors**. A `500 Internal Server Error` or `401 Unauthorized` returns `(Data, URLResponse)` successfully -- only transport-level failures (no network, DNS failure, timeout) cause a throw. The response's HTTP status code must be validated explicitly.

Additionally, the code lacks structured logging and crash reporting, meaning any failure in production is invisible.

## Define a Typed Network Error

```swift
enum NetworkError: LocalizedError {
    case invalidResponse
    case httpError(statusCode: Int, data: Data)
    case decodingFailed(underlying: Error)

    var errorDescription: String? {
        switch self {
        case .invalidResponse:
            return "Response was not a valid HTTP response"
        case .httpError(let statusCode, _):
            return "HTTP error \(statusCode)"
        case .decodingFailed(let underlying):
            return "Decoding failed: \(underlying.localizedDescription)"
        }
    }
}
```

## Set Up Logger Category

```swift
import os

extension Logger {
    private static let subsystem = Bundle.main.bundleIdentifier!
    static let networking = Logger(subsystem: subsystem, category: "Networking")
}
```

## Implement the Fixed Function

```swift
func fetchProducts() async throws -> [Product] {
    let (data, response) = try await URLSession.shared.data(from: productsURL)

    // URLSession does not throw for HTTP errors -- validate status code explicitly
    guard let httpResponse = response as? HTTPURLResponse else {
        Logger.networking.fault("Response is not HTTPURLResponse for \(self.productsURL.path, privacy: .public)")
        let error = NetworkError.invalidResponse
        ErrorReporter.shared.recordNonFatal(error, context: ["url": productsURL.absoluteString])
        throw error
    }

    guard (200...299).contains(httpResponse.statusCode) else {
        Logger.networking.error(
            "HTTP \(httpResponse.statusCode, privacy: .public) for \(self.productsURL.path, privacy: .public)"
        )
        let error = NetworkError.httpError(statusCode: httpResponse.statusCode, data: data)
        ErrorReporter.shared.recordNonFatal(error, context: [
            "url": productsURL.absoluteString,
            "statusCode": httpResponse.statusCode
        ])
        throw error
    }

    do {
        return try JSONDecoder().decode([Product].self, from: data)
    } catch {
        Logger.networking.error(
            "Decoding [Product] failed: \(error.localizedDescription, privacy: .public)"
        )
        ErrorReporter.shared.recordNonFatal(error, context: [
            "url": productsURL.absoluteString,
            "responseSize": data.count
        ])
        throw NetworkError.decodingFailed(underlying: error)
    }
}
```

## Call Site with Full Observability

When calling this from a SwiftUI `.task` or a `Task {}`, ensure errors are caught with observability and CancellationError is handled separately:

```swift
.task {
    do {
        products = try await fetchProducts()
    } catch is CancellationError {
        // View disappeared -- normal lifecycle, do not report
    } catch {
        loadError = error
        Logger.networking.error("fetchProducts failed: \(error.localizedDescription, privacy: .public)")
        ErrorReporter.shared.recordNonFatal(error, context: ["screen": "productList"])
    }
}
```

## What Changed and Why

| Issue in original code | Fix applied |
|---|---|
| HTTP status codes not validated -- a `4xx`/`5xx` silently passes through as if successful | Added `guard` on `HTTPURLResponse` and status code range `200...299` |
| No structured logging -- failures invisible on production devices | Added `Logger.networking` with appropriate log levels and privacy annotations |
| No crash reporting -- errors never reach a remote dashboard | Added `ErrorReporter.shared.recordNonFatal()` with contextual metadata at every failure point |
| Decoding errors propagate with no context | Wrapped decoding in `do/catch`, logged the failure, reported to crash SDK, and re-threw as a typed `NetworkError.decodingFailed` |
| No typed error -- callers cannot distinguish failure reasons | Introduced `NetworkError` enum so callers can pattern-match on `.httpError(statusCode:)` vs `.decodingFailed` vs `.invalidResponse` |

## ErrorReporter Protocol Reference

The `ErrorReporter.shared.recordNonFatal()` calls above use a protocol-based abstraction that wraps your chosen crash SDK (Sentry, Crashlytics, or PostHog). This avoids scattering vendor-specific API calls throughout your codebase:

```swift
protocol ErrorReporter: Sendable {
    func recordNonFatal(_ error: Error, context: [String: Any])
    func addBreadcrumb(message: String, category: String, level: BreadcrumbLevel, data: [String: Any]?)
    func setUserID(_ userID: String?)
}
```

Implement this protocol with your chosen SDK (see crash-sdk-integration reference for Sentry and Crashlytics implementations), then expose it as a shared singleton. This gives you vendor independence -- swapping from Crashlytics to Sentry requires changing one class, not every call site.
