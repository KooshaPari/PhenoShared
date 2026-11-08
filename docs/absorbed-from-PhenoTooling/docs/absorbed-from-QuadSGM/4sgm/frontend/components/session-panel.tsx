'use client';

import { useState, type FormEvent } from 'react';
import { RefreshCw, ShoppingCart, UserCircle, Activity, ArrowRight, Tag, ExternalLink } from 'lucide-react';
import type { SessionSnapshot } from '@/types/session';

interface SessionPanelProps {
  session: SessionSnapshot | null;
  loading: boolean;
  error?: string | null;
  busy: boolean;
  feedback?: string | null;
  collapsed: boolean;
  onToggle: () => void;
  onRefresh: () => void;
  onAddItem: (sku: string, quantity: number) => Promise<boolean>;
  onAdjustItem: (sku: string, quantity: number) => Promise<boolean>;
  onApplyDiscount: (code: string) => Promise<boolean>;
  onNavigate: (path: string, label?: string) => Promise<boolean>;
}

export function SessionPanel({
  session,
  loading,
  error,
  busy,
  feedback,
  collapsed,
  onToggle,
  onRefresh,
  onAddItem,
  onAdjustItem,
  onApplyDiscount,
  onNavigate,
}: SessionPanelProps) {
  const [skuInput, setSkuInput] = useState('');
  const [qtyInput, setQtyInput] = useState(1);
  const [discountInput, setDiscountInput] = useState('');

  const handleAddItem = async (e: FormEvent) => {
    e.preventDefault();
    if (!skuInput.trim() || qtyInput <= 0) return;
    const success = await onAddItem(skuInput.trim().toUpperCase(), qtyInput);
    if (success) {
      setSkuInput('');
      setQtyInput(1);
    }
  };

  const handleDiscount = async (e: FormEvent) => {
    e.preventDefault();
    if (!discountInput.trim()) return;
    const success = await onApplyDiscount(discountInput.trim().toUpperCase());
    if (success) {
      setDiscountInput('');
    }
  };

  const renderCartItems = () => {
    if (!session) return null;
    return session.cart.items.map((item) => (
      <div key={item.sku} className="flex items-center justify-between rounded border border-gray-200 bg-white p-2 text-sm">
        <div>
          <p className="font-medium text-gray-900">{item.name}</p>
          <p className="text-xs text-gray-500">SKU {item.sku}</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            className="rounded border border-gray-300 px-2 py-1 text-xs"
            onClick={() => void onAdjustItem(item.sku, Math.max(item.quantity - 1, 0))}
            disabled={busy}
          >
            -
          </button>
          <span className="text-sm font-semibold">{item.quantity}</span>
          <button
            className="rounded border border-gray-300 px-2 py-1 text-xs"
            onClick={() => void onAdjustItem(item.sku, item.quantity + 1)}
            disabled={busy}
          >
            +
          </button>
        </div>
      </div>
    ));
  };

  return (
    <aside
      className={`flex h-full flex-col border-gray-200 bg-gray-50 p-4 text-sm lg:border-l ${
        collapsed ? 'overflow-hidden' : 'overflow-y-auto'
      }`}
    >
      <div className="mb-4 flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-wide text-gray-500">Customer Session</p>
          <p className="text-lg font-semibold text-gray-900">Realtime context</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={onToggle}
            className="inline-flex items-center gap-1 rounded border border-gray-300 px-2 py-1 text-xs text-gray-700 hover:bg-white"
          >
            {collapsed ? 'Expand' : 'Collapse'}
          </button>
          <button
            onClick={onRefresh}
            className="inline-flex items-center gap-1 rounded border border-gray-300 px-2 py-1 text-xs text-gray-700 hover:bg-white"
            disabled={loading || collapsed}
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {error && !collapsed && (
        <div className="mb-3 rounded border border-red-200 bg-red-50 p-2 text-xs text-red-700">
          {error}
        </div>
      )}

      {!session && !loading && !collapsed && (
        <p className="text-xs text-gray-500">No session data available.</p>
      )}

      {session && !collapsed && (
        <div className="flex-1 space-y-4 overflow-y-auto pr-1">
          <section className="rounded-lg border border-white bg-white/80 p-3 shadow-sm">
            <div className="mb-2 flex items-center gap-2 text-gray-800">
              <UserCircle size={16} />
              <span className="text-xs font-semibold uppercase text-gray-500">Profile</span>
            </div>
            <p className="text-base font-semibold text-gray-900">{session.user.name}</p>
            <p className="text-xs text-gray-500">{session.user.company}</p>
            <div className="mt-2 flex flex-wrap gap-1">
              <span className="rounded border border-blue-200 bg-blue-50 px-2 py-0.5 text-[11px] text-blue-700">
                Tier: {session.user.tier.toUpperCase()}
              </span>
              <span className="rounded border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[11px] text-emerald-700">
                Lifetime ${session.user.accountValue.toLocaleString()}
              </span>
            </div>
            <div className="mt-3 space-y-1 text-xs text-gray-600">
              <p>Rep: {session.user.assignedRep}</p>
              <p>Email: {session.user.email}</p>
              <p>Phone: {session.user.phone}</p>
            </div>
            <div className="mt-3 flex flex-wrap gap-1">
              {session.user.personaTags.map((tag) => (
                <span key={tag} className="rounded-full bg-gray-100 px-2 py-0.5 text-[11px] text-gray-600">
                  #{tag}
                </span>
              ))}
            </div>
          </section>

          <section className="rounded-lg border border-white bg-white/80 p-3 shadow-sm">
            <div className="mb-2 flex items-center gap-2 text-gray-800">
              <ShoppingCart size={16} />
              <span className="text-xs font-semibold uppercase text-gray-500">Cart</span>
            </div>
            <div className="space-y-2">{renderCartItems()}</div>
            <div className="mt-3 text-xs text-gray-600">
              <p>Subtotal: ${session.cart.subtotal.toFixed(2)}</p>
              <p>Discounts: -${session.cart.discounts.toFixed(2)}</p>
              <p className="font-semibold text-gray-900">Due now: ${session.cart.total.toFixed(2)}</p>
            </div>
            <form onSubmit={(event) => void handleAddItem(event)} className="mt-3 flex flex-col gap-2 text-xs">
              <div className="flex gap-2">
                <input
                  value={skuInput}
                  onChange={(e) => setSkuInput(e.target.value)}
                  placeholder="SKU"
                  className="flex-1 rounded border border-gray-300 px-2 py-1"
                  aria-label="SKU"
                />
                <input
                  type="number"
                  min={1}
                  value={qtyInput}
                  onChange={(e) => setQtyInput(Number(e.target.value))}
                  className="w-16 rounded border border-gray-300 px-2 py-1"
                  aria-label="Quantity"
                />
              </div>
              <button
                type="submit"
                disabled={busy}
                className="rounded bg-blue-600 px-2 py-1 text-xs font-semibold text-white hover:bg-blue-500 disabled:opacity-50"
              >
                Add to cart
              </button>
            </form>
            <form onSubmit={(event) => void handleDiscount(event)} className="mt-3 flex gap-2 text-xs">
              <input
                value={discountInput}
                onChange={(e) => setDiscountInput(e.target.value)}
                placeholder="Discount code"
                className="flex-1 rounded border border-gray-300 px-2 py-1"
              />
              <button
                type="submit"
                disabled={busy}
                className="rounded border border-gray-300 px-2 py-1 font-semibold text-gray-700 hover:bg-gray-100"
              >
                Apply
              </button>
            </form>
          </section>

          <section className="rounded-lg border border-white bg-white/80 p-3 shadow-sm">
            <div className="mb-2 flex items-center gap-2 text-gray-800">
              <Activity size={16} />
              <span className="text-xs font-semibold uppercase text-gray-500">Live activity</span>
            </div>
            <div className="space-y-2 text-xs text-gray-600">
              {session.activity.pagesViewed.slice(0, 4).map((view) => (
                <div key={`${view.path}-${view.timestamp}`} className="rounded border border-gray-200 bg-gray-50 p-2">
                  <p className="font-medium text-gray-900">{view.label}</p>
                  <p className="text-[11px] text-gray-500">{view.path}</p>
                  <p className="text-[11px] text-gray-400">{new Date(view.timestamp).toLocaleTimeString()}</p>
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-lg border border-white bg-white/80 p-3 shadow-sm">
            <div className="mb-2 flex items-center gap-2 text-gray-800">
              <Tag size={16} />
              <span className="text-xs font-semibold uppercase text-gray-500">Knowledge focus</span>
            </div>
            <div className="space-y-2">
              {session.knowledgeSignals.map((signal) => (
                <div key={signal.topic} className="flex items-center justify-between text-xs text-gray-700">
                  <span>{signal.topic}</span>
                  <span className="text-gray-500">{Math.round(signal.confidence * 100)}%</span>
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-lg border border-white bg-white/80 p-3 shadow-sm">
            <div className="mb-2 flex items-center gap-2 text-gray-800">
              <ArrowRight size={16} />
              <span className="text-xs font-semibold uppercase text-gray-500">Agent controls</span>
            </div>
            <div className="space-y-2">
              {session.capabilities.quickLinks.map((link) => (
                <button
                  key={link.path}
                  onClick={() => void onNavigate(link.path, link.label)}
                  disabled={busy}
                  className="flex w-full items-center justify-between rounded border border-gray-200 bg-white px-3 py-2 text-left text-xs text-gray-700 hover:bg-gray-50"
                >
                  <span>{link.label}</span>
                  <ExternalLink size={14} />
                </button>
              ))}
            </div>
          </section>
        </div>
      )}

      {feedback && !collapsed && (
        <div className="mt-3 rounded border border-blue-200 bg-blue-50 p-2 text-xs text-blue-700">
          {feedback}
        </div>
      )}
    </aside>
  );
}

export default SessionPanel;
