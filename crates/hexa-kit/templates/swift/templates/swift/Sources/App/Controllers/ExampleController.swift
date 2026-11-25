import Vapor

struct ExampleController: RouteCollection {
    func boot(routes: RoutesBuilder) throws {
        let api = routes.grouped("api", "v1")
        let examples = api.grouped("examples")
        
        examples.get(use: index)
        examples.post(use: create)
        examples.group(":id") { example in
            example.get(use: show)
            example.put(use: update)
            example.delete(use: delete)
        }
    }
    
    func index(req: Request) async throws -> [ExampleEntity.Public] {
        let repository = ExampleRepository(req: req)
        let useCase = ListExamplesUseCase(repository: repository)
        return try await useCase.execute()
    }
    
    func show(req: Request) async throws -> ExampleEntity.Public {
        let id = try req.parameters.require("id", as: UUID.self)
        let repository = ExampleRepository(req: req)
        let useCase = GetExampleUseCase(repository: repository)
        return try await useCase.execute(id)
    }
    
    func create(req: Request) async throws -> ExampleEntity.Public {
        let input = try req.content.decode(ExampleEntity.Create.self)
        let repository = ExampleRepository(req: req)
        let useCase = CreateExampleUseCase(repository: repository)
        return try await useCase.execute(input)
    }
    
    func update(req: Request) async throws -> ExampleEntity.Public {
        let id = try req.parameters.require("id", as: UUID.self)
        let input = try req.content.decode(ExampleEntity.Update.self)
        let repository = ExampleRepository(req: req)
        let useCase = UpdateExampleUseCase(repository: repository)
        return try await useCase.execute((id, input))
    }
    
    func delete(req: Request) async throws -> HTTPStatus {
        let id = try req.parameters.require("id", as: UUID.self)
        let repository = ExampleRepository(req: req)
        let useCase = DeleteExampleUseCase(repository: repository)
        try await useCase.execute(id)
        return .noContent
    }
}