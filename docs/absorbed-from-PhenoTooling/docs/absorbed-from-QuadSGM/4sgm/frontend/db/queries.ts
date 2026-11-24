/**
 * Drizzle query helpers for common operations
 * Use these in server components and API routes
 */

import { db } from './client';
import { products, chatSessions, documents } from './schema';
import { eq, like, desc, type InferSelectModel } from 'drizzle-orm';

export type Product = InferSelectModel<typeof products>;

/**
 * Get all products, optionally filtered by category
 */
export async function getProducts(category?: string): Promise<Product[]> {
  try {
    if (!db) {
      console.warn('Database not available; returning empty products');
      return [];
    }
    if (category) {
      return await db
        .select()
        .from(products)
        .where(eq(products.category, category))
        .orderBy(desc(products.createdAt));
    }
    return await db
      .select()
      .from(products)
      .orderBy(desc(products.createdAt));
  } catch (error) {
    console.error('Failed to fetch products:', error);
    return [];
  }
}

/**
 * Get a single product by SKU
 */
export async function getProductBySku(sku: string) {
  try {
    if (!db) return null;
    const result = await db
      .select()
      .from(products)
      .where(eq(products.sku, sku))
      .limit(1);
    return result[0] || null;
  } catch (error) {
    console.error('Failed to fetch product:', error);
    return null;
  }
}

/**
 * Get a chat session by ID
 */
export async function getChatSession(sessionId: string) {
  try {
    if (!db) return null;
    const result = await db
      .select()
      .from(chatSessions)
      .where(eq(chatSessions.id, sessionId))
      .limit(1);
    return result[0] || null;
  } catch (error) {
    console.error('Failed to fetch session:', error);
    return null;
  }
}

/**
 * Create or update a chat session
 */
export async function upsertChatSession(
  sessionId: string,
  userId: string | null,
  data: Record<string, unknown>
) {
  try {
    if (!db) return null;
    return await db
      .insert(chatSessions)
      .values({
        id: sessionId,
        userId,
        data,
      })
      .onConflictDoUpdate({
        target: chatSessions.id,
        set: { data, updatedAt: new Date() },
      });
  } catch (error) {
    console.error('Failed to upsert session:', error);
    return null;
  }
}

/**
 * Search documents by title or content
 */
export async function searchDocuments(query: string) {
  try {
    if (!db) return [];
    return await db
      .select()
      .from(documents)
      .where(like(documents.title, `%${query}%`))
      .limit(10);
  } catch (error) {
    console.error('Failed to search documents:', error);
    return [];
  }
}
