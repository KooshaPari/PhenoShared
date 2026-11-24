plugins {
    kotlin("jvm") version "2.0.0"
    id("io.ktor.server.ktor-jvm") version "2.3.7" apply false
}

group = "com.phenotype"
version = "0.1.0"

repositories {
    mavenCentral()
}

subprojects {
    apply(plugin = "kotlin")

    repositories {
        mavenCentral()
    }

    dependencies {
        implementation("org.jetbrains.kotlin:kotlin-stdlib")
        testImplementation("org.jetbrains.kotlin:kotlin-test")
    }
}

allprojects {
    tasks.withType<org.jetbrains.kotlin.gradle.tasks.KotlinCompile>().configureEach {
        kotlinOptions {
            jvmTarget = "21"
            freeCompilerArgs = listOf("-Xjsr305=strict")
        }
    }
}
