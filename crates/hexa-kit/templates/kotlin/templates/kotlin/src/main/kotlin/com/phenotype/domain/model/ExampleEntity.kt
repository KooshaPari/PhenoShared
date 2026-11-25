package com.phenotype.domain.model

import com.phenotype.domain.errors.InvariantViolationError
import com.phenotype.domain.errors.ValidationError
import java.time.Instant
import java.util.UUID

/**
 * Entity status enum
 */
enum class EntityStatus {
    PENDING,
    ACTIVE,
    ARCHIVED;

    fun canTransitionTo(target: EntityStatus): Boolean = when (this) {
        PENDING -> target == ACTIVE
        ACTIVE -> target == ARCHIVED
        ARCHIVED -> false
    }
}

/**
 * Domain entity representing an example
 */
class ExampleEntity private constructor(
    val id: String,
    val name: String,
    val description: String,
    val status: EntityStatus,
    val createdAt: Instant,
    val updatedAt: Instant
) {
    /**
     * Rename the entity
     */
    fun rename(newName: String): ExampleEntity {
        if (newName.isBlank()) {
            throw ValidationError("Name cannot be blank")
        }
        return copy(name = newName, updatedAt = Instant.now())
    }

    /**
     * Update description
     */
    fun updateDescription(newDescription: String): ExampleEntity {
        return copy(description = newDescription, updatedAt = Instant.now())
    }

    /**
     * Activate the entity
     */
    fun activate(): ExampleEntity {
        if (!status.canTransitionTo(EntityStatus.ACTIVE)) {
            throw InvariantViolationError("Cannot activate from status: $status")
        }
        return copy(status = EntityStatus.ACTIVE, updatedAt = Instant.now())
    }

    /**
     * Archive the entity
     */
    fun archive(): ExampleEntity {
        if (!status.canTransitionTo(EntityStatus.ARCHIVED)) {
            throw InvariantViolationError("Cannot archive from status: $status")
        }
        return copy(status = EntityStatus.ARCHIVED, updatedAt = Instant.now())
    }

    private fun copy(
        name: String = this.name,
        description: String = this.description,
        status: EntityStatus = this.status,
        updatedAt: Instant = this.updatedAt
    ): ExampleEntity = ExampleEntity(
        id = this.id,
        name = name,
        description = description,
        status = status,
        createdAt = this.createdAt,
        updatedAt = updatedAt
    )

    companion object {
        /**
         * Create a new example entity
         */
        fun create(name: String, description: String = ""): ExampleEntity {
            if (name.isBlank()) {
                throw ValidationError("Name cannot be blank")
            }
            val now = Instant.now()
            return ExampleEntity(
                id = UUID.randomUUID().toString(),
                name = name.trim(),
                description = description.trim(),
                status = EntityStatus.PENDING,
                createdAt = now,
                updatedAt = now
            )
        }

        /**
         * Reconstitute an entity from persistence
         */
        fun reconstitute(
            id: String,
            name: String,
            description: String,
            status: EntityStatus,
            createdAt: Instant,
            updatedAt: Instant
        ): ExampleEntity = ExampleEntity(
            id = id,
            name = name,
            description = description,
            status = status,
            createdAt = createdAt,
            updatedAt = updatedAt
        )
    }
}
