import Foundation
import Fluent

public protocol RepositoryProtocol: Sendable {
    associatedtype Entity
    
    func find(id: UUID) async throws -> Entity?
    func findAll() async throws -> [Entity]
    func create(_ entity: Entity) async throws
    func update(_ entity: Entity) async throws
    func delete(id: UUID) async throws
}

public protocol ExampleRepositoryProtocol: RepositoryProtocol where Entity == ExampleEntity {
    func findByName(_ name: String) async throws -> [ExampleEntity]
}