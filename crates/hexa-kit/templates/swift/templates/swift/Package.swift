// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "TemplateSwiftApp",
    platforms: [
        .macOS(.v14)
    ],
    products: [
        .executable(name: "TemplateSwiftApp", targets: ["App"])
    ],
    targets: [
        .executableTarget(name: "App", path: "Sources/App"),
        .testTarget(name: "UnitTests", dependencies: ["App"], path: "Tests/Unit"),
        .testTarget(name: "IntegrationTests", dependencies: ["App"], path: "Tests/Integration")
    ]
)
