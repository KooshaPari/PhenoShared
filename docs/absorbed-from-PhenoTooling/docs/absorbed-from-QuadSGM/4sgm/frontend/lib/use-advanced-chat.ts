/**
 * Advanced Chat Hook (useAdvancedChat)
 * Vercel AI SDK v6 with Phase 5-6 enhancements
 * - Streaming responses
 * - Multi-step tool calling
 * - Structured outputs
 * - Multi-modal support
 * - Error recovery
 */

import { useCallback, useRef, useState } from "react"
import {
  toolHandlers,
  type SearchKnowledgeBaseResult,
  type ShippingInfoResult,
  type ReturnPolicyResult,
  type BulkPricingResult,
  type InventoryResult,
  type EscalationResult,
} from "./ai-client"

export interface Message {
  id: string
  role: "user" | "assistant" | "system"
  content: string
  timestamp: number
  citations?: Array<{
    title: string
    content: string
    similarity: number
  }>
  metadata?: {
    confidence?: number
    requiresEscalation?: boolean
    tokensUsed?: { prompt: number; completion: number }
    responseTimeMs?: number
    reranked?: boolean
  }
}

export interface ToolCall {
  id: string
  name: string
  arguments: Record<string, unknown>
  result?: ToolResult
  status: "pending" | "success" | "error"
}

// Tool result types - union of all possible tool results
export type ToolResult =
  | SearchKnowledgeBaseResult
  | ShippingInfoResult
  | ReturnPolicyResult
  | BulkPricingResult
  | InventoryResult
  | EscalationResult

// Multi-step tool calling result
export interface ToolCallResult {
  toolName: string
  result?: ToolResult
  error?: string
  success: boolean
}

// SSE event data types
export interface SSEMetadataEvent {
  type: "metadata"
  data: Message["metadata"]
}

export interface SSETokenEvent {
  type: "token"
  data: string
}

export interface SSECitationsEvent {
  type: "citations"
  data: Message["citations"]
}

export interface SSEToolCallEvent {
  type: "toolCall"
  name: string
  arguments: Record<string, unknown>
}

export interface SSECompleteEvent {
  type: "complete"
  data: Message["metadata"]
}

export interface SSEErrorEvent {
  type: "error"
  message: string
}

export type SSEEvent =
  | SSEMetadataEvent
  | SSETokenEvent
  | SSECitationsEvent
  | SSEToolCallEvent
  | SSECompleteEvent
  | SSEErrorEvent

// Type guard to validate SSE event structure
function isValidSSEEvent(data: unknown): data is SSEEvent {
  if (!data || typeof data !== "object") return false
  const event = data as { type?: string }
  return (
    event.type === "metadata" ||
    event.type === "token" ||
    event.type === "citations" ||
    event.type === "toolCall" ||
    event.type === "complete" ||
    event.type === "error"
  )
}

export interface UseAdvancedChatOptions {
  apiEndpoint?: string
  systemPrompt?: string
  maxTokens?: number
  temperature?: number
  enableMultiModal?: boolean
  enableReranking?: boolean
  enableCaching?: boolean
  onStatusChange?: (status: "connecting" | "streaming" | "idle" | "error") => void
  onToolCall?: (tool: ToolCall) => void
}

/**
 * Advanced chat hook with all Phase 5-6 features
 * Handles streaming, tool calling, and structured outputs
 */
export function useAdvancedChat(options: UseAdvancedChatOptions = {}) {
  const {
    apiEndpoint = "/api/chat",
    enableMultiModal = true,
    enableReranking = true,
    enableCaching = true,
    onStatusChange,
    onToolCall,
  } = options

  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [toolCalls, setToolCalls] = useState<ToolCall[]>([])
  const abortControllerRef = useRef<AbortController | null>(null)

  /**
   * Process tool call (Phase 5)
   */
  const processToolCall = useCallback(
    async (toolName: string, toolArgs: Record<string, unknown>): Promise<ToolResult> => {
      const toolId = `tool_${Date.now()}`
      const toolCall: ToolCall = {
        id: toolId,
        name: toolName,
        arguments: toolArgs,
        status: "pending",
      }

      setToolCalls((prev) => [...prev, toolCall])
      onToolCall?.(toolCall)

      try {
        let result: ToolResult
        switch (toolName) {
          case "searchKnowledgeBase":
            result = await toolHandlers.searchKnowledgeBase(
              toolArgs.query as string,
              toolArgs.topK as number
            )
            break
          case "getShippingInfo":
            result = await toolHandlers.getShippingInfo(
              toolArgs.destination as string,
              toolArgs.weight as number | undefined
            )
            break
          case "getReturnPolicy":
            result = await toolHandlers.getReturnPolicy(toolArgs.category as string | undefined)
            break
          case "getBulkPricing":
            result = await toolHandlers.getBulkPricing(
              toolArgs.sku as string,
              toolArgs.quantity as number,
              toolArgs.customerTier as string | undefined
            )
            break
          case "checkInventory":
            result = await toolHandlers.checkInventory(
              toolArgs.sku as string,
              toolArgs.quantity as number,
              toolArgs.warehouse as string | undefined
            )
            break
          case "escalateToHuman":
            result = await toolHandlers.escalateToHuman(
              toolArgs.reason as string,
              toolArgs.context as string
            )
            break
          default:
            throw new Error(`Unknown tool: ${toolName}`)
        }

        setToolCalls((prev) =>
          prev.map((tc) =>
            tc.id === toolId
              ? { ...tc, result, status: "success" }
              : tc
          )
        )

        return result
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : String(err)
        const errorResult: ToolResult = { error: errorMsg }
        setToolCalls((prev) =>
          prev.map((tc) =>
            tc.id === toolId
              ? { ...tc, status: "error", result: errorResult }
              : tc
          )
        )
        throw err
      }
    },
    [onToolCall]
  )

  /**
   * Handle multi-step tool calling (Phase 5)
   * Allows model to call multiple tools in sequence
   */
  const handleMultiStepToolCalling = useCallback(
    async (
      toolCalls: Array<{ name: string; arguments: Record<string, unknown> }>
    ): Promise<ToolCallResult[]> => {
      const results: ToolCallResult[] = []

      for (const call of toolCalls) {
        try {
          const result = await processToolCall(call.name, call.arguments)
          results.push({
            toolName: call.name,
            result,
            success: true,
          })
        } catch (err) {
          results.push({
            toolName: call.name,
            error: err instanceof Error ? err.message : String(err),
            success: false,
          })
        }
      }

      return results
    },
    [processToolCall]
  )

  /**
   * Send message and stream response (Phase 2-5)
   */
  const sendMessage = useCallback(
    async (
      userMessage: string,
      attachments?: File[] // Phase 5: multi-modal
    ) => {
      if (!userMessage.trim()) return

      // Create user message
      const userMsg: Message = {
        id: `msg_${Date.now()}`,
        role: "user",
        content: userMessage,
        timestamp: Date.now(),
      }

      setMessages((prev) => [...prev, userMsg])
      setInput("")
      setIsLoading(true)
      setError(null)
      onStatusChange?.("connecting")

      // Cancel previous request if still in progress
      abortControllerRef.current?.abort()
      abortControllerRef.current = new AbortController()

      try {
        // Prepare request body
        const requestBody: Record<string, unknown> = {
          message: userMessage,
          sessionId: `session_${Date.now()}`,
          conversationHistory: messages,
          useHybridSearch: true,
          enableReranking: enableReranking,
          enableCaching: enableCaching,
          clientType: "web",
          clientVersion: "1.0",
        }

        // Phase 5: Add attachments if provided
        if (attachments && enableMultiModal) {
          const mediaFiles = []
          for (const file of attachments) {
            const base64 = await new Promise<string>((resolve) => {
              const reader = new FileReader()
              reader.onload = () => {
                const result = reader.result as string
                resolve(result.split(",")[1])
              }
              reader.readAsDataURL(file)
            })
            mediaFiles.push({
              filename: file.name,
              mimeType: file.type,
              data: base64,
            })
          }
          requestBody.mediaFiles = mediaFiles
        }

        // Stream response
        onStatusChange?.("streaming")

        const response = await fetch(apiEndpoint, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${localStorage.getItem("authToken") || ""}`,
          },
          body: JSON.stringify(requestBody),
          signal: abortControllerRef.current.signal,
        })

        if (!response.ok) {
          throw new Error(`API error: ${response.statusText}`)
        }

        // Handle streaming response
        const reader = response.body?.getReader()
        if (!reader) throw new Error("No response body")

        let assistantContent = ""
        let citations: Message["citations"] = []
        let metadata: Message["metadata"] = {}

        const decoder = new TextDecoder()

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          const chunk = decoder.decode(value)
          const lines = chunk.split("\n")

          for (const line of lines) {
            if (!line.trim()) continue

            // Parse SSE format: data: {...}
            if (line.startsWith("data: ")) {
              try {
                const parsedData: unknown = JSON.parse(line.slice(6))

                if (!isValidSSEEvent(parsedData)) {
                  console.warn("Invalid SSE event format:", parsedData)
                  continue
                }

                const data: SSEEvent = parsedData

                if (data.type === "metadata") {
                  metadata = data.data
                } else if (data.type === "token") {
                  assistantContent += data.data
                  // Update message in real-time
                  setMessages((prev) => {
                    const lastMsg = prev[prev.length - 1]
                    if (lastMsg?.role === "assistant" && lastMsg.id.startsWith("streaming_")) {
                      return [
                        ...prev.slice(0, -1),
                        {
                          ...lastMsg,
                          content: assistantContent,
                        },
                      ]
                    }
                    return prev
                  })
                } else if (data.type === "citations") {
                  citations = data.data
                } else if (data.type === "toolCall") {
                  // Phase 5: Handle tool calls
                  const toolResult = await processToolCall(data.name, data.arguments)
                  console.log(`Tool ${data.name} result:`, toolResult)
                } else if (data.type === "complete") {
                  metadata = { ...metadata, ...data.data }
                } else if (data.type === "error") {
                  throw new Error(data.message)
                }
              } catch (parseError) {
                console.error("Failed to parse SSE data:", parseError)
              }
            }
          }
        }

        // Add final assistant message
        const assistantMsg: Message = {
          id: `msg_${Date.now()}`,
          role: "assistant",
          content: assistantContent,
          timestamp: Date.now(),
          citations: citations.length > 0 ? citations : undefined,
          metadata,
        }

        setMessages((prev) => {
          // Remove streaming message if exists
          const filtered = prev.filter((m) => !m.id.startsWith("streaming_"))
          return [...filtered, assistantMsg]
        })

        onStatusChange?.("idle")
      } catch (err) {
        if (err instanceof Error && err.name === "AbortError") {
          console.log("Request cancelled")
        } else {
          const errorMsg = err instanceof Error ? err.message : String(err)
          setError(errorMsg)
          onStatusChange?.("error")
          console.error("Chat error:", err)
        }
      } finally {
        setIsLoading(false)
      }
    },
    [
      messages,
      apiEndpoint,
      enableReranking,
      enableCaching,
      enableMultiModal,
      onStatusChange,
      processToolCall,
    ]
  )

  /**
   * Cancel ongoing request
   */
  const cancel = useCallback(() => {
    abortControllerRef.current?.abort()
    setIsLoading(false)
    onStatusChange?.("idle")
  }, [onStatusChange])

  /**
   * Clear conversation
   */
  const clear = useCallback(() => {
    setMessages([])
    setInput("")
    setError(null)
    setToolCalls([])
  }, [])

  /**
   * Retry last message
   */
  const retry = useCallback(() => {
    if (messages.length === 0) return

    // Find last user message
    let lastUserMsg: Message | null = null
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === "user") {
        lastUserMsg = messages[i]
        break
      }
    }

    if (lastUserMsg) {
      // Remove assistant message after last user message
      setMessages((prev) => {
        const lastUserIndex = prev.findIndex((m) => m.id === lastUserMsg.id)
        return prev.slice(0, lastUserIndex + 1)
      })

      // Resend
      void sendMessage(lastUserMsg.content)
    }
  }, [messages, sendMessage])

  return {
    messages,
    input,
    setInput,
    isLoading,
    error,
    toolCalls,
    sendMessage,
    cancel,
    clear,
    retry,
    handleMultiStepToolCalling,
  }
}

export type UseAdvancedChatReturn = ReturnType<typeof useAdvancedChat>
