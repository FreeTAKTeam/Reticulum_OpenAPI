import { useCallback, useMemo, useState, type ReactNode } from 'react';

import { ToastContext, type ToastContextValue, type ToastOptions } from './ToastContext';

const DEFAULT_DURATION_MS = 4000;

interface Toast extends Required<ToastOptions> {
  id: string;
}

function generateToastId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export function ToastProvider({ children }: { children: ReactNode }): JSX.Element {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const dismissToast = useCallback<ToastContextValue['dismissToast']>((id) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const pushToast = useCallback<ToastContextValue['pushToast']>(
    ({ message, type = 'info', durationMs = DEFAULT_DURATION_MS }) => {
      const id = generateToastId();
      const toast: Toast = { id, message, type, durationMs };
      setToasts((current) => [...current, toast]);
      window.setTimeout(() => dismissToast(id), durationMs);
    },
    [dismissToast],
  );

  const value = useMemo<ToastContextValue>(
    () => ({
      pushToast,
      dismissToast,
    }),
    [pushToast, dismissToast],
  );

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="toast-container" role="status" aria-live="polite">
        {toasts.map((toast) => (
          <div key={toast.id} className={`toast toast-${toast.type}`}>
            <span>{toast.message}</span>
            <button
              type="button"
              className="toast-dismiss"
              onClick={() => dismissToast(toast.id)}
              aria-label="Dismiss notification"
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
