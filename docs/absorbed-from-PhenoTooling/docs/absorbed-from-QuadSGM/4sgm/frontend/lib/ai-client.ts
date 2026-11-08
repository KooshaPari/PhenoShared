/**
 * Vercel AI SDK v6 Client Configuration
 * Multi-provider LLM support with streaming
 * Phase 5-6: Advanced features (multi-step tools, reranking, multi-modal)
 */

import { createAnthropic } from "@ai-sdk/anthropic"
import { createOpenAI } from "@ai-sdk/openai"

/**
 * Initialize Anthropic client (Claude)
 * Primary LLM for RAG and reasoning
 */
export const anthropic = createAnthropic({
  apiKey: process.env.NEXT_PUBLIC_ANTHROPIC_API_KEY,
  baseURL: process.env.NEXT_PUBLIC_ANTHROPIC_BASE_URL,
})

/**
 * Initialize OpenAI client (fallback + embeddings)
 * Secondary LLM and embeddings generation
 */
export const openai = createOpenAI({
  apiKey: process.env.NEXT_PUBLIC_OPENROUTER_API_KEY,
  baseURL: process.env.NEXT_PUBLIC_OPENROUTER_BASE_URL,
})

/**
 * Model selection strategy
 * Phase 5: Multi-step tool calling support
 */
export const modelConfig = {
  // Primary model for complex reasoning
  primary: "claude-3-5-sonnet-20241022",
  // Fast model for simple queries
  fast: "claude-3-haiku-20240307",
  // Fallback model
  fallback: "claude-3-5-sonnet-20241022",
}

/**
 * Get optimal model for current request
 * Phase 5: Multi-step tool calling support
 */
export function getOptimalModel(
  useAdvancedFeatures: boolean = false,
  queryComplexity: "simple" | "moderate" | "complex" = "moderate"
) {
  // Use fast model for simple queries
  if (queryComplexity === "simple" && !useAdvancedFeatures) {
    return anthropic(modelConfig.fast)
  }

  // Use primary model for advanced features or complex queries
  if (useAdvancedFeatures || queryComplexity === "complex") {
    return anthropic(modelConfig.primary)
  }

  // Default to primary model
  return anthropic(modelConfig.primary)
}

/**
 * Chat client configuration
 * Supports streaming, tool calling, and structured outputs
 */
export const chatConfig = {
  // Model selection
  model: anthropic("claude-3-5-sonnet-20241022"),

  // Streaming settings
  temperature: 0.7,
  maxTokens: 1024,
  topP: 0.9,

  // Safety settings
  system: `You are a helpful customer support AI assistant for 4SGM.
Your role is to answer customer questions about products, shipping, returns, and policies.
Always be helpful, accurate, and professional.
If you're unsure about something, be honest and offer to escalate to a human representative.`,

  // Tools configuration (Phase 5: multi-step tool calling)
  tools: {
    // Tool 1: Search knowledge base
    searchKnowledgeBase: {
      description: "Search the knowledge base for relevant information",
      parameters: {
        type: "object",
        properties: {
          query: {
            type: "string",
            description: "Search query to find relevant documents",
          },
          topK: {
            type: "number",
            description: "Number of results to return (default: 5)",
            default: 5,
          },
        },
        required: ["query"],
      },
    },

    // Tool 2: Get shipping information
    getShippingInfo: {
      description: "Get shipping information for a destination",
      parameters: {
        type: "object",
        properties: {
          destination: {
            type: "string",
            description: "Destination country or region",
          },
          weight: {
            type: "number",
            description: "Package weight in kg (optional)",
          },
        },
        required: ["destination"],
      },
    },

    // Tool 3: Check return policy
    getReturnPolicy: {
      description: "Get return policy information",
      parameters: {
        type: "object",
        properties: {
          category: {
            type: "string",
            description: "Product category (optional)",
          },
        },
      },
    },

    // Tool 4: Get bulk pricing (Phase 7: Wholesale)
    getBulkPricing: {
      description: "Get bulk pricing for wholesale customers",
      parameters: {
        type: "object",
        properties: {
          sku: {
            type: "string",
            description: "Product SKU",
          },
          quantity: {
            type: "number",
            description: "Order quantity",
          },
          customerTier: {
            type: "string",
            enum: ["retail", "wholesale", "distributor"],
            description: "Customer tier for pricing",
          },
        },
        required: ["sku", "quantity"],
      },
    },

    // Tool 5: Check inventory (Phase 7: Wholesale)
    checkInventory: {
      description: "Check product inventory availability",
      parameters: {
        type: "object",
        properties: {
          sku: {
            type: "string",
            description: "Product SKU",
          },
          quantity: {
            type: "number",
            description: "Requested quantity",
          },
          warehouse: {
            type: "string",
            description: "Preferred warehouse (optional)",
          },
        },
        required: ["sku", "quantity"],
      },
    },

    // Tool 6: Escalate to human (Phase 5-6)
    escalateToHuman: {
      description: "Escalate conversation to human support representative",
      parameters: {
        type: "object",
        properties: {
          reason: {
            type: "string",
            description: "Reason for escalation",
          },
          context: {
            type: "string",
            description: "Conversation context for human",
          },
        },
        required: ["reason"],
      },
    },
  },

  // Multi-step tool calling (Phase 5)
  // stopWhen can be configured per request
  // Example: stopWhen: stepCountIs(5) for up to 5 tool calls
}

/**
 * Supported LLM models with capabilities
 * Phase 5: Multi-modal support
 */
export const supportedModels = {
  claude35Sonnet: {
    id: "claude-3-5-sonnet-20241022",
    name: "Claude 3.5 Sonnet",
    provider: "anthropic",
    capabilities: ["streaming", "tools", "vision", "json"],
    maxTokens: 200000,
    costPer1kTokens: { input: 0.003, output: 0.015 },
  },
  claude3Opus: {
    id: "claude-3-opus-20240229",
    name: "Claude 3 Opus",
    provider: "anthropic",
    capabilities: ["streaming", "tools", "vision"],
    maxTokens: 200000,
    costPer1kTokens: { input: 0.015, output: 0.075 },
  },
  gpt4o: {
    id: "gpt-4o",
    name: "GPT-4 Omni",
    provider: "openai",
    capabilities: ["streaming", "tools", "vision", "json"],
    maxTokens: 128000,
    costPer1kTokens: { input: 0.005, output: 0.015 },
  },
  gpt4Turbo: {
    id: "gpt-4-turbo",
    name: "GPT-4 Turbo",
    provider: "openai",
    capabilities: ["streaming", "tools", "vision"],
    maxTokens: 128000,
    costPer1kTokens: { input: 0.01, output: 0.03 },
  },
}

/**
 * Phase 5: Tool handlers for client-side processing
 * These mirror backend MCP tools
 */

interface SearchResult {
  id: string;
  title: string;
  content: string;
  category: string;
  similarity: number;
}

export interface SearchKnowledgeBaseResult {
  error?: string;
  results: SearchResult[];
  [key: string]: unknown;
}

export interface ShippingInfoResult {
  error?: string;
  destination?: string;
  methods?: Array<{
    name: string;
    days: number;
    cost: number;
    currency: string;
  }>;
  [key: string]: unknown;
}

export interface ReturnPolicyResult {
  error?: string;
  days?: number;
  conditions?: string[];
  refundMethod?: string;
  restockingFee?: number;
  [key: string]: unknown;
}

export interface EscalationResult {
  error?: string;
  ticketId: string | null;
  [key: string]: unknown;
}

export interface BulkPricingResult {
  error?: string;
  sku?: string;
  quantity?: number;
  tier?: string;
  unitPrice?: number;
  totalPrice?: number;
  currency?: string;
  discount?: number;
  [key: string]: unknown;
}

export interface InventoryResult {
  error?: string;
  sku?: string;
  available?: number;
  warehouse?: string;
  inStock?: boolean;
  estimatedRestock?: string;
  [key: string]: unknown;
}

export const toolHandlers = {
  async searchKnowledgeBase(query: string, topK: number = 5): Promise<SearchKnowledgeBaseResult> {
    try {
      const response = await fetch("/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, topK }),
      })

      if (!response.ok) throw new Error("Search failed")
      return await response.json() as SearchKnowledgeBaseResult
    } catch (error) {
      console.error("Search error:", error)
      return { error: String(error), results: [] }
    }
  },

  async getShippingInfo(destination: string, weight?: number): Promise<ShippingInfoResult> {
    try {
      const response = await fetch("/api/shipping", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ destination, weight }),
      })

      if (!response.ok) throw new Error("Shipping lookup failed")
      return await response.json() as ShippingInfoResult
    } catch (error) {
      console.error("Shipping error:", error)
      return { error: String(error) }
    }
  },

  async getReturnPolicy(category?: string): Promise<ReturnPolicyResult> {
    try {
      const response = await fetch("/api/returns", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ category }),
      })

      if (!response.ok) throw new Error("Return policy lookup failed")
      return await response.json() as ReturnPolicyResult
    } catch (error) {
      console.error("Return policy error:", error)
      return { error: String(error) }
    }
  },

  async escalateToHuman(reason: string, context: string): Promise<EscalationResult> {
    try {
      const response = await fetch("/api/escalate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason, context }),
      })

      if (!response.ok) throw new Error("Escalation failed")
      return await response.json() as EscalationResult
    } catch (error) {
      console.error("Escalation error:", error)
      return { error: String(error), ticketId: null }
    }
  },

  async getBulkPricing(sku: string, quantity: number, customerTier?: string): Promise<BulkPricingResult> {
    try {
      const response = await fetch("/api/pricing", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sku, quantity, customerTier }),
      })

      if (!response.ok) throw new Error("Bulk pricing lookup failed")
      return await response.json() as BulkPricingResult
    } catch (error) {
      console.error("Bulk pricing error:", error)
      return { error: String(error) }
    }
  },

  async checkInventory(sku: string, quantity: number, warehouse?: string): Promise<InventoryResult> {
    try {
      const response = await fetch("/api/inventory", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sku, quantity, warehouse }),
      })

      if (!response.ok) throw new Error("Inventory check failed")
      return await response.json() as InventoryResult
    } catch (error) {
      console.error("Inventory error:", error)
      return { error: String(error) }
    }
  },
}

/**
 * Phase 5: Structured output schemas using Zod
 * For type-safe tool responses
 */
import { z } from "zod"

export const SearchResultsSchema = z.object({
  results: z.array(
    z.object({
      id: z.string(),
      title: z.string(),
      content: z.string(),
      category: z.string(),
      similarity: z.number(),
    })
  ),
  total: z.number(),
  query: z.string(),
})

export const ShippingInfoSchema = z.object({
  destination: z.string(),
  methods: z.array(
    z.object({
      name: z.string(),
      days: z.number(),
      cost: z.number(),
      currency: z.string(),
    })
  ),
  estimatedDelivery: z.string().optional(),
})

export const ReturnPolicySchema = z.object({
  days: z.number(),
  conditions: z.array(z.string()),
  refundMethod: z.string(),
  restockingFee: z.number().optional(),
})

export const EscalationSchema = z.object({
  ticketId: z.string(),
  status: z.string(),
  estimatedWaitTime: z.number(),
  message: z.string(),
})
