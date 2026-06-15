/**
 * Minimal in-app toaster. Sprint 0 ships a no-op stub; Sprint 1
 * (VS-Auth) wires real `success`/`error` toasts.
 */
import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import type { ReactNode } from 'react';

type ToastKind = 'info' | 'success' | 'error';

interface Toast {
  id: string;
  kind: ToastKind;
  message: string;
}

interface ToasterContextValue {
  push: (kind: ToastKind, message: string) => void;
}

const ToasterContext = createContext<ToasterContextValue | null>(null);

export const ToasterProvider = ({ children }: { children: ReactNode }) => {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const push = useCallback((kind: ToastKind, message: string) => {
    const id = `t-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    setToasts((prev) => [...prev, { id, kind, message }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  }, []);

  const value = useMemo(() => ({ push }), [push]);

  return (
    <ToasterContext.Provider value={value}>
      {children}
      <div
        role="status"
        aria-live="polite"
        style={{
          position: 'fixed',
          bottom: '1rem',
          right: '1rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.5rem',
          zIndex: 9999,
        }}
      >
        {toasts.map((t) => (
          <div
            key={t.id}
            style={{
              background: 'var(--color-surface)',
              border: `1px solid ${
                t.kind === 'error'
                  ? 'var(--color-danger)'
                  : t.kind === 'success'
                    ? 'var(--color-success)'
                    : 'var(--color-border)'
              }`,
              padding: '0.75rem 1rem',
              borderRadius: 'var(--radius-md)',
              boxShadow: 'var(--shadow-md)',
              minWidth: 240,
            }}
          >
            {t.message}
          </div>
        ))}
      </div>
    </ToasterContext.Provider>
  );
};

export const useToaster = (): ToasterContextValue => {
  const ctx = useContext(ToasterContext);
  if (!ctx) throw new Error('useToaster must be used inside <ToasterProvider>');
  return ctx;
};
