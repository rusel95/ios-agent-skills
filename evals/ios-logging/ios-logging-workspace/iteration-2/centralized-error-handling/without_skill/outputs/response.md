# Handling Errors in SwiftUI Views

Setting an error string and showing an alert is a common starting point, but it limits you as your app grows. Here is a more structured approach.

## 1. Define a Typed Error Model

Instead of raw strings, use a dedicated error type that conforms to `LocalizedError`:

```swift
enum AppError: LocalizedError {
    case networkUnavailable
    case unauthorized
    case serverError(statusCode: Int)
    case decodingFailed
    case unknown(Error)

    var errorDescription: String? {
        switch self {
        case .networkUnavailable:
            return "No internet connection. Please check your network settings."
        case .unauthorized:
            return "Your session has expired. Please sign in again."
        case .serverError(let code):
            return "Server returned an error (code \(code))."
        case .decodingFailed:
            return "Failed to process the server response."
        case .unknown(let error):
            return error.localizedDescription
        }
    }
}
```

## 2. Use an Optional Error as Alert State

SwiftUI works well when you bind an alert directly to an optional `Identifiable` error:

```swift
struct IdentifiableError: Identifiable {
    let id = UUID()
    let error: AppError
}

struct ContentView: View {
    @State private var currentError: IdentifiableError?

    var body: some View {
        VStack { /* ... */ }
            .alert(item: $currentError) { wrapper in
                Alert(
                    title: Text("Error"),
                    message: Text(wrapper.error.localizedDescription),
                    dismissButton: .default(Text("OK"))
                )
            }
    }

    func loadData() {
        Task {
            do {
                try await fetchSomething()
            } catch let error as AppError {
                currentError = IdentifiableError(error: error)
            } catch {
                currentError = IdentifiableError(error: .unknown(error))
            }
        }
    }
}
```

## 3. Centralize Error Presentation with a View Modifier

To avoid repeating alert logic in every view, extract it into a reusable modifier:

```swift
struct ErrorAlertModifier: ViewModifier {
    @Binding var error: AppError?

    func body(content: Content) -> some View {
        content
            .alert(
                "Something went wrong",
                isPresented: Binding<Bool>(
                    get: { error != nil },
                    set: { if !$0 { error = nil } }
                ),
                presenting: error
            ) { _ in
                Button("OK", role: .cancel) { }
            } message: { error in
                Text(error.localizedDescription)
            }
    }
}

extension View {
    func errorAlert(_ error: Binding<AppError?>) -> some View {
        modifier(ErrorAlertModifier(error: error))
    }
}
```

Usage becomes a single line:

```swift
.errorAlert($viewModel.error)
```

## 4. Keep Error Handling in the ViewModel

Views should not contain business logic around errors. The view model (or `@Observable` class) should catch, map, and expose the error:

```swift
@Observable
class ItemsViewModel {
    var items: [Item] = []
    var error: AppError?
    var isLoading = false

    func load() async {
        isLoading = true
        defer { isLoading = false }

        do {
            items = try await repository.fetchItems()
        } catch let appError as AppError {
            error = appError
        } catch {
            error = .unknown(error)
        }
    }
}
```

The view simply observes `error` and uses the `.errorAlert` modifier.

## 5. Add Recovery Actions When Appropriate

For errors that have a clear recovery path, provide action buttons instead of a plain dismiss:

```swift
.alert(
    "Something went wrong",
    isPresented: $showError,
    presenting: currentError
) { error in
    switch error {
    case .networkUnavailable:
        Button("Retry") { Task { await viewModel.load() } }
        Button("Cancel", role: .cancel) { }
    case .unauthorized:
        Button("Sign In") { router.navigate(to: .login) }
    default:
        Button("OK", role: .cancel) { }
    }
} message: { error in
    Text(error.localizedDescription)
}
```

## Summary

| Practice | Benefit |
|---|---|
| Typed error enum conforming to `LocalizedError` | Consistent, testable error messages |
| Optional error as alert binding | Clean SwiftUI state management |
| Reusable `.errorAlert()` view modifier | No duplicated alert boilerplate |
| Error handling in ViewModel, not View | Separation of concerns |
| Recovery actions per error case | Better user experience |

This approach scales well: you add new cases to the enum, the compiler tells you everywhere you need to handle them, and the UI presentation stays in one place.
