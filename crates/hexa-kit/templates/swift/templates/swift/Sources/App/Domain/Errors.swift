import Foundation

public enum DomainError: Error {
    case notFound(id: UUID)
    case invalidInput(String)
    case businessRuleViolation(String)
    case invalidStateTransition(from: String, to: String)
    
    public var message: String {
        switch self {
        case .notFound(let id):
            return "Entity not found: \(id)"
        case .invalidInput(let reason):
            return "Invalid input: \(reason)"
        case .businessRuleViolation(let rule):
            return "Business rule violated: \(rule)"
        case .invalidStateTransition(let from, let to):
            return "Invalid state transition from \(from) to \(to)"
        }
    }
}