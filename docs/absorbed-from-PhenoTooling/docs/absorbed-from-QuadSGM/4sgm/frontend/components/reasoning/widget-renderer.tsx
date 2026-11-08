"use client";

import { memo, type ReactNode } from 'react';
import clsx from 'clsx';
import {
  BarChart3,
  Circle,
  GitBranch,
  LayoutList,
  ListChecks,
  PieChart,
  TrendingUp,
} from 'lucide-react';
import type {
  SSEWidgetEvent,
  SSEDecisionTreeWidgetProps,
  SSEDecisionNode,
  SSEBadgeWidgetProps,
  SSEMeterWidgetProps,
  SSETagWidgetProps,
  SSEComparisonWidgetProps,
  SSEMetricsCardWidgetProps,
  SSEDistributionChartWidgetProps,
  SSETimelineWidgetProps,
} from '@/types/sse';

type WidgetRendererProps = {
  event: SSEWidgetEvent;
  compact?: boolean;
};

const placementClass: Record<SSEWidgetEvent['placement'], string> = {
  inline: 'rounded-full border px-3 py-1 text-xs font-semibold',
  message: 'rounded-2xl border px-4 py-3 text-sm shadow-sm',
  embedded: 'rounded-2xl border px-4 py-4 text-sm shadow-sm',
};

const colorClass = (color?: string) => {
  switch (color) {
    case 'green':
    case 'emerald':
      return 'text-emerald-700';
    case 'blue':
      return 'text-blue-700';
    case 'yellow':
    case 'amber':
      return 'text-amber-700';
    case 'red':
      return 'text-red-700';
    case 'purple':
      return 'text-purple-700';
    case 'orange':
      return 'text-orange-700';
    default:
      return 'text-gray-700';
  }
};

const renderBadge = (props: SSEBadgeWidgetProps) => (
  <div className="flex items-center gap-2 text-xs font-semibold">
    <Circle size={10} className={colorClass(props.color)} />
    <span>{props.text ?? 'Badge'}</span>
    {typeof props.score === 'number' && <span>{Math.round(props.score * 100)}%</span>}
  </div>
);

const renderMeter = (props: SSEMeterWidgetProps) => {
  const current = Number(props.current ?? 0);
  const threshold = Number(props.threshold || 1);
  const pct = Math.min(100, Math.round((current / threshold) * 100));
  return (
    <div>
      <div className="flex items-center justify-between text-xs font-semibold text-gray-700">
        <span>{props.label ?? 'Progress'}</span>
        <span>
          {current.toLocaleString()} / {threshold.toLocaleString()} {props.unit}
        </span>
      </div>
      <div className="mt-1 h-2 rounded-full bg-gray-100">
        <div className="h-full rounded-full bg-blue-500" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
};

const renderTag = (props: SSETagWidgetProps) => (
  <span className="inline-flex items-center rounded-full bg-gray-100 px-3 py-1 text-xs font-semibold text-gray-700">
    {props.text}
  </span>
);

const renderComparison = (props: SSEComparisonWidgetProps) => (
  <div className="space-y-2">
    {props.options.map((opt) => (
      <div key={opt.name} className="rounded-lg border border-gray-200 bg-white p-3 text-xs">
        <div className="flex items-center justify-between text-sm font-semibold text-gray-900">
          <span>{opt.name}</span>
          <span className="text-gray-500">{Math.round(opt.score * 100)}%</span>
        </div>
        <div className="mt-1 grid gap-2 sm:grid-cols-2">
          <div>
            <p className="text-[11px] font-semibold uppercase text-emerald-600">Pros</p>
            <ul className="list-disc pl-4 text-[11px] text-gray-600">
              {opt.pros.map((pro) => (
                <li key={pro}>{pro}</li>
              ))}
            </ul>
          </div>
          <div>
            <p className="text-[11px] font-semibold uppercase text-rose-600">Cons</p>
            <ul className="list-disc pl-4 text-[11px] text-gray-600">
              {opt.cons.map((con) => (
                <li key={con}>{con}</li>
              ))}
            </ul>
          </div>
        </div>
        {opt.recommended && (
          <div className="mt-2 inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-1 text-[11px] font-semibold text-emerald-700">
            <ListChecks size={12} /> Recommended
          </div>
        )}
      </div>
    ))}
  </div>
);

const renderMetricsCard = (props: SSEMetricsCardWidgetProps) => (
  <div className="grid gap-3 sm:grid-cols-2">
    {props.metrics.map((metric) => (
      <div key={metric.label} className="rounded-lg border border-gray-100 bg-gray-50 p-3">
        <p className="text-xs font-semibold uppercase text-gray-500">{metric.label}</p>
        <p className={clsx('text-lg font-semibold', colorClass(metric.color))}>{metric.value}</p>
        {metric.unit && <p className="text-xs text-gray-500">{metric.unit}</p>}
      </div>
    ))}
  </div>
);

const renderDistribution = (props: SSEDistributionChartWidgetProps) => (
  <div className="space-y-2">
    {props.data.map((point) => (
      <div key={point.label}>
        <div className="flex items-center justify-between text-xs font-semibold text-gray-700">
          <span>{point.label}</span>
          <span>{point.percentage ? `${Math.round(point.percentage)}%` : point.value}</span>
        </div>
        <div className="mt-1 h-2 rounded-full bg-gray-100">
          <div
            className="h-full rounded-full bg-emerald-500"
            style={{ width: `${Math.min(100, point.percentage ?? 0)}%` }}
          />
        </div>
      </div>
    ))}
  </div>
);

const renderTimeline = (props: SSETimelineWidgetProps) => (
  <div className="space-y-3">
    {props.events.map((timelineEvent) => (
      <div key={`${timelineEvent.label}-${timelineEvent.date}`} className="flex items-center gap-3">
        <div
          className={clsx(
            'flex h-8 w-8 items-center justify-center rounded-full text-xs font-semibold',
            timelineEvent.status === 'completed'
              ? 'bg-emerald-50 text-emerald-700'
              : timelineEvent.status === 'current'
                ? 'bg-blue-50 text-blue-700'
                : 'bg-gray-100 text-gray-500'
          )}
        >
          {timelineEvent.status === 'scheduled' ? '•' : timelineEvent.status.slice(0, 1).toUpperCase()}
        </div>
        <div className="text-xs text-gray-700">
          <p className="font-semibold text-gray-900">{timelineEvent.label}</p>
          <p className="text-[11px] text-gray-500">{timelineEvent.date}</p>
        </div>
      </div>
    ))}
  </div>
);

const renderDecisionTree = (props: SSEDecisionTreeWidgetProps) => {
  if (!props.root) return null;

  const renderNode = (node: SSEDecisionNode, depth = 0): ReactNode => (
    <div className="pl-3">
      <p className="text-xs font-semibold text-gray-800">
        {'— '.repeat(depth)}
        {node.question}
      </p>
      {node.outcome && <p className="text-[11px] text-gray-500">Outcome: {node.outcome}</p>}
      {node.children?.length ? (
        <div className="ml-3 border-l border-gray-200 pl-3">
          {node.children.map((child) => (
            <div key={child.question}>{renderNode(child, depth + 1)}</div>
          ))}
        </div>
      ) : null}
    </div>
  );

  return renderNode(props.root);
};

const iconMap: Record<SSEWidgetEvent['widget_type'], typeof PieChart> = {
  badge: Circle,
  meter: TrendingUp,
  tag: LayoutList,
  comparison: ListChecks,
  metrics_card: BarChart3,
  distribution_chart: PieChart,
  timeline: ListChecks,
  decision_tree: GitBranch,
};

export const WidgetRenderer = memo(({ event, compact = false }: WidgetRendererProps) => {
  const Icon = iconMap[event.widget_type];

  type WidgetPropsByType = {
    badge: SSEBadgeWidgetProps;
    meter: SSEMeterWidgetProps;
    tag: SSETagWidgetProps;
    comparison: SSEComparisonWidgetProps;
    metrics_card: SSEMetricsCardWidgetProps;
    distribution_chart: SSEDistributionChartWidgetProps;
    timeline: SSETimelineWidgetProps;
    decision_tree: SSEDecisionTreeWidgetProps;
  };

  const getProps = <T extends SSEWidgetEvent['widget_type']>(
    evt: SSEWidgetEvent,
    type: T,
  ): WidgetPropsByType[T] | undefined => {
    if (evt.widget_type !== type) return undefined;
    return evt.props as WidgetPropsByType[T];
  };

  let body: ReactNode = null;
  switch (event.widget_type) {
    case 'badge': {
      const props = getProps(event, 'badge');
      body = props ? renderBadge(props) : null;
      break;
    }
    case 'meter': {
      const props = getProps(event, 'meter');
      body = props ? renderMeter(props) : null;
      break;
    }
    case 'tag': {
      const props = getProps(event, 'tag');
      body = props ? renderTag(props) : null;
      break;
    }
    case 'comparison': {
      const props = getProps(event, 'comparison');
      body = props ? renderComparison(props) : null;
      break;
    }
    case 'metrics_card': {
      const props = getProps(event, 'metrics_card');
      body = props ? renderMetricsCard(props) : null;
      break;
    }
    case 'distribution_chart': {
      const props = getProps(event, 'distribution_chart');
      body = props ? renderDistribution(props) : null;
      break;
    }
    case 'timeline': {
      const props = getProps(event, 'timeline');
      body = props ? renderTimeline(props) : null;
      break;
    }
    case 'decision_tree': {
      const props = getProps(event, 'decision_tree');
      body = props ? renderDecisionTree(props) : null;
      break;
    }
    default:
      body = <div className="text-xs text-gray-500">Unsupported widget</div>;
  }

  return (
    <div
      className={clsx(
        'border border-gray-200 bg-white',
        placementClass[event.placement],
        compact && 'text-xs'
      )}
      data-widget-type={event.widget_type}
    >
      <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
        {Icon ? <Icon size={14} /> : null}
        <span>{event.widget_type.replace('_', ' ')}</span>
      </div>
      {body}
    </div>
  );
});

WidgetRenderer.displayName = 'WidgetRenderer';
