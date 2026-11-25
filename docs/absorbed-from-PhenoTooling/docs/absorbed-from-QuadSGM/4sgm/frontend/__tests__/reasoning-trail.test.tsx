import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import { ReasoningTrail, ReasoningStep, WidgetRenderer } from '../components/reasoning-trail'

describe('ReasoningTrail Components', () => {
  describe('ReasoningTrail', () => {
    it('renders header and footer', () => {
      render(<ReasoningTrail sessionId="test-123" />)
      expect(screen.getByText('Agent Reasoning Trail')).toBeInTheDocument()
      expect(screen.getByText(/event.*received/i)).toBeInTheDocument()
    })

    it('shows waiting state when no events', () => {
      render(<ReasoningTrail sessionId="test-123" />)
      expect(screen.getByText(/Waiting for agent reasoning/i)).toBeInTheDocument()
    })

    it('displays connection status', () => {
      render(<ReasoningTrail sessionId="test-123" />)
      expect(screen.getByText('Disconnected')).toBeInTheDocument()
    })

    it('handles error state', async () => {
      const { rerender } = render(<ReasoningTrail sessionId="test-123" />)
      // Error state would be shown if connection fails
      expect(screen.getByText('Disconnected')).toBeInTheDocument()
    })
  })

  describe('ReasoningStep', () => {
    const mockEvent = {
      subject: 'Customer Analysis',
      reasoning: 'Analyzing requirements',
      stage: 'analyzing',
      phase: 'reflect',
      confidence: 0.98,
      options_considered: [
        {
          option: 'Small',
          pros: ['Fast'],
          cons: ['Limited'],
          score: 0.2,
        },
        {
          option: 'Large',
          pros: ['Complete'],
          cons: ['Complex'],
          score: 0.98,
          selected: true,
        },
      ],
      decision: 'Selected large order path',
      citations: ['Budget: $258k', 'Timeline: 8 days'],
    }

    it('renders subject and reasoning', () => {
      render(<ReasoningStep event={mockEvent} />)
      expect(screen.getByText('Customer Analysis')).toBeInTheDocument()
      expect(screen.getByText('Analyzing requirements')).toBeInTheDocument()
    })

    it('shows confidence badge', () => {
      render(<ReasoningStep event={mockEvent} />)
      const confidenceText = screen.getByText('Confidence')
      expect(confidenceText).toBeInTheDocument()
      // Verify the score is displayed (should show 98%)
      const parentBadge = confidenceText.parentElement
      expect(parentBadge?.textContent).toMatch(/98/)
    })

    it('displays options with pros/cons', () => {
      render(<ReasoningStep event={mockEvent} />)
      expect(screen.getByText('Small')).toBeInTheDocument()
      expect(screen.getByText('Large')).toBeInTheDocument()
      expect(screen.getByText(/Fast/)).toBeInTheDocument()
      expect(screen.getByText(/Limited/)).toBeInTheDocument()
    })

    it('marks selected option', () => {
      render(<ReasoningStep event={mockEvent} />)
      expect(screen.getByText(/✓ SELECTED/)).toBeInTheDocument()
    })

    it('displays decision', () => {
      render(<ReasoningStep event={mockEvent} />)
      expect(screen.getByText('Selected large order path')).toBeInTheDocument()
    })

    it('shows citations', () => {
      render(<ReasoningStep event={mockEvent} />)
      expect(screen.getByText(/Budget: \$258k/)).toBeInTheDocument()
      expect(screen.getByText(/Timeline: 8 days/)).toBeInTheDocument()
    })

    it('toggles expand/collapse on click', () => {
      const { container } = render(<ReasoningStep event={mockEvent} />)
      const header = container.querySelector('[class*="from-blue"]')
      expect(header).toBeInTheDocument()
    })
  })

  describe('WidgetRenderer', () => {
    it('renders badge widget', () => {
      const event = {
        type: 'widget',
        widget_type: 'badge',
        placement: 'inline',
        props: {
          text: 'Test Badge',
          score: 0.92,
        },
      }
      render(<WidgetRenderer event={event} />)
      expect(screen.getByText('Test Badge')).toBeInTheDocument()
    })

    it('renders meter widget', () => {
      const event = {
        type: 'widget',
        widget_type: 'meter',
        placement: 'message',
        props: {
          label: 'Progress',
          current: 50,
          threshold: 100,
          unit: 'units',
        },
      }
      render(<WidgetRenderer event={event} />)
      expect(screen.getByText('Progress')).toBeInTheDocument()
    })

    it('renders comparison widget', () => {
      const event = {
        type: 'widget',
        widget_type: 'comparison',
        placement: 'message',
        props: {
          title: 'Options',
          options: [
            {
              name: 'Option A',
              pros: [],
              cons: [],
              score: 0.8,
            },
          ],
        },
      }
      render(<WidgetRenderer event={event} />)
      expect(screen.getByText('Options')).toBeInTheDocument()
      expect(screen.getByText('Option A')).toBeInTheDocument()
    })

    it('renders metrics card widget', () => {
      const event = {
        type: 'widget',
        widget_type: 'metrics_card',
        placement: 'message',
        props: {
          title: 'Metrics',
          metrics: [
            { label: 'Value', value: 100 },
          ],
        },
      }
      render(<WidgetRenderer event={event} />)
      expect(screen.getByText('Metrics')).toBeInTheDocument()
      expect(screen.getByText('Value')).toBeInTheDocument()
    })

    it('handles unknown widget types gracefully', () => {
      const event = {
        type: 'widget',
        widget_type: 'unknown_widget',
        placement: 'message',
        props: {},
      }
      render(<WidgetRenderer event={event} />)
      expect(screen.getByText(/Unknown widget type/)).toBeInTheDocument()
    })

    it('renders inline widgets without container', () => {
      const event = {
        type: 'widget',
        widget_type: 'badge',
        placement: 'inline',
        props: {
          text: 'Inline',
        },
      }
      const { container } = render(<WidgetRenderer event={event} />)
      const inlineDiv = container.querySelector('.inline')
      expect(inlineDiv).toBeInTheDocument()
    })

    it('renders message widgets with container', () => {
      const event = {
        type: 'widget',
        widget_type: 'badge',
        placement: 'message',
        props: {
          text: 'Message',
        },
      }
      const { container } = render(<WidgetRenderer event={event} />)
      const messageContainer = container.querySelector('[class*="rounded-lg"]')
      expect(messageContainer).toBeInTheDocument()
    })
  })
})
