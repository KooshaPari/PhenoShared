import { defineConfig } from 'drizzle-kit';

export default defineConfig({
  schema: './db/schema.ts',
  dialect: 'postgresql',
  dbCredentials: {
    url: process.env.DATABASE_URL || 'postgresql://localhost:5432/sgm4',
  },
  out: './db/migrations',
  migrations: {
    prefix: 'timestamp',
  },
});
