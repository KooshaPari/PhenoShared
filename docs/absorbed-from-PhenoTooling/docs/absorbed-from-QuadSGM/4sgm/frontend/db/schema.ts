import {
  pgTable,
  text,
  jsonb,
  timestamp,
  integer,
  real,
  index,
  uniqueIndex,
} from 'drizzle-orm/pg-core';

/**
 * Chat Sessions - Customer session context and state
 * Mirrors backend ChatSession model
 */
export const chatSessions = pgTable(
  'chat_sessions',
  {
    id: text('id').primaryKey(),
    userId: text('user_id'),
    data: jsonb('data').notNull(), // SessionSnapshot serialized
    createdAt: timestamp('created_at', { withTimezone: true }).defaultNow(),
    updatedAt: timestamp('updated_at', { withTimezone: true }).defaultNow(),
  },
  (table) => ({
    userIdIdx: index('ix_chat_sessions_user_id').on(table.userId),
  })
);

/**
 * Documents - Knowledge base for RAG
 * Mirrors backend Document model
 */
export const documents = pgTable(
  'documents',
  {
    id: text('id').primaryKey(),
    title: text('title').notNull(),
    content: text('content').notNull(),
    embedding: jsonb('embedding'), // Vector as JSON (pgvector later)
    docMetadata: jsonb('doc_metadata'),
    createdAt: timestamp('created_at', { withTimezone: true }).defaultNow(),
  },
  (table) => ({
    titleIdx: index('ix_documents_title').on(table.title),
  })
);

/**
 * Products - 4SGM product catalog
 * Mirrors backend Product model
 */
export const products = pgTable(
  'products',
  {
    id: text('id').primaryKey(),
    sku: text('sku').notNull().unique(),
    name: text('name').notNull(),
    description: text('description'),
    price: real('price').notNull(),
    quantityOnHand: integer('quantity_on_hand').notNull().default(0),
    category: text('category'),
    productMetadata: jsonb('product_metadata'),
    createdAt: timestamp('created_at', { withTimezone: true }).defaultNow(),
    updatedAt: timestamp('updated_at', { withTimezone: true }).defaultNow(),
  },
  (table) => ({
    skuIdx: uniqueIndex('ix_products_sku').on(table.sku),
    categoryIdx: index('ix_products_category').on(table.category),
  })
);
