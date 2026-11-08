/**
 * Drizzle ORM client for PostgreSQL
 * Use this in server-side code (API routes, server components)
 */

import { drizzle, type PostgresJsDatabase } from 'drizzle-orm/postgres-js';
import postgres from 'postgres';
import * as schema from './schema';

// Only initialize in server-side environments
const dbUrl = process.env.DATABASE_URL || process.env.SUPABASE_DB_URL;
if (!dbUrl) {
  console.warn(
    '⚠️  DATABASE_URL not set; database operations will be unavailable'
  );
}

// Create a postgres connection pool with error handling
type DbType = PostgresJsDatabase<typeof schema> | null;

let queryClient: ReturnType<typeof postgres> | null = null;
let db: DbType = null;

try {
  queryClient = postgres(dbUrl || '', {
    max: 1, // Single connection for serverless
    idle_timeout: 20,
    connect_timeout: 10,
  });

  // Initialize Drizzle with our schema
  db = drizzle(queryClient, { schema });
} catch (error) {
  console.error('Failed to initialize Drizzle client:', error);
  db = null;
}

export { db };
export type Database = DbType;
