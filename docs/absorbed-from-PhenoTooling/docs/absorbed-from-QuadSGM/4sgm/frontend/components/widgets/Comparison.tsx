import React from 'react'

export interface ComparisonOption {
  name: string
  pros: string[]
  cons: string[]
  score: number
  recommended?: boolean
}

export interface ComparisonProps {
  title: string
  options: ComparisonOption[]
}

/**
 * Comparison Widget - Side-by-side option evaluation
 */
export function ComparisonWidget({ title, options }: ComparisonProps) {
  return (
    <div className="space-y-4">
      <h3 className="font-bold text-lg text-gray-900">{title}</h3>
      <div className="space-y-3">
        {options.map((option, idx) => (
          <div
            key={idx}
            className={`p-4 rounded-lg border-2 ${
              option.recommended
                ? 'border-green-500 bg-green-50'
                : 'border-gray-200 bg-white'
            }`}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h4 className="font-semibold text-gray-900">{option.name}</h4>
                  {option.recommended && (
                    <span className="text-xs font-bold text-green-700 bg-green-200 px-2 py-1 rounded">
                      ⭐ RECOMMENDED
                    </span>
                  )}
                </div>

                <div className="mt-3 space-y-2">
                  <div>
                    <p className="text-xs font-bold text-green-700">Pros:</p>
                    <ul className="text-sm text-gray-700 space-y-1">
                      {option.pros.map((pro, i) => (
                        <li key={`pro-${i}`}>✓ {pro}</li>
                      ))}
                    </ul>
                  </div>
                  {option.cons.length > 0 && (
                    <div>
                      <p className="text-xs font-bold text-red-700">Cons:</p>
                      <ul className="text-sm text-gray-700 space-y-1">
                        {option.cons.map((con, i) => (
                          <li key={`con-${i}`}>✗ {con}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>

              <div className="ml-4 text-right">
                <div className="text-3xl font-bold text-gray-900">
                  {(option.score * 100).toFixed(0)}%
                </div>
                <div
                  className={`mt-2 h-2 w-16 rounded-full ${
                    option.score >= 0.85
                      ? 'bg-green-500'
                      : option.score >= 0.75
                      ? 'bg-blue-500'
                      : option.score >= 0.5
                      ? 'bg-yellow-500'
                      : 'bg-red-500'
                  }`}
                />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
