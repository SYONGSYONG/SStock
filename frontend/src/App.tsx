import { useCallback, useEffect, useState } from "react";
import {
  ApiError,
  addStrategy,
  addWatch,
  deleteStrategy,
  getHealth,
  getMarketStatus,
  getQuote,
  getSignals,
  getStrategies,
  listWatchlist,
  removeWatch,
  setStrategyEnabled,
  startMarket,
  stopMarket,
} from "./api/client";
import { ModeBanner } from "./components/ModeBanner";
import { WatchList } from "./components/WatchList";
import { QuoteTable } from "./components/QuoteTable";
import { MarketControl } from "./components/MarketControl";
import { StrategyPanel } from "./components/StrategyPanel";
import { SignalLog } from "./components/SignalLog";
import { useLiveQuotes } from "./hooks/useLiveQuotes";
import type { MarketStatus, Signal, StrategyConfig, TradingMode, WatchItem } from "./types";

const SIGNAL_POLL_MS = 5000;

export function App() {
  const [mode, setMode] = useState<TradingMode>("paper");
  const [items, setItems] = useState<WatchItem[]>([]);
  const [market, setMarket] = useState<MarketStatus>({ running: false, symbols: [], dashboard_clients: 0 });
  const [strategies, setStrategies] = useState<StrategyConfig[]>([]);
  const [signals, setSignals] = useState<Signal[]>([]);
  const [watchError, setWatchError] = useState<string | null>(null);
  const [strategyError, setStrategyError] = useState<string | null>(null);
  const { quotes, connected, mergeSnapshot } = useLiveQuotes();

  const refreshWatch = useCallback(async () => {
    const list = await listWatchlist();
    setItems(list);
    const snapshots = await Promise.all(list.map((it) => getQuote(it.symbol).catch(() => null)));
    mergeSnapshot(snapshots.filter((q): q is NonNullable<typeof q> => q !== null));
  }, [mergeSnapshot]);

  const refreshStrategies = useCallback(async () => {
    setStrategies(await getStrategies());
  }, []);

  useEffect(() => {
    getHealth().then((h) => setMode(h.mode as TradingMode)).catch(() => {});
    refreshWatch().catch(() => {});
    refreshStrategies().catch(() => {});
    getMarketStatus().then(setMarket).catch(() => {});
  }, [refreshWatch, refreshStrategies]);

  // 신호 로그 폴링
  useEffect(() => {
    const tick = () => getSignals(50).then(setSignals).catch(() => {});
    tick();
    const id = setInterval(tick, SIGNAL_POLL_MS);
    return () => clearInterval(id);
  }, []);

  const handleAddWatch = async (symbol: string, name?: string) => {
    setWatchError(null);
    try {
      await addWatch(symbol, name);
      await refreshWatch();
    } catch (e) {
      setWatchError(e instanceof ApiError ? e.message : "추가 실패");
    }
  };

  const handleRemoveWatch = async (symbol: string) => {
    await removeWatch(symbol).catch(() => {});
    await refreshWatch();
  };

  const handleAddStrategy = async (body: Parameters<typeof addStrategy>[0]) => {
    setStrategyError(null);
    try {
      await addStrategy(body);
      await refreshStrategies();
    } catch (e) {
      setStrategyError(e instanceof ApiError ? e.message : "전략 추가 실패");
    }
  };

  const handleToggleStrategy = async (id: number, enabled: boolean) => {
    await setStrategyEnabled(id, enabled).catch(() => {});
    await refreshStrategies();
  };

  const handleRemoveStrategy = async (id: number) => {
    await deleteStrategy(id).catch(() => {});
    await refreshStrategies();
  };

  const handleStart = async () => setMarket(await startMarket());
  const handleStop = async () => {
    const r = await stopMarket();
    setMarket((m) => ({ ...m, running: r.running }));
  };

  return (
    <div className="app">
      <ModeBanner mode={mode} marketRunning={market.running} connected={connected} />
      <main className="layout">
        <aside className="sidebar">
          <WatchList items={items} onAdd={handleAddWatch} onRemove={handleRemoveWatch} error={watchError} />
          <StrategyPanel
            configs={strategies}
            onAdd={handleAddStrategy}
            onToggle={handleToggleStrategy}
            onRemove={handleRemoveStrategy}
            error={strategyError}
          />
          <MarketControl
            running={market.running}
            clients={market.dashboard_clients}
            onStart={handleStart}
            onStop={handleStop}
          />
        </aside>
        <div className="content">
          <QuoteTable items={items} quotes={quotes} />
          <SignalLog signals={signals} />
        </div>
      </main>
    </div>
  );
}
