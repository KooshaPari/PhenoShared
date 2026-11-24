'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import type { PointerEvent as ReactPointerEvent } from 'react';
import { useRouter } from 'next/navigation';
import { useSession } from '@/components/session-provider';
import { Send, X, MessageCircle, Package, RefreshCw, CreditCard, BookOpen, Loader, Maximize2, Beaker, Brain } from 'lucide-react';
import type {
  SSEEvent,
  AssistantWidgetData,
  ControlAction,
  SSEAgentReasoningEvent,
  SSEWidgetEvent,
} from '@/types/sse';
import {
  isTokenEvent,
  isProgressEvent,
  isCompleteEvent,
  isErrorEvent,
  isMetadataEvent,
  isResearchEvent,
  isInsightEvent,
  isControlEvent,
  isReasoningEvent,
  isWidgetEvent,
} from '@/types/sse';
import type { SessionSnapshot, SessionActionRequest } from '@/types/session';
import { createSession as createServerSession, fetchSessionSnapshot, postSessionAction } from '@/lib/session-api';
import ReasoningStep from '@/components/reasoning/reasoning-step';
import { WidgetRenderer } from '@/components/reasoning/widget-renderer';
import ReasoningPanel from '@/components/reasoning/reasoning-panel';

const WIDGET_MIN_WIDTH = 360;
const WIDGET_MIN_HEIGHT = 420;
const WIDGET_MAX_WIDTH = 1200;
const WIDGET_MAX_HEIGHT = 820;

const clamp = (value: number, min: number, max: number) => Math.min(Math.max(value, min), max);

type Message = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  isStreaming?: boolean; // True while receiving tokens
  sources?: Array<{
    title: string;
    content: string;
    category: string;
    similarity: number;
  }>;
  confidence?: number;
  requiresEscalation?: boolean;
  tokenCount?: number;
  characterCount?: number;
  researchLogs?: ResearchLog[];
  insights?: SessionInsight[];
  widgets?: AssistantWidgetData[];
  reasoningSteps?: SSEAgentReasoningEvent[];
  widgetEvents?: SSEWidgetEvent[];
};
type ResearchLog = {
  stage: 'reflect' | 'plan' | 'execute' | 'reason' | 'synthesis';
  heading: string;
  details: string;
  citations?: string[] | null;
};

type SessionInsight =
  | {
      type: 'profile';
      profile: {
        name: string;
        company: string;
        tier: string;
        email: string;
        phone: string;
        accountValue: number;
        rep?: string | null;
      };
    }
  | {
      type: 'cart';
      cart: {
        subtotal: number;
        discounts: number;
        total: number;
        itemCount: number;
      };
    }
  | {
      type: 'knowledge';
      signals: SessionSnapshot['knowledgeSignals'];
    }
  | {
      type: 'quickLinks';
      links: { label: string; path: string }[];
    };

type DragContext = { type: 'widget'; startX: number; startY: number; startWidth: number; startHeight: number };

const currencyFormatter = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' });

const formatCurrency = (value: number) => currencyFormatter.format(value ?? 0);

const formatNumber = (value: number) => (Number.isFinite(value) ? value.toLocaleString('en-US') : '0');

const hashSnapshot = (snapshot: SessionSnapshot): string =>
  JSON.stringify({
    sessionId: snapshot.sessionId,
    user: snapshot.user,
    cart: {
      subtotal: snapshot.cart.subtotal,
      discounts: snapshot.cart.discounts,
      total: snapshot.cart.total,
      items: snapshot.cart.items.map((item) => ({ sku: item.sku, quantity: item.quantity })),
    },
    knowledge: snapshot.knowledgeSignals,
    capabilities: snapshot.capabilities,
  });

const buildInsights = (snapshot: SessionSnapshot): SessionInsight[] => {
  const insights: SessionInsight[] = [];

  insights.push({
    type: 'profile',
    profile: {
      name: snapshot.user.name,
      company: snapshot.user.company,
      tier: snapshot.user.tier,
      email: snapshot.user.email,
      phone: snapshot.user.phone,
      accountValue: snapshot.user.accountValue,
      rep: snapshot.user.assignedRep,
    },
  });

  const itemCount = snapshot.cart.items.reduce((acc, item) => acc + item.quantity, 0);
  insights.push({
    type: 'cart',
    cart: {
      subtotal: snapshot.cart.subtotal,
      discounts: snapshot.cart.discounts,
      total: snapshot.cart.total,
      itemCount,
    },
  });

  if (snapshot.knowledgeSignals?.length) {
    insights.push({ type: 'knowledge', signals: snapshot.knowledgeSignals });
  }

  const quickLinks = snapshot.capabilities?.quickLinks ?? [];
  if (quickLinks.length) {
    insights.push({
      type: 'quickLinks',
      links: quickLinks.map((link) => ({ label: link.label, path: link.path })),
    });
  }

  return insights;
};

export default function ChatWidget() {
  const router = useRouter();
  const { sessionId: globalSessionId } = useSession();

  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  // Always use globalSessionId - SessionProvider guarantees it's initialized
  const sessionId = globalSessionId;
  const [sessionData, setSessionData] = useState<SessionSnapshot | null>(null);
  const [sessionError, setSessionError] = useState<string | null>(null);
  const [sessionBusy, setSessionBusy] = useState(false);
  const [widgetSize, setWidgetSize] = useState({ width: 960, height: 620 });
  const [isDesktop, setIsDesktop] = useState(false);
  const [reasoningTimeline, setReasoningTimeline] = useState<SSEAgentReasoningEvent[]>([]);
  const [widgetTimeline, setWidgetTimeline] = useState<SSEWidgetEvent[]>([]);
  const [isReasoningPanelOpen, setIsReasoningPanelOpen] = useState(true); // Always show, collapsed by default
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const dragContextRef = useRef<DragContext | null>(null);
  const widgetSizeRef = useRef(widgetSize);
  const lastSnapshotHashRef = useRef<string | null>(null);

  const pushSessionInsights = useCallback(
    (snapshot: SessionSnapshot, reason: string) => {
      const insights = buildInsights(snapshot);
      if (!insights.length) return;
      const message: Message = {
        id: `insight-${Date.now()}`,
        role: 'assistant',
        content: reason,
        insights,
      };
      setMessages((prev) => [...prev, message]);
    },
    [setMessages]
  );

  const maybeInjectSessionInsights = useCallback(
    (snapshot: SessionSnapshot, reason: string, force = false) => {
      const hash = hashSnapshot(snapshot);
      if (!force && hash === lastSnapshotHashRef.current) {
        return;
      }
      lastSnapshotHashRef.current = hash;
      pushSessionInsights(snapshot, reason);
    },
    [pushSessionInsights]
  );

  // Auto-scroll to latest message
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    widgetSizeRef.current = widgetSize;
  }, [widgetSize]);

  useEffect(() => {
    if (!isOpen) {
      setIsReasoningPanelOpen(false);
    }
  }, [isOpen]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const media = window.matchMedia('(min-width: 1024px)');
    const handleChange = () => setIsDesktop(media.matches);
    handleChange();
    media.addEventListener('change', handleChange);
    return () => media.removeEventListener('change', handleChange);
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const syncSizes = () => {
      const widthLimit = Math.max(
        WIDGET_MIN_WIDTH,
        Math.min(WIDGET_MAX_WIDTH, window.innerWidth - 32)
      );
      const heightLimit = Math.max(
        WIDGET_MIN_HEIGHT,
        Math.min(WIDGET_MAX_HEIGHT, window.innerHeight - 32)
      );
      setWidgetSize((prev) => ({
        width: clamp(prev.width, WIDGET_MIN_WIDTH, widthLimit),
        height: clamp(prev.height, WIDGET_MIN_HEIGHT, heightLimit),
      }));
    };

    syncSizes();
    window.addEventListener('resize', syncSizes);
    return () => window.removeEventListener('resize', syncSizes);
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const handleMove = (event: PointerEvent) => {
      const ctx = dragContextRef.current;
      if (!ctx) return;
      event.preventDefault();

      if (ctx.type === 'widget') {
        const deltaX = event.clientX - ctx.startX;
        const deltaY = event.clientY - ctx.startY;
        const widthLimit = Math.max(
          WIDGET_MIN_WIDTH,
          Math.min(WIDGET_MAX_WIDTH, window.innerWidth - 32)
        );
        const heightLimit = Math.max(
          WIDGET_MIN_HEIGHT,
          Math.min(WIDGET_MAX_HEIGHT, window.innerHeight - 32)
        );
        setWidgetSize({
          width: clamp(ctx.startWidth + deltaX, WIDGET_MIN_WIDTH, widthLimit),
          height: clamp(ctx.startHeight + deltaY, WIDGET_MIN_HEIGHT, heightLimit),
        });
      }
    };

    const handleUp = () => {
      if (dragContextRef.current && typeof document !== 'undefined') {
        document.body.style.userSelect = '';
      }
      dragContextRef.current = null;
    };

    window.addEventListener('pointermove', handleMove);
    window.addEventListener('pointerup', handleUp);
    return () => {
      window.removeEventListener('pointermove', handleMove);
      window.removeEventListener('pointerup', handleUp);
    };
  }, []);

  const hydrateSession = useCallback(async (id: string) => {
    setSessionError(null);
    try {
      const snapshot = await fetchSessionSnapshot(id);
      setSessionData(snapshot);
      // setSessionId is not available in this component; sessionId comes from SessionProvider
      maybeInjectSessionInsights(snapshot, 'Session insights updated');
      return true;
    } catch (error) {
      setSessionError(error instanceof Error ? error.message : 'Unable to load session insights');
      // setSessionId is not available in this component; reset via SessionProvider if needed
      return false;
    }
  }, [maybeInjectSessionInsights]);

  const ensureSession = useCallback(async (): Promise<boolean> => {
    // Session is guaranteed to exist from SessionProvider (persisted via cookies)
    if (sessionId) {
      if (!sessionData) {
        return hydrateSession(sessionId);
      }
      return true;
    }

    // Fallback: Create session if somehow missing (shouldn't happen with SessionProvider guard)
    setSessionError(null);
    try {
      const snapshot = await createServerSession();
      setSessionData(snapshot);
      maybeInjectSessionInsights(snapshot, 'Session created', true);
      return true;
    } catch (error) {
      setSessionError(error instanceof Error ? error.message : 'Unable to create session');
      return false;
    }
  }, [sessionId, sessionData, hydrateSession, maybeInjectSessionInsights]);

  useEffect(() => {
    void ensureSession();
  }, [ensureSession]);

  useEffect(() => {
    if (isOpen) {
      void ensureSession();
    }
  }, [isOpen, ensureSession]);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const ready = await ensureSession();
    if (!ready || !sessionId) {
      setSessionError('Unable to initialize session. Please refresh.');
      return;
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
    };

    // Add user message
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    // Create placeholder for streaming assistant message
    const assistantMessageId = (Date.now() + 1).toString();
    const placeholderMessage: Message = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      isStreaming: true,
    };

    setMessages((prev) => [...prev, placeholderMessage]);

    // Start streaming
    startStreamingChat(userMessage, assistantMessageId, sessionId);
  };

  const startStreamingChat = (userMessage: Message, messageId: string, activeSessionId: string) => {
    try {
      const historyPayload = JSON.stringify(
        messages.map(({ role, content }) => ({ role, content }))
      );

      const queryParams = new URLSearchParams({
        message: userMessage.content,
        sessionId: activeSessionId,
        history: historyPayload,
      });

      const streamUrl = `/api/chat/stream?${queryParams.toString()}`;
      console.log('[Chat] Starting stream:', streamUrl);

      const eventSource = new EventSource(streamUrl);
      eventSourceRef.current = eventSource;

      let accumulatedContent = '';
      let confidence: number | undefined;
      let tokenCount = 0;
      let characterCount = 0;

      const parseSSEEvent = (eventData: string): SSEEvent | null => {
        try {
          const trimmed = eventData.trim();
          if (!trimmed) return null;
          return JSON.parse(trimmed) as SSEEvent;
        } catch (error) {
          console.error('[Chat] Failed to parse SSE payload:', eventData.slice(0, 100), error);
          return null;
        }
      };

      const handleStreamMessage = (event: MessageEvent<string>) => {
        try {
          const streamEvent = parseSSEEvent(event.data);
          if (!streamEvent) {
            console.warn('[Chat] Received empty or invalid SSE event');
            return;
          }

          if (isTokenEvent(streamEvent)) {
            const tokenEvent = streamEvent;
            accumulatedContent += tokenEvent.data;
            tokenCount = tokenEvent.token_count;

            console.log('[Chat] Token event - accumulated so far:', accumulatedContent.substring(0, 100));

            setMessages((prev) => {
              const updated = prev.map((m) =>
                m.id === messageId
                  ? {
                      ...m,
                      content: accumulatedContent,
                      isStreaming: true,
                      tokenCount,
                    }
                  : m
              );
              console.log('[Chat] Updated message content:', updated.find(m => m.id === messageId)?.content?.substring(0, 100));
              return updated;
            });
          } else if (isResearchEvent(streamEvent)) {
            const researchEvent = streamEvent;
            const log: ResearchLog = {
              stage: researchEvent.stage,
              heading: researchEvent.heading,
              details: researchEvent.details,
              citations: researchEvent.citations,
            };

            setMessages((prev) =>
              prev.map((m) =>
                m.id === messageId
                  ? {
                      ...m,
                      researchLogs: [...(m.researchLogs ?? []), log],
                    }
                  : m
              )
            );
          } else if (isInsightEvent(streamEvent)) {
            if (streamEvent.widgets?.length) {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === messageId
                    ? {
                        ...m,
                        widgets: [...(m.widgets ?? []), ...streamEvent.widgets],
                      }
                    : m
                )
              );
            }
          } else if (isControlEvent(streamEvent)) {
            for (const action of streamEvent.actions) {
              void executeControlAction(action);
            }
          } else if (isReasoningEvent(streamEvent)) {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === messageId
                  ? {
                      ...m,
                      reasoningSteps: [...(m.reasoningSteps ?? []), streamEvent],
                    }
                  : m
              )
            );
            setReasoningTimeline((prev) => [...prev, streamEvent]);
          } else if (isWidgetEvent(streamEvent)) {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === messageId
                  ? {
                      ...m,
                      widgetEvents: [...(m.widgetEvents ?? []), streamEvent],
                    }
                  : m
              )
            );
            setWidgetTimeline((prev) => [...prev, streamEvent]);
          } else if (isProgressEvent(streamEvent)) {
            const progressEvent = streamEvent;
            characterCount = progressEvent.character_count;
            tokenCount = progressEvent.token_count;
          } else if (isCompleteEvent(streamEvent)) {
            const completeEvent = streamEvent;
            const finalContent = completeEvent.message;
            tokenCount = completeEvent.token_count;
            characterCount = completeEvent.character_count;
            confidence = 0.85;

            setMessages((prev) =>
              prev.map((m) =>
                m.id === messageId
                  ? {
                      ...m,
                      content:
                        (m.widgets?.length ?? 0) > 0
                          ? 'Cart and logistics plan ready. Expand the widgets to review every category.'
                          : finalContent,
                      isStreaming: false,
                      tokenCount,
                      characterCount,
                      confidence,
                      requiresEscalation: confidence < 0.6,
                    }
                  : m
              )
            );

            eventSource.close();
            setIsLoading(false);
          } else if (isErrorEvent(streamEvent)) {
            const errorEvent = streamEvent;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === messageId
                  ? {
                      ...m,
                      content: `Error: ${errorEvent.message}. Please try again or contact support@4sgm.com`,
                      isStreaming: false,
                    }
                  : m
              )
            );

            eventSource.close();
            setIsLoading(false);
          } else if (isMetadataEvent(streamEvent)) {
            const metadataEvent = streamEvent;
            console.log('[Chat] Stream metadata:', metadataEvent);
          }
        } catch (parseError) {
          console.error('[Chat] Failed to handle SSE event:', parseError);
        }
      };

      eventSource.addEventListener('message', handleStreamMessage);

      eventSource.onerror = (error) => {
        console.error('[Chat] SSE connection error:', error);
        eventSource.close();
        setIsLoading(false);

        setMessages((prev) =>
          prev.map((m) =>
            m.id === messageId
              ? {
                  ...m,
                  content: 'Connection lost. Please try again or contact support@4sgm.com',
                  isStreaming: false,
                }
              : m
          )
        );
      };
    } catch (error) {
      console.error('[Chat] Setup error:', error);
      setIsLoading(false);

      const errorMessage: Message = {
        id: (Date.now() + 2).toString(),
        role: 'assistant',
        content: `Setup error: ${error instanceof Error ? error.message : 'Unknown error'}. Please try again.`,
      };

      setMessages((prev) => [...prev, errorMessage]);
    }
  };

  const handleSuggestion = (suggestion: string) => {
    setInput(suggestion);
    // Focus input for immediate send
    setTimeout(() => {
      document.querySelector('input')?.focus();
    }, 0);
  };

  const runSessionAction = useCallback(
    async (action: SessionActionRequest, successMessage: string) => {
      const ready = await ensureSession();
      if (!ready || !sessionId) {
        const errorMessage: Message = {
          id: `session-error-${Date.now()}`,
          role: 'assistant',
          content: 'Session unavailable. Please try again.',
        };
        setMessages((prev) => [...prev, errorMessage]);
        return false;
      }

      setSessionBusy(true);
      try {
        const updated = await postSessionAction(sessionId, action);
        setSessionData(updated);
        maybeInjectSessionInsights(updated, successMessage, true);
        return true;
      } catch (error) {
        const details = error instanceof Error ? error.message : 'Session update failed';
        setMessages((prev) => [
          ...prev,
          {
            id: `session-error-${Date.now()}`,
            role: 'assistant',
            content: details,
          },
        ]);
        return false;
      } finally {
        setSessionBusy(false);
      }
    },
    [ensureSession, sessionId, maybeInjectSessionInsights, setMessages]
  );

  const executeControlAction = useCallback(
    async (control: ControlAction) => {
      const announcement = control.announce ?? control.label;
      if (announcement) {
        const controlMessage: Message = {
          id: `control-${Date.now()}`,
          role: 'assistant',
          content: announcement,
        };
        setMessages((prev) => [...prev, controlMessage]);
      }

      if (control.kind === 'navigate') {
        try {
          // Session persists via cookies - no need to add to URL
          router.push(control.path);
        } catch (navError) {
          console.error('[Chat] Control navigation failed:', navError);
        }
        if (control.sessionAction) {
          await runSessionAction(
            control.sessionAction,
            announcement ?? `Navigated to ${control.label}`
          );
        }
        return;
      }

      await runSessionAction(control.action, announcement ?? control.label);
    },
    [router, runSessionAction, setMessages]
  );

  const handleNavigateSession = useCallback(
    (path: string, label?: string) => {
      try {
        router.push(path);
      } catch (navError) {
        console.error('[Chat] Manual navigation failed:', navError);
      }
      return runSessionAction(
        { action: 'set_view', payload: { path, label } },
        `Navigated to ${label ?? path}`
      );
    },
    [router, runSessionAction]
  );

  const renderInsightWidget = useCallback(
    (insight: SessionInsight) => {
      switch (insight.type) {
        case 'profile': {
          const { profile } = insight;
          return (
            <div>
              <p className="text-xs font-semibold uppercase text-gray-500">Customer Profile</p>
              <div className="mt-1 text-base font-semibold text-gray-900">{profile.name}</div>
              <div className="text-xs text-gray-600">{profile.company}</div>
              <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-gray-600">
                <span>Tier: <span className="font-medium text-gray-900">{profile.tier.toUpperCase()}</span></span>
                <span>Lifetime: <span className="font-medium text-gray-900">{formatCurrency(profile.accountValue)}</span></span>
                <span>Email: <span className="font-medium text-gray-900">{profile.email}</span></span>
                <span>Phone: <span className="font-medium text-gray-900">{profile.phone}</span></span>
              </div>
              {profile.rep && (
                <div className="mt-1 text-xs text-gray-600">Rep: <span className="font-medium text-gray-900">{profile.rep}</span></div>
              )}
            </div>
          );
        }
        case 'cart': {
          const { cart } = insight;
          return (
            <div>
              <p className="text-xs font-semibold uppercase text-gray-500">Cart Snapshot</p>
              <div className="mt-2 flex items-baseline justify-between">
                <div>
                  <p className="text-xs text-gray-500">Subtotal</p>
                  <p className="text-lg font-semibold text-gray-900">{formatCurrency(cart.subtotal)}</p>
                </div>
                <div className="text-right">
                  <p className="text-xs text-gray-500">Due now</p>
                  <p className="text-lg font-semibold text-gray-900">{formatCurrency(cart.total)}</p>
                </div>
              </div>
              <div className="mt-1 flex justify-between text-xs text-gray-600">
                <span>Discounts: {formatCurrency(cart.discounts)}</span>
                <span>{cart.itemCount} items</span>
              </div>
            </div>
          );
        }
        case 'knowledge': {
          return (
            <div>
              <p className="text-xs font-semibold uppercase text-gray-500">Knowledge Focus</p>
              <div className="mt-2 space-y-1">
                {insight.signals.map((signal) => (
                  <div key={signal.topic} className="flex items-center justify-between text-xs">
                    <span className="text-gray-700">{signal.topic}</span>
                    <span className="font-medium text-gray-900">{Math.round(signal.confidence * 100)}%</span>
                  </div>
                ))}
              </div>
            </div>
          );
        }
        case 'quickLinks': {
          return (
            <div>
              <p className="text-xs font-semibold uppercase text-gray-500">Agent Controls</p>
              <div className="mt-2 space-y-2">
                {insight.links.map((link) => (
                  <button
                    key={link.path}
                    onClick={() => void handleNavigateSession(link.path, link.label)}
                    disabled={sessionBusy}
                    className="flex w-full items-center justify-between rounded-lg border border-gray-200 bg-white px-3 py-2 text-left text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <span>{link.label}</span>
                    <span className="text-gray-400">↗</span>
                  </button>
                ))}
              </div>
            </div>
          );
        }
        default:
          return null;
      }
    },
    [handleNavigateSession, sessionBusy]
  );

  const renderAssistantWidget = useCallback(
    (widget: AssistantWidgetData) => {
      switch (widget.kind) {
        case 'cart_plan':
          return (
            <div>
              <p className="text-xs font-semibold uppercase text-gray-500">Cart Mix Blueprint</p>
              <div className="mt-1 text-sm text-gray-700">
                Budget {formatCurrency(widget.budget)} · {formatNumber(widget.totalUnits)} units
              </div>
              <div className="mt-3 space-y-3">
                {widget.categories.map((category) => (
                  <div key={category.name} className="rounded-lg border border-gray-200 bg-gray-50 p-3">
                    <div className="flex items-center justify-between text-sm font-semibold text-gray-900">
                      <span>
                        {category.name}
                        <span className="ml-2 text-xs font-normal text-gray-500">
                          {Math.round((category.share ?? 0) * 100)}%
                        </span>
                      </span>
                      <span>{formatCurrency(category.budget)}</span>
                    </div>
                    <p className="mt-1 text-xs text-gray-600">{category.notes}</p>
                    <div className="mt-3 space-y-2">
                      {category.items.map((item) => (
                        <div key={item.sku} className="flex items-center justify-between rounded-md bg-white/80 px-2 py-1 text-xs text-gray-600">
                          <div>
                            <div className="font-semibold text-gray-900">{item.name}</div>
                            <div className="text-[11px] text-gray-500">{item.sku}</div>
                          </div>
                          <div className="text-right">
                            <div className="text-sm font-semibold text-gray-900">{formatNumber(item.units)} u</div>
                            <button
                              type="button"
                              disabled={sessionBusy}
                              onClick={() => void handleNavigateSession(`/catalog/${item.sku}`, `${item.sku} details`)}
                              className="text-[11px] font-semibold text-blue-600 hover:text-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
                            >
                              View SKU
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        case 'logistics_plan':
          return (
            <div>
              <p className="text-xs font-semibold uppercase text-gray-500">Container Logistics</p>
              <div className="mt-2 grid grid-cols-2 gap-2 text-sm text-gray-700">
                <div>
                  Containers
                  <div className="text-base font-semibold text-gray-900">
                    {widget.quantity} × {widget.containerType.toUpperCase()}
                  </div>
                </div>
                <div className="text-right">
                  Shipping Cost
                  <div className="text-base font-semibold text-gray-900">{formatCurrency(widget.totalShippingCost)}</div>
                </div>
                <div>
                  Lead Time
                  <div className="text-sm font-medium text-gray-900">{widget.leadTimeDays} days</div>
                </div>
                <div className="text-right">
                  Per-Unit Ship
                  <div className="text-sm font-medium text-gray-900">{formatCurrency(widget.costPerUnit)}</div>
                </div>
                <div className="col-span-2 text-xs text-gray-600">Pallets total: {formatNumber(widget.palletsTotal)}</div>
              </div>
            </div>
          );
        case 'quote_summary':
          return (
            <div>
              <p className="text-xs font-semibold uppercase text-gray-500">Quote Summary</p>
              <div className="mt-1 text-sm text-gray-700">Quote {widget.quoteId}</div>
              <div className="mt-2 flex items-center justify-between">
                <div>
                  <p className="text-xs text-gray-500">Total</p>
                  <p className="text-lg font-semibold text-gray-900">{formatCurrency(widget.total)}</p>
                </div>
                <div className="text-right">
                  <p className="text-xs text-gray-500">Discount</p>
                  <p className="text-lg font-semibold text-gray-900">{widget.discountPercent}%</p>
                </div>
              </div>
              <div className="mt-1 text-xs text-gray-600">
                Terms: <span className="font-medium text-gray-900">{widget.netTerms}</span> · Valid until {widget.validUntil}
              </div>
              {(widget.itemsCount || widget.totalUnits) && (
                <div className="mt-1 text-xs text-gray-600">
                  Scope: {widget.itemsCount ?? 0} items / {formatNumber(widget.totalUnits ?? 0)} units
                </div>
              )}
            </div>
          );
        default:
          return null;
      }
    },
    [handleNavigateSession, sessionBusy]
  );

  const startWidgetResize = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>) => {
      if (!isDesktop) return;
      event.preventDefault();
      event.stopPropagation();
      dragContextRef.current = {
        type: 'widget',
        startX: event.clientX,
        startY: event.clientY,
        startWidth: widgetSize.width,
        startHeight: widgetSize.height,
      };
      if (typeof document !== 'undefined') {
        document.body.style.userSelect = 'none';
      }
    },
    [isDesktop, widgetSize]
  );

  const widgetWidthStyle = isDesktop
    ? { width: `${widgetSize.width}px` }
    : { width: 'min(1100px, calc(100vw - 2rem))' };

  const widgetHeightStyle = isDesktop
    ? { height: `${widgetSize.height}px` }
    : { height: 'min(640px, calc(100vh - 2rem))' };

  return (
    <>
      {/* Chat Toggle Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="fixed bottom-4 right-4 bg-blue-600 text-white p-4 rounded-full shadow-lg hover:bg-blue-700 transition-all duration-200 transform hover:scale-110"
          aria-label="Open chat"
          title="Open 4SGM Support Chat"
        >
          <MessageCircle size={24} />
        </button>
      )}

      {/* Chat Window */}
      {isOpen && (
        <div className="fixed bottom-4 right-4 z-50 w-full" style={widgetWidthStyle}>
          <div
            className="relative flex w-full flex-col overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-2xl"
            style={widgetHeightStyle}
          >
            <div className="flex items-center justify-between border-b border-gray-200 px-5 py-3">
              <div>
                <p className="text-sm font-semibold text-gray-900">4SGM Support</p>
                <p className="text-xs text-gray-500">Session {sessionData?.sessionId ?? sessionId}</p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setIsReasoningPanelOpen(true)}
                  aria-label="Open reasoning trail"
                  className="rounded-full p-1 text-gray-500 transition hover:bg-gray-100"
                >
                  <Brain size={18} />
                </button>
                <button
                  onClick={() => setIsOpen(false)}
                  aria-label="Close chat"
                  className="rounded-full p-1 text-gray-500 transition hover:bg-gray-100"
                >
                  <X size={18} />
                </button>
              </div>
            </div>

            <div className="flex min-h-0 flex-1 flex-col">
              <div className="flex-1 overflow-y-auto bg-gray-50 p-4">
                {sessionError && (
                  <div className="mb-3 rounded border border-red-200 bg-red-50 p-2 text-xs text-red-700">
                    {sessionError}
                  </div>
                )}
                {messages.length === 0 && (
                    <div className="mt-8 text-center text-gray-500">
                      <p className="mb-4">Hi! How can I help you today?</p>
                      <div className="mt-4 space-y-2">
                        <button
                          onClick={() => handleSuggestion('What are your shipping policies?')}
                          className="flex w-full items-center space-x-3 rounded-lg p-3 transition-colors hover:bg-blue-50"
                        >
                          <Package size={18} className="text-blue-600" />
                          <span className="text-gray-700">Shipping policies</span>
                        </button>
                        <button
                          onClick={() => handleSuggestion('What is your return policy?')}
                          className="flex w-full items-center space-x-3 rounded-lg p-3 transition-colors hover:bg-blue-50"
                        >
                          <RefreshCw size={18} className="text-blue-600" />
                          <span className="text-gray-700">Returns & refunds</span>
                        </button>
                        <button
                          onClick={() => handleSuggestion('What payment methods do you accept?')}
                          className="flex w-full items-center space-x-3 rounded-lg p-3 transition-colors hover:bg-blue-50"
                        >
                          <CreditCard size={18} className="text-blue-600" />
                          <span className="text-gray-700">Payment methods</span>
                        </button>
                      </div>
                    </div>
                  )}

                  {messages.map((m) => (
                    <div
                      key={m.id}
                      className={`mb-2 flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div className="flex max-w-[80%] flex-col">
                        {m.role === 'assistant' && m.researchLogs && m.researchLogs.length > 0 && (
                          <details className="mb-2 rounded-lg border border-purple-200 bg-purple-50 p-2 text-xs text-gray-700">
                            <summary className="flex cursor-pointer items-center gap-2 text-sm font-semibold text-purple-700">
                              <Beaker size={14} />
                              Research trail ({m.researchLogs.length})
                            </summary>
                            <div className="mt-2 space-y-2">
                              {m.researchLogs.map((log, idx) => (
                                <div key={`${log.stage}-${idx}`} className="rounded border border-purple-200 bg-white/70 p-2">
                                  <div className="text-[11px] font-semibold uppercase text-purple-500">{log.stage}</div>
                                  <div className="text-sm font-medium text-gray-900">{log.heading}</div>
                                  <p className="mt-1 text-xs text-gray-600">{log.details}</p>
                                  {log.citations && log.citations.length > 0 && (
                                    <ul className="mt-1 list-disc pl-4 text-[11px] text-gray-500">
                                      {log.citations.map((cite, citeIdx) => (
                                        <li key={`${idx}-${citeIdx}`}>{cite}</li>
                                      ))}
                                    </ul>
                                  )}
                                </div>
                              ))}
                            </div>
                          </details>
                        )}

                        <div
                          className={`rounded-2xl p-3 text-sm ${
                            m.role === 'user'
                              ? 'bg-blue-600 text-white'
                              : 'bg-white text-gray-900 shadow'
                          }`}
                        >
                          <div className="whitespace-pre-wrap break-words">
                            {m.content ? m.content : '...'}
                          </div>
                          {m.isStreaming && (
                            <div className="mt-2 flex items-center space-x-1 text-xs">
                              <Loader size={14} className="animate-spin" />
                              <span className="opacity-75">Streaming...</span>
                            </div>
                          )}
                          {m.tokenCount && !m.isStreaming && (
                            <div className="mt-1 text-xs opacity-75">{m.tokenCount} tokens</div>
                          )}
                        </div>

                        {m.role === 'assistant' && m.reasoningSteps && m.reasoningSteps.length > 0 && (
                          <div className="mt-2 space-y-3">
                            {m.reasoningSteps.map((event, idx) => (
                              <ReasoningStep key={`${event.timestamp}-${idx}`} event={event} />
                            ))}
                          </div>
                        )}

                        {m.role === 'assistant' && m.widgetEvents && m.widgetEvents.length > 0 && (
                          <div className="mt-2 space-y-3">
                            {m.widgetEvents.map((event, idx) => (
                              <WidgetRenderer key={`${event.widget_type}-${idx}-${event.timestamp}`} event={event} />
                            ))}
                          </div>
                        )}

                        {m.role === 'assistant' && m.widgets && m.widgets.length > 0 && (
                          <div className="mt-2 space-y-3">
                            {m.widgets.map((widget, idx) => (
                              <div key={`${widget.kind}-${idx}`} className="rounded-xl border border-blue-100 bg-blue-50/60 p-3 text-sm text-gray-800 shadow-sm">
                                {renderAssistantWidget(widget)}
                              </div>
                            ))}
                          </div>
                        )}

                        {m.role === 'assistant' && m.insights && m.insights.length > 0 && (
                          <div className="mt-2 space-y-3">
                            {m.insights.map((insight, idx) => (
                              <div key={`${insight.type}-${idx}`} className="rounded-xl border border-gray-200 bg-white p-3 text-sm text-gray-800 shadow-sm">
                                {renderInsightWidget(insight)}
                              </div>
                            ))}
                          </div>
                        )}

                        {m.role === 'assistant' && m.sources && m.sources.length > 0 && (
                          <div className="mt-2 rounded-lg border border-blue-200 bg-blue-50 p-2">
                            <div className="mb-1 flex items-center gap-2 text-sm font-medium text-blue-700">
                              <BookOpen size={14} />
                              <span>Sources</span>
                            </div>
                            {m.sources.slice(0, 2).map((source, idx) => (
                              <div key={idx} className="mt-1 text-xs text-gray-600">
                                <span className="font-medium">{source.title}</span>
                                <span className="text-gray-500"> - {source.category}</span>
                              </div>
                            ))}
                          </div>
                        )}

                      </div>
                    </div>
                  ))}

                  <div ref={messagesEndRef} />
                </div>

              <form onSubmit={(event) => void handleSubmit(event)} className="border-t border-gray-200 bg-white p-4">
                <div className="flex gap-2">
                  <input
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Type your message..."
                    disabled={isLoading}
                    className="flex-1 rounded-xl border border-gray-300 px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600 disabled:bg-gray-100"
                    aria-label="Chat message input"
                  />
                  <button
                    type="submit"
                    disabled={isLoading || !input.trim()}
                    className="rounded-xl bg-blue-600 px-4 py-2 text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                    title="Send message"
                  >
                    <Send size={18} />
                  </button>
                </div>
              </form>
            </div>

            <div
              className="pointer-events-auto absolute bottom-2 right-2 hidden cursor-nwse-resize items-center gap-1 rounded border border-gray-300 bg-white/90 px-2 py-1 text-[11px] font-semibold text-gray-600 shadow lg:flex"
              onPointerDown={startWidgetResize}
              aria-label="Resize widget"
            >
              <Maximize2 size={12} />
              Resize
            </div>
          </div>
        </div>
      )}
      <ReasoningPanel
        open={isOpen && isReasoningPanelOpen}
        onClose={() => setIsReasoningPanelOpen(false)}
        reasoning={reasoningTimeline}
        widgets={widgetTimeline}
        defaultCollapsed={true}
      />
    </>
  );
}
