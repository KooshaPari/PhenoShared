import React from 'react'

export interface TagProps {
  text: string
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info'
  icon?: string
}

/**
 * Tag Widget - Labeled badge for classification
 */
export function TagWidget({ text, variant = 'default', icon }: TagProps) {
  const variantMap = {
    default: 'bg-gray-100 text-gray-800 border-gray-300',
    success: 'bg-green-100 text-green-800 border-green-300',
    warning: 'bg-yellow-100 text-yellow-800 border-yellow-300',
    danger: 'bg-red-100 text-red-800 border-red-300',
    info: 'bg-blue-100 text-blue-800 border-blue-300',
  }

  const iconMap: Record<string, string> = {
    checkmark: '✓',
    star: '⭐',
    warning: '⚠️',
    info: 'ℹ️',
    alert: '🔔',
  }

  const displayIcon = icon ? iconMap[icon] || icon : null

  return (
    <span
      className={`inline-flex items-center gap-2 px-3 py-1 rounded-lg border font-medium text-sm ${variantMap[variant]}`}
    >
      {displayIcon && <span>{displayIcon}</span>}
      {text}
    </span>
  )
}
