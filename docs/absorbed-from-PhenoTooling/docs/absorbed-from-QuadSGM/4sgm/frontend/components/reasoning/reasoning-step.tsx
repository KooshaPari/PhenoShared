"use client";

import { memo } from 'react';
import clsx from 'clsx';
import { Brain, ClipboardList, Search, Zap, CheckCircle2, Circle } from 'lucide-react';
import type { SSEAgentReasoningEvent, SSEOptionItem } from '@/types/sse';

type ReasoningStepProps = {
  event: SSEAgentReasoningEvent;
  dense?: boolean;
};

const phaseMeta: Record<
  SSEAgentReasoningEvent['phase'],
  { label: string; icon: typeof Brain; color: string }
> = {
  reflect: { label: 'Reflect', icon: Search, color: 'text-purple-600 bg-purple-50' },
  plan: { label: 'Plan', icon: ClipboardList, color: 'text-blue-600 bg-blue-50' },
  execute: { label: 'Execute', icon: Zap, color: 'text-emerald-600 bg-emerald-50' },
};

const stageLabel: Record<SSEAgentReasoningEvent['stage'], string> = {
  analyzing: 'Analyzing',
  evaluating: 'Evaluating',
  deciding: 'Deciding',
  confirming: 'Confirming',
};

const confidenceColor = (score: number) => {
  if (score >= 0.85) return 'bg-emerald-50 text-emerald-700 border-emerald-200';
  if (score >= 0.75) return 'bg-blue-50 text-blue-700 border-blue-200';
  if (score >= 0.5) return 'bg-amber-50 text-amber-700 border-amber-200';
  return 'bg-red-50 text-red-700 border-red-200';
};

const OptionList = ({ options }: { options: SSEOptionItem[] }) => (
  <div className="mt-3 space-y-2">
    {options.map((option) => (
      <div
        key={option.option}
        className={clsx(
          'rounded-lg border p-2 text-xs',
          option.selected
            ? 'border-emerald-200 bg-emerald-50'
            : 'border-gray-200 bg-white'
        )}
      >
        <div className="flex items-center justify-between text-sm font-semibold text-gray-800">
          <span>{option.option}</span>
          <span className="text-gray-500">{Math.round(option.score * 100)}%</span>
        </div>
        <div className="mt-1 grid gap-2 sm:grid-cols-2">
          <div>
            <p className="text-[11px] font-semibold uppercase text-gray-500">Pros</p>
            <ul className="list-disc pl-4 text-[11px] text-gray-600">
              {option.pros.map((pro) => (
                <li key={pro}>{pro}</li>
              ))}
            </ul>
          </div>
          <div>
            <p className="text-[11px] font-semibold uppercase text-gray-500">Cons</p>
            <ul className="list-disc pl-4 text-[11px] text-gray-600">
              {option.cons.map((con) => (
                <li key={con}>{con}</li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    ))}
  </div>
);

const ReasoningStep = memo(({ event, dense = false }: ReasoningStepProps) => {
  const phase = phaseMeta[event.phase];
  const PhaseIcon = phase.icon;

  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-4 text-sm shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <div className={clsx('flex h-10 w-10 items-center justify-center rounded-full', phase.color)}>
            <PhaseIcon size={18} />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase text-gray-500">
              {phase.label} · {stageLabel[event.stage]}
            </p>
            <p className="text-base font-semibold text-gray-900">{event.subject}</p>
          </div>
        </div>
        <span
          className={clsx(
            'rounded-full border px-3 py-1 text-xs font-semibold',
            confidenceColor(event.confidence)
          )}
        >
          {(event.confidence * 100).toFixed(0)}% confidence
        </span>
      </div>

      <p className="mt-3 text-sm text-gray-700">{event.reasoning}</p>

      {!dense && event.options_considered.length > 0 && <OptionList options={event.options_considered} />}

      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-gray-600">
        <span className="flex items-center gap-1 rounded-full bg-gray-100 px-2 py-1 font-semibold text-gray-700">
          <CheckCircle2 size={14} className="text-emerald-600" />
          {event.decision}
        </span>
        {event.citations?.length ? (
          <span className="flex items-center gap-1 rounded-full bg-gray-100 px-2 py-1 text-gray-600">
            <Circle size={12} /> {event.citations.length} citations
          </span>
        ) : null}
        <span className="text-[11px] uppercase tracking-wide text-gray-400">
          {new Date(event.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
      </div>
    </div>
  );
});

ReasoningStep.displayName = 'ReasoningStep';

export default ReasoningStep;
