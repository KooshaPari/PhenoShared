package com.phenotype.adapters.http

import com.phenotype.application.ExampleService
import com.phenotype.domain.errors.EntityNotFoundError
import com.phenotype.domain.errors.ValidationError
import com.phenotype.domain.ports.inbound.CreateInput
import com.phenotype.domain.ports.inbound.UpdateInput
import io.ktor.server.application.Application
import io.ktor.server.application.call
import io.ktor.server.plugins.BadRequestException
import io.ktor.server.plugins.NotFoundException
import io.ktor.server.request.receive
import io.ktor.server.response.respond
import io.ktor.server.response.respondText
import io.ktor.server.routing.*

/**
 * Configure HTTP routing
 */
fun Application.configureRouting(service: ExampleService) {
    routing {
        get("/health") {
            call.respondText("OK")
        }

        route("/api/v1/examples") {
            post {
                val input = call.receive<CreateInputDto>()
                val result = service.create(CreateInput(input.name, input.description))
                call.respond(HttpCreated(result.toDto()))
            }

            get {
                val result = service.list()
                call.respond(HttpList(result.map { it.toDto() }))
            }

            get("/{id}") {
                val id = call.parameters["id"] ?: throw BadRequestException("ID required")
                try {
                    val result = service.getById(id)
                    call.respond(HttpOk(result.toDto()))
                } catch (e: EntityNotFoundError) {
                    throw NotFoundException(e.message)
                }
            }

            put("/{id}") {
                val id = call.parameters["id"] ?: throw BadRequestException("ID required")
                val input = call.receive<UpdateInputDto>()
                try {
                    val result = service.update(UpdateInput(id, input.name, input.description))
                    call.respond(HttpOk(result.toDto()))
                } catch (e: EntityNotFoundError) {
                    throw NotFoundException(e.message)
                } catch (e: ValidationError) {
                    throw BadRequestException(e.message)
                }
            }

            delete("/{id}") {
                val id = call.parameters["id"] ?: throw BadRequestException("ID required")
                try {
                    service.delete(id)
                    call.respond(HttpNoContent)
                } catch (e: EntityNotFoundError) {
                    throw NotFoundException(e.message)
                }
            }
        }
    }
}

// DTOs
data class CreateInputDto(val name: String, val description: String = "")
data class UpdateInputDto(val name: String, val description: String)
data class ExampleDto(
    val id: String,
    val name: String,
    val description: String,
    val status: String,
    val createdAt: String,
    val updatedAt: String
)
data class HttpOk<T>(val data: T)
data class HttpCreated<T>(val data: T)
object HttpNoContent
data class HttpList<T>(val data: List<T>)

fun com.phenotype.domain.model.ExampleEntity.toDto() = ExampleDto(
    id = id,
    name = name,
    description = description,
    status = status.name,
    createdAt = createdAt.toString(),
    updatedAt = updatedAt.toString()
)
