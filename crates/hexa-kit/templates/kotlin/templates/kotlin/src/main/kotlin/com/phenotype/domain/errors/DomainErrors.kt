package com.phenotype.domain.errors

/**
 * Base sealed class for all domain errors
 */
sealed class DomainError(message: String, cause: Throwable? = null) : Exception(message, cause) {
    final override fun fillInStackTrace(): Throwable = this
}

/**
 * Error thrown when an entity is not found
 */
class EntityNotFoundError(entityType: String, id: String) : DomainError("$entityType not found: $id")

/**
 * Error thrown when input validation fails
 */
class ValidationError(message: String) : DomainError(message)

/**
 * Error thrown when a domain invariant is violated
 */
class InvariantViolationError(message: String) : DomainError(message)

/**
 * Error thrown for internal domain operations
 */
class InternalError(message: String, cause: Throwable? = null) : DomainError(message, cause)
