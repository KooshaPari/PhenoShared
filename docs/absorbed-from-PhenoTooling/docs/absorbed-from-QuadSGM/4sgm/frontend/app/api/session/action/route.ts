import { NextResponse } from 'next/server';
import type { SessionActionRequest, SessionSnapshot } from '@/types/session';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export const runtime = 'nodejs';

interface SessionActionBody {
  sessionId: string;
  action: SessionActionRequest;
}

type BackendError = { detail?: string; error?: string; details?: string };

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as SessionActionBody;
    if (!body?.sessionId) {
      return NextResponse.json({ error: 'Missing sessionId' }, { status: 400 });
    }

    const response = await fetch(`${BACKEND_URL}/api/session/${body.sessionId}/actions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: body.action }),
    });

    const payload = (await response.json()) as SessionSnapshot | BackendError;
    return NextResponse.json(payload, { status: response.status });
  } catch (error) {
    return NextResponse.json(
      {
        error: 'Failed to apply session action',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 502 }
    );
  }
}
