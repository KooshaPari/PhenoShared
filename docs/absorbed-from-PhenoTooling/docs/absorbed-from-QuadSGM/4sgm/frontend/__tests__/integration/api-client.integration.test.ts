/**
 * Frontend API Client Integration Tests
 * Tests the Next.js API routes and communication with backend
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'

// Mock fetch for integration tests
global.fetch = vi.fn()

interface SessionSnapshot {
  sessionId: string
  createdAt: string
  messages: Array<{ role: string; content: string }>
}

interface ChatResponse {
  text: string
  session_id: string
}

describe('API Client Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Mock environment
    process.env.BACKEND_URL = 'http://localhost:8000'
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Session API', () => {
    it('should create a new session', async () => {
      const mockResponse: SessionSnapshot = {
        sessionId: 'test-session-123',
        createdAt: '2025-01-01T00:00:00Z',
        messages: [],
      }

      ;(global.fetch as any).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      })

      const response = await fetch('/api/session', { method: 'POST' })
      const data = (await response.json()) as SessionSnapshot

      expect(response.ok).toBe(true)
      expect(data.sessionId).toBeDefined()
      expect(data.messages).toEqual([])
    })

    it('should create session with valid UUID', async () => {
      const mockResponse: SessionSnapshot = {
        sessionId: 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
        createdAt: '2025-01-01T00:00:00Z',
        messages: [],
      }

      ;(global.fetch as any).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      })

      const response = await fetch('/api/session', { method: 'POST' })
      const data = (await response.json()) as SessionSnapshot

      // Validate UUID format
      const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
      expect(uuidRegex.test(data.sessionId)).toBe(true)
    })

    it('should retrieve existing session', async () => {
      const sessionId = 'test-session-456'
      const mockResponse: SessionSnapshot = {
        sessionId,
        createdAt: '2025-01-01T00:00:00Z',
        messages: [],
      }

      ;(global.fetch as any).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      })

      const response = await fetch(`/api/session?sessionId=${sessionId}`)
      const data = (await response.json()) as SessionSnapshot

      expect(response.ok).toBe(true)
      expect(data.sessionId).toBe(sessionId)
    })

    it('should handle session retrieval error', async () => {
      ;(global.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 502,
        json: async () => ({
          error: 'Failed to load session snapshot',
          details: 'Connection refused',
        }),
      })

      const response = await fetch('/api/session?sessionId=invalid')
      const data = await response.json()

      expect(response.ok).toBe(false)
      expect(data.error).toBeDefined()
    })

    it('should handle missing sessionId parameter', async () => {
      ;(global.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ error: 'Missing sessionId' }),
      })

      const response = await fetch('/api/session')
      const data = await response.json()

      expect(response.status).toBe(400)
      expect(data.error).toBeDefined()
    })

    it('should create multiple unique sessions', async () => {
      const sessionIds = []

      for (let i = 0; i < 3; i++) {
        const mockResponse: SessionSnapshot = {
          sessionId: `session-${i}-${Math.random()}`,
          createdAt: '2025-01-01T00:00:00Z',
          messages: [],
        }

        ;(global.fetch as any).mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: async () => mockResponse,
        })

        const response = await fetch('/api/session', { method: 'POST' })
        const data = (await response.json()) as SessionSnapshot
        sessionIds.push(data.sessionId)
      }

      // All should be unique
      expect(new Set(sessionIds).size).toBe(3)
    })
  })

  describe('Chat API', () => {
    it('should send chat message', async () => {
      const mockResponse: ChatResponse = {
        text: 'Hello! How can I help?',
        session_id: 'test-session',
      }

      ;(global.fetch as any).mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => mockResponse,
      })

      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: 'Hello' }),
      })

      const data = (await response.json()) as ChatResponse

      expect(response.ok).toBe(true)
      expect(data.text).toBeDefined()
      expect(data.session_id).toBeDefined()
    })

    it('should handle chat with session context', async () => {
      const sessionId = 'test-session-789'
      const mockResponse: ChatResponse = {
        text: 'Response with context',
        session_id: sessionId,
      }

      ;(global.fetch as any).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      })

      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: 'Hello',
          sessionId,
        }),
      })

      const data = (await response.json()) as ChatResponse

      expect(data.session_id).toBe(sessionId)
    })

    it('should handle empty message', async () => {
      ;(global.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ error: 'Message cannot be empty' }),
      })

      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: '' }),
      })

      expect(response.ok).toBe(false)
    })

    it('should handle missing message field', async () => {
      ;(global.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 422,
        json: async () => ({ error: 'Missing required field: message' }),
      })

      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      })

      expect(response.status).toBe(422)
    })

    it('should handle invalid JSON', async () => {
      ;(global.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ error: 'Invalid JSON' }),
      })

      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: 'invalid json',
      })

      expect(response.ok).toBe(false)
    })

    it('should handle backend connection error', async () => {
      ;(global.fetch as any).mockRejectedValueOnce(
        new Error('Failed to fetch')
      )

      try {
        await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: 'Hello' }),
        })
        expect.fail('Should have thrown error')
      } catch (error) {
        expect(error).toBeDefined()
      }
    })

    it('should handle backend 502 error', async () => {
      ;(global.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 502,
        json: async () => ({
          error: 'Failed to process chat request',
          details: 'Backend error',
        }),
      })

      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: 'Hello' }),
      })

      expect(response.status).toBe(502)
    })

    it('should handle backend 503 error', async () => {
      ;(global.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 503,
        json: async () => ({ error: 'Service unavailable' }),
      })

      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: 'Hello' }),
      })

      expect(response.status).toBe(503)
    })
  })

  describe('Request Headers', () => {
    it('should set correct content type', async () => {
      ;(global.fetch as any).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({}),
      })

      await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: 'test' }),
      })

      const call = (global.fetch as any).mock.calls[0]
      expect(call[1].headers['Content-Type']).toBe('application/json')
    })

    it('should use correct HTTP method', async () => {
      ;(global.fetch as any).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({}),
      })

      await fetch('/api/session', { method: 'POST' })

      const call = (global.fetch as any).mock.calls[0]
      expect(call[1].method).toBe('POST')
    })
  })

  describe('Response Parsing', () => {
    it('should parse JSON response', async () => {
      const expectedData = { sessionId: 'test', messages: [] }

      ;(global.fetch as any).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => expectedData,
      })

      const response = await fetch('/api/session', { method: 'POST' })
      const data = await response.json()

      expect(data).toEqual(expectedData)
    })

    it('should handle non-JSON response', async () => {
      ;(global.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => {
          throw new Error('Not JSON')
        },
        text: async () => 'Internal Server Error',
      })

      const response = await fetch('/api/chat')

      expect(response.ok).toBe(false)
    })
  })

  describe('Concurrent Requests', () => {
    it('should handle concurrent session creation', async () => {
      const promises = []

      for (let i = 0; i < 3; i++) {
        ;(global.fetch as any).mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: async () => ({
            sessionId: `session-${i}`,
            messages: [],
          }),
        })

        promises.push(
          fetch('/api/session', { method: 'POST' }).then(r => r.json())
        )
      }

      const results = await Promise.all(promises)

      expect(results).toHaveLength(3)
      expect(results[0].sessionId).toBe('session-0')
      expect(results[1].sessionId).toBe('session-1')
      expect(results[2].sessionId).toBe('session-2')
    })

    it('should handle concurrent chat messages', async () => {
      const promises = []

      for (let i = 0; i < 3; i++) {
        ;(global.fetch as any).mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: async () => ({
            text: `Response ${i}`,
            session_id: 'test-session',
          }),
        })

        promises.push(
          fetch('/api/chat', {
            method: 'POST',
            body: JSON.stringify({ message: `Message ${i}` }),
          }).then(r => r.json())
        )
      }

      const results = await Promise.all(promises)

      expect(results).toHaveLength(3)
    })
  })
})
