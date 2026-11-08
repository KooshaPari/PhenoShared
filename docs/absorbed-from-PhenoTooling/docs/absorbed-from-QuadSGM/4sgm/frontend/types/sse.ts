/**
 * Type Contracts for 4SGM Chatbot SSE/API Communication
 * MUST match backend/types.py exactly
 */

import type { SessionActionRequest } from './session';

export type SSETokenEvent = {
  type: 'token';
  timestamp: string;
  data: string; // The actual token text
  token_count: number;
};

export type SSEProgressEvent = {
  type: 'progress';
  timestamp: string;
  character_count: number;
  token_count: number;
};

export type SSECompleteEvent = {
  type: 'complete';
  timestamp: string;
  message: string; // Full accumulated message
  session_id: string;
  token_count: number;
  character_count: number;
  documents_used: number;
};

export type SSEErrorEvent = {
  type: 'error';
  timestamp: string;
  message: string;
};

export type SSEMetadataEvent = {
  type: 'metadata';
  timestamp: string;
  session_id: string;
  document_count: number;
};

export type SSEResearchEvent = {
  type: 'research';
  timestamp: string;
  stage: 'reflect' | 'plan' | 'execute' | 'reason' | 'synthesis';
  heading: string;
  details: string;
  citations: string[] | null;
  evidence?: Record<string, unknown>[];
  metrics?: Record<string, number>;
};

export type SSEOptionItem = {
  option: string;
  pros: string[];
  cons: string[];
  score: number;
  selected?: boolean;
};

export type SSEAgentReasoningEvent = {
  type: 'agent_reasoning';
  timestamp: string;
  phase: 'reflect' | 'plan' | 'execute';
  stage: 'analyzing' | 'evaluating' | 'deciding' | 'confirming';
  subject: string;
  reasoning: string;
  options_considered: SSEOptionItem[];
  decision: string;
  confidence: number;
  citations?: string[];
};

// Union of all possible SSE events
export type CartPlanCategory = {
  name: string;
  budget: number;
  units: number;
  avgUnitCost: number;
  notes: string;
  share: number;
  items: Array<{ sku: string; name: string; units: number }>;
};

export type CartPlanWidgetData = {
  kind: 'cart_plan';
  budget: number;
  totalUnits: number;
  categories: CartPlanCategory[];
};

export type LogisticsPlanWidgetData = {
  kind: 'logistics_plan';
  containerType: string;
  quantity: number;
  totalShippingCost: number;
  leadTimeDays: number;
  palletsTotal: number;
  costPerUnit: number;
};

export type QuoteSummaryWidgetData = {
  kind: 'quote_summary';
  quoteId: string;
  total: number;
  discountPercent: number;
  netTerms: string;
  validUntil: string;
  itemsCount: number | null;
  totalUnits: number | null;
};

export type AssistantWidgetData =
  | CartPlanWidgetData
  | LogisticsPlanWidgetData
  | QuoteSummaryWidgetData;

export type SSEBadgeWidgetProps = {
  text: string;
  score?: number;
  title?: string;
  label?: string;
  value?: string | number;
  color?: string;
  icon?: string;
};

export type SSEMeterWidgetProps = {
  title?: string;
  label?: string;
  color?: string;
  current: number;
  threshold: number;
  unit: string;
  show_percentage?: boolean;
};

export type SSETagWidgetProps = {
  text: string;
  variant: 'default' | 'success' | 'warning' | 'danger' | 'info';
  label?: string;
  icon?: string;
};

export type SSEComparisonOption = {
  name: string;
  pros: string[];
  cons: string[];
  score: number;
  recommended?: boolean;
};

export type SSEComparisonWidgetProps = {
  title?: string;
  options: SSEComparisonOption[];
};

export type SSEMetric = {
  label: string;
  value: string | number;
  unit?: string;
  color?: string;
  bold?: boolean;
};

export type SSEMetricsCardWidgetProps = {
  title?: string;
  metrics: SSEMetric[];
};

export type SSEDistributionDataPoint = {
  label: string;
  value: number;
  percentage?: number;
  color?: string;
  units?: number;
};

export type SSEDistributionChartWidgetProps = {
  chart_type: 'pie' | 'bar' | 'stacked_bar';
  data: SSEDistributionDataPoint[];
  total?: number;
  title?: string;
};

export type SSETimelineEvent = {
  label: string;
  date: string;
  status: 'completed' | 'current' | 'scheduled' | 'delayed';
};

export type SSETimelineWidgetProps = {
  events: SSETimelineEvent[];
  buffer_days?: number;
  deadline?: string;
  title?: string;
};

export type SSEDecisionNode = {
  question: string;
  children?: SSEDecisionNode[];
  label?: string;
  outcome?: string;
  icon?: string;
};

export type SSEDecisionTreeWidgetProps = {
  title?: string;
  root: SSEDecisionNode;
};

export type SSEWidgetEvent = {
  type: 'widget';
  timestamp: string;
  widget_type:
    | 'badge'
    | 'meter'
    | 'tag'
    | 'comparison'
    | 'metrics_card'
    | 'distribution_chart'
    | 'timeline'
    | 'decision_tree';
  placement: 'inline' | 'message' | 'embedded';
  props:
    | SSEBadgeWidgetProps
    | SSEMeterWidgetProps
    | SSETagWidgetProps
    | SSEComparisonWidgetProps
    | SSEMetricsCardWidgetProps
    | SSEDistributionChartWidgetProps
    | SSETimelineWidgetProps
    | SSEDecisionTreeWidgetProps;
  markdown?: string;
};

export type SSEInsightEvent = {
  type: 'insight';
  timestamp: string;
  widgets: AssistantWidgetData[];
};

export type NavigateControlAction = {
  kind: 'navigate';
  path: string;
  label: string;
  announce?: string;
  sessionAction?: SessionActionRequest;
};

export type SessionControlAction = {
  kind: 'session_action';
  action: SessionActionRequest;
  label: string;
  announce?: string;
};

export type ControlAction = NavigateControlAction | SessionControlAction;

export type SSEControlEvent = {
  type: 'control';
  timestamp: string;
  session_id: string;
  actions: ControlAction[];
};

export type SSEEvent =
  | SSETokenEvent
  | SSEProgressEvent
  | SSECompleteEvent
  | SSEErrorEvent
  | SSEMetadataEvent
  | SSEResearchEvent
  | SSEAgentReasoningEvent
  | SSEWidgetEvent
  | SSEInsightEvent
  | SSEControlEvent;

/**
 * Type guard functions for safe event handling
 */
export function isTokenEvent(event: SSEEvent): event is SSETokenEvent {
  return event.type === 'token';
}

export function isProgressEvent(event: SSEEvent): event is SSEProgressEvent {
  return event.type === 'progress';
}

export function isCompleteEvent(event: SSEEvent): event is SSECompleteEvent {
  return event.type === 'complete';
}

export function isErrorEvent(event: SSEEvent): event is SSEErrorEvent {
  return event.type === 'error';
}

export function isMetadataEvent(event: SSEEvent): event is SSEMetadataEvent {
  return event.type === 'metadata';
}

export function isResearchEvent(event: SSEEvent): event is SSEResearchEvent {
  return event.type === 'research';
}

export function isReasoningEvent(event: SSEEvent): event is SSEAgentReasoningEvent {
  return event.type === 'agent_reasoning';
}

export function isWidgetEvent(event: SSEEvent): event is SSEWidgetEvent {
  return event.type === 'widget';
}

export function isInsightEvent(event: SSEEvent): event is SSEInsightEvent {
  return event.type === 'insight';
}

export function isControlEvent(event: SSEEvent): event is SSEControlEvent {
  return event.type === 'control';
}
