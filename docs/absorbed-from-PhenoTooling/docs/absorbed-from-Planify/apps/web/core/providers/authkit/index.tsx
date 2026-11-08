/**
 * Copyright (c) 2025-present AgilePlus
 * SPDX-License-Identifier: AGPL-3.0-only
 *
 * AuthKit Provider - Integrates AuthKit token authentication with Plane.
 *
 * Usage:
 *   - Set AUTHKIT_API_URL and AUTHKIT_API_KEY in your .env
 *   - Tokens are stored in httpOnly cookies, validated server-side via AuthKitTokenAuthentication
 *   - Client uses useAuthKit() hook to access auth state
 */

"use client";

import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { IUser } from "@plane/types";

// ============================================================================
// Types
// ============================================================================

export interface AuthKitUser extends IUser {
  auth_token?: string;
}

export interface AuthKitTokens {
  access_token: string;
  refresh_token?: string;
  expires_at?: number;
}

export interface AuthKitSession {
  user: AuthKitUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

export interface IAuthKitContext {
  session: AuthKitSession;
  signIn: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  signOut: () => Promise<void>;
  refreshSession: () => Promise<void>;
  getAccessToken: () => string | null;
  setTokens: (tokens: AuthKitTokens) => void;
  clearTokens: () => void;
}

const AuthKitContext = createContext<IAuthKitContext | null>(null);

// ============================================================================
// Token Store
// ============================================================================

let _accessToken: string | null = null;

function setAuthKitTokens(tokens: AuthKitTokens): void {
  _accessToken = tokens.access_token;
}

function clearAuthKitTokens(): void {
  _accessToken = null;
}

function getAuthKitAccessToken(): string | null {
  return _accessToken;
}

// ============================================================================
// AuthKit API Client
// ============================================================================

const API_BASE = process.env.NEXT_PUBLIC_AUTHKIT_API_URL || "http://localhost:8001";

async function authKitFetch<T = unknown>(
  endpoint: string,
  options: RequestInit = {},
  accessToken?: string | null
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`;
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
    credentials: "include",
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: response.statusText }));
    throw new Error((error as { message?: string }).message || `AuthKit API error: ${response.status}`);
  }

  return response.json();
}

// ============================================================================
// Provider
// ============================================================================

export function AuthKitProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<AuthKitSession>({
    user: null,
    isAuthenticated: false,
    isLoading: true,
  });

  const refreshSession = useCallback(async () => {
    try {
      const data = await authKitFetch<{ user: AuthKitUser }>(
        "/auth/me",
        {},
        _accessToken
      );
      setSession({ user: data.user, isAuthenticated: true, isLoading: false });
    } catch {
      setSession({ user: null, isAuthenticated: false, isLoading: false });
    }
  }, []);

  useEffect(() => {
    refreshSession();
    const interval = setInterval(refreshSession, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [refreshSession]);

  const signIn = useCallback(async (email: string, password: string) => {
    try {
      const data = await authKitFetch<{ user: AuthKitUser; tokens: AuthKitTokens }>(
        "/auth/sign-in",
        { method: "POST", body: JSON.stringify({ email, password }) }
      );
      setAuthKitTokens(data.tokens);
      setSession({ user: data.user, isAuthenticated: true, isLoading: false });
      return { success: true };
    } catch (err: unknown) {
      return { success: false, error: (err as Error).message || "Sign in failed" };
    }
  }, []);

  const signOut = useCallback(async () => {
    try {
      await authKitFetch("/auth/sign-out", { method: "POST" }, _accessToken);
    } finally {
      clearAuthKitTokens();
      setSession({ user: null, isAuthenticated: false, isLoading: false });
    }
  }, []);

  const getAccessToken = useCallback(() => _accessToken, []);

  const setTokens = useCallback((tokens: AuthKitTokens) => {
    setAuthKitTokens(tokens);
  }, []);

  const clearTokens = useCallback(() => {
    clearAuthKitTokens();
  }, []);

  const value = useMemo<IAuthKitContext>(
    () => ({
      session,
      signIn,
      signOut,
      refreshSession,
      getAccessToken,
      setTokens,
      clearTokens,
    }),
    [session, signIn, signOut, refreshSession, getAccessToken, setTokens, clearTokens]
  );

  return <AuthKitContext.Provider value={value}>{children}</AuthKitContext.Provider>;
}

// ============================================================================
// Hooks
// ============================================================================

export function useAuthKit(): IAuthKitContext {
  const ctx = useContext(AuthKitContext);
  if (!ctx) throw new Error("useAuthKit must be used within <AuthKitProvider>");
  return ctx;
}

export function useAuthKitSession() {
  return useAuthKit().session;
}
