import Foundation

private func stripTrailingSlash(_ s: String) -> String {
    s.hasSuffix("/") ? String(s.dropLast()) : s
}

@main struct NativeContractTests {
    static func main() async throws {
        let fixture = URL(fileURLWithPath: CommandLine.arguments[1])
        let requests = try JSONDecoder().decode([PendingRequest].self, from: Data(contentsOf: fixture))
        precondition(requests.count == 6)
        if case .boolean(_, let value) = requests[0].spec.field { precondition(value == true) }
        else { fatalError("Rust boolean schema did not decode") }
        if case .text(_, let value, _, _, let secret, _) = requests[1].spec.field {
            precondition(value == "synthetic-default" && secret == true)
        } else { fatalError("secret text schema did not decode") }
        precondition(requests[0].spec.buttons?.defer_label == "Later")
        precondition(requests[0].spec.details?.command == "synthetic-command")
        precondition(requests[0].spec.details?.items?.first?.display.contains("synthetic-file") == true)
        precondition(requests[0].spec.details?.effects == ["synthetic-effect"])
        precondition(requests[0].spec.notes?.defaultValue == "synthetic-note")
        precondition(requests[0].spec.notes?.maxLength == 200)
        let home = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        let config = try InboxConfiguration(arguments: ["--inbox-root", home.path,
            "--endpoint", "http://127.0.0.1:17917/inbox", "--title", "Candidate"], environment: [:])
        // Canonical path comparison: `URL(fileURLWithPath:, isDirectory:true).standardizedFileURL`
        // keeps a trailing "/" to flag the directory, while `appendingPathComponent`
        // of a leaf component produces no trailing slash. Both are valid
        // canonical forms; compare them on a slash-normalized basis without
        // weakening the URL/host/port/scheme checks.
        precondition(stripTrailingSlash(config.root.standardizedFileURL.path)
                     == stripTrailingSlash(home.standardizedFileURL.path),
                     "inbox root should canonicalize to home, got \(config.root.standardizedFileURL.path) vs \(home.standardizedFileURL.path)")
        precondition(config.endpoint.port == 17917 && config.windowTitle == "Candidate")
        let confirm = try RequestTransport.request(configuration: config, id: "synthetic", action: .confirm,
            value: "true", notes: "test & + unicode café")
        precondition(confirm.httpMethod == "POST" && confirm.url?.query == nil)
        let body = try JSONSerialization.jsonObject(with: confirm.httpBody!) as! [String: String]
        precondition(body["confirm"] == "ok" && body["value"] == "true" && body["notes"] == "test & + unicode café")
        for action in [RequestTransport.Action.cancel, .defer] {
            let request = try RequestTransport.request(configuration: config, id: "synthetic", action: action, value: nil, notes: nil)
            let body = try JSONSerialization.jsonObject(with: request.httpBody!) as! [String: String]
            precondition(body[action.rawValue] != nil && body["confirm"] == nil && body["value"] == nil)
        }
        do { _ = try InboxConfiguration(arguments: ["--endpoint", "https://example.com"], environment: [:]); fatalError("nonlocal endpoint accepted") }
        catch InboxConfiguration.ConfigurationError.nonLocalEndpoint { }
        try FileManager.default.createDirectory(at: home, withIntermediateDirectories: true)
        let lock = try JSONSerialization.data(withJSONObject: ["port": 17818, "bind": "127.0.0.1"])
        try lock.write(to: home.appendingPathComponent("daemon.lock"))
        let discovered = try InboxConfiguration(arguments: ["--inbox-root", home.path], environment: [:])
        precondition(discovered.endpoint.port == 17818)
        let xdg = try InboxConfiguration(arguments: [], environment: ["XDG_DATA_HOME": home.path])
        precondition(xdg.root.path == home.appendingPathComponent("phinbox").path)
        print("PASS native schema/defaults/details/secret/defer; POST body; root/port discovery; local endpoint restriction")
        if CommandLine.arguments.count == 4 {
            let endpoint = CommandLine.arguments[2], root = URL(fileURLWithPath: CommandLine.arguments[3])
            let live = try InboxConfiguration(arguments: ["--endpoint", endpoint, "--inbox-root", root.path], environment: [:])
            for (id, action, value) in [("native-confirm", RequestTransport.Action.confirm, "true"),
                                         ("native-cancel", .cancel, ""), ("native-defer", .defer, "")] {
                let request = try RequestTransport.request(configuration: live, id: id, action: action,
                    value: action == .confirm ? value : nil, notes: nil)
                let (_, response) = try await URLSession.shared.data(for: request)
                precondition((response as? HTTPURLResponse)?.statusCode == 200, "native daemon submission failed")
            }
            let answered = root.appendingPathComponent("answered")
            let confirm = try JSONSerialization.jsonObject(with: Data(contentsOf: answered.appendingPathComponent("native-confirm.json"))) as! [String: Any]
            let result = confirm["response"] as! [String: Any]
            precondition(result["status"] as? String == "answered")
            let value = result["value"] as! [String: Any]
            precondition(value["kind"] as? String == "boolean" && value["value"] as? Bool == true)
            let cancel = try JSONSerialization.jsonObject(with: Data(contentsOf: answered.appendingPathComponent("native-cancel.json"))) as! [String: Any]
            precondition((cancel["response"] as? [String: Any])?["status"] as? String == "cancelled")
            let deferred = try JSONSerialization.jsonObject(with: Data(contentsOf: root.appendingPathComponent("inbox/native-defer.json"))) as! [String: Any]
            precondition(deferred["state"] as? String == "pending")
            precondition((deferred["response"] as? [String: Any])?["status"] as? String == "deferred")
            print("PASS actual Swift transport -> isolated Rust daemon: typed true, cancellation, durable defer")
        }
    }
}
