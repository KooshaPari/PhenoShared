import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000'

interface SessionResponse {
  sessionId?: string
  user?: Record<string, unknown>
  cart?: Record<string, unknown>
  [key: string]: unknown
}

function isSessionResponse(data: unknown): data is SessionResponse {
  return typeof data === 'object' && data !== null
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ sessionId: string }> }
) {
  try {
    const { sessionId } = await params

    const authHeader = request.headers.get('authorization')

    // Proxy to backend session API
    const response = await fetch(`${BACKEND_URL}/api/session/${sessionId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...(authHeader ? { 'Authorization': authHeader } : {}),
      },
    })

    if (!response.ok) {
      const error = await response.text()
      console.error('Backend session API error:', response.status, error)
      return NextResponse.json(
        { error: 'Session not found or unavailable' },
        { status: response.status }
      )
    }

    const jsonData: unknown = await response.json()
    if (!isSessionResponse(jsonData)) {
      return NextResponse.json(
        { error: 'Invalid response format' },
        { status: 500 }
      )
    }
    return NextResponse.json(jsonData)
  } catch (error) {
    console.error('Session API route error:', error)
    const errorMessage = error instanceof Error ? error.message : "Unknown error"
    return NextResponse.json(
      { error: 'Internal server error', details: errorMessage },
      { status: 500 }
    )
  }
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ sessionId: string }> }
) {
  try {
    const { sessionId } = await params
    const body: unknown = await request.json()

    const authHeader = request.headers.get('authorization')

    // Proxy to backend session API
    const response = await fetch(`${BACKEND_URL}/api/session/${sessionId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...(authHeader ? { 'Authorization': authHeader } : {}),
      },
      body: JSON.stringify(body),
    })

    if (!response.ok) {
      const error = await response.text()
      console.error('Backend session update error:', response.status, error)
      return NextResponse.json(
        { error: 'Failed to update session' },
        { status: response.status }
      )
    }

    const jsonData: unknown = await response.json()
    if (!isSessionResponse(jsonData)) {
      return NextResponse.json(
        { error: 'Invalid response format' },
        { status: 500 }
      )
    }
    return NextResponse.json(jsonData)
  } catch (error) {
    console.error('Session update API route error:', error)
    const errorMessage = error instanceof Error ? error.message : "Unknown error"
    return NextResponse.json(
      { error: 'Internal server error', details: errorMessage },
      { status: 500 }
    )
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ sessionId: string }> }
) {
  try {
    const { sessionId } = await params

    const authHeader = request.headers.get('authorization')

    // Proxy to backend session API
    const response = await fetch(`${BACKEND_URL}/api/session/${sessionId}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        ...(authHeader ? { 'Authorization': authHeader } : {}),
      },
    })

    if (!response.ok) {
      const error = await response.text()
      console.error('Backend session delete error:', response.status, error)
      return NextResponse.json(
        { error: 'Failed to delete session' },
        { status: response.status }
      )
    }

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Session delete API route error:', error)
    const errorMessage = error instanceof Error ? error.message : "Unknown error"
    return NextResponse.json(
      { error: 'Internal server error', details: errorMessage },
      { status: 500 }
    )
  }
}
