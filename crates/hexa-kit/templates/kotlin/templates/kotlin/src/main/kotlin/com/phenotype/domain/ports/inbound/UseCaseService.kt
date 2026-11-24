package com.phenotype.domain.ports.inbound

import com.phenotype.domain.model.ExampleEntity

/**
 * Inbound port for use cases
 */
interface UseCaseService {
    /**
     * Create a new entity
     */
    suspend fun create(input: CreateInput): ExampleEntity

    /**
     * Get entity by ID
     */
    suspend fun getById(id: String): ExampleEntity

    /**
     * Update an entity
     */
    suspend fun update(input: UpdateInput): ExampleEntity

    /**
     * Delete an entity
     */
    suspend fun delete(id: String)

    /**
     * List all entities
     */
    suspend fun list(): List<ExampleEntity>
}

/**
 * Input for creating an entity
 */
data class CreateInput(
    val name: String,
    val description: String = ""
)

/**
 * Input for updating an entity
 */
data class UpdateInput(
    val id: String,
    val name: String,
    val description: String
)
