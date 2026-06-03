import { renderHook, act } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { useLiveQuotes } from "../hooks/useLiveQuotes";

type WsHandler = ((ev?: any) => void) | null;

class MockWebSocket {
  static instances: MockWebSocket[] = [];
  static OPEN = 1;
  static CLOSED = 3;

  readyState = MockWebSocket.OPEN;
  onopen: WsHandler = null;
  onclose: WsHandler = null;
  onmessage: WsHandler = null;
  onerror: WsHandler = null;
  url: string;

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  close() {
    if (this.readyState === MockWebSocket.CLOSED) return;
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.({});
  }

  emitOpen() {
    this.onopen?.({});
  }

  emitMessage(data: any) {
    this.onmessage?.({ data: JSON.stringify(data) });
  }
}

describe("useLiveQuotes", () => {
  beforeEach(() => {
    MockWebSocket.instances = [];
    vi.stubGlobal("WebSocket", MockWebSocket as any);
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  test("연결이 끊기면 백오프 후 재연결한다", () => {
    const { result, unmount } = renderHook(() => useLiveQuotes());

    expect(MockWebSocket.instances).toHaveLength(1);
    expect(result.current.connected).toBe(false);

    act(() => {
      MockWebSocket.instances[0].emitOpen();
    });
    expect(result.current.connected).toBe(true);

    act(() => {
      MockWebSocket.instances[0].close();
    });
    expect(result.current.connected).toBe(false);

    act(() => {
      vi.advanceTimersByTime(500);
    });
    expect(MockWebSocket.instances).toHaveLength(2);

    act(() => {
      MockWebSocket.instances[1].emitOpen();
    });
    expect(result.current.connected).toBe(true);

    unmount();
  });

  test("틱 메시지를 합친다", () => {
    const { result } = renderHook(() => useLiveQuotes("paper"));
    act(() => {
      MockWebSocket.instances[0].emitOpen();
      MockWebSocket.instances[0].emitMessage({
        type: "tick",
        mode: "paper",
        data: { symbol: "005930", price: 70000, change: 100 },
      });
    });

    expect(result.current.quotes["005930"].price).toBe(70000);
    expect(result.current.quotes["005930"].change).toBe(100);
  });

  test("다른 모드 메시지는 필터링한다", () => {
    const { result } = renderHook(() => useLiveQuotes("paper"));
    act(() => {
      MockWebSocket.instances[0].emitOpen();
      // live 모드 메시지 전송
      MockWebSocket.instances[0].emitMessage({
        type: "tick",
        mode: "live",
        data: { symbol: "005930", price: 70000, change: 100 },
      });
    });

    // paper 모드이므로 live 메시지는 무시됨
    expect(result.current.quotes["005930"]).toBeUndefined();
  });

  test("모드 전환 시 이전 모드의 시세를 초기화한다", () => {
    type ViewMode = "paper" | "live";
    const { result, rerender } = renderHook(
      ({ viewMode }: { viewMode: ViewMode }) => useLiveQuotes(viewMode),
      { initialProps: { viewMode: "paper" as ViewMode } },
    );

    act(() => {
      MockWebSocket.instances[0].emitOpen();
      MockWebSocket.instances[0].emitMessage({
        type: "tick",
        mode: "paper",
        data: { symbol: "005930", price: 70000 },
      });
    });

    expect(result.current.quotes["005930"]).toBeDefined();

    act(() => {
      rerender({ viewMode: "live" as ViewMode });
    });

    // 모드 전환 후 이전 시세는 초기화됨
    expect(result.current.quotes["005930"]).toBeUndefined();
  });
});
