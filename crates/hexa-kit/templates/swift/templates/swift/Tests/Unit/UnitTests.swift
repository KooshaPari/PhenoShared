import XCTest
@testable import App

final class UnitTests: XCTestCase {
    func testSmoke() throws {
        XCTAssertEqual("template-swift-app".split(separator: "-")[0], "template")
    }
}
