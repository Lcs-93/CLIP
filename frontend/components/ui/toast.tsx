"use client";

import { createContext, useCallback, useContext, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, CheckCircle2, Info, X } from "lucide-react";

import { cn } from "@/lib/cn";

export type ToastVariant = "success" | "error" | "info";

interface ShowToastOptions {
  title: string;
  description?: string;
  variant?: ToastVariant;
  durationMs?: number;
}

interface ToastEntry extends ShowToastOptions {
  id: string;
  variant: ToastVariant;
  durationMs: number;
}

interface ToastContextValue {
  showToast: (options: ShowToastOptions) => string;
  dismissToast: (id: string) => void;
}

const DEFAULT_DURATION_MS = 3600;
const MAX_TOASTS = 4;

const ToastContext = createContext<ToastContextValue | undefined>(undefined);

function variantClasses(variant: ToastVariant) {
  if (variant === "success") {
    return "border-emerald-500/35 bg-emerald-500/10 text-emerald-950 dark:text-emerald-100";
  }
  if (variant === "error") {
    return "border-destructive/40 bg-destructive/10 text-destructive";
  }
  return "border-sky-500/35 bg-sky-500/10 text-sky-900 dark:text-sky-100";
}

function variantIcon(variant: ToastVariant) {
  if (variant === "success") return CheckCircle2;
  if (variant === "error") return AlertTriangle;
  return Info;
}

function toastId() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function ToastCard({
  toast,
  onDismiss,
}: {
  toast: ToastEntry;
  onDismiss: (id: string) => void;
}) {
  const Icon = variantIcon(toast.variant);

  return (
    <motion.div
      layout
      role={toast.variant === "error" ? "alert" : "status"}
      aria-live={toast.variant === "error" ? "assertive" : "polite"}
      initial={{ opacity: 0, y: 14, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 8, scale: 0.98 }}
      transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
      className={cn(
        "pointer-events-auto relative w-full overflow-hidden rounded-xl border px-3.5 py-3 shadow-[0_20px_52px_-36px_rgba(15,23,42,0.8)] backdrop-blur-xl",
        variantClasses(toast.variant)
      )}
    >
      <div className="flex items-start gap-2.5 pr-8">
        <Icon className="mt-0.5 h-4 w-4 shrink-0" />
        <div className="min-w-0">
          <p className="text-sm font-semibold">{toast.title}</p>
          {toast.description ? (
            <p className="mt-0.5 text-xs leading-5 text-current/85">{toast.description}</p>
          ) : null}
        </div>
      </div>

      <button
        type="button"
        aria-label="Dismiss notification"
        onClick={() => onDismiss(toast.id)}
        className="absolute right-1.5 top-1.5 inline-flex h-7 w-7 items-center justify-center rounded-md text-current/70 transition hover:bg-black/10 hover:text-current dark:hover:bg-white/10"
      >
        <X className="h-3.5 w-3.5" />
      </button>
    </motion.div>
  );
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastEntry[]>([]);

  const dismissToast = useCallback((id: string) => {
    setToasts((current) => current.filter((item) => item.id !== id));
  }, []);

  const showToast = useCallback((options: ShowToastOptions) => {
    const id = toastId();
    const entry: ToastEntry = {
      id,
      title: options.title,
      description: options.description,
      variant: options.variant ?? "info",
      durationMs: options.durationMs ?? DEFAULT_DURATION_MS,
    };

    setToasts((current) => [...current, entry].slice(-MAX_TOASTS));
    window.setTimeout(() => {
      dismissToast(id);
    }, entry.durationMs);
    return id;
  }, [dismissToast]);

  const value = useMemo(
    () => ({
      showToast,
      dismissToast,
    }),
    [dismissToast, showToast]
  );

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="pointer-events-none fixed inset-x-4 bottom-4 z-[120] flex justify-end sm:inset-x-6 sm:bottom-6">
        <div className="w-full max-w-sm space-y-2.5">
          <AnimatePresence initial={false}>
            {toasts.map((toast) => (
              <ToastCard key={toast.id} toast={toast} onDismiss={dismissToast} />
            ))}
          </AnimatePresence>
        </div>
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within ToastProvider");
  }
  return context;
}
