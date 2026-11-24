# Claude AI Agent Guide — template-lang-swift

This repository is designed to work seamlessly with Claude (and other advanced AI agents) as an autonomous software engineer.

## Quick Start

```bash
# Generate Xcode project
xcodegen generate

# Build
xcodebuild -scheme App -configuration Debug

# Test
xcodebuild test -scheme App

# Format
swiftformat .
```

## Repository Mental Model

### Project Structure

```
Sources/
  App/
    AppDelegate.swift
    SceneDelegate.swift
  Features/
    Home/
      HomeView.swift
      HomeViewModel.swift
      HomeCoordinator.swift
    Profile/
  Core/
    Network/
      APIClient.swift
      Endpoints.swift
    Persistence/
      Repository.swift
    Extensions/
  Models/
  Services/
Tests/
  AppTests/
  FeaturesTests/
```

### Style Constraints

- **Line length:** 120 characters
- **Formatter:** SwiftFormat
- **Linter:** SwiftLint
- **Access control:** private by default, internal for library APIs
- **Protocols:** Use protocol composition

### Agent Must

- Use Swift Concurrency (async/await)
- Prefer value types (structs)
- Use protocols for abstraction
- Document public APIs
- Write XCTest tests

## Standard Operating Loop

1. **Review** - Read requirements
2. **Research** - Check existing patterns
3. **Plan** - Design types and protocols
4. **Execute** - Implement with TDD
5. **Test** - XCTest verification
6. **Polish** - Format and lint

## CLI Reference

```bash
# XcodeGen
xcodegen generate

# Build
xcodebuild -scheme <name> build
xcodebuild -scheme <name> -configuration Release build

# Test
xcodebuild test -scheme <name>
xcodebuild test -scheme <name> -destination 'platform=iOS Simulator,name=iPhone 15'

# Formatting
swiftformat .
swiftlint autocorrect

# Dependencies
swift package resolve
swift package update
```

## Architecture Patterns

### MVVM + Coordinator

```swift
// View
struct HomeView: View {
    @StateObject var viewModel: HomeViewModel
    
    var body: some View {
        List(viewModel.items) { item in
            Text(item.title)
        }
        .task {
            await viewModel.loadItems()
        }
    }
}

// ViewModel
@MainActor
final class HomeViewModel: ObservableObject {
    @Published var items: [Item] = []
    @Published var isLoading = false
    
    private let repository: ItemRepository
    
    func loadItems() async {
        isLoading = true
        defer { isLoading = false }
        items = try! await repository.fetchItems()
    }
}

// Coordinator
protocol Coordinator {
    func start()
}

final class HomeCoordinator: Coordinator {
    private let navigationController: UINavigationController
    
    init(navigationController: UINavigationController) {
        self.navigationController = navigationController
    }
    
    func start() {
        let viewModel = HomeViewModel(repository: repository)
        let view = HomeView(viewModel: viewModel)
        // Bridge to UIKit
    }
}
```

### Repository Pattern

```swift
protocol ItemRepository {
    func fetchItems() async throws -> [Item]
    func saveItem(_ item: Item) async throws
}

final class RemoteItemRepository: ItemRepository {
    private let client: APIClient
    
    func fetchItems() async throws -> [Item] {
        try await client.get("/items")
    }
    
    func saveItem(_ item: Item) async throws {
        try await client.post("/items", body: item)
    }
}
```

### Actor for Thread Safety

```swift
actor CacheStore {
    private var cache: [String: Data] = [:]
    
    func get(_ key: String) -> Data? {
        cache[key]
    }
    
    func set(_ key: String, value: Data) {
        cache[key] = value
    }
}
```

## Testing Patterns

```swift
final class HomeViewModelTests: XCTestCase {
    var viewModel: HomeViewModel!
    var mockRepository: MockItemRepository!
    
    override func setUp() async throws {
        mockRepository = MockItemRepository()
        viewModel = HomeViewModel(repository: mockRepository)
    }
    
    func testLoadItemsSuccess() async throws {
        let items = [Item(id: "1", title: "Test")]
        mockRepository.mockFetchItems = items
        
        try await viewModel.loadItems()
        
        XCTAssertEqual(viewModel.items.count, 1)
        XCTAssertEqual(viewModel.items.first?.title, "Test")
    }
}

final class MockItemRepository: ItemRepository {
    var mockFetchItems: [Item] = []
    var mockFetchError: Error?
    
    func fetchItems() async throws -> [Item] {
        if let error = mockFetchError {
            throw error
        }
        return mockFetchItems
    }
}
```

## Security Guidelines

- Store secrets in Keychain
- Use HTTPS for all network requests
- Validate SSL certificates
- Sanitize user input
- Use parameterized queries
- Log security events

## Troubleshooting

```bash
# Clean build
xcodebuild clean
rm -rf ~/Library/Developer/Xcode/DerivedData

# Reset packages
rm -rf SourcePackages
swift package resolve

# Simulator issues
xcrun simctl list devices
xcrun simctl erase <device>
```
