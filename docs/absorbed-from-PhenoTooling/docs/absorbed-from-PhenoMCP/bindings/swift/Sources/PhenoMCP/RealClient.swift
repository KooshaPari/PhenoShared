import Foundation

/// Real Swift MCP Client with actual HTTP networking
public actor RealMCPClient {
    private let endpoint: URL
    private let session: URLSession
    private var sessionId: String?
    private var protocolVersion: String = "2024-11-05"

    public init(endpoint: String) throws {
        guard let url = URL(string: endpoint) else {
            throw MCPClientError.invalidEndpoint
        }
        self.endpoint = url
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        self.session = URLSession(configuration: config)
    }

    /// Initialize connection
    public func initialize() async throws -> ServerInfo {
        let body: [String: Any] = [
            "jsonrpc": "2.0",
            "id": UUID().uuidString,
            "method": "initialize",
            "params": [
                "protocolVersion": protocolVersion,
                "capabilities": [:],
                "clientInfo": ["name": "pheno-swift", "version": "0.1.0"]
            ]
        ]
        
        let data = try await post(body)
        guard let result = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let resultObj = result["result"] as? [String: Any],
              let serverInfo = resultObj["serverInfo"] as? [String: Any] else {
            throw MCPClientError.noResult
        }
        
        return ServerInfo(
            name: serverInfo["name"] as? String ?? "",
            version: serverInfo["version"] as? String ?? ""
        )
    }

    /// List tools
    public func listTools() async throws -> [McpTool] {
        let body: [String: Any] = [
            "jsonrpc": "2.0",
            "id": UUID().uuidString,
            "method": "tools/list"
        ]
        
        let data = try await post(body)
        guard let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let result = json["result"] as? [String: Any],
              let toolsArray = result["tools"] as? [[String: Any]] else {
            return []
        }
        
        return toolsArray.map { tool in
            McpTool(
                name: tool["name"] as? String ?? "",
                description: tool["description"] as? String ?? "",
                inputSchema: [:]
            )
        }
    }

    /// Call tool
    public func callTool(name: String, arguments: [String: Any]) async throws -> ToolResult {
        let body: [String: Any] = [
            "jsonrpc": "2.0",
            "id": UUID().uuidString,
            "method": "tools/call",
            "params": ["name": name, "arguments": arguments]
        ]
        
        let data = try await post(body)
        guard let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let result = json["result"] as? [String: Any],
              let contentArray = result["content"] as? [[String: Any]] else {
            throw MCPClientError.noResult
        }
        
        let first = contentArray.first
        return ToolResult(
            type: first?["type"] as? String ?? "text",
            text: first?["text"] as? String
        )
    }

    private func post(_ body: [String: Any]) async throws -> Data {
        var request = URLRequest(url: endpoint)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: body)
        
        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse,
              (200...299).contains(httpResponse.statusCode) else {
            throw MCPClientError.httpError((response as? HTTPURLResponse)?.statusCode ?? 0)
        }
        
        return data
    }
}

public struct ServerInfo {
    public let name: String
    public let version: String
}

public struct McpTool: Identifiable {
    public let id: String
    public let name: String
    public let description: String
    public let inputSchema: [String: Any]
    
    public init(name: String, description: String, inputSchema: [String: Any]) {
        self.id = name
        self.name = name
        self.description = description
        self.inputSchema = inputSchema
    }
}

public struct ToolResult {
    public let type: String
    public let text: String?
}

public enum MCPClientError: Error {
    case invalidEndpoint
    case noResult
    case invalidResponse
    case httpError(Int)
}
