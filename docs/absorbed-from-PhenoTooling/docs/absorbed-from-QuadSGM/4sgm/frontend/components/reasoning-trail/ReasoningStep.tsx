import React, { useState } from 'react'
import { BadgeWidget } from '../widgets/Badge'
import type { AgentReasoningEvent } from './ReasoningTrail'

interface ReasoningStepProps {
  event: AgentReasoningEvent
}

/**
 * ReasoningStep - Display a single reasoning event
 */
export function ReasoningStep({ event }: ReasoningStepProps) {
  const [expanded, setExpanded] = useState(true)

  const phaseEmoji = {
    reflect: '🔍',
    plan: '📋',
    execute: '⚙️',
    reason: '🧠',
  }[event.phase] || '⛬'

  const stageLabel = {
    analyzing: 'Analyzing',
    evaluating: 'Evaluating',
    deciding: 'Deciding',
    confirming: 'Confirming',
  }[event.stage] || event.stage

  return (
    <div className="bg-white rounded-lg border border-blue-200 overflow-hidden shadow-sm hover:shadow-md transition-shadow">
      {/* Header */}
      <div
        className="p-4 bg-gradient-to-r from-blue-50 to-blue-100 border-b border-blue-200 cursor-pointer hover:bg-blue-100"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-2xl">{phaseEmoji}</span>
              <div>
                <h3 className="font-bold text-gray-900">{event.subject}</h3>
                <p className="text-xs text-gray-600">{stageLabel}</p>
              </div>
            </div>
          </div>
          <div className="text-right">
            <BadgeWidget
              text="Confidence"
              score={event.confidence}
              icon={event.confidence >= 0.8 ? 'checkmark' : undefined}
              inline={true}
            />
          </div>
        </div>
      </div>

      {/* Content */}
      {expanded && (
        <div className="p-4 space-y-4">
          {/* Reasoning description */}
          <div>
            <p className="text-sm text-gray-700 italic">{event.reasoning}</p>
          </div>

          {/* Options considered */}
          {event.options_considered && event.options_considered.length > 0 && (
            <div>
              <p className="text-xs font-bold text-gray-900 mb-2">Options Considered:</p>
              <div className="space-y-2">
                {event.options_considered.map((option, idx) => (
                  <div
                    key={idx}
                    className={`p-3 rounded-lg border ${
                      option.selected
                        ? 'bg-green-50 border-green-300'
                        : 'bg-gray-50 border-gray-200'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <p className="text-sm font-medium text-gray-900">
                          {option.option}
                          {option.selected && <span className="ml-2 text-green-700">✓ SELECTED</span>}
                        </p>
                        {option.pros && option.pros.length > 0 && (
                          <ul className="text-xs text-green-700 mt-1 ml-4">
                            {option.pros.map((pro, i) => (
                              <li key={i}>+ {pro}</li>
                            ))}
                          </ul>
                        )}
                        {option.cons && option.cons.length > 0 && (
                          <ul className="text-xs text-red-700 mt-1 ml-4">
                            {option.cons.map((con, i) => (
                              <li key={i}>- {con}</li>
                            ))}
                          </ul>
                        )}
                      </div>
                      <div className="ml-4 text-right">
                        <div className="text-lg font-bold text-gray-900">
                          {(option.score * 100).toFixed(0)}%
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Decision */}
          <div className="p-3 bg-green-50 border border-green-300 rounded-lg">
            <p className="text-sm font-medium text-green-900">
              <span className="text-lg mr-2">✓</span>
              {event.decision}
            </p>
          </div>

          {/* Citations */}
          {event.citations && event.citations.length > 0 && (
            <div className="pt-2 border-t border-gray-200">
              <p className="text-xs font-bold text-gray-600 mb-2">Evidence:</p>
              <div className="space-y-1">
                {event.citations.map((citation, idx) => (
                  <p key={idx} className="text-xs text-gray-600">
                    • {citation}
                  </p>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Collapse indicator */}
      {!expanded && (
        <div className="px-4 py-2 bg-gray-50 border-t border-gray-200 text-xs text-gray-500">
          Click to expand details
        </div>
      )}
    </div>
  )
}
