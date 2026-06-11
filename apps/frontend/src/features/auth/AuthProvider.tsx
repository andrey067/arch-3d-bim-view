/**
 * Sprint 1 — AuthProvider with real API integration.
 *
 * Manages authentication state: user, tokens (localStorage),
 * login, register, refresh, logout. Restores session on boot.
 */
import { createContext, useCallback, useEffect, useMemo, useState } from 'react';
import type { User } from '@/shared/api/types';
import { apiClient, setAuthToken, setUnauthorizedHandler } from '@/shared/api/apiClient';

export type AuthStatus = 'loading' | 'authed' | 'anonymous';

export interface AuthContextValue {
  user: User | null;
  status: AuthStatus;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, displayName?: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

const ACCESS_KEY = 'app3d.access_token';
const REFRESH_KEY = 'app3d.refresh_token';

interface AuthProviderProps {
  children: React.ReactNode;
}

export const AuthProvider = ({ children }: AuthProviderProps) => {
  const [user, setUser] = useState<User | null>(null);
  const [status, setStatus] = useState<AuthStatus>('loading');

  // Restore session on mount
  useEffect(() => {
    const token = localStorage.getItem(ACCESS_KEY);
    if (!token) {
      setStatus('anonymous');
      return;
    }
    setAuthToken(token);
    apiClient
      .get<User>('/api/v1/auth/me')
      .then((u) => {
        setUser(u);
        setStatus('authed');
      })
      .catch(() => {
        localStorage.removeItem(ACCESS_KEY);
        localStorage.removeItem(REFRESH_KEY);
        setAuthToken(null);
        setStatus('anonymous');
      });
  }, []);

  // Register 401 handler for transparent refresh
  useEffect(() => {
    setUnauthorizedHandler(async () => {
      const refreshToken = localStorage.getItem(REFRESH_KEY);
      if (!refreshToken) {
        setUser(null);
        setStatus('anonymous');
        return;
      }
      try {
        const resp = await apiClient.post<{
          access_token: string;
          refresh_token: string;
        }>('/api/v1/auth/refresh', { refresh_token: refreshToken });
        localStorage.setItem(ACCESS_KEY, resp.access_token);
        localStorage.setItem(REFRESH_KEY, resp.refresh_token);
        setAuthToken(resp.access_token);
      } catch {
        localStorage.removeItem(ACCESS_KEY);
        localStorage.removeItem(REFRESH_KEY);
        setAuthToken(null);
        setUser(null);
        setStatus('anonymous');
      }
    });
    return () => setUnauthorizedHandler(null);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const resp = await apiClient.post<{
      access_token: string;
      refresh_token: string;
    }>('/api/v1/auth/login', { email, password });
    localStorage.setItem(ACCESS_KEY, resp.access_token);
    localStorage.setItem(REFRESH_KEY, resp.refresh_token);
    setAuthToken(resp.access_token);
    const me = await apiClient.get<User>('/api/v1/auth/me');
    setUser(me);
    setStatus('authed');
  }, []);

  const register = useCallback(
    async (email: string, password: string, displayName?: string) => {
      await apiClient.post('/api/v1/auth/register', {
        email,
        password,
        display_name: displayName,
      });
      // Auto-login after register
      await login(email, password);
    },
    [login],
  );

  const logout = useCallback(async () => {
    const refreshToken = localStorage.getItem(REFRESH_KEY);
    if (refreshToken) {
      try {
        await apiClient.post('/api/v1/auth/logout', { refresh_token: refreshToken });
      } catch {
        // Logout is idempotent — ignore errors
      }
    }
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    setAuthToken(null);
    setUser(null);
    setStatus('anonymous');
  }, []);

  const refresh = useCallback(async () => {
    const refreshToken = localStorage.getItem(REFRESH_KEY);
    if (!refreshToken) return;
    const resp = await apiClient.post<{
      access_token: string;
      refresh_token: string;
    }>('/api/v1/auth/refresh', { refresh_token: refreshToken });
    localStorage.setItem(ACCESS_KEY, resp.access_token);
    localStorage.setItem(REFRESH_KEY, resp.refresh_token);
    setAuthToken(resp.access_token);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ user, status, login, register, logout, refresh }),
    [user, status, login, register, logout, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
