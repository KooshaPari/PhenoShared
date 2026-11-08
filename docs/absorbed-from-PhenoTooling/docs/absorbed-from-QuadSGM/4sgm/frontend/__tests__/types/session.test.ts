import { describe, it, expect } from 'vitest';
import type {
  SessionSnapshot,
  SessionActionRequest,
  SessionUserProfile,
  SessionCartItem,
  SessionCartSnapshot,
  SessionActivitySnapshot,
} from '@/types/session';

describe('session types', () => {
  describe('SessionUserProfile', () => {
    it('should accept valid user profile with all fields', () => {
      const profile: SessionUserProfile = {
        id: 'user-1',
        name: 'John Doe',
        company: 'ACME Corp',
        tier: 'wholesale',
        accountValue: 50000,
        personaTags: ['bulk-buyer', 'seasonal'],
        email: 'john@acme.com',
        phone: '+1-555-0100',
        preferredLanguage: 'en',
        assignedRep: 'Rep A',
      };

      expect(profile.id).toBe('user-1');
      expect(profile.tier).toBe('wholesale');
    });

    it('should accept valid user profile with optional fields', () => {
      const profile: SessionUserProfile = {
        id: 'user-2',
        name: 'Jane Smith',
        company: 'XYZ Inc',
        tier: 'retail',
        accountValue: 10000,
        personaTags: [],
        email: 'jane@xyz.com',
        phone: '+1-555-0101',
      };

      expect(profile.tier).toBe('retail');
      expect(profile.assignedRep).toBeUndefined();
    });

    it('should support all tier types', () => {
      const tiers: Array<SessionUserProfile['tier']> = [
        'retail',
        'wholesale',
        'distributor',
        'vip',
      ];

      tiers.forEach((tier) => {
        const profile: SessionUserProfile = {
          id: 'user-1',
          name: 'Test',
          company: 'Test Co',
          tier,
          accountValue: 1000,
          personaTags: [],
          email: 'test@test.com',
          phone: '555-0000',
        };
        expect(profile.tier).toBe(tier);
      });
    });
  });

  describe('SessionCartItem', () => {
    it('should accept valid cart item with all fields', () => {
      const item: SessionCartItem = {
        sku: 'SKU-001',
        name: 'Product A',
        quantity: 10,
        unitPrice: 25.0,
        status: 'in_cart',
        image: '/images/product-a.jpg',
      };

      expect(item.sku).toBe('SKU-001');
      expect(item.status).toBe('in_cart');
      expect(item.quantity).toBe(10);
    });

    it('should accept cart item without optional image', () => {
      const item: SessionCartItem = {
        sku: 'SKU-002',
        name: 'Product B',
        quantity: 5,
        unitPrice: 50.0,
        status: 'backorder',
      };

      expect(item.image).toBeUndefined();
    });

    it('should support all status types', () => {
      const statuses: Array<SessionCartItem['status']> = [
        'in_cart',
        'backorder',
        'saved',
        'fulfilled',
      ];

      statuses.forEach((status) => {
        const item: SessionCartItem = {
          sku: 'SKU-TEST',
          name: 'Test Product',
          quantity: 1,
          unitPrice: 100,
          status,
        };
        expect(item.status).toBe(status);
      });
    });
  });

  describe('SessionCartSnapshot', () => {
    it('should accept valid cart snapshot', () => {
      const cart: SessionCartSnapshot = {
        id: 'cart-1',
        items: [
          {
            sku: 'SKU-001',
            name: 'Product A',
            quantity: 10,
            unitPrice: 25.0,
            status: 'in_cart',
          },
        ],
        subtotal: 250.0,
        discounts: 25.0,
        total: 225.0,
        promoCodes: ['SUMMER20'],
        auditTrail: [],
      };

      expect(cart.total).toBe(225.0);
      expect(cart.items).toHaveLength(1);
      expect(cart.promoCodes).toContain('SUMMER20');
    });

    it('should accept cart with no items', () => {
      const cart: SessionCartSnapshot = {
        id: 'cart-2',
        items: [],
        subtotal: 0,
        discounts: 0,
        total: 0,
        promoCodes: [],
        auditTrail: [],
      };

      expect(cart.items).toHaveLength(0);
      expect(cart.total).toBe(0);
    });

    it('should track multiple promo codes', () => {
      const cart: SessionCartSnapshot = {
        id: 'cart-3',
        items: [],
        subtotal: 100,
        discounts: 15,
        total: 85,
        promoCodes: ['CODE1', 'CODE2', 'CODE3'],
        auditTrail: [],
      };

      expect(cart.promoCodes).toHaveLength(3);
    });
  });

  describe('SessionActivitySnapshot', () => {
    it('should track page views with details', () => {
      const activity: SessionActivitySnapshot = {
        pagesViewed: [
          {
            path: '/catalog',
            label: 'Catalog',
            timestamp: '2024-01-01T10:00:00Z',
            dwellSeconds: 30,
          },
        ],
        cartHistory: [],
        currentView: {
          path: '/cart',
          label: 'Shopping Cart',
          since: '2024-01-01T10:30:00Z',
        },
      };

      expect(activity.pagesViewed).toHaveLength(1);
      expect(activity.pagesViewed[0].dwellSeconds).toBe(30);
    });

    it('should track last viewed product', () => {
      const activity: SessionActivitySnapshot = {
        pagesViewed: [],
        cartHistory: [],
        lastViewedProduct: {
          sku: 'SKU-001',
          name: 'Product A',
          category: 'Electronics',
          inventoryAvailable: 50,
        },
        currentView: {
          path: '/',
          label: 'Home',
          since: '2024-01-01T10:00:00Z',
        },
      };

      expect(activity.lastViewedProduct?.name).toBe('Product A');
      expect(activity.lastViewedProduct?.inventoryAvailable).toBe(50);
    });

    it('should track current view location', () => {
      const activity: SessionActivitySnapshot = {
        pagesViewed: [],
        cartHistory: [],
        currentView: {
          path: '/product/SKU-123',
          label: 'Product Details',
          since: '2024-01-01T10:15:00Z',
        },
      };

      expect(activity.currentView.path).toBe('/product/SKU-123');
    });
  });

  describe('SessionSnapshot', () => {
    it('should construct complete session snapshot', () => {
      const snapshot: SessionSnapshot = {
        sessionId: 'session-123',
        user: {
          id: 'user-1',
          name: 'John Doe',
          company: 'ACME',
          tier: 'wholesale',
          accountValue: 50000,
          personaTags: ['bulk-buyer'],
          email: 'john@acme.com',
          phone: '+1-555-0100',
          assignedRep: 'Rep A',
        },
        knowledgeSignals: [
          { topic: 'shipping', confidence: 0.9, lastTouched: '2024-01-01' },
        ],
        cart: {
          id: 'cart-1',
          items: [],
          subtotal: 0,
          discounts: 0,
          total: 0,
          promoCodes: [],
          auditTrail: [],
        },
        activity: {
          pagesViewed: [],
          cartHistory: [],
          currentView: {
            path: '/',
            label: 'Home',
            since: '2024-01-01T10:00:00Z',
          },
        },
        lastUpdated: '2024-01-01T10:30:00Z',
        capabilities: {
          quickLinks: [{ label: 'Catalog', path: '/catalog' }],
          availableDiscounts: [],
        },
      };

      expect(snapshot.sessionId).toBe('session-123');
      expect(snapshot.user.tier).toBe('wholesale');
      expect(snapshot.knowledgeSignals).toHaveLength(1);
    });

    it('should support optional currentIntent', () => {
      const snapshot: SessionSnapshot = {
        sessionId: 'session-456',
        user: {
          id: 'user-2',
          name: 'Jane',
          company: 'XYZ',
          tier: 'retail',
          accountValue: 1000,
          personaTags: [],
          email: 'jane@xyz.com',
          phone: '555-0000',
        },
        knowledgeSignals: [],
        cart: {
          id: 'cart-2',
          items: [],
          subtotal: 0,
          discounts: 0,
          total: 0,
          promoCodes: [],
          auditTrail: [],
        },
        activity: {
          pagesViewed: [],
          cartHistory: [],
          currentView: { path: '/', label: 'Home', since: '2024-01-01T10:00:00Z' },
        },
        lastUpdated: '2024-01-01T10:00:00Z',
        capabilities: {
          quickLinks: [],
          availableDiscounts: [],
        },
        currentIntent: 'checkout',
      };

      expect(snapshot.currentIntent).toBe('checkout');
    });
  });

  describe('SessionActionRequest', () => {
    it('should construct add_cart_item action', () => {
      const action: SessionActionRequest = {
        action: 'add_cart_item',
        payload: {
          sku: 'SKU-001',
          quantity: 10,
          name: 'Product A',
          unitPrice: 25.0,
        },
      };

      expect(action.action).toBe('add_cart_item');
      expect(action.payload.sku).toBe('SKU-001');
    });

    it('should construct update_cart_item action', () => {
      const action: SessionActionRequest = {
        action: 'update_cart_item',
        payload: {
          sku: 'SKU-001',
          quantity: 20,
        },
      };

      expect(action.action).toBe('update_cart_item');
      expect(action.payload.quantity).toBe(20);
    });

    it('should construct remove_cart_item action', () => {
      const action: SessionActionRequest = {
        action: 'remove_cart_item',
        payload: {
          sku: 'SKU-001',
        },
      };

      expect(action.action).toBe('remove_cart_item');
    });

    it('should construct apply_discount action', () => {
      const action: SessionActionRequest = {
        action: 'apply_discount',
        payload: {
          code: 'SUMMER20',
        },
      };

      expect(action.action).toBe('apply_discount');
      expect(action.payload.code).toBe('SUMMER20');
    });

    it('should construct set_view action', () => {
      const action: SessionActionRequest = {
        action: 'set_view',
        payload: {
          path: '/catalog',
          label: 'Catalog',
        },
      };

      expect(action.action).toBe('set_view');
      expect(action.payload.path).toBe('/catalog');
    });

    it('should construct log_activity action', () => {
      const action: SessionActionRequest = {
        action: 'log_activity',
        payload: {
          path: '/product/SKU-001',
          label: 'Product Details',
          dwellSeconds: 60,
        },
      };

      expect(action.action).toBe('log_activity');
      expect(action.payload.dwellSeconds).toBe(60);
    });
  });
});
