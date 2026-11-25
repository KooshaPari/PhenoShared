/**
 * Advanced Chat Widget Component
 * Vercel AI SDK v6 with Phase 5-6 features
 * - Real-time streaming
 * - Multi-step tool calling
 * - Multi-modal input (images/PDFs)
 * - Citations and sources
 * - Confidence scoring
 * - Human escalation
 */

"use client"

import React, { useEffect, useRef, useState } from "react"
import { useAdvancedChat } from "../lib/use-advanced-chat"
import { MessageCircle, Send, Paperclip, AlertCircle, Zap, ThumbsUp, ThumbsDown } from "lucide-react"

interface AdvancedChatWidgetProps {
  apiEndpoint?: string
  title?: string
  placeholder?: string
  enableMultiModal?: boolean
  enableReranking?: boolean
  theme?: "light" | "dark"
}

export function AdvancedChatWidget({
  apiEndpoint = "/api/chat",
  title = "4SGM AI Assistant",
  placeholder = "Ask about shipping, returns, products...",
  enableMultiModal = true,
  enableReranking = true,
  theme = "light",
}: AdvancedChatWidgetProps) {
  const {
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
  } = useAdvancedChat({
    apiEndpoint,
    enableMultiModal,
    enableReranking,
  })

  const [attachments, setAttachments] = useState<File[]>([])
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  // Handle file selection
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
    const validFiles = files.filter((f) => {
      const isImage = f.type.startsWith("image/")
      const isPdf = f.type === "application/pdf"
      return isImage || isPdf
    })

    if (validFiles.length !== files.length) {
      alert("Only images (JPG, PNG, etc.) and PDFs are supported")
    }

    setAttachments((prev) => [...prev, ...validFiles])
  }

  // Handle send message
  const handleSend = (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return

    void sendMessage(input, attachments)
    setAttachments([])
  }

  // Theme classes
  const bgClass = theme === "dark" ? "bg-gray-900" : "bg-white"
  const textClass = theme === "dark" ? "text-gray-100" : "text-gray-900"
  const borderClass = theme === "dark" ? "border-gray-700" : "border-gray-200"
  const hoverClass = theme === "dark" ? "hover:bg-gray-800" : "hover:bg-gray-50"

  return (
    <div className={`flex flex-col h-[600px] rounded-lg border ${borderClass} ${bgClass} shadow-lg overflow-hidden`}>
      {/* Header */}
      <div className={`flex items-center justify-between p-4 border-b ${borderClass}`}>
        <div className="flex items-center gap-2">
          <MessageCircle className="w-5 h-5 text-blue-500" />
          <h2 className={`text-lg font-semibold ${textClass}`}>{title}</h2>
        </div>
        {messages.length > 0 && (
          <button
            onClick={clear}
            className={`text-sm px-3 py-1 rounded ${hoverClass} transition-colors`}
          >
            Clear
          </button>
        )}
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <MessageCircle className="w-12 h-12 mx-auto mb-2 opacity-30" />
              <p className={`text-sm opacity-50 ${textClass}`}>
                Start a conversation to get help with 4SGM products and services
              </p>
            </div>
          </div>
        )}

        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[80%] rounded-lg p-3 ${
                message.role === "user"
                  ? "bg-blue-500 text-white rounded-br-none"
                  : "bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-bl-none"
              }`}
            >
              {/* Message Content */}
              <p className="whitespace-pre-wrap text-sm leading-relaxed">{message.content}</p>

              {/* Citations (Phase 5) */}
              {message.citations && message.citations.length > 0 && (
                <div className="mt-3 pt-3 border-t border-gray-300 dark:border-gray-600">
                  <p className="text-xs font-semibold mb-2 opacity-70">Sources:</p>
                  <div className="space-y-1">
                    {message.citations.map((citation, i) => (
                      <div key={i} className="text-xs opacity-70">
                        <p className="font-medium">{citation.title}</p>
                        <p className="italic">{citation.content.slice(0, 100)}...</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Metadata (Phase 5) */}
              {message.metadata && (
                <div className="mt-2 pt-2 border-t border-gray-300 dark:border-gray-600 flex items-center gap-2 text-xs opacity-70">
                  {message.metadata.confidence && (
                    <span>
                      Confidence: {(message.metadata.confidence * 100).toFixed(0)}%
                    </span>
                  )}
                  {message.metadata.requiresEscalation && (
                    <span className="flex items-center gap-1 text-orange-500">
                      <AlertCircle className="w-3 h-3" />
                      Escalation recommended
                    </span>
                  )}
                  {message.metadata.reranked && (
                    <span className="flex items-center gap-1 text-blue-500">
                      <Zap className="w-3 h-3" />
                      Reranked
                    </span>
                  )}
                </div>
              )}

              {/* Feedback buttons */}
              {message.role === "assistant" && (
                <div className="mt-2 flex gap-2">
                  <button
                    className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition-colors"
                    title="Helpful"
                  >
                    <ThumbsUp className="w-4 h-4" />
                  </button>
                  <button
                    className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition-colors"
                    title="Not helpful"
                  >
                    <ThumbsDown className="w-4 h-4" />
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Tool Calls (Phase 5) */}
        {toolCalls.length > 0 && (
          <div className="text-xs opacity-70 space-y-1">
            {toolCalls.map((tool) => (
              <div key={tool.id} className="flex items-center gap-2">
                <span className="text-blue-500">→</span>
                <span className="font-mono">{tool.name}({JSON.stringify(tool.arguments)})</span>
                <span
                  className={`px-2 py-0.5 rounded ${
                    tool.status === "pending"
                      ? "bg-yellow-100 text-yellow-800"
                      : tool.status === "success"
                        ? "bg-green-100 text-green-800"
                        : "bg-red-100 text-red-800"
                  }`}
                >
                  {tool.status}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Loading indicator */}
        {isLoading && (
          <div className="flex items-center gap-2 text-sm opacity-70">
            <span className="inline-block w-2 h-2 bg-blue-500 rounded-full animate-bounce"></span>
            <span>AI is thinking...</span>
          </div>
        )}

        {/* Error display */}
        {error && (
          <div className="bg-red-100 dark:bg-red-900 border border-red-300 dark:border-red-700 rounded p-3 text-sm text-red-800 dark:text-red-200">
            <p className="font-semibold flex items-center gap-2 mb-1">
              <AlertCircle className="w-4 h-4" />
              Error
            </p>
            <p>{error}</p>
            {messages.length > 0 && (
              <button
                onClick={retry}
                className="mt-2 text-xs underline hover:no-underline"
              >
                Retry last message
              </button>
            )}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className={`border-t ${borderClass} p-4 space-y-3`}>
        {/* Attachments display */}
        {attachments.length > 0 && (
          <div className="flex gap-2 flex-wrap">
            {attachments.map((file, i) => (
              <div
                key={i}
                className="bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 px-2 py-1 rounded text-xs flex items-center gap-1"
              >
                <Paperclip className="w-3 h-3" />
                {file.name}
                <button
                  onClick={() => setAttachments((prev) => prev.filter((_, idx) => idx !== i))}
                  className="ml-1 hover:opacity-70"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Input form */}
        <form onSubmit={(e) => void handleSend(e)} className="flex gap-2">
          {/* File input button */}
          {enableMultiModal && (
            <>
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept="image/*,.pdf"
                onChange={handleFileSelect}
                className="hidden"
              />
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={isLoading}
                className={`p-2 rounded transition-colors ${hoverClass} disabled:opacity-50`}
                title="Attach image or PDF (Phase 5)"
              >
                <Paperclip className="w-5 h-5" />
              </button>
            </>
          )}

          {/* Message input */}
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={placeholder}
            disabled={isLoading}
            className={`flex-1 px-4 py-2 border rounded-lg outline-none transition-colors ${borderClass} ${
              isLoading ? "opacity-50" : "focus:ring-2 focus:ring-blue-500"
            }`}
          />

          {/* Send/Cancel button */}
          <button
            type={isLoading ? "button" : "submit"}
            onClick={isLoading ? cancel : undefined}
            disabled={!input.trim() && !attachments.length && !isLoading}
            className="p-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 transition-colors"
          >
            <Send className="w-5 h-5" />
          </button>
        </form>
      </div>
    </div>
  )
}

export default AdvancedChatWidget
