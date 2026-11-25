package com.phenotype.config

import com.phenotype.adapters.persistence.InMemoryRepository
import com.phenotype.application.ExampleService
import com.phenotype.domain.ports.outbound.Repository
import org.koin.dsl.module
import org.koin.core.context.startKoin

/**
 * Koin dependency injection modules
 */
val appModule = module {
    // Repository
    single<Repository> { InMemoryRepository() }

    // Services
    single { ExampleService(get()) }
}

/**
 * Initialize Koin DI container
 */
fun initKoin() = startKoin {
    modules(appModule)
}
