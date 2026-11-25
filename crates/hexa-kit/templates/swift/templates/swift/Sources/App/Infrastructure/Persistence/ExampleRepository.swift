import Foundation
import Fluent
import Vapor

struct ExampleRepository: ExampleRepositoryProtocol {
    let database: Database
    
    init(req: Request) {
        self.database = req.db
    }
    
    func find(id: UUID) async throws -> ExampleEntity? {
        try await ExampleEntity.find(id, on: database)
    }
    
    func findAll() async throws -> [ExampleEntity] {
        try await ExampleEntity.query(on: database).all()
    }
    
    func create(_ entity: ExampleEntity) async throws {
        try await entity.save(on: database)
    }
    
    func update(_ entity: ExampleEntity) async throws {
        try await entity.update(on: database)
    }
    
    func delete(id: UUID) async throws {
        guard let entity = try await find(id: id) else {
            throw DomainError.notFound(id: id)
        }
        try await entity.delete(on: database)
    }
    
    func findByName(_ name: String) async throws -> [ExampleEntity] {
        try await ExampleEntity.query(on: database)
            .filter(\.$name == name)
            .all()
    }
}