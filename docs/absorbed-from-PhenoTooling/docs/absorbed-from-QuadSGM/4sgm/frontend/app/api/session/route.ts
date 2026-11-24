import { NextResponse } from 'next/server';
import type { SessionSnapshot } from '@/types/session';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

type BackendError = { detail?: string; error?: string; details?: string };

export const runtime = 'nodejs';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const sessionId = searchParams.get('sessionId');

  if (!sessionId) {
    return NextResponse.json({ error: 'Missing sessionId' }, { status: 400 });
  }

  try {
    const response = await fetch(`${BACKEND_URL}/api/session/${sessionId}`, {
      headers: { 'Content-Type': 'application/json' },
      cache: 'no-store',
    });

    const payload = (await response.json()) as SessionSnapshot | BackendError;
    return NextResponse.json(payload, { status: response.status });
  } catch (error) {
    return NextResponse.json(
      {
        error: 'Failed to load session snapshot',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 502 }
    );
  }
}

export async function POST(request: Request) {
  let body: Record<string, unknown> = {};
  try {
    body = (await request.json()) as Record<string, unknown>;
  } catch {
    // ignore, allow empty body
  }

  try {
    const response = await fetch(`${BACKEND_URL}/api/session`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    const payload = (await response.json()) as SessionSnapshot | BackendError;
    return NextResponse.json(payload, { status: response.status });
  } catch (error) {
    return NextResponse.json(
      {
        error: 'Failed to create session',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 502 }
    );
  }
}
