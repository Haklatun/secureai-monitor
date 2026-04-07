import { useEffect, useRef, useCallback } from "react";
import { getAccessToken } from "./api";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";

export interface AlertMessage {
  type: "alert";
  log_id: string;
  severity: "low" | "medium" | "high" | "critical";
  anomaly_score: number;
  source_ip: string | null;
  event_type: string;
}

type Handler = (msg: AlertMessage) => void;

export function useAlertSocket(onAlert: Handler) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>();

  const connect = useCallback(() => {
    const token = getAccessToken();
    if (!token) return;

    const ws = new WebSocket(`${WS_URL}/ws/alerts?token=${token}`);
    wsRef.current = ws;

    ws.onopen = () => console.log("[WS] connected");

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data) as AlertMessage;
        onAlert(msg);
      } catch {
        // ignore malformed messages
      }
    };

    ws.onclose = () => {
      console.log("[WS] closed — reconnecting in 3s");
      reconnectTimer.current = setTimeout(connect, 3000);
    };

    ws.onerror = () => ws.close();
  }, [onAlert]);

  useEffect(() => {
    connect();
    // Keep-alive ping
    const ping = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send("ping");
      }
    }, 25_000);

    return () => {
      clearInterval(ping);
      clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);
}
