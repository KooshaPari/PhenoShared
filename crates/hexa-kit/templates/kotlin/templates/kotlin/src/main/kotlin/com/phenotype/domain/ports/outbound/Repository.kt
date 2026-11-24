package com.phenotype.domain.ports.outbound

import com.phenotype.domain.model.ExampleEntity

/**
 * Outbound port for repository
 */
interface Repository {
    /**
     * Save an entity
     */
    suspend fun save(entity: ExampleEntity)

    /**
     * Find entity by ID
     */
    suspend fun findById(id: String): ExampleEntity?

    /**
     * Find all entities
     */
    suspend fun findAll(): List<ExampleEntity>

    /**
     * Delete entity by ID
     */
    suspend fun delete(id: String)

    /**
     * Check if entity exists
     */
    suspend fun exists(id: String): Boolean
}

/**
 * Outbound port for unit of work
 */
interface UnitOfWork {
    val repository: Repository

    suspend fun commit()
    suspend fun rollback()
}
