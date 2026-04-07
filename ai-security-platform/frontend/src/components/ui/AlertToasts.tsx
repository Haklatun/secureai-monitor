"use client";

import { useEffect, useState } from "react";
import { X, AlertTriangle } from "lucide-react";
import clsx from "clsx";
import type { AlertMessage } from "@/lib/websocket";

interface Toast extends AlertMessage {
  toastId: string;
}

interface Props {
  alerts: Toast[];
  onDismiss: (id: string) => void;
}

export function AlertToasts({ alerts, onDismiss }: Props) {
  return (
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full">
      {alerts.map((a) => (
        <div
          key={a.toastId}
          className={clsx(
            "flex items-start gap-3 p-3 rounded-xl border text-sm shadow-sm animate-in slide-in-from-right",
            a.severity === "critical" || a.severity === "high"
              ? "bg-red-50 border-red-200"
              : a.severity === "medium"
              ? "bg-yellow-50 border-yellow-200"
              : "bg-white border-gray-200"
          )}
        >
          <AlertTriangle
            size={15}
            className={clsx(
              "mt-0.5 shrink-0",
              a.severity === "high" || a.severity === "critical"
                ? "text-red-500"
                : "text-yellow-600"
            )}
          />
          <div className="flex-1 min-w-0">
            <p className="font-medium text-gray-900 text-xs capitalize">{a.severity} alert</p>
            <p className="text-gray-600 text-xs truncate">{a.event_type}</p>
            {a.source_ip && (
              <p className="text-gray-400 text-xs font-mono">{a.source_ip}</p>
            )}
          </div>
          <button
            onClick={() => onDismiss(a.toastId)}
            className="text-gray-400 hover:text-gray-600 shrink-0"
          >
            <X size={13} />
          </button>
        </div>
      ))}
    </div>
  );
}

// Hook to manage toast queue
export function useAlertToasts() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  function addToast(alert: AlertMessage) {
    const toastId = `${alert.log_id}-${Date.now()}`;
    setToasts((prev) => [{ ...alert, toastId }, ...prev].slice(0, 5));
    setTimeout(() => dismiss(toastId), 6000);
  }

  function dismiss(id: string) {
    setToasts((prev) => prev.filter((t) => t.toastId !== id));
  }

  return { toasts, addToast, dismiss };
}
