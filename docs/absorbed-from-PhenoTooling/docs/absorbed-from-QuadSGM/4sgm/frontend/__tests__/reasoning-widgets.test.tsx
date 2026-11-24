import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import ReasoningStep from '@/components/reasoning/reasoning-step';
import { WidgetRenderer } from '@/components/reasoning/widget-renderer';
import type { SSEAgentReasoningEvent, SSEWidgetEvent } from '@/types/sse';

const mockReasoningEvent = (): SSEAgentReasoningEvent => ({
  type: 'agent_reasoning',
  timestamp: new Date().toISOString(),
  phase: 'plan',
  stage: 'evaluating',
  subject: 'Category allocation',
  reasoning: 'Comparing inventory turnover and gross margin by category.',
  options_considered: [
    {
      option: 'Household first',
      pros: ['High velocity'],
      cons: ['Seasonal risk'],
      score: 0.78,
      selected: true,
    },
  ],
  decision: 'Balanced mix',
  confidence: 0.9,
});

const mockWidgetEvent = (type: 'badge' | 'metrics_card'): SSEWidgetEvent => ({
  type: 'widget',
  timestamp: new Date().toISOString(),
  widget_type: type,
  placement: 'message',
  props:
    type === 'metrics_card'
      ? {
          metrics: [
            { label: 'Budget', value: '$250k' },
            { label: 'Units', value: '185,000' },
          ],
        }
      : type === 'badge'
        ? { text: 'High confidence', score: 0.92 }
        : { options: [] },
});

describe('Reasoning components', () => {
  it('renders reasoning step with subject and decision', () => {
    const event = mockReasoningEvent();
    render(<ReasoningStep event={event} />);
    expect(screen.getByText('Category allocation')).toBeInTheDocument();
    expect(screen.getByText('Balanced mix')).toBeInTheDocument();
    expect(screen.getByText(/confidence/i)).toBeInTheDocument();
  });

  it('renders badge widget with score', () => {
    const event = mockWidgetEvent('badge');
    render(<WidgetRenderer event={event} />);
    expect(screen.getByText('High confidence')).toBeInTheDocument();
    expect(screen.getByText(/92%/)).toBeInTheDocument();
  });

  it('renders metrics card widget values', () => {
    const event = mockWidgetEvent('metrics_card');
    render(<WidgetRenderer event={event} />);
    expect(screen.getByText('Budget')).toBeInTheDocument();
    expect(screen.getByText('$250k')).toBeInTheDocument();
  });
});
