import { describe, it, expect } from 'vitest';
import {
  isTokenEvent,
  isProgressEvent,
  isCompleteEvent,
  isErrorEvent,
  isMetadataEvent,
  isResearchEvent,
  isReasoningEvent,
  isWidgetEvent,
  isInsightEvent,
  isControlEvent,
  type SSEEvent,
  type SSETokenEvent,
  type SSEProgressEvent,
  type SSECompleteEvent,
  type SSEErrorEvent,
  type SSEMetadataEvent,
  type SSEResearchEvent,
  type SSEAgentReasoningEvent,
  type SSEWidgetEvent,
  type SSEInsightEvent,
  type SSEControlEvent,
} from '@/types/sse';

describe('SSE Types and Type Guards', () => {
  describe('SSETokenEvent', () => {
    it('should construct valid token event', () => {
      const event: SSETokenEvent = {
        type: 'token',
        timestamp: '2024-01-01T10:00:00Z',
        data: 'Hello',
        token_count: 1,
      };

      expect(event.type).toBe('token');
      expect(event.data).toBe('Hello');
      expect(event.token_count).toBe(1);
    });

    it('should identify token event with type guard', () => {
      const event: SSEEvent = {
        type: 'token',
        timestamp: '2024-01-01T10:00:00Z',
        data: 'Test',
        token_count: 1,
      };

      expect(isTokenEvent(event)).toBe(true);
      expect(isProgressEvent(event)).toBe(false);
    });
  });

  describe('SSEProgressEvent', () => {
    it('should construct valid progress event', () => {
      const event: SSEProgressEvent = {
        type: 'progress',
        timestamp: '2024-01-01T10:00:00Z',
        character_count: 50,
        token_count: 10,
      };

      expect(event.character_count).toBe(50);
      expect(event.token_count).toBe(10);
    });

    it('should identify progress event with type guard', () => {
      const event: SSEEvent = {
        type: 'progress',
        timestamp: '2024-01-01T10:00:00Z',
        character_count: 100,
        token_count: 20,
      };

      expect(isProgressEvent(event)).toBe(true);
      expect(isTokenEvent(event)).toBe(false);
    });
  });

  describe('SSECompleteEvent', () => {
    it('should construct valid complete event', () => {
      const event: SSECompleteEvent = {
        type: 'complete',
        timestamp: '2024-01-01T10:00:00Z',
        message: 'Full response message',
        session_id: 'session-123',
        token_count: 50,
        character_count: 500,
        documents_used: 3,
      };

      expect(event.message).toBe('Full response message');
      expect(event.documents_used).toBe(3);
    });

    it('should identify complete event with type guard', () => {
      const event: SSEEvent = {
        type: 'complete',
        timestamp: '2024-01-01T10:00:00Z',
        message: 'Done',
        session_id: 'session-456',
        token_count: 100,
        character_count: 1000,
        documents_used: 5,
      };

      expect(isCompleteEvent(event)).toBe(true);
    });
  });

  describe('SSEErrorEvent', () => {
    it('should construct valid error event', () => {
      const event: SSEErrorEvent = {
        type: 'error',
        timestamp: '2024-01-01T10:00:00Z',
        message: 'An error occurred',
      };

      expect(event.message).toBe('An error occurred');
    });

    it('should identify error event with type guard', () => {
      const event: SSEEvent = {
        type: 'error',
        timestamp: '2024-01-01T10:00:00Z',
        message: 'Connection failed',
      };

      expect(isErrorEvent(event)).toBe(true);
      expect(isCompleteEvent(event)).toBe(false);
    });
  });

  describe('SSEMetadataEvent', () => {
    it('should construct valid metadata event', () => {
      const event: SSEMetadataEvent = {
        type: 'metadata',
        timestamp: '2024-01-01T10:00:00Z',
        session_id: 'session-123',
        document_count: 5,
      };

      expect(event.document_count).toBe(5);
    });

    it('should identify metadata event with type guard', () => {
      const event: SSEEvent = {
        type: 'metadata',
        timestamp: '2024-01-01T10:00:00Z',
        session_id: 'session-789',
        document_count: 10,
      };

      expect(isMetadataEvent(event)).toBe(true);
    });
  });

  describe('SSEResearchEvent', () => {
    it('should construct valid research event with all stages', () => {
      const stages = ['reflect', 'plan', 'execute', 'reason', 'synthesis'] as const;

      stages.forEach((stage) => {
        const event: SSEResearchEvent = {
          type: 'research',
          timestamp: '2024-01-01T10:00:00Z',
          stage,
          heading: `${stage} phase`,
          details: 'Details about this stage',
          citations: ['Citation 1', 'Citation 2'],
          evidence: [{ key: 'value' }],
          metrics: { score: 0.95 },
        };

        expect(event.stage).toBe(stage);
        expect(event.citations).toHaveLength(2);
      });
    });

    it('should construct research event without optional fields', () => {
      const event: SSEResearchEvent = {
        type: 'research',
        timestamp: '2024-01-01T10:00:00Z',
        stage: 'plan',
        heading: 'Planning',
        details: 'Planning details',
        citations: null,
      };

      expect(event.citations).toBeNull();
      expect(event.evidence).toBeUndefined();
    });

    it('should identify research event with type guard', () => {
      const event: SSEEvent = {
        type: 'research',
        timestamp: '2024-01-01T10:00:00Z',
        stage: 'execute',
        heading: 'Executing',
        details: 'Execution details',
        citations: [],
      };

      expect(isResearchEvent(event)).toBe(true);
    });
  });

  describe('SSEAgentReasoningEvent', () => {
    it('should construct valid agent reasoning event', () => {
      const event: SSEAgentReasoningEvent = {
        type: 'agent_reasoning',
        timestamp: '2024-01-01T10:00:00Z',
        phase: 'reflect',
        stage: 'analyzing',
        subject: 'Cart optimization',
        reasoning: 'Considering different strategies',
        options_considered: [
          {
            option: 'Option A',
            pros: ['Pro 1', 'Pro 2'],
            cons: ['Con 1'],
            score: 0.85,
            selected: true,
          },
        ],
        decision: 'Selected Option A',
        confidence: 0.9,
        citations: ['Reference 1'],
      };

      expect(event.confidence).toBe(0.9);
      expect(event.options_considered).toHaveLength(1);
    });

    it('should identify reasoning event with type guard', () => {
      const event: SSEEvent = {
        type: 'agent_reasoning',
        timestamp: '2024-01-01T10:00:00Z',
        phase: 'plan',
        stage: 'evaluating',
        subject: 'Test subject',
        reasoning: 'Test reasoning',
        options_considered: [],
        decision: 'Test decision',
        confidence: 0.8,
      };

      expect(isReasoningEvent(event)).toBe(true);
    });
  });

  describe('SSEWidgetEvent', () => {
    it('should construct badge widget event', () => {
      const event: SSEWidgetEvent = {
        type: 'widget',
        timestamp: '2024-01-01T10:00:00Z',
        widget_type: 'badge',
        placement: 'inline',
        props: {
          text: 'High Priority',
          score: 0.95,
          title: 'Priority Badge',
          color: 'red',
        },
        markdown: 'Badge markdown',
      };

      expect(event.widget_type).toBe('badge');
      expect(event.placement).toBe('inline');
    });

    it('should construct metrics card widget event', () => {
      const event: SSEWidgetEvent = {
        type: 'widget',
        timestamp: '2024-01-01T10:00:00Z',
        widget_type: 'metrics_card',
        placement: 'message',
        props: {
          title: 'Key Metrics',
          metrics: [
            { label: 'Total', value: 1000, unit: 'units' },
            { label: 'Percentage', value: 50, unit: '%', color: 'green' },
          ],
        },
      };

      expect(event.widget_type).toBe('metrics_card');
      expect(
        'metrics' in event.props && event.props.metrics
      ).toBeDefined();
    });

    it('should identify widget event with type guard', () => {
      const event: SSEEvent = {
        type: 'widget',
        timestamp: '2024-01-01T10:00:00Z',
        widget_type: 'tag',
        placement: 'embedded',
        props: { text: 'Test', variant: 'success' },
      };

      expect(isWidgetEvent(event)).toBe(true);
    });
  });

  describe('SSEInsightEvent', () => {
    it('should construct insight event with widgets', () => {
      const event: SSEInsightEvent = {
        type: 'insight',
        timestamp: '2024-01-01T10:00:00Z',
        widgets: [
          {
            kind: 'cart_plan',
            budget: 5000,
            totalUnits: 100,
            categories: [
              {
                name: 'Category A',
                budget: 2500,
                units: 50,
                avgUnitCost: 50,
                notes: 'Notes',
                share: 0.5,
                items: [{ sku: 'SKU-001', name: 'Product A', units: 50 }],
              },
            ],
          },
        ],
      };

      expect(event.widgets).toHaveLength(1);
      expect(event.widgets[0].kind).toBe('cart_plan');
    });

    it('should identify insight event with type guard', () => {
      const event: SSEEvent = {
        type: 'insight',
        timestamp: '2024-01-01T10:00:00Z',
        widgets: [],
      };

      expect(isInsightEvent(event)).toBe(true);
    });
  });

  describe('SSEControlEvent', () => {
    it('should construct control event with navigate action', () => {
      const event: SSEControlEvent = {
        type: 'control',
        timestamp: '2024-01-01T10:00:00Z',
        session_id: 'session-123',
        actions: [
          {
            kind: 'navigate',
            path: '/catalog',
            label: 'Browse Catalog',
            announce: 'Navigating to catalog',
          },
        ],
      };

      expect(event.actions).toHaveLength(1);
      expect(event.actions[0].kind).toBe('navigate');
    });

    it('should construct control event with session action', () => {
      const event: SSEControlEvent = {
        type: 'control',
        timestamp: '2024-01-01T10:00:00Z',
        session_id: 'session-456',
        actions: [
          {
            kind: 'session_action',
            action: {
              action: 'add_cart_item',
              payload: { sku: 'SKU-001', quantity: 5 },
            },
            label: 'Add to Cart',
            announce: 'Item added to cart',
          },
        ],
      };

      expect(event.actions).toHaveLength(1);
      expect(event.actions[0].kind).toBe('session_action');
    });

    it('should identify control event with type guard', () => {
      const event: SSEEvent = {
        type: 'control',
        timestamp: '2024-01-01T10:00:00Z',
        session_id: 'session-789',
        actions: [],
      };

      expect(isControlEvent(event)).toBe(true);
    });
  });

  describe('Type guard accuracy', () => {
    it('should correctly identify each event type', () => {
      const events: SSEEvent[] = [
        {
          type: 'token',
          timestamp: '2024-01-01T10:00:00Z',
          data: 'Hi',
          token_count: 1,
        },
        {
          type: 'progress',
          timestamp: '2024-01-01T10:00:00Z',
          character_count: 50,
          token_count: 10,
        },
        {
          type: 'complete',
          timestamp: '2024-01-01T10:00:00Z',
          message: 'Done',
          session_id: 'session-123',
          token_count: 100,
          character_count: 1000,
          documents_used: 5,
        },
        {
          type: 'error',
          timestamp: '2024-01-01T10:00:00Z',
          message: 'Error',
        },
        {
          type: 'metadata',
          timestamp: '2024-01-01T10:00:00Z',
          session_id: 'session-123',
          document_count: 5,
        },
      ];

      expect(isTokenEvent(events[0])).toBe(true);
      expect(isProgressEvent(events[1])).toBe(true);
      expect(isCompleteEvent(events[2])).toBe(true);
      expect(isErrorEvent(events[3])).toBe(true);
      expect(isMetadataEvent(events[4])).toBe(true);
    });

    it('should not cross-identify different event types', () => {
      const tokenEvent: SSEEvent = {
        type: 'token',
        timestamp: '2024-01-01T10:00:00Z',
        data: 'Test',
        token_count: 1,
      };

      expect(isTokenEvent(tokenEvent)).toBe(true);
      expect(isProgressEvent(tokenEvent)).toBe(false);
      expect(isCompleteEvent(tokenEvent)).toBe(false);
      expect(isErrorEvent(tokenEvent)).toBe(false);
    });
  });

  describe('Widget type variants', () => {
    it('should support all widget types', () => {
      const widgetTypes = [
        'badge',
        'meter',
        'tag',
        'comparison',
        'metrics_card',
        'distribution_chart',
        'timeline',
        'decision_tree',
      ] as const;

      widgetTypes.forEach((widgetType) => {
        const event: SSEWidgetEvent = {
          type: 'widget',
          timestamp: '2024-01-01T10:00:00Z',
          widget_type: widgetType,
          placement: 'inline',
          props: {} as any,
        };

        expect(event.widget_type).toBe(widgetType);
      });
    });

    it('should support all placement types', () => {
      const placements = ['inline', 'message', 'embedded'] as const;

      placements.forEach((placement) => {
        const event: SSEWidgetEvent = {
          type: 'widget',
          timestamp: '2024-01-01T10:00:00Z',
          widget_type: 'badge',
          placement,
          props: { text: 'Test' },
        };

        expect(event.placement).toBe(placement);
      });
    });
  });
});
