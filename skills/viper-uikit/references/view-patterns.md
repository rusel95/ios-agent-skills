# View Patterns — Passive UIViewController

## How to Use This Reference

Read this when creating or refactoring the View layer of a VIPER module. Covers the passive View philosophy, lifecycle forwarding, UITableView/UICollectionView data flow, and common gotchas.

---

## The Passive View Rule

The View (UIViewController) is "as dumb as possible." It:
- **Waits** for Presenter to give it content — never asks
- **Forwards** lifecycle events and user actions to Presenter
- **Renders** ViewModels it receives — makes zero decisions about content
- **Owns** UIKit concerns: outlets, layout, animations, gesture recognizers, keyboard management

```swift
class OrderListViewController: UIViewController {
    var presenter: OrderListPresenterInput!

    // MARK: - UI Elements
    private let tableView = UITableView()
    private let activityIndicator = UIActivityIndicatorView(style: .large)

    // MARK: - Data (from Presenter)
    private var viewModels: [OrderCellViewModel] = []

    // MARK: - Lifecycle (forward to Presenter)
    override func viewDidLoad() {
        super.viewDidLoad()
        setupUI()
        presenter.viewDidLoad()  // forward — Presenter decides what happens
    }

    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        presenter.viewWillAppear()
    }
}

// MARK: - ViewInput (Presenter tells View what to display)
extension OrderListViewController: OrderListViewInput {
    func render(state: ViewState<[OrderCellViewModel]>) {
        switch state {
        case .idle:
            break
        case .loading:
            activityIndicator.startAnimating()
            tableView.isHidden = true
        case .loaded(let items):
            activityIndicator.stopAnimating()
            viewModels = items
            tableView.isHidden = false
            tableView.reloadData()
        case .empty:
            activityIndicator.stopAnimating()
            showEmptyState()
        case .error(let error):
            activityIndicator.stopAnimating()
            showErrorView(title: error.title, message: error.message, retryable: error.isRetryable)
        }
    }
}
```

## UITableView / UICollectionView Data Flow

View holds an array of ViewModels provided by Presenter. View is the DataSource/Delegate, but data comes from Presenter:

```swift
// MARK: - UITableViewDataSource
extension OrderListViewController: UITableViewDataSource {
    func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int {
        viewModels.count  // data from Presenter
    }

    func tableView(_ tableView: UITableView, cellForRowAt indexPath: IndexPath) -> UITableViewCell {
        let cell = tableView.dequeueReusableCell(withIdentifier: OrderCell.reuseId, for: indexPath) as! OrderCell
        cell.configure(with: viewModels[indexPath.row])
        return cell
    }
}

// MARK: - UITableViewDelegate (forward decisions to Presenter)
extension OrderListViewController: UITableViewDelegate {
    func tableView(_ tableView: UITableView, didSelectRowAt indexPath: IndexPath) {
        presenter.didSelectOrder(at: indexPath.row)  // forward — Presenter decides
    }

    func tableView(_ tableView: UITableView, commit editingStyle: UITableViewCell.EditingStyle, forRowAt indexPath: IndexPath) {
        if editingStyle == .delete {
            presenter.didRequestDeleteOrder(at: indexPath.row)  // forward — Presenter decides
        }
    }
}
```

## Lifecycle Forwarding Pattern

```swift
// View forwards events — NEVER acts on them directly

override func viewDidLoad() {
    super.viewDidLoad()
    setupUI()           // View's own concern (layout, outlets)
    presenter.viewDidLoad()  // Presenter decides what to fetch
}

// ❌ WRONG — View making decisions
override func viewDidLoad() {
    super.viewDidLoad()
    apiService.fetchData()      // View fetching data directly
    tableView.reloadData()      // View deciding when to reload
}
```

## Pull-to-Refresh

```swift
private func setupRefreshControl() {
    let refreshControl = UIRefreshControl()
    refreshControl.addTarget(self, action: #selector(didPullToRefresh), for: .valueChanged)
    tableView.refreshControl = refreshControl
}

@objc private func didPullToRefresh() {
    presenter.didPullToRefresh()  // forward to Presenter
}

// View protocol method (called by Presenter when refresh completes)
func endRefreshing() {
    tableView.refreshControl?.endRefreshing()
}
```

## Gotchas

**UITabBarController timing:** `viewDidLoad` fires BEFORE init completes for tab bar children. Wire Presenter in Builder before returning the VC — never rely on `viewDidLoad` for Presenter availability.

**iOS 13+ modal `.automatic`:** `viewWillAppear` of the presenting VC is NOT called when the modal is dismissed by swipe. Use `.fullScreen` or implement `UIAdaptivePresentationControllerDelegate`.

**Interactive pop gesture:** When user swipes back, Router is not notified. Use `UINavigationControllerDelegate.didShow` to sync Router/Coordinator state.

**Constructor injection with Storyboard:** If using storyboards, you can't use init injection for the VC. Use property injection (`vc.presenter = presenter`) in the Builder after instantiation. Programmatic VCs are preferred because they allow constructor injection.
