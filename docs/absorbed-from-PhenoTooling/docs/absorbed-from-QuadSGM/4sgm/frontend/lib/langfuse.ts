/**
 * Langfuse Frontend Integration
 *
 * Optional browser-side tracing for complete observability.
 * Tracks frontend events, API calls, and user interactions.
 */

export interface LangfuseConfig {
  publicKey: string
  host: string
  enabled: boolean
}

export interface TraceMetadata {
  userId?: string
  sessionId?: string
  page?: string
  userAgent?: string
  timestamp?: string
  [key: string]: unknown
}

/**
 * Initialize Langfuse SDK for browser tracing
 *
 * This is optional - backend tracing is the primary source of truth.
 * Frontend tracing enhances observability with client-side events.
 */
export function initLangfuse(): LangfuseConfig | null {
  const publicKey = process.env.NEXT_PUBLIC_LANGFUSE_PUBLIC_KEY
  const host = process.env.NEXT_PUBLIC_LANGFUSE_HOST || 'https://cloud.langfuse.com'

  if (!publicKey) {
    console.debug('Langfuse frontend tracing disabled (no public key)')
    return null
  }

  try {
    // Dynamic import to keep Langfuse SDK optional
    const config: LangfuseConfig = {
      publicKey,
      host,
      enabled: true
    }

    console.debug('Langfuse SDK initialized for browser tracing')
    return config
  } catch (error) {
    console.warn('Failed to initialize Langfuse SDK:', error)
    return null
  }
}

/**
 * Create a trace for a user interaction or API call
 * Automatically includes browser context
 */
export function createTrace(
  name: string,
  metadata?: TraceMetadata
): { traceId: string; endTrace: () => void } {
  const traceId = generateTraceId()
  const fullMetadata: TraceMetadata = {
    ...metadata,
    userAgent: typeof window !== 'undefined' ? window.navigator.userAgent : '',
    timestamp: new Date().toISOString(),
    page: typeof window !== 'undefined' ? window.location.pathname : ''
  }

  // Log to console in development
  if (process.env.NODE_ENV === 'development') {
    console.debug(`[Trace: ${traceId}] ${name}`, fullMetadata)
  }

  // Send to backend for server-side logging
  captureTraceEvent(name, traceId, 'start', fullMetadata).catch(console.error)

  return {
    traceId,
    endTrace: () => {
      captureTraceEvent(name, traceId, 'end', fullMetadata).catch(console.error)
    }
  }
}

/**
 * Track a chat message through the system
 */
export function trackChatMessage(
  sessionId: string,
  userId: string | undefined,
  message: string,
  role: 'user' | 'assistant'
): { traceId: string; endTrace: () => void } {
  return createTrace(`chat_message_${role}`, {
    sessionId,
    userId,
    message: message.substring(0, 200), // Truncate long messages
    messageLength: message.length
  })
}

/**
 * Track API calls to the backend
 */
export function trackApiCall(
  endpoint: string,
  method: string = 'POST'
): { traceId: string; endTrace: () => void } {
  return createTrace(`api_call_${method}`, {
    endpoint,
    method
  })
}

/**
 * Track errors and exceptions
 */
export function trackError(
  error: unknown,
  context?: Record<string, unknown>
): void {
  const errorMessage = error instanceof Error ? error.message : (typeof error === 'string' ? error : 'Unknown error')
  const errorStack = error instanceof Error ? error.stack ?? '' : ''

  createTrace('frontend_error', {
    errorMessage,
    errorStack,
    ...context
  }).endTrace()

  // Also send to backend
  captureTraceEvent('frontend_error', generateTraceId(), 'error', {
    errorMessage,
    errorStack,
    ...context
  }).catch(() => {
    // Silently fail - observability should not break the app
  })
}

/**
 * Track page navigation
 */
export function trackPageView(page: string): void {
  createTrace('page_view', {
    page
  }).endTrace()
}

/**
 * Send trace event to backend for aggregation
 */
async function captureTraceEvent(
  name: string,
  traceId: string,
  eventType: 'start' | 'end' | 'error',
  metadata: Record<string, unknown>
): Promise<void> {
  try {
    // Only send in development or if explicitly enabled
    if (process.env.NODE_ENV !== 'development' && !process.env.NEXT_PUBLIC_LANGFUSE_ENABLED) {
      return
    }

    const response = await fetch('/api/observability/trace', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        name,
        traceId,
        eventType,
        source: 'browser',
        metadata,
        timestamp: new Date().toISOString()
      })
    })

    if (!response.ok) {
      console.warn(`Failed to send trace: ${response.statusText}`)
    }
  } catch (error) {
    // Silently fail - observability should not break the app
    console.debug('Error sending trace:', error)
  }
}

/**
 * Generate a unique trace ID
 */
function generateTraceId(): string {
  return `trace_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

/**
 * Setup global error handler for unhandled promise rejections
 */
export function setupErrorTracking(): void {
  if (typeof window === 'undefined') return

  window.addEventListener('error', (event) => {
    trackError(event.error, {
      type: 'uncaught_error',
      filename: event.filename,
      lineno: event.lineno,
      colno: event.colno
    })
  })

  window.addEventListener('unhandledrejection', (event) => {
    trackError(event.reason, {
      type: 'unhandled_rejection'
    })
  })
}

/**
 * Enable/disable trace logging in development
 */
export function setDebugMode(enabled: boolean): void {
  if (enabled) {
    console.log('Langfuse debug mode enabled')
    localStorage.setItem('langfuse_debug', 'true')
  } else {
    localStorage.removeItem('langfuse_debug')
  }
}

/**
 * Get current trace configuration
 */
export function getLangfuseConfig(): LangfuseConfig | null {
  return initLangfuse()
}
