import type { SessionSnapshot, SessionActionRequest } from '@/types/session';

const SESSION_ENDPOINT = '/api/session';
const SESSION_ACTION_ENDPOINT = '/api/session/action';

type ErrorPayload = { details?: string };

async function parseResponse<T>(response: Response, fallbackMessage: string): Promise<T> {
  const body = (await response.json()) as T | ErrorPayload;
  if (!response.ok) {
    const details = (body as ErrorPayload)?.details;
    throw new Error(details ?? fallbackMessage);
  }
  return body as T;
}

export async function createSession(params: { userTier?: string } = {}): Promise<SessionSnapshot> {
  const response = await fetch(SESSION_ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });

  return parseResponse<SessionSnapshot>(response, 'Unable to create session');
}

export async function fetchSessionSnapshot(sessionId: string): Promise<SessionSnapshot> {
  const response = await fetch(`${SESSION_ENDPOINT}/${encodeURIComponent(sessionId)}`, {
    cache: 'no-store',
  });

  return parseResponse<SessionSnapshot>(response, 'Unable to load session insights');
}

export async function postSessionAction(
  sessionId: string,
  action: SessionActionRequest,
): Promise<SessionSnapshot> {
  const response = await fetch(SESSION_ACTION_ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sessionId, action }),
  });

  return parseResponse<SessionSnapshot>(response, 'Session update failed');
}
