import { useCallback, useEffect, useRef, useState } from "react";
import type { Quote } from "../types";

const RECONNECT_MIN_MS = 500;
const RECONNECT_MAX_MS = 10_000;

export function useLiveQuotes() {
  const [quotes, setQuotes] = useState<Record<string, Quote>>({});
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);
  const retryCountRef = useRef(0);
  const shouldReconnectRef = useRef(true);

  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimerRef.current != null) {
      window.clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    if (!shouldReconnectRef.current) return;
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) return;

    const proto = location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${location.host}/ws/quotes`);
    wsRef.current = ws;

    ws.onopen = () => {
      retryCountRef.current = 0;
      clearReconnectTimer();
      setConnected(true);
    };

    ws.onclose = () => {
      wsRef.current = null;
      setConnected(false);
      if (!shouldReconnectRef.current) return;

      const retry = retryCountRef.current + 1;
      retryCountRef.current = retry;
      const delay = Math.min(RECONNECT_MIN_MS * 2 ** (retry - 1), RECONNECT_MAX_MS);
      clearReconnectTimer();
      reconnectTimerRef.current = window.setTimeout(() => {
        connect();
      }, delay);
    };

    ws.onerror = () => {
      try {
        ws.close();
      } catch {
        // ignore close errors
      }
    };

    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.type === "tick" && msg.data?.symbol) {
          setQuotes((prev) => ({ ...prev, [msg.data.symbol]: { ...prev[msg.data.symbol], ...msg.data } }));
        }
      } catch {
        // ignore malformed messages
      }
    };
  }, [clearReconnectTimer]);

  useEffect(() => {
    shouldReconnectRef.current = true;
    connect();

    return () => {
      shouldReconnectRef.current = false;
      clearReconnectTimer();
      const ws = wsRef.current;
      wsRef.current = null;
      if (ws) {
        try {
          ws.close();
        } catch {
          // ignore close errors
        }
      }
    };
  }, [clearReconnectTimer, connect]);

  const mergeSnapshot = useCallback((snapshot: Quote[]) => {
    setQuotes((prev) => {
      const next = { ...prev };
      for (const q of snapshot) next[q.symbol] = { ...next[q.symbol], ...q };
      return next;
    });
  }, []);

  return { quotes, connected, mergeSnapshot };
}
