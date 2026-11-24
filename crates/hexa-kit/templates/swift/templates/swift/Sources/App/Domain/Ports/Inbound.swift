import Foundation

public protocol UseCaseProtocol: Sendable {
    associatedtype Input
    associatedtype Output
    
    func execute(_ input: Input) async throws -> Output
}

public protocol GetExampleUseCaseProtocol: UseCaseProtocol where Input == UUID, Output == ExampleEntity.Public { }
public protocol ListExamplesUseCaseProtocol: UseCaseProtocol where Input == Void, Output == [ExampleEntity.Public] { }
public protocol CreateExampleUseCaseProtocol: UseCaseProtocol where Input == ExampleEntity.Create, Output == ExampleEntity.Public { }
public protocol UpdateExampleUseCaseProtocol: UseCaseProtocol where Input == (id: UUID, data: ExampleEntity.Update), Output == ExampleEntity.Public { }
public protocol DeleteExampleUseCaseProtocol: UseCaseProtocol where Input == UUID, Output == Void { }