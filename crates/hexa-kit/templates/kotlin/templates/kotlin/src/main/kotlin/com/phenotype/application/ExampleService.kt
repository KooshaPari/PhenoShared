package com.phenotype.application

import com.phenotype.domain.errors.EntityNotFoundError
import com.phenotype.domain.errors.ValidationError
import com.phenotype.domain.model.ExampleEntity
import com.phenotype.domain.ports.inbound.CreateInput
import com.phenotype.domain.ports.inbound.UpdateInput
import com.phenotype.domain.ports.inbound.UseCaseService
import com.phenotype.domain.ports.outbound.Repository

/**
 * Application service implementing the use case
 */
class ExampleService(
    private val repository: Repository
) : UseCaseService {

    override suspend fun create(input: CreateInput): ExampleEntity {
        if (input.name.isBlank()) {
            throw ValidationError("Name cannot be blank")
        }

        val entity = ExampleEntity.create(
            name = input.name,
            description = input.description
        )

        repository.save(entity)
        return entity
    }

    override suspend fun getById(id: String): ExampleEntity {
        return repository.findById(id)
            ?: throw EntityNotFoundError("ExampleEntity", id)
    }

    override suspend fun update(input: UpdateInput): ExampleEntity {
        if (input.id.isBlank()) {
            throw ValidationError("ID cannot be blank")
        }

        val entity = getById(input.id)
        val updated = entity
            .rename(input.name)
            .updateDescription(input.description)

        repository.save(updated)
        return updated
    }

    override suspend fun delete(id: String) {
        if (!repository.exists(id)) {
            throw EntityNotFoundError("ExampleEntity", id)
        }
        repository.delete(id)
    }

    override suspend fun list(): List<ExampleEntity> {
        return repository.findAll()
    }
}
