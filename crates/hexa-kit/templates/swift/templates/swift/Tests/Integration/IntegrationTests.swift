import XCTest
@testable import App

final class IntegrationTests: XCTestCase {
    func testIntegrationSmoke() throws {
        XCTAssertNotNil(process.argv)
    }
}
