import React from 'react'

export interface BadgeProps {
  text: string
  score?: number
  color?: 'green' | 'blue' | 'yellow' | 'red' | 'purple' | 'orange'
  icon?: string
  inline?: boolean
}

/**
 * Badge Widget - Simple confidence/status indicator
 * Auto-colors based on confidence score
 */
export function BadgeWidget({
  text,
  score,
  color = 'blue',
  icon,
}: BadgeProps) {
  const colorMap = {
    green: 'bg-green-100 text-green-800 border-green-300',
    blue: 'bg-blue-100 text-blue-800 border-blue-300',
    yellow: 'bg-yellow-100 text-yellow-800 border-yellow-300',
    red: 'bg-red-100 text-red-800 border-red-300',
    purple: 'bg-purple-100 text-purple-800 border-purple-300',
    orange: 'bg-orange-100 text-orange-800 border-orange-300',
  }

  const iconMap: Record<string, string> = {
    checkmark: '✓',
    star: '⭐',
    warning: '⚠️',
    question: '❓',
    info: 'ℹ️',
  }

  // Auto-color based on score if provided
  const getColorFromScore = (s: number): 'green' | 'blue' | 'yellow' | 'red' => {
    if (s >= 0.9) return 'green'
    if (s >= 0.75) return 'blue'
    if (s >= 0.6) return 'yellow'
    return 'red'
  }

  const finalColor = score !== undefined ? getColorFromScore(score) : color

  const displayIcon = icon ? iconMap[icon] || icon : null
  const displayScore = score !== undefined ? `${(score * 100).toFixed(0)}%` : null

  const baseClass = `inline-flex items-center gap-2 px-3 py-1 rounded-full border font-medium ${colorMap[finalColor]}`

  return (
    <span className={baseClass}>
      {displayIcon && <span>{displayIcon}</span>}
      <span>{text}</span>
      {displayScore && <span className="font-bold">{displayScore}</span>}
    </span>
  )
}
