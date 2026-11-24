import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import {
  createSession,
  fetchSessionSnapshot,
  postSessionAction,
} from '@/lib/session-api';
import type { SessionSnapshot, SessionActionRequest } from '@/types/session';

describe('session-api', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  const mockSessionSnapshot: SessionSnapshot = {
    sessionId: 'test-session-123',
    user: {
      id: 'user-1',
      name: 'John Doe',
      company: 'ACME Corp',
      tier: 'wholesale',
      accountValue: 50000,
      personaTags: ['bulk-buyer', 'seasonal'],
      email: 'john@acme.com',
      phone: '+1-555-0100',
      assignedRep: 'Rep A',
    },
    knowledgeSignals: [
      { topic: 'shipping', confidence: 0.9, lastTouched: '2024-01-01' },
      { topic: 'returns', confidence: 0.8, lastTouched: '2024-01-02' },
    ],
    cart: {
      id: 'cart-1',
      items: [
        {
          sku: 'SKU-001',
          name: 'Product A',
          quantity: 10,
          unitPrice: 25.0,
          status: 'in_cart',
        },
      ],
      subtotal: 250.0,
      discounts: 0,
      total: 250.0,
      promoCodes: [],
      auditTrail: [],
    },
    activity: {
      pagesViewed: [
        {
          path: '/catalog',
          label: 'Catalog',
          timestamp: '2024-01-01T10:00:00Z',
          dwellSeconds: 30,
        },
      ],
      cartHistory: [],
      currentView: {
        path: '/cart',
        label: 'Shopping Cart',
        since: '2024-01-01T10:30:00Z',
      },
    },
    lastUpdated: '2024-01-01T10:30:00Z',
    capabilities: {
      quickLinks: [{ label: 'Home', path: '/' }],
      availableDiscounts: [],
    },
  };

  describe('createSession', () => {
    it('should create a new session with default params', async () => {
      const mockFetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => mockSessionSnapshot,
      });
      global.fetch = mockFetch;

      const result = await createSession();

      expect(mockFetch).toHaveBeenCalledWith('/api/session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      expect(result).toEqual(mockSessionSnapshot);
    });

    it('should create a session with user tier param', async () => {
      const mockFetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => mockSessionSnapshot,
      });
      global.fetch = mockFetch;

      const result = await createSession({ userTier: 'distributor' });

      expect(mockFetch).toHaveBeenCalledWith('/api/session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userTier: 'distributor' }),
      });
      expect(result).toEqual(mockSessionSnapshot);
    });

    it('should throw error with details when response not ok', async () => {
      const mockFetch = vi.fn().mockResolvedValueOnce({
        ok: false,
        json: async () => ({ details: 'Session creation failed' }),
      });
      global.fetch = mockFetch;

      await expect(createSession()).rejects.toThrow('Session creation failed');
    });

    it('should throw default error when response not ok without details', async () => {
      const mockFetch = vi.fn().mockResolvedValueOnce({
        ok: false,
        json: async () => ({}),
      });
      global.fetch = mockFetch;

      await expect(createSession()).rejects.toThrow('Unable to create session');
    });

    it('should handle fetch network error', async () => {
      const mockFetch = vi.fn().mockRejectedValueOnce(new Error('Network error'));
      global.fetch = mockFetch;

      await expect(createSession()).rejects.toThrow('Network error');
    });
  });

  describe('fetchSessionSnapshot', () => {
    it('should fetch session snapshot by ID', async () => {
      const mockFetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => mockSessionSnapshot,
      });
      global.fetch = mockFetch;

      const result = await fetchSessionSnapshot('test-session-123');

      expect(mockFetch).toHaveBeenCalledWith('/api/session/test-session-123', {
        cache: 'no-store',
      });
      expect(result).toEqual(mockSessionSnapshot);
    });

    it('should encode special characters in session ID', async () => {
      const mockFetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => mockSessionSnapshot,
      });
      global.fetch = mockFetch;

      const sessionId = 'test/session?id=123';
      await fetchSessionSnapshot(sessionId);

      expect(mockFetch).toHaveBeenCalledWith(
        `/api/session/${encodeURIComponent(sessionId)}`,
        { cache: 'no-store' }
      );
    });

    it('should throw error when fetch fails', async () => {
      const mockFetch = vi.fn().mockResolvedValueOnce({
        ok: false,
        json: async () => ({ details: 'Session not found' }),
      });
      global.fetch = mockFetch;

      await expect(fetchSessionSnapshot('invalid-id')).rejects.toThrow('Session not found');
    });

    it('should throw default error when response not ok without details', async () => {
      const mockFetch = vi.fn().mockResolvedValueOnce({
        ok: false,
        json: async () => ({}),
      });
      global.fetch = mockFetch;

      await expect(fetchSessionSnapshot('test-id')).rejects.toThrow(
        'Unable to load session insights'
      );
    });
  });

  describe('postSessionAction', () => {
    it('should post add_cart_item action', async () => {
      const mockFetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => mockSessionSnapshot,
      });
      global.fetch = mockFetch;

      const action: SessionActionRequest = {
        action: 'add_cart_item',
        payload: { sku: 'SKU-001', quantity: 5, name: 'Product A', unitPrice: 25.0 },
      };

      const result = await postSessionAction('test-session-123', action);

      expect(mockFetch).toHaveBeenCalledWith('/api/session/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sessionId: 'test-session-123', action }),
      });
      expect(result).toEqual(mockSessionSnapshot);
    });

    it('should post update_cart_item action', async () => {
      const mockFetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => mockSessionSnapshot,
      });
      global.fetch = mockFetch;

      const action: SessionActionRequest = {
        action: 'update_cart_item',
        payload: { sku: 'SKU-001', quantity: 20 },
      };

      await postSessionAction('test-session-123', action);

      expect(mockFetch).toHaveBeenCalledWith('/api/session/action', expect.any(Object));
    });

    it('should post apply_discount action', async () => {
      const mockFetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => mockSessionSnapshot,
      });
      global.fetch = mockFetch;

      const action: SessionActionRequest = {
        action: 'apply_discount',
        payload: { code: 'SUMMER20' },
      };

      await postSessionAction('test-session-123', action);

      expect(mockFetch).toHaveBeenCalledWith('/api/session/action', expect.any(Object));
    });

    it('should post set_view action', async () => {
      const mockFetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => mockSessionSnapshot,
      });
      global.fetch = mockFetch;

      const action: SessionActionRequest = {
        action: 'set_view',
        payload: { path: '/catalog', label: 'Catalog' },
      };

      await postSessionAction('test-session-123', action);

      expect(mockFetch).toHaveBeenCalledWith('/api/session/action', expect.any(Object));
    });

    it('should throw error when post fails', async () => {
      const mockFetch = vi.fn().mockResolvedValueOnce({
        ok: false,
        json: async () => ({ details: 'Action failed' }),
      });
      global.fetch = mockFetch;

      const action: SessionActionRequest = {
        action: 'add_cart_item',
        payload: { sku: 'SKU-001', quantity: 5 },
      };

      await expect(postSessionAction('test-session-123', action)).rejects.toThrow(
        'Action failed'
      );
    });

    it('should throw default error when response not ok without details', async () => {
      const mockFetch = vi.fn().mockResolvedValueOnce({
        ok: false,
        json: async () => ({}),
      });
      global.fetch = mockFetch;

      const action: SessionActionRequest = {
        action: 'add_cart_item',
        payload: { sku: 'SKU-001', quantity: 5 },
      };

      await expect(postSessionAction('test-session-123', action)).rejects.toThrow(
        'Session update failed'
      );
    });
  });
});
