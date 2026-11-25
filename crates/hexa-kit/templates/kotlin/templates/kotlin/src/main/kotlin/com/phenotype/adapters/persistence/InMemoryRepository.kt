package com.phenotype.adapters.persistence

import com.phenotype.domain.model.EntityStatus
import com.phenotype.domain.model.ExampleEntity
import com.phenotype.domain.ports.outbound.Repository
import java.time.Instant
import java.util.concurrent.ConcurrentHashMap

/**
 * In-memory repository implementation
 */
class InMemoryRepository : Repository {
    private val storage = ConcurrentHashMap<String, ExampleEntity>()

    override suspend fun save(entity: ExampleEntity) {
        storage[entity.id] = entity
    }

    override suspend fun findById(id: String): ExampleEntity? {
        return storage[id]
    }

    override suspend fun findAll(): List<ExampleEntity> {
        return storage.values.toList()
    }

    override suspend fun delete(id: String) {
        storage.remove(id)
    }

    override suspend fun exists(id: String): Boolean {
        return storage.containsKey(id)
    }

    fun clear() {
        storage.clear()
    }
}
