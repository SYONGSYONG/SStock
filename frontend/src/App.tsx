import { useCallback, useEffect, useState } from "react";
import {
  ApiError,
  addStrategy,
  addWatch,
  deleteBudget,
  deleteStrategy,
  getAudit,
  getBotStatus,
  getBudgets,
  getMarketStatus,
  getOrders,
  getPositions,
  getQuote,
  getSignals,
  getStrategies,
  listWatchlist,
  removeWatch,
  searchStocks,
  setBudget,
  setStrategyEnabled,
  startBot,
  startMarket,
  stopBot,
  stopMarket,
} from "./api/client";
import { ModeBanner } from "./components/ModeBanner";
import { WatchList } from "./components/WatchList";
import { QuoteTable } from "./components/QuoteTable";
import { MarketControl } from "./components/MarketControl";
import { BotControl } from "./components/BotControl";
import { StrategyPanel } from "./components/StrategyPanel";
import { SignalLog } from "./components/SignalLog";
import { PositionTable } from "./components/PositionTable";
import { OrderLog } from "./components/OrderLog";
import { AuditLogView } from "./components/AuditLogView";
import { BudgetPanel } from "./components/BudgetPanel";
import { useLiveQuotes } from "./hooks/useLiveQuotes";
import type {
  AuditLog,
  BotStatus,
  Budget,
  MarketStatus,
  Order,
  Position,
  Signal,
  StrategyConfig,
  WatchItem,
} from "./types";

const POLL_MS = 5000;

export function App() {
  const [items, setItems] = useState<WatchItem[]>([]);
  const [market, setMarket] = useState<MarketStatus>({ running: false, symbols: [], dashboard_clients: 0 });
  const [bot, setBot] = useState<BotStatus>({ running: false, market_running: false, mode: "paper" });
  const [strategies, setStrategies] = useState<StrategyConfig[]>([]);
  const [signals, setSignals] = useState<Signal[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [positions, setPositions] = useState<Position[]>([]);
  const [audit, setAudit] = useState<AuditLog[]>([]);
  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [watchError, setWatchError] = useState<string | null>(null);
  const [strategyError, setStrategyError] = useState<string | null>(null);
  const [botError, setBotError] = useState<string | null>(null);
  const [budgetError, setBudgetError] = useState<string | null>(null);
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
    refreshWatch().catch(() => {});
    refreshStrategies().catch(() => {});
    getMarketStatus().then(setMarket).catch(() => {});
  }, [refreshWatch, refreshStrategies]);

  // 봇/신호/주문/포지션/로그 폴링
  useEffect(() => {
    const tick = () => {
      getBotStatus().then(setBot).catch(() => {});
      getSignals(50).then(setSignals).catch(() => {});
      getOrders(50).then(setOrders).catch(() => {});
      getPositions().then(setPositions).catch(() => {});
      getAudit(100).then(setAudit).catch(() => {});
      getBudgets().then(setBudgets).catch(() => {});
      getMarketStatus().then(setMarket).catch(() => {});
    };
    tick();
    const id = setInterval(tick, POLL_MS);
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

  const handleBotStart = async (confirmLive: boolean) => {
    setBotError(null);
    try {
      setBot(await startBot(confirmLive));
    } catch (e) {
      setBotError(e instanceof ApiError ? e.message : "봇 시작 실패");
    }
  };

  const handleBotStop = async () => {
    const r = await stopBot();
    setBot((b) => ({ ...b, running: r.running }));
  };

  const handleMarketStart = async () => setMarket(await startMarket());
  const handleMarketStop = async () => {
    const r = await stopMarket();
    setMarket((m) => ({ ...m, running: r.running }));
  };

  const handleSetBudget = async (symbol: string, principal: number) => {
    setBudgetError(null);
    try {
      await setBudget(symbol, principal);
      setBudgets(await getBudgets());
    } catch (e) {
      setBudgetError(e instanceof ApiError ? e.message : "칸막이 설정 실패");
    }
  };

  const handleRemoveBudget = async (symbol: string) => {
    await deleteBudget(symbol).catch(() => {});
    setBudgets(await getBudgets());
  };

  return (
    <div className="app">
      <ModeBanner mode={bot.mode} botRunning={bot.running} connected={connected} />
      <main className="layout">
        <aside className="sidebar">
          <WatchList
            items={items}
            onAdd={handleAddWatch}
            onRemove={handleRemoveWatch}
            search={searchStocks}
            error={watchError}
          />
          <StrategyPanel
            configs={strategies}
            onAdd={handleAddStrategy}
            onToggle={handleToggleStrategy}
            onRemove={handleRemoveStrategy}
            error={strategyError}
          />
          <BudgetPanel
            budgets={budgets}
            items={items}
            onSet={handleSetBudget}
            onRemove={handleRemoveBudget}
            error={budgetError}
          />
          <BotControl
            running={bot.running}
            mode={bot.mode}
            onStart={handleBotStart}
            onStop={handleBotStop}
            error={botError}
          />
          <MarketControl
            running={market.running}
            clients={market.dashboard_clients}
            onStart={handleMarketStart}
            onStop={handleMarketStop}
          />
        </aside>
        <div className="content">
          <QuoteTable items={items} quotes={quotes} />
          <PositionTable positions={positions} quotes={quotes} />
          <OrderLog orders={orders} />
          <SignalLog signals={signals} />
          <AuditLogView logs={audit} />
        </div>
      </main>
    </div>
  );
}
