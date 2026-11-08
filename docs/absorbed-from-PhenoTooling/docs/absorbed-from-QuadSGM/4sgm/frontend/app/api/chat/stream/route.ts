/**
 * Streaming Chat Endpoint
 * Proxies streaming requests from frontend to backend /stream-chat endpoint
 * Uses Server-Sent Events (SSE) for real-time token delivery
 *
 * Flow:
 * 1. Receive SSE request from frontend
 * 2. Extract message, sessionId, history from query parameters
 * 3. Forward to backend /stream-chat endpoint
 * 4. Proxy SSE stream back to frontend
 * 5. Handle errors gracefully
 */

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';
const BACKEND_RETRY_ATTEMPTS = Math.max(
  1,
  Number.parseInt(process.env.BACKEND_RETRY_ATTEMPTS || '3', 10)
);
const BACKEND_RETRY_DELAY_MS = Math.max(
  100,
  Number.parseInt(process.env.BACKEND_RETRY_DELAY_MS || '500', 10)
);

const sleep = (ms: number) =>
  new Promise((resolve) => setTimeout(resolve, ms));

async function fetchBackendWithRetry(url: URL, init: RequestInit): Promise<Response> {
  let attempt = 0;
  let lastError: unknown;

  while (attempt < BACKEND_RETRY_ATTEMPTS) {
    try {
      if (attempt > 0) {
        console.warn(
          `[API Stream] Retry ${attempt + 1}/${BACKEND_RETRY_ATTEMPTS} connecting to backend`
        );
      }

      return await fetch(url.toString(), init);
    } catch (error) {
      lastError = error;
      attempt += 1;

      if (attempt >= BACKEND_RETRY_ATTEMPTS) {
        throw lastError ?? error;
      }

      await sleep(BACKEND_RETRY_DELAY_MS);
    }
  }

  throw lastError ?? new Error('Unknown backend fetch error');
}

// Required for streaming responses in Next.js
export const runtime = 'nodejs';
export const maxDuration = 30; // Allow up to 30 seconds for streaming

/**
 * GET /api/chat/stream
 *
 * Query Parameters:
 *   message (required): User's message
 *   sessionId (optional): Session identifier for conversation tracking
 *   history (optional): JSON string of previous messages
 *
 * Returns:
 *   Server-Sent Events stream with tokens and metadata
 *
 * Example Request:
 *   GET /api/chat/stream?message=Hello&sessionId=session123&history=[]
 *
 * Example Response Events:
 *   - metadata: {type: "metadata", session_id: "...", document_count: ...}
 *   - token: {type: "token", data: "Hello", token_count: 5}
 *   - progress: {type: "progress", character_count: 100, token_count: 25}
 *   - complete: {type: "complete", message: "...", token_count: ..., ...}
 *   - error: {type: "error", message: "Error description"}
 */
export async function GET(request: Request): Promise<Response> {
  try {
    const { searchParams } = new URL(request.url);

    // Extract query parameters
    const message = searchParams.get('message');
    const sessionId = searchParams.get('sessionId') || 'default-' + Date.now();
    const history = searchParams.get('history') || '[]';

    // Validate required parameters
    if (!message) {
      return new Response(
        JSON.stringify({ error: 'Missing required "message" parameter' }),
        {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // Validate JSON in history parameter
    try {
      JSON.parse(history);
    } catch {
      return new Response(
        JSON.stringify({ error: 'Invalid "history" JSON format' }),
        {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // Build backend URL with query parameters
    const backendUrl = new URL(`${BACKEND_URL}/api/stream-chat`);
    backendUrl.searchParams.set('message', message);
    backendUrl.searchParams.set('session_id', sessionId);
    backendUrl.searchParams.set('conversation_history', history);

    console.log(`[API Stream] Connecting to backend: ${backendUrl.toString()}`);

    // Make request to backend streaming endpoint
    const response = await fetchBackendWithRetry(backendUrl, {
      method: 'GET',
      headers: {
        'Accept': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
    });

    // Handle backend errors
    if (!response.ok) {
      const errorText = await response.text();
      console.error(`[API Stream] Backend error (${response.status}): ${errorText}`);

      return new Response(
        JSON.stringify({
          error: `Backend error: ${response.status}`,
          details: errorText,
        }),
        {
          status: response.status,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // Response is successful SSE stream
    if (!response.body) {
      return new Response(
        JSON.stringify({ error: 'Backend returned no response body' }),
        {
          status: 500,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    console.log('[API Stream] Backend connected, proxying SSE stream to client');

    // Create proper SSE response with frontend headers
    return new Response(response.body, {
      status: 200,
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'X-Accel-Buffering': 'no', // Disable buffering in proxies
        'Access-Control-Allow-Origin': '*',
      },
    });
  } catch (error) {
    console.error('[API Stream] Error:', error);

    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    const causeText =
      error instanceof Error && error.cause
        ? typeof error.cause === 'string'
          ? error.cause
          : error.cause instanceof Error
            ? error.cause.message
            : undefined
        : undefined;
    const backendUnavailable =
      errorMessage.includes('fetch failed') ||
      (causeText?.includes('ECONNREFUSED') ?? false);

    if (backendUnavailable) {
      console.error('[API Stream] Backend unreachable at', BACKEND_URL);
    }

    return new Response(
      JSON.stringify({
        error: 'Streaming setup failed',
        message: errorMessage,
        details: backendUnavailable
          ? `Unable to reach backend at ${BACKEND_URL}. Is the FastAPI server running?`
          : undefined,
      }),
      {
        status: backendUnavailable ? 503 : 500,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}

/**
 * OPTIONS request for CORS preflight
 */
export function OPTIONS(): Response {
  return new Response(null, {
    status: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Accept',
    },
  });
}
