import React from 'react'
import { BadgeWidget } from '../widgets/Badge'
import { MeterWidget } from '../widgets/Meter'
import { TagWidget } from '../widgets/Tag'
import { ComparisonWidget } from '../widgets/Comparison'
import { MetricsCardWidget } from '../widgets/MetricsCard'
import type { WidgetEvent } from './ReasoningTrail'

interface WidgetRendererProps {
  event: WidgetEvent
}

interface TimelineEvent {
  label: string
  date: string
  status: string
}

type BadgeProps = { text: string; score?: number; color?: 'green' | 'blue' | 'yellow' | 'red' | 'purple' | 'orange'; icon?: string; inline?: boolean };
type MeterProps = { label: string; current: number | string; threshold: number | string; unit?: string; showPercentage?: boolean };
type TagProps = { text: string; variant?: 'default' | 'success' | 'warning' | 'danger' | 'info'; icon?: string };
type ComparisonOption = { name: string; pros: string[]; cons: string[]; score: number; recommended?: boolean };
type ComparisonProps = { title: string; options: ComparisonOption[] };
type Metric = { label: string; value: string | number; unit?: string; color?: string; bold?: boolean };
type MetricsCardProps = { title: string; metrics: Metric[] };

/**
 * WidgetRenderer - Dispatches events to appropriate widget components
 */
export function WidgetRenderer({ event }: WidgetRendererProps) {
  const { widget_type, placement = 'message', props = {} } = event

  const renderWidget = () => {
    switch (widget_type) {
      case 'badge':
        return <BadgeWidget {...(props as BadgeProps)} inline={placement === 'inline'} />

      case 'meter':
        return <MeterWidget {...(props as MeterProps)} />

      case 'tag':
        return <TagWidget {...(props as TagProps)} />

      case 'comparison':
        return <ComparisonWidget {...(props as ComparisonProps)} />

      case 'metrics_card':
        return <MetricsCardWidget {...(props as MetricsCardProps)} />

      case 'distribution_chart':
        return (
          <div className="p-4 bg-white rounded-lg border border-gray-200">
            <h3 className="font-bold text-gray-900 mb-3">{typeof props.title === 'string' ? props.title : ''}</h3>
            <div className="h-64 flex items-center justify-center bg-gray-50 rounded border border-gray-200">
              <p className="text-sm text-gray-500">Chart visualization (Recharts)</p>
            </div>
          </div>
        )

      case 'timeline':
        return (
          <div className="p-4 bg-white rounded-lg border border-gray-200 space-y-4">
            <h3 className="font-bold text-gray-900">{typeof props.title === 'string' ? props.title : ''}</h3>
            {(props.events as TimelineEvent[] | undefined)?.map((evt, idx) => (
              <div key={idx} className="flex gap-4">
                <div className="flex flex-col items-center">
                  <div className="w-4 h-4 bg-blue-500 rounded-full"></div>
                  {idx < ((props.events as TimelineEvent[])?.length || 0) - 1 && (
                    <div className="w-1 h-12 bg-gray-300 my-2"></div>
                  )}
                </div>
                <div className="pb-4">
                  <p className="font-medium text-gray-900">{evt.label}</p>
                  <p className="text-sm text-gray-600">{evt.date}</p>
                  <span className="inline-block mt-1 text-xs px-2 py-1 rounded bg-blue-100 text-blue-800">
                    {evt.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )

      case 'decision_tree':
        return (
          <div className="p-4 bg-white rounded-lg border border-gray-200">
            <h3 className="font-bold text-gray-900 mb-3">{typeof props.title === 'string' ? props.title : ''}</h3>
            <div className="bg-gray-50 p-4 rounded border border-gray-200 text-sm text-gray-600">
              Interactive decision tree visualization
            </div>
          </div>
        )

      default:
        return (
          <div className="p-4 bg-yellow-50 rounded-lg border border-yellow-200">
            <p className="text-sm text-yellow-800">
              Unknown widget type: {widget_type}
            </p>
          </div>
        )
    }
  }

  // Inline widgets render without container
  if (placement === 'inline') {
    return <div className="inline">{renderWidget()}</div>
  }

  // Message widgets render with container
  return (
    <div className="p-4 bg-white rounded-lg border border-gray-200 shadow-sm">
      {renderWidget()}
    </div>
  )
}
