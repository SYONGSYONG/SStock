import { useCallback, useEffect, useState } from "react";
import {
  ApiError,
  addWatch,
  getHealth,
  getMarketStatus,
  getQuote,
  listWatchlist,
  removeWatch,
  startMarket,
  stopMarket,
} from "./api/client";
import { ModeBanner } from "./components/ModeBanner";
import { WatchList } from "./components/WatchList";
import { QuoteTable } from "./components/QuoteTable";
import { MarketControl } from "./components/MarketControl";
import { useLiveQuotes } from "./hooks/useLiveQuotes";
import type { MarketStatus, TradingMode, WatchItem } from "./types";

export function App() {
  const [mode, setMode] = useState<TradingMode>("paper");
  const [items, setItems] = useState<WatchItem[]>([]);
  const [market, setMarket] = useState<MarketStatus>({ running: false, symbols: [], dashboard_clients: 0 });
  const [watchError, setWatchError] = useState<string | null>(null);
  const { quotes, connected, mergeSnapshot } = useLiveQuotes();

  const refreshWatch = useCallback(async () => {
    const list = await listWatchlist();
    setItems(list);
    const snapshots = await Promise.all(
      list.map((it) => getQuote(it.symbol).catch(() => null)),
    );
    mergeSnapshot(snapshots.filter((q): q is NonNullable<typeof q> => q !== null));
  }, [mergeSnapshot]);

  useEffect(() => {
    getHealth().then((h) => setMode(h.mode as TradingMode)).catch(() => {});
    refreshWatch().catch(() => {});
    getMarketStatus().then(setMarket).catch(() => {});
  }, [refreshWatch]);

  const handleAdd = async (symbol: string, name?: string) => {
    setWatchError(null);
    try {
      await addWatch(symbol, name);
      await refreshWatch();
    } catch (e) {
      setWatchError(e instanceof ApiError ? e.message : "추가 실패");
    }
  };

  const handleRemove = async (symbol: string) => {
    await removeWatch(symbol).catch(() => {});
    await refreshWatch();
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
          <WatchList items={items} onAdd={handleAdd} onRemove={handleRemove} error={watchError} />
          <MarketControl
            running={market.running}
            clients={market.dashboard_clients}
            onStart={handleStart}
            onStop={handleStop}
          />
        </aside>
        <div className="content">
          <QuoteTable items={items} quotes={quotes} />
        </div>
      </main>
    </div>
  );
}
