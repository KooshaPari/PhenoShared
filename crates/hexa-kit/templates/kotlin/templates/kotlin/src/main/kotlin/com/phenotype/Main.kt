package com.phenotype

import com.phenotype.adapters.http.configureRouting
import com.phenotype.adapters.persistence.InMemoryRepository
import com.phenotype.application.ExampleService
import io.ktor.server.engine.embeddedServer
import io.ktor.server.cio.CIO

fun main() {
    // Initialize dependencies
    val repository = InMemoryRepository()
    val service = ExampleService(repository)

    // Start server
    val server = embeddedServer(CIO, port = 8080) {
        configureRouting(service)
    }

    println("Starting server on :8080")
    server.start(wait = true)
}
