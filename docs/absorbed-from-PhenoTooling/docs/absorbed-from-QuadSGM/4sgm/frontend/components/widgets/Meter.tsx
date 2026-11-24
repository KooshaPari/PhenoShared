import React from 'react'

export interface MeterProps {
  label: string
  current: number | string
  threshold: number | string
  unit?: string
  showPercentage?: boolean
}

/**
 * Meter Widget - Progress toward threshold
 * Visual indicator of progress with percentage
 */
export function MeterWidget({
  label,
  current,
  threshold,
  unit = '',
  showPercentage = true,
}: MeterProps) {
  const currentNum = typeof current === 'string' ? parseFloat(current) : current
  const thresholdNum = typeof threshold === 'string' ? parseFloat(threshold) : threshold

  const percentage = thresholdNum > 0 ? (currentNum / thresholdNum) * 100 : 0
  const barWidth = Math.min(percentage, 100)

  const formatValue = (val: number) => {
    if (val >= 1000000) {
      const m = val / 1000000
      return m % 1 === 0 ? `${m}M` : `${m.toFixed(1)}M`
    }
    if (val >= 1000) {
      const k = val / 1000
      return k % 1 === 0 ? `${k}k` : `${k.toFixed(1)}k`
    }
    return val.toFixed(0)
  }

  return (
    <div className="space-y-2">
      <div className="flex justify-between text-sm">
        <span className="font-medium text-gray-700">{label}</span>
        <span className="text-gray-600">
          {formatValue(currentNum)}{unit && ` ${unit}`} / {formatValue(thresholdNum)}
          {unit && ` ${unit}`}
          {showPercentage && ` (${percentage.toFixed(0)}%)`}
        </span>
      </div>
      <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`h-full transition-all duration-300 ${
            percentage >= 100 ? 'bg-green-500' : percentage >= 75 ? 'bg-blue-500' : 'bg-yellow-500'
          }`}
          style={{ width: `${barWidth}%` }}
        />
      </div>
    </div>
  )
}
