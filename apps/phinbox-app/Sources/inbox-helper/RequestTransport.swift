import Foundation

/// The same JSON body accepted by the Rust inbox HTTP form handler.
struct RequestTransport {
    enum Action: String { case confirm, cancel, `defer` }
    static func request(configuration: InboxConfiguration, id: String,
                        action: Action, value: String?, notes: String?) throws -> URLRequest {
        guard !id.isEmpty, !id.contains("/"), !id.contains("\\"), id != ".", id != ".." else {
            throw TransportError.invalidID
        }
        let url = configuration.endpoint.appendingPathComponent("inbox")
            .appendingPathComponent(id).appendingPathComponent("answer")
        var body = [action.rawValue: action == .cancel ? "1" : "ok"]
        if action == .confirm, let value { body["value"] = value }
        if let notes, !notes.isEmpty { body["notes"] = notes }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: body, options: [.sortedKeys])
        return request
    }
    enum TransportError: Error { case invalidID }
}
