/**
 * Chat API Route Handler
 * Next.js App Router with Vercel AI SDK v6
 * Phase 5-6: Multi-step tools, streaming, structured outputs
 */

import { streamText } from "ai"
import { anthropic } from "@/lib/ai-client"
import { NextResponse } from 'next/server'

interface ChatRequest {
  message: string
  conversationHistory?: Array<{ role: string; content: string }>
  sessionId?: string
  useHybridSearch?: boolean
  enableReranking?: boolean
  enableCaching?: boolean
  mediaFiles?: Array<{ filename: string; mimeType: string; data: string }>
}

/**
 * POST /api/chat
 * Streaming with Vercel AI SDK v6 using direct LLM calls
 */
export async function POST(request: Request) {
  try {
    const body = await request.json() as ChatRequest
    const { message, conversationHistory = [] } = body

    // Use direct streaming with the LLM (v6 approach - streamText is synchronous)
    const result = streamText({
      model: anthropic("claude-3-5-sonnet-20241022"),
      system: `You are a helpful customer support AI assistant for 4SGM.
Your role is to answer customer questions about products, shipping, returns, and policies.

Always be helpful, accurate, and professional.
When you need information, use the available tools to search the knowledge base.
If you find multiple relevant documents, cite them in your response.
If you're unsure or unable to help, offer to escalate to a human representative.

Guidelines:
- Use tools to find accurate information
- Cite your sources
- Be concise but thorough
- If confidence is low (<0.6), recommend escalation
- For complex issues, use multiple tools if needed`,
      messages: [
        ...conversationHistory.map((m) => ({
          role: m.role as "user" | "assistant",
          content: m.content,
        })),
        { role: "user", content: message },
      ],
      temperature: 0.7,
    })

    // Return streaming response
    return result.toTextStreamResponse()
  } catch (err) {
    console.error("Chat API error:", err)
    const errorMessage = err instanceof Error ? err.message : "Unknown error"
    return NextResponse.json(
      { error: "Failed to process chat request", details: errorMessage },
      { status: 500 }
    )
  }
}
