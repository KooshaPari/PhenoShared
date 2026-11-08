package com.phenotype.mcp

import io.ktor.client.*
import io.ktor.client.engine.cio.*
import io.ktor.client.plugins.contentnegotiation.*
import io.ktor.client.plugins.logging.*
import io.ktor.client.request.*
import io.ktor.http.*
import io.ktor.serialization.kotlinx.json.*
import kotlinx.serialization.*
import kotlinx.serialization.json.*

/**
 * Real Ktor-based MCP client with actual HTTP
 */
class KtorMcpClient(private val endpoint: String) {
    private val client = HttpClient(CIO) {
        install(ContentNegotiation) {
            json(Json { ignoreUnknownKeys = true; isLenient = true })
        }
        install(Logging) { logger = Logger.DEFAULT; level = LogLevel.INFO }
        install(HttpTimeout) { requestTimeoutMillis = 60000 }
    }

    @Serializable data class JsonRpcRequest(val jsonrpc: String="2.0", val id: String, val method: String, val params: Map<String, @Serializable Value>?=null)
    @Serializable data class JsonRpcResponse<T>(val jsonrpc: String, val id: String?, val result: T?, val error: JsonRpcError?)
    @Serializable data class JsonRpcError(val code: Int, val message: String)
    @Serializable data class ServerInfo(val name: String, val version: String)
    @Serializable data class ToolInfo(val name: String, val description: String)

    suspend fun initialize(): ServerInfo {
        val req = JsonRpcRequest(id=java.util.UUID.randomUUID().toString(), method="initialize",
            params=mapOf("protocolVersion" to "2024-11-05".jsonPrimitive, "capabilities" to JsonPrimitive("{}".jsonPrimitive)))
        val resp = client.post(endpoint) { contentType(ContentType.Application.Json); setBody(req) }
        val body = resp.bodyAsText()
        val json = Json.parseToJsonElement(body).jsonObject
        return Json.decodeFromJsonElement(json["result"]!!.jsonObject)
    }

    suspend fun listTools(): List<ToolInfo> {
        val req = JsonRpcRequest(id=java.util.UUID.randomUUID().toString(), method="tools/list")
        val resp = client.post(endpoint) { contentType(ContentType.Application.Json); setBody(req) }
        val body = resp.bodyAsText()
        val json = Json.parseToJsonElement(body).jsonObject
        return Json.decodeFromJsonElement(json["result"]!!.jsonObject)
    }

    fun close() { client.close() }
}
