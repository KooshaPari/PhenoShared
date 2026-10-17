import Foundation

struct InboxConfiguration {
    let root: URL
    let endpoint: URL
    let windowTitle: String
    let diagnose: Bool

    init(arguments: [String] = Array(CommandLine.arguments.dropFirst()),
         environment: [String: String] = ProcessInfo.processInfo.environment,
         home: URL = FileManager.default.homeDirectoryForCurrentUser) throws {
        var rootPath: String?, address: String?, title: String?
        var diagnose = false
        var index = 0
        while index < arguments.count {
            let option = arguments[index]
            if option == "--diagnose" { diagnose = true; index += 1; continue }
            guard ["--inbox-root", "--endpoint", "--title"].contains(option),
                  index + 1 < arguments.count else { throw ConfigurationError.invalidArguments }
            let value = arguments[index + 1]
            switch option {
            case "--inbox-root": rootPath = value
            case "--endpoint": address = value
            default: title = value
            }
            index += 2
        }
        let defaultRoot = environment["XDG_DATA_HOME"].map { URL(fileURLWithPath: $0).appendingPathComponent("phinbox") }
            ?? home.appendingPathComponent("Library/Application Support/phinbox")
        root = URL(fileURLWithPath: rootPath ?? environment["PHINBOX_INBOX_DIR"] ?? defaultRoot.path,
                   isDirectory: true).standardizedFileURL
        if address == nil, let data = try? Data(contentsOf: root.appendingPathComponent("daemon.lock")),
           let lock = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
           let port = lock["port"] as? Int, (1...65535).contains(port),
           let bind = lock["bind"] as? String, ["127.0.0.1", "::1"].contains(bind) {
            address = "http://\(bind == "::1" ? "[::1]" : bind):\(port)"
        }
        let port = environment["PHINBOX_PORT"].flatMap(Int.init) ?? 7117
        guard (1...65535).contains(port),
              var components = URLComponents(string: address ?? "http://127.0.0.1:\(port)"),
              components.scheme == "http", let host = components.host,
              ["127.0.0.1", "localhost", "::1", "[::1]"].contains(host),
              components.user == nil, components.password == nil,
              components.query == nil, components.fragment == nil else {
            throw ConfigurationError.nonLocalEndpoint
        }
        components.path = ""
        guard let url = components.url else { throw ConfigurationError.nonLocalEndpoint }
        endpoint = url
        windowTitle = title ?? environment["PHINBOX_WINDOW_TITLE"] ?? "Phinbox"
        self.diagnose = diagnose
    }
    enum ConfigurationError: Error { case invalidArguments, nonLocalEndpoint }
}
