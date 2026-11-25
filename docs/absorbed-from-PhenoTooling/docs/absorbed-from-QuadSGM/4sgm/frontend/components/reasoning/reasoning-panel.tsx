"use client";

import { memo, useState } from 'react';
import { X, Brain, ChevronDown, ChevronRight } from 'lucide-react';
import type { SSEAgentReasoningEvent, SSEWidgetEvent } from '@/types/sse';
import ReasoningStep from './reasoning-step';
import { WidgetRenderer } from './widget-renderer';

type ReasoningPanelProps = {
  open: boolean;
  onClose: () => void;
  reasoning: SSEAgentReasoningEvent[];
  widgets: SSEWidgetEvent[];
  defaultCollapsed?: boolean;
};

const ReasoningPanel = memo(({ open, onClose, reasoning, widgets, defaultCollapsed = false }: ReasoningPanelProps) => {
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-stretch justify-end">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} role="presentation" />
      <aside className="relative ml-auto flex h-full w-full max-w-md flex-col bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
          <div className="flex items-center gap-2 text-gray-800">
            <Brain size={18} className="text-blue-600" />
            <div>
              <p className="text-sm font-semibold">Reasoning Trail</p>
              <p className="text-xs text-gray-500">{reasoning.length} steps • {widgets.length} widgets</p>
            </div>
          </div>
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => setIsCollapsed(!isCollapsed)}
              className="rounded-full p-1 text-gray-500 transition hover:bg-gray-100"
              aria-label={isCollapsed ? "Expand reasoning panel" : "Collapse reasoning panel"}
            >
              {isCollapsed ? <ChevronRight size={18} /> : <ChevronDown size={18} />}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="rounded-full p-1 text-gray-500 transition hover:bg-gray-100"
              aria-label="Close reasoning panel"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        <div className={`flex-1 overflow-y-auto bg-gray-50 transition-all duration-200 ${isCollapsed ? 'hidden' : 'p-4'}`}>
          {reasoning.length === 0 && widgets.length === 0 ? (
            <p className="text-sm text-gray-500">No reasoning steps streamed yet.</p>
          ) : (
            <div className="space-y-4">
              {reasoning.map((event) => (
                <ReasoningStep key={event.timestamp + event.subject} event={event} dense />
              ))}

              {widgets.length > 0 && (
                <div className="space-y-3">
                  <p className="text-xs font-semibold uppercase text-gray-500">Widgets</p>
                  {widgets.map((event, idx) => (
                    <WidgetRenderer key={`${event.widget_type}-${idx}-${event.timestamp}`} event={event} />
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </aside>
    </div>
  );
});

ReasoningPanel.displayName = 'ReasoningPanel';

export default ReasoningPanel;
