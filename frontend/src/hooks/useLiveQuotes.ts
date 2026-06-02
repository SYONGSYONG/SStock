import { useCallback, useEffect, useRef, useState } from "react";
import type { Quote } from "../types";

/** 대시보드 WebSocket(/ws/quotes)에 연결해 실시간 체결을 종목별로 병합한다. */
export function useLiveQuotes() {
  const [quotes, setQuotes] = useState<Record<string, Quote>>({});
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${location.host}/ws/quotes`);
    wsRef.current = ws;
    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.type === "tick" && msg.data?.symbol) {
          setQuotes((prev) => ({ ...prev, [msg.data.symbol]: { ...prev[msg.data.symbol], ...msg.data } }));
        }
      } catch {
        // 파싱 불가 메시지는 무시
      }
    };
    return () => ws.close();
  }, []);

  /** REST 스냅샷을 병합한다(초기 표시용). */
  const mergeSnapshot = useCallback((snapshot: Quote[]) => {
    setQuotes((prev) => {
      const next = { ...prev };
      for (const q of snapshot) next[q.symbol] = { ...next[q.symbol], ...q };
      return next;
    });
  }, []);

  return { quotes, connected, mergeSnapshot };
}
