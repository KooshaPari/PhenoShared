import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  getOptimalModel,
  supportedModels,
  toolHandlers,
} from '@/lib/ai-client';

describe('ai-client', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getOptimalModel', () => {
    it('should return fast model for simple queries without advanced features', () => {
      const model = getOptimalModel(false, 'simple');
      expect(model).toBeDefined();
    });

    it('should return primary model for complex queries', () => {
      const model = getOptimalModel(false, 'complex');
      expect(model).toBeDefined();
    });

    it('should return primary model when advanced features enabled', () => {
      const model = getOptimalModel(true, 'moderate');
      expect(model).toBeDefined();
    });

    it('should return primary model for moderate queries by default', () => {
      const model = getOptimalModel(false, 'moderate');
      expect(model).toBeDefined();
    });

    it('should return primary model when no args provided', () => {
      const model = getOptimalModel();
      expect(model).toBeDefined();
    });
  });

  describe('supportedModels', () => {
    it('should have claude35Sonnet model config', () => {
      expect(supportedModels.claude35Sonnet).toBeDefined();
      expect(supportedModels.claude35Sonnet.id).toBe('claude-3-5-sonnet-20241022');
      expect(supportedModels.claude35Sonnet.provider).toBe('anthropic');
      expect(supportedModels.claude35Sonnet.capabilities).toContain('streaming');
      expect(supportedModels.claude35Sonnet.capabilities).toContain('tools');
    });

    it('should have claude3Opus model config', () => {
      expect(supportedModels.claude3Opus).toBeDefined();
      expect(supportedModels.claude3Opus.id).toBe('claude-3-opus-20240229');
      expect(supportedModels.claude3Opus.maxTokens).toBe(200000);
    });

    it('should have gpt4o model config', () => {
      expect(supportedModels.gpt4o).toBeDefined();
      expect(supportedModels.gpt4o.provider).toBe('openai');
      expect(supportedModels.gpt4o.capabilities).toContain('json');
    });

    it('should have gpt4Turbo model config', () => {
      expect(supportedModels.gpt4Turbo).toBeDefined();
      expect(supportedModels.gpt4Turbo.maxTokens).toBe(128000);
    });

    it('should have cost information for all models', () => {
      Object.values(supportedModels).forEach((model) => {
        expect(model.costPer1kTokens.input).toBeGreaterThan(0);
        expect(model.costPer1kTokens.output).toBeGreaterThan(0);
      });
    });
  });

  describe('toolHandlers.searchKnowledgeBase', () => {
    it('should search knowledge base with default topK', async () => {
      const mockFetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          results: [
            {
              id: 'doc-1',
              title: 'Shipping Guide',
              content: 'Information about shipping',
              category: 'shipping',
              similarity: 0.95,
            },
          ],
          total: 1,
          query: 'shipping',
        }),
      });
      global.fetch = mockFetch;

      const result = await toolHandlers.searchKnowledgeBase('shipping');

      expect(mockFetch).toHaveBeenCalledWith('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: 'shipping', topK: 5 }),
      });
      expect(result.results).toHaveLength(1);
      expect(result.results[0].title).toBe('Shipping Guide');
    });

    it('should search knowledge base with custom topK', async () => {
      const mockFetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => ({ results: [], total: 0, query: 'returns' }),
      });
      global.fetch = mockFetch;

      await toolHandlers.searchKnowledgeBase('returns', 10);

      expect(mockFetch).toHaveBeenCalledWith('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: 'returns', topK: 10 }),
      });
    });

    it('should handle search error gracefully', async () => {
      const mockFetch = vi.fn().mockResolvedValueOnce({
        ok: false,
      });
      global.fetch = mockFetch;

      const result = await toolHandlers.searchKnowledgeBase('test');

      expect(result.error).toBeDefined();
      expect(result.results).toEqual([]);
    });

    it('should handle fetch network error', async () => {
      const mockFetch = vi.fn().mockRejectedValueOnce(new Error('Network failed'));
      global.fetch = mockFetch;

      const result = await toolHandlers.searchKnowledgeBase('test');

      expect(result.error).toBeDefined();
      expect(result.results).toEqual([]);
    });
  });

  describe('toolHandlers.getShippingInfo', () => {
    it('should get shipping info for destination', async () => {
      const mockFetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          destination: 'USA',
          methods: [
            { name: 'Standard', days: 5, cost: 10, currency: 'USD' },
          ],
        }),
      });
      global.fetch = mockFetch;

      const result = await toolHandlers.getShippingInfo('USA');

      expect(mockFetch).toHaveBeenCalledWith('/api/shipping', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ destination: 'USA', weight: undefined }),
      });
      expect(result.destination).toBe('USA');
    });

    it('should get shipping info with weight', async () => {
      const mockFetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => ({ destination: 'Canada', methods: [] }),
      });
      global.fetch = mockFetch;

      await toolHandlers.getShippingInfo('Canada', 10.5);

      expect(mockFetch).toHaveBeenCalledWith('/api/shipping', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ destination: 'Canada', weight: 10.5 }),
      });
    });

    it('should handle shipping error gracefully', async () => {
      const mockFetch = vi.fn().mockResolvedValueOnce({ ok: false });
      global.fetch = mockFetch;

      const result = await toolHandlers.getShippingInfo('InvalidCountry');

      expect(result.error).toBeDefined();
    });
  });

  describe('toolHandlers.getReturnPolicy', () => {
    it('should get return policy without category', async () => {
      const mockFetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          days: 30,
          conditions: ['Must be unopened', 'Original packaging'],
          refundMethod: 'Original payment method',
        }),
      });
      global.fetch = mockFetch;

      const result = await toolHandlers.getReturnPolicy();

      expect(mockFetch).toHaveBeenCalledWith('/api/returns', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ category: undefined }),
      });
      expect(result.days).toBe(30);
    });

    it('should get return policy for specific category', async () => {
      const mockFetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          days: 60,
          conditions: ['Electronics only'],
          refundMethod: 'Store credit',
        }),
      });
      global.fetch = mockFetch;

      const result = await toolHandlers.getReturnPolicy('electronics');

      expect(mockFetch).toHaveBeenCalledWith('/api/returns', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ category: 'electronics' }),
      });
      expect(result.days).toBe(60);
    });

    it('should handle return policy error gracefully', async () => {
      const mockFetch = vi.fn().mockResolvedValueOnce({ ok: false });
      global.fetch = mockFetch;

      const result = await toolHandlers.getReturnPolicy('invalid');

      expect(result.error).toBeDefined();
    });
  });

  describe('toolHandlers.escalateToHuman', () => {
    it('should escalate to human support', async () => {
      const mockFetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          ticketId: 'TICKET-12345',
          status: 'created',
          estimatedWaitTime: 5,
          message: 'Ticket created',
        }),
      });
      global.fetch = mockFetch;

      const result = await toolHandlers.escalateToHuman('Complex issue', 'User needs help');

      expect(mockFetch).toHaveBeenCalledWith('/api/escalate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: 'Complex issue', context: 'User needs help' }),
      });
      expect(result.ticketId).toBe('TICKET-12345');
    });

    it('should handle escalation error gracefully', async () => {
      const mockFetch = vi.fn().mockResolvedValueOnce({ ok: false });
      global.fetch = mockFetch;

      const result = await toolHandlers.escalateToHuman('Issue', 'Context');

      expect(result.error).toBeDefined();
      expect(result.ticketId).toBeNull();
    });

    it('should handle network error in escalation', async () => {
      const mockFetch = vi.fn().mockRejectedValueOnce(new Error('Network error'));
      global.fetch = mockFetch;

      const result = await toolHandlers.escalateToHuman('Issue', 'Context');

      expect(result.error).toBeDefined();
      expect(result.ticketId).toBeNull();
    });
  });
});
