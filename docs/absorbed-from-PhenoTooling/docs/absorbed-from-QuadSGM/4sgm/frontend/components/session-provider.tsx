'use client';

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';

interface SessionContextType {
  sessionId: string;
  conversationHistory: Array<{ role: string; content: string }>;
  addToHistory: (role: string, content: string) => void;
  clearHistory: () => void;
}

const SessionContext = createContext<SessionContextType | null>(null);

// Helper functions for cookie management
function getCookie(name: string): string | null {
  if (typeof document === 'undefined') return null;
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop()?.split(';').shift() || null;
  return null;
}

function setCookie(name: string, value: string, days: number = 30) {
  if (typeof document === 'undefined') return;
  const expires = new Date();
  expires.setTime(expires.getTime() + days * 24 * 60 * 60 * 1000);
  document.cookie = `${name}=${value}; expires=${expires.toUTCString()}; path=/; SameSite=Lax`;
}

interface ParsedHistoryItem {
  role: unknown;
  content: unknown;
}

export function SessionProvider({ children }: { children: ReactNode }) {
  const [sessionId, setSessionId] = useState<string>('');
  const [conversationHistory, setConversationHistory] = useState<Array<{ role: string; content: string }>>([]);
  const [isInitialized, setIsInitialized] = useState(false);

  // Initialize session from cookies on mount
  useEffect(() => {
    // Get or create sessionId from cookie
    let sessionIdFromCookie = getCookie('sessionId');
    if (!sessionIdFromCookie) {
      sessionIdFromCookie = `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      setCookie('sessionId', sessionIdFromCookie, 30); // 30 day expiry
    }

    // Get conversation history from cookie
    const historyFromCookie = getCookie('conversationHistory');
    let history: Array<{ role: string; content: string }> = [];
    if (historyFromCookie) {
      try {
        const parsed = JSON.parse(decodeURIComponent(historyFromCookie)) as ParsedHistoryItem[];
        // Validate and filter the parsed data
        if (Array.isArray(parsed)) {
          history = parsed
            .filter((item): item is { role: string; content: string } => {
              return (
                item != null &&
                typeof item.role === 'string' &&
                typeof item.content === 'string'
              );
            });
        }
      } catch {
        history = [];
      }
    }

    setSessionId(sessionIdFromCookie);
    setConversationHistory(history);
    setIsInitialized(true);
  }, []);

  // Persist conversation history to cookie whenever it changes
  useEffect(() => {
    if (isInitialized && conversationHistory.length > 0) {
      setCookie('conversationHistory', encodeURIComponent(JSON.stringify(conversationHistory)), 30);
    }
  }, [conversationHistory, isInitialized]);

  const addToHistory = (role: string, content: string) => {
    setConversationHistory(prev => [...prev, { role, content }]);
  };

  const clearHistory = () => {
    setConversationHistory([]);
    setCookie('conversationHistory', '', 0); // Delete cookie by setting expiry to past
  };

  // Always provide context, but ensure sessionId is populated before children render
  return (
    <SessionContext.Provider value={{ sessionId, conversationHistory, addToHistory, clearHistory }}>
      {isInitialized ? children : null}
    </SessionContext.Provider>
  );
}

export function useSession() {
  const context = useContext(SessionContext);
  if (!context) {
    throw new Error('useSession must be used within SessionProvider');
  }
  return context;
}
