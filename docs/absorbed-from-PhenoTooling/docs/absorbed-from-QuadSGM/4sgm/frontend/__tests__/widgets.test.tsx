import React from 'react'
import { render, screen } from '@testing-library/react'
import {
  BadgeWidget,
  MeterWidget,
  TagWidget,
  ComparisonWidget,
  MetricsCardWidget,
} from '../components/widgets'

describe('Widget Components', () => {
  describe('BadgeWidget', () => {
    it('renders with text and score', () => {
      render(<BadgeWidget text="High Confidence" score={0.92} />)
      expect(screen.getByText('High Confidence')).toBeInTheDocument()
      expect(screen.getByText('92%')).toBeInTheDocument()
    })

    it('auto-colors green for high confidence', () => {
      const { container } = render(<BadgeWidget text="Test" score={0.95} />)
      const badge = container.querySelector('span')
      expect(badge).toHaveClass('bg-green-100')
    })

    it('auto-colors blue for good confidence', () => {
      const { container } = render(<BadgeWidget text="Test" score={0.80} />)
      const badge = container.querySelector('span')
      expect(badge).toHaveClass('bg-blue-100')
    })

    it('auto-colors yellow for moderate confidence', () => {
      const { container } = render(<BadgeWidget text="Test" score={0.60} />)
      const badge = container.querySelector('span')
      expect(badge).toHaveClass('bg-yellow-100')
    })

    it('auto-colors red for low confidence', () => {
      const { container } = render(<BadgeWidget text="Test" score={0.30} />)
      const badge = container.querySelector('span')
      expect(badge).toHaveClass('bg-red-100')
    })

    it('renders with icon', () => {
      render(<BadgeWidget text="Test" icon="checkmark" />)
      expect(screen.getByText('✓')).toBeInTheDocument()
    })

    it('renders without score when not provided', () => {
      render(<BadgeWidget text="Test" />)
      expect(screen.getByText('Test')).toBeInTheDocument()
      expect(screen.queryByText('%')).not.toBeInTheDocument()
    })
  })

  describe('MeterWidget', () => {
    it('renders label and values', () => {
      render(
        <MeterWidget
          label="Budget"
          current={258000}
          threshold={150000}
          unit="$"
        />
      )
      expect(screen.getByText('Budget')).toBeInTheDocument()
      expect(screen.getByText(/258k/)).toBeInTheDocument()
      expect(screen.getByText(/150k/)).toBeInTheDocument()
    })

    it('calculates percentage correctly', () => {
      render(
        <MeterWidget
          label="Test"
          current={75}
          threshold={100}
          showPercentage={true}
        />
      )
      expect(screen.getByText(/75%/)).toBeInTheDocument()
    })

    it('shows progress bar at correct width', () => {
      const { container } = render(
        <MeterWidget
          label="Test"
          current={50}
          threshold={100}
        />
      )
      const progressBar = container.querySelector('[style*="width"]')
      expect(progressBar).toHaveStyle('width: 50%')
    })

    it('colors bar green when 100% or above', () => {
      const { container } = render(
        <MeterWidget
          label="Test"
          current={120}
          threshold={100}
        />
      )
      const bar = container.querySelector('.bg-green-500')
      expect(bar).toBeInTheDocument()
    })
  })

  describe('TagWidget', () => {
    it('renders text and variant', () => {
      render(<TagWidget text="Success" variant="success" />)
      expect(screen.getByText('Success')).toBeInTheDocument()
    })

    it('applies success variant styles', () => {
      const { container } = render(<TagWidget text="Test" variant="success" />)
      const tag = container.querySelector('span')
      expect(tag).toHaveClass('bg-green-100')
    })

    it('applies danger variant styles', () => {
      const { container } = render(<TagWidget text="Test" variant="danger" />)
      const tag = container.querySelector('span')
      expect(tag).toHaveClass('bg-red-100')
    })

    it('renders with icon', () => {
      render(<TagWidget text="Test" icon="star" />)
      expect(screen.getByText('⭐')).toBeInTheDocument()
    })
  })

  describe('ComparisonWidget', () => {
    it('renders title and options', () => {
      const options = [
        {
          name: 'Option A',
          pros: ['Pro 1'],
          cons: ['Con 1'],
          score: 0.8,
        },
      ]
      render(<ComparisonWidget title="Compare" options={options} />)
      expect(screen.getByText('Compare')).toBeInTheDocument()
      expect(screen.getByText('Option A')).toBeInTheDocument()
    })

    it('shows score as percentage', () => {
      const options = [
        {
          name: 'Test',
          pros: [],
          cons: [],
          score: 0.92,
        },
      ]
      render(<ComparisonWidget title="Test" options={options} />)
      expect(screen.getByText('92%')).toBeInTheDocument()
    })

    it('marks recommended option', () => {
      const options = [
        {
          name: 'Recommended',
          pros: [],
          cons: [],
          score: 0.95,
          recommended: true,
        },
      ]
      const { container } = render(
        <ComparisonWidget title="Test" options={options} />
      )
      const badge = screen.getByText('⭐ RECOMMENDED')
      expect(badge).toBeInTheDocument()
    })

    it('displays pros and cons', () => {
      const options = [
        {
          name: 'Option',
          pros: ['Good point'],
          cons: ['Bad point'],
          score: 0.8,
        },
      ]
      render(<ComparisonWidget title="Test" options={options} />)
      expect(screen.getByText(/Good point/)).toBeInTheDocument()
      expect(screen.getByText(/Bad point/)).toBeInTheDocument()
    })
  })

  describe('MetricsCardWidget', () => {
    it('renders title and metrics', () => {
      const metrics = [
        { label: 'Units', value: 194753, unit: 'units' },
      ]
      render(<MetricsCardWidget title="Summary" metrics={metrics} />)
      expect(screen.getByText('Summary')).toBeInTheDocument()
      expect(screen.getByText('Units')).toBeInTheDocument()
      expect(screen.getByText('194753')).toBeInTheDocument()
    })

    it('renders units', () => {
      const metrics = [
        { label: 'Budget', value: 258000, unit: '$' },
      ]
      render(<MetricsCardWidget title="Test" metrics={metrics} />)
      expect(screen.getByText('$')).toBeInTheDocument()
    })

    it('bolds metrics when specified', () => {
      const metrics = [
        { label: 'Total', value: 100, bold: true },
      ]
      const { container } = render(
        <MetricsCardWidget title="Test" metrics={metrics} />
      )
      const boldValue = container.querySelector('.font-black')
      expect(boldValue).toBeInTheDocument()
    })

    it('applies color styling', () => {
      const metrics = [
        { label: 'Success', value: 100, color: 'green' },
      ]
      const { container } = render(
        <MetricsCardWidget title="Test" metrics={metrics} />
      )
      expect(container.querySelector('.text-green-700')).toBeInTheDocument()
    })
  })
})
