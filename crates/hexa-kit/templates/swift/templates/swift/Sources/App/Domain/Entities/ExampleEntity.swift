import Foundation
import Vapor
import Fluent

public final class ExampleEntity: Model {
    public static let schema = "examples"
    
    @ID(key: .id)
    public var id: UUID?
    
    @Field(key: "name")
    public var name: String
    
    @Field(key: "description")
    public var description: String
    
    @Field(key: "status")
    public var status: Status
    
    @Timestamp(key: "created_at", on: .create)
    public var createdAt: Date?
    
    @Timestamp(key: "updated_at", on: .update)
    public var updatedAt: Date?
    
    public init() { }
    
    public init(
        id: UUID? = nil,
        name: String,
        description: String,
        status: Status = .pending
    ) {
        self.id = id
        self.name = name
        self.description = description
        self.status = status
    }
    
    public enum Status: String, Codable {
        case pending = "PENDING"
        case active = "ACTIVE"
        case archived = "ARCHIVED"
    }
    
    public func activate() throws {
        guard status == .pending else {
            throw DomainError.invalidStateTransition(from: status.rawValue, to: Status.active.rawValue)
        }
        status = .active
    }
    
    public func archive() throws {
        guard status == .active else {
            throw DomainError.invalidStateTransition(from: status.rawValue, to: Status.archived.rawValue)
        }
        status = .archived
    }
}

extension ExampleEntity {
    struct Create: Content {
        let name: String
        let description: String
    }
    
    struct Update: Content {
        let name: String?
        let description: String?
    }
    
    struct Public: Content {
        let id: UUID?
        let name: String
        let description: String
        let status: String
        let createdAt: Date?
        let updatedAt: Date?
    }
    
    func toPublic() -> Public {
        Public(
            id: id,
            name: name,
            description: description,
            status: status.rawValue,
            createdAt: createdAt,
            updatedAt: updatedAt
        )
    }
}