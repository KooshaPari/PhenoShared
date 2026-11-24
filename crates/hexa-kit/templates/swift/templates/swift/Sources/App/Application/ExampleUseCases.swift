import Foundation
import Fluent

public struct GetExampleUseCase: GetExampleUseCaseProtocol {
    let repository: ExampleRepositoryProtocol
    
    public init(repository: ExampleRepositoryProtocol) {
        self.repository = repository
    }
    
    public func execute(_ id: UUID) async throws -> ExampleEntity.Public {
        guard let entity = try await repository.find(id: id) else {
            throw DomainError.notFound(id: id)
        }
        return entity.toPublic()
    }
}

public struct ListExamplesUseCase: ListExamplesUseCaseProtocol {
    let repository: ExampleRepositoryProtocol
    
    public init(repository: ExampleRepositoryProtocol) {
        self.repository = repository
    }
    
    public func execute(_ input: Void) async throws -> [ExampleEntity.Public] {
        let entities = try await repository.findAll()
        return entities.map { $0.toPublic() }
    }
}

public struct CreateExampleUseCase: CreateExampleUseCaseProtocol {
    let repository: ExampleRepositoryProtocol
    
    public init(repository: ExampleRepositoryProtocol) {
        self.repository = repository
    }
    
    public func execute(_ input: ExampleEntity.Create) async throws -> ExampleEntity.Public {
        let entity = ExampleEntity(
            name: input.name,
            description: input.description
        )
        try await repository.create(entity)
        return entity.toPublic()
    }
}

public struct UpdateExampleUseCase: UpdateExampleUseCaseProtocol {
    let repository: ExampleRepositoryProtocol
    
    public init(repository: ExampleRepositoryProtocol) {
        self.repository = repository
    }
    
    public func execute(_ input: (id: UUID, data: ExampleEntity.Update)) async throws -> ExampleEntity.Public {
        guard let entity = try await repository.find(id: input.id) else {
            throw DomainError.notFound(id: input.id)
        }
        
        if let name = input.data.name {
            entity.name = name
        }
        if let description = input.data.description {
            entity.description = description
        }
        
        try await repository.update(entity)
        return entity.toPublic()
    }
}

public struct DeleteExampleUseCase: DeleteExampleUseCaseProtocol {
    let repository: ExampleRepositoryProtocol
    
    public init(repository: ExampleRepositoryProtocol) {
        self.repository = repository
    }
    
    public func execute(_ id: UUID) async throws {
        try await repository.delete(id: id)
    }
}