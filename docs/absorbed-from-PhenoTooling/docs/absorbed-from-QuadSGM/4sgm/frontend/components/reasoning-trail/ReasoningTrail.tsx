'use client'

import React, { useState, useEffect, useRef } from 'react'
import { ReasoningStep } from './ReasoningStep'
import { WidgetRenderer } from './WidgetRenderer'

export interface SSEEvent {
  type: string
  timestamp: string
  [key: string]: unknown
}

export interface AgentReasoningEvent extends SSEEvent {
  type: 'agent_reasoning'
  subject: string
  reasoning: string
  stage: string
  phase: string
  confidence: number
  options_considered?: Array<{
    option: string
    pros?: string[]
    cons?: string[]
    score: number
    selected?: boolean
  }>
  decision: string
  citations?: string[]
}

export interface WidgetEvent extends SSEEvent {
  type: 'widget'
  widget_type: string
  placement?: string
  props: Record<string, unknown>
  markdown?: string
}

interface ReasoningTrailProps {
  sessionId: string
  className?: string
}

/**
 * ReasoningTrail - Main component for displaying agent reasoning
 * Listens to SSE stream and renders reasoning events + widgets
 */
export function ReasoningTrail({ sessionId, className = '' }: ReasoningTrailProps) {
  const [events, setEvents] = useState<SSEEvent[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    // Auto-scroll to bottom as new events arrive
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [events])

  useEffect(() => {
    let eventSource: EventSource | null = null

    try {
      // Connect to chat SSE endpoint
      eventSource = new EventSource(`/api/chat/stream?session_id=${sessionId}`)

      eventSource.onopen = () => {
        setIsConnected(true)
        setError(null)
      }

      eventSource.onmessage = (event) => {
        try {
          const eventData = String(event.data)
          const parsedData: unknown = JSON.parse(eventData)
          // Validate the parsed data has required SSEEvent properties
          if (
            parsedData &&
            typeof parsedData === 'object' &&
            'type' in parsedData &&
            'timestamp' in parsedData
          ) {
            setEvents((prev) => [...prev, parsedData as SSEEvent])
          }
        } catch (e) {
          console.error('Failed to parse SSE event', e)
        }
      }

      eventSource.onerror = (error) => {
        setIsConnected(false)
        setError('Connection lost')
        console.error('SSE error', error)
        eventSource?.close()
      }
    } catch (e) {
      setError('Failed to connect to chat stream')
      console.error('Connection error', e)
    }

    return () => {
      eventSource?.close()
    }
  }, [sessionId])

  return (
    <div className={`flex flex-col h-full ${className}`}>
      {/* Header */}
      <div className="border-b border-gray-200 bg-white px-4 py-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-gray-900">Agent Reasoning Trail</h2>
          <div className="flex items-center gap-2">
            <div
              className={`w-3 h-3 rounded-full ${
                isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'
              }`}
            />
            <span className="text-sm text-gray-600">
              {isConnected ? 'Live' : 'Disconnected'}
            </span>
          </div>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="bg-red-50 border-b border-red-200 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Events scroll area */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto bg-gradient-to-b from-slate-50 to-white"
      >
        {events.length === 0 ? (
          <div className="flex items-center justify-center h-full text-gray-500">
            <div className="text-center">
              <p className="text-lg font-medium mb-1">Waiting for agent reasoning...</p>
              <p className="text-sm text-gray-400">Events will appear here as they stream</p>
            </div>
          </div>
        ) : (
          <div className="space-y-4 p-4">
            {events.map((event, idx) => (
              <div key={idx}>
                {event.type === 'agent_reasoning' && (
                  <ReasoningStep event={event as AgentReasoningEvent} />
                )}
                {event.type === 'widget' && (
                  <WidgetRenderer event={event as WidgetEvent} />
                )}
                {event.type === 'research' && (
                  <div className="p-4 bg-white rounded-lg border border-gray-200">
                    <h4 className="font-bold text-gray-900">{typeof event.heading === 'string' ? event.heading : ''}</h4>
                    <p className="text-sm text-gray-700 mt-2">{typeof event.details === 'string' ? event.details : ''}</p>
                  </div>
                )}
                {event.type === 'token' && event.data && (
                  <div className="p-4 bg-white rounded-lg border border-gray-200">
                    <p className="text-gray-900">{typeof event.data === 'string' ? event.data : ''}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer - event count */}
      <div className="border-t border-gray-200 bg-white px-4 py-2 text-xs text-gray-500">
        {events.length} event{events.length !== 1 ? 's' : ''} received
      </div>
    </div>
  )
}
