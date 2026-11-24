export type CartItemStatus = 'in_cart' | 'backorder' | 'saved' | 'fulfilled';

export interface SessionCartItem {
  sku: string;
  name: string;
  quantity: number;
  unitPrice: number;
  status: CartItemStatus;
  image?: string;
}

export interface DiscountOffer {
  code: string;
  label: string;
  value: number;
  type: 'percent' | 'fixed';
  expiresOn?: string;
}

export interface QuickLinkTarget {
  label: string;
  path: string;
  description?: string;
}

export interface PageViewEvent {
  path: string;
  label: string;
  timestamp: string;
  dwellSeconds: number;
}

export interface CartAuditEntry {
  timestamp: string;
  action: 'add' | 'remove' | 'update' | 'discount' | 'navigate';
  sku?: string;
  quantityChange?: number;
  note?: string;
  performedBy: 'user' | 'agent';
}

export interface SessionKnowledgeSignal {
  topic: string;
  confidence: number;
  lastTouched: string;
}

export interface SessionUserProfile {
  id: string;
  name: string;
  company: string;
  tier: 'retail' | 'wholesale' | 'distributor' | 'vip';
  accountValue: number;
  personaTags: string[];
  email: string;
  phone: string;
  preferredLanguage?: string;
  assignedRep?: string;
}

export interface SessionCartSnapshot {
  id: string;
  items: SessionCartItem[];
  subtotal: number;
  discounts: number;
  total: number;
  promoCodes: string[];
  auditTrail: CartAuditEntry[];
}

export interface SessionActivitySnapshot {
  pagesViewed: PageViewEvent[];
  cartHistory: CartAuditEntry[];
  lastViewedProduct?: {
    sku: string;
    name: string;
    category: string;
    inventoryAvailable: number;
  };
  currentView: {
    path: string;
    label: string;
    since: string;
  };
}

export interface SessionSnapshot {
  sessionId: string;
  user: SessionUserProfile;
  knowledgeSignals: SessionKnowledgeSignal[];
  cart: SessionCartSnapshot;
  activity: SessionActivitySnapshot;
  currentIntent?: string;
  lastUpdated: string;
  capabilities: {
    quickLinks: QuickLinkTarget[];
    availableDiscounts: DiscountOffer[];
  };
}

export type SessionActionRequest =
  | {
      action: 'add_cart_item';
      payload: { sku: string; quantity: number; name?: string; unitPrice?: number };
    }
  | {
      action: 'update_cart_item';
      payload: { sku: string; quantity: number };
    }
  | {
      action: 'remove_cart_item';
      payload: { sku: string };
    }
  | {
      action: 'apply_discount';
      payload: { code: string };
    }
  | {
      action: 'set_view';
      payload: { path: string; label?: string };
    }
  | {
      action: 'log_activity';
      payload: { path: string; label: string; dwellSeconds: number };
    };

export type SessionActionResponse = SessionSnapshot;

export type SessionActionHandler = (action: SessionActionRequest) => Promise<SessionActionResponse>;
