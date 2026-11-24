import React from 'react'

export interface Metric {
  label: string
  value: string | number
  unit?: string
  color?: string
  bold?: boolean
}

export interface MetricsCardProps {
  title: string
  metrics: Metric[]
}

/**
 * Metrics Card Widget - Grid of key metrics
 */
export function MetricsCardWidget({ title, metrics }: MetricsCardProps) {
  const colorMap: Record<string, string> = {
    green: 'text-green-700 bg-green-50',
    blue: 'text-blue-700 bg-blue-50',
    yellow: 'text-yellow-700 bg-yellow-50',
    red: 'text-red-700 bg-red-50',
    success: 'text-green-700 bg-green-50',
    warning: 'text-yellow-700 bg-yellow-50',
    danger: 'text-red-700 bg-red-50',
    info: 'text-blue-700 bg-blue-50',
  }

  return (
    <div className="space-y-4">
      <h3 className="font-bold text-lg text-gray-900">{title}</h3>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {metrics.map((metric, idx) => {
          const colorClass = metric.color ? colorMap[metric.color] || 'text-gray-700 bg-gray-50' : 'text-gray-700 bg-gray-50'
          return (
            <div
              key={idx}
              className={`p-4 rounded-lg border border-gray-200 ${colorClass}`}
            >
              <p className="text-xs font-medium text-gray-600 mb-1">{metric.label}</p>
              <div className={`text-2xl font-bold ${metric.bold ? 'font-black' : ''}`}>
                {metric.value}
              </div>
              {metric.unit && <p className="text-xs text-gray-600 mt-1">{metric.unit}</p>}
            </div>
          )
        })}
      </div>
    </div>
  )
}
