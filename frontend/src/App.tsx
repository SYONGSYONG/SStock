import { Suspense, lazy, useCallback, useEffect, useState } from "react";
import {
  ApiError,
  addStrategy,
  addWatch,
  deleteBudget,
  deleteStrategy,
  getAccountBalance,
  getChart,
  getCompanyOverview,
  getAudit,
  getBotStatus,
  getBudgets,
  getMarketStatus,
  getOrders,
  getPositions,
  getQuote,
  getRecommend,
  getRegimes,
  getRiskLimits,
  getSignals,
  getStrategyPerformance,
  getTradePnl,
  getStrategies,
  getThemes,
  listWatchlist,
  removeWatch,
  searchStocks,
  setBudget,
  setStrategyEnabled,
  startBot,
  startMarket,
  stopBot,
  stopMarket,
  subscribeRecommend,
  updateRiskLimits,
} from "./api/client";
import { ModeBanner } from "./components/ModeBanner";
import { WatchQuotes } from "./components/WatchQuotes";
import { MarketControl } from "./components/MarketControl";
import { BotControl } from "./components/BotControl";
import { RiskLimitBar } from "./components/RiskLimitBar";
import { StrategyPanel } from "./components/StrategyPanel";
import {
  StrategyPerformance,
  perfPeriodStart,
  type PerfPeriod,
} from "./components/StrategyPerformance";
import { SignalLog } from "./components/SignalLog";
import { PositionTable } from "./components/PositionTable";
import { OrderLog } from "./components/OrderLog";
import { AuditLogView } from "./components/AuditLogView";
import { AccountPanel } from "./components/AccountPanel";

// 차트 라이브러리(lightweight-charts)는 무거우므로 모달을 열 때만 지연 로딩
const ChartModal = lazy(() =>
  import("./components/ChartModal").then((m) => ({ default: m.ChartModal })),
);
import { RecommendPage } from "./components/RecommendPage";
import { TradePnlPage } from "./components/TradePnlPage";
import { useLiveQuotes } from "./hooks/useLiveQuotes";
import type {
  AccountBalance,
  AuditLog,
  BotStatus,
  Budget,
  MarketStatus,
  Order,
  Position,
  RiskLimit,
  Signal,
  StrategyConfig,
  StrategyPerfRow,
  TradingMode,
  WatchItem,
} from "./types";

const POLL_MS = 5000;

export function App() {
  const [viewMode, setViewMode] = useState<TradingMode>("paper");
  const [items, setItems] = useState<WatchItem[]>([]);
  const [market, setMarket] = useState<MarketStatus>({ running: false, symbols: [], dashboard_clients: 0 });
  const [botPaper, setBotPaper] = useState<BotStatus>({ running: false, market_running: false, mode: "paper" });
  const [botLive, setBotLive] = useState<BotStatus>({ running: false, market_running: false, mode: "live" });
  const [strategies, setStrategies] = useState<StrategyConfig[]>([]);
  const [symbolPreset, setSymbolPreset] = useState<{ value: string; n: number }>({ value: "", n: 0 });
  const [signals, setSignals] = useState<Signal[]>([]);
  const [perf, setPerf] = useState<StrategyPerfRow[]>([]);
  const [perfPeriod, setPerfPeriod] = useState<PerfPeriod>("all");
  const [orders, setOrders] = useState<Order[]>([]);
  const [positions, setPositions] = useState<Position[]>([]);
  const [audit, setAudit] = useState<AuditLog[]>([]);
  const [regimes, setRegimes] = useState<Record<string, string>>({});
  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [riskLimit, setRiskLimit] = useState<RiskLimit | null>(null);
  const [riskLimitError, setRiskLimitError] = useState<string | null>(null);
  const [account, setAccount] = useState<AccountBalance | null>(null);
  const [chartTarget, setChartTarget] = useState<{ symbol: string; name?: string | null; source: "dashboard" | "recommend" } | null>(null);
  const [watchError, setWatchError] = useState<string | null>(null);
  const [strategyError, setStrategyError] = useState<string | null>(null);
  const [botError, setBotError] = useState<string | null>(null);
  const [budgetError, setBudgetError] = useState<string | null>(null);
  const [tab, setTab] = useState<"dashboard" | "recommend" | "trade_pnl">("dashboard");
  const { quotes, connected, mergeSnapshot } = useLiveQuotes(viewMode);

  // 보는 모드에 해당하는 봇 상태 선택
  const bot = viewMode === "paper" ? botPaper : botLive;

  const refreshWatch = useCallback(async () => {
    const list = await listWatchlist(viewMode);
    setItems(list);
    const snapshots = await Promise.all(list.map((it) => getQuote(it.symbol).catch(() => null)));
    mergeSnapshot(snapshots.filter((q): q is NonNullable<typeof q> => q !== null));
  }, [viewMode, mergeSnapshot]);

  const refreshStrategies = useCallback(async () => {
    setStrategies(await getStrategies(viewMode));
  }, [viewMode]);

  useEffect(() => {
    refreshWatch().catch(() => {});
    refreshStrategies().catch(() => {});
    getMarketStatus(viewMode).then(setMarket).catch(() => {});
    getRiskLimits(viewMode).then(setRiskLimit).catch(() => {});
  }, [viewMode, refreshWatch, refreshStrategies]);

  // 봇/신호/주문/포지션/로그 폴링.
  // 대시보드 탭이 실제로 보일 때만 폴링한다 — 추천 탭/백그라운드/차트 모달 중에는
  // 멈춰 KIS 호출(잔고·포지션)을 아껴 차트 등 사용자 조회와의 레이트리밋 경합을 막는다.
  const chartOpen = chartTarget !== null;
  useEffect(() => {
    if (tab !== "dashboard" || chartOpen) return;

    const tick = () => {
      if (document.hidden) return; // 탭이 백그라운드면 건너뜀
      // 양쪽 봇 상태를 모두 폴링(헤더에 표기)
      getBotStatus("paper").then(setBotPaper).catch(() => {});
      getBotStatus("live").then(setBotLive).catch(() => {});
      // 나머지는 보는 모드로 폴링
      getSignals(50, viewMode).then(setSignals).catch(() => {});
      getStrategyPerformance(viewMode, perfPeriodStart(perfPeriod))
        .then((d) => setPerf(d.rows))
        .catch(() => {});
      getOrders(50, viewMode).then(setOrders).catch(() => {});
      getPositions(viewMode).then(setPositions).catch(() => {});
      getAudit(100, viewMode).then(setAudit).catch(() => {});
      getRegimes(viewMode).then(setRegimes).catch(() => {});
      getBudgets(viewMode).then(setBudgets).catch(() => {});
      getRiskLimits(viewMode).then(setRiskLimit).catch(() => {});
      getAccountBalance(viewMode).then(setAccount).catch(() => {});
      getMarketStatus(viewMode).then(setMarket).catch(() => {});
    };
    const onVisible = () => {
      if (!document.hidden) tick(); // 다시 보이면 즉시 1회 갱신
    };
    document.addEventListener("visibilitychange", onVisible);
    tick();
    const id = setInterval(tick, POLL_MS);
    return () => {
      clearInterval(id);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [viewMode, tab, chartOpen, perfPeriod]);

  const handleAddWatch = async (symbol: string, name?: string) => {
    setWatchError(null);
    try {
      await addWatch(symbol, viewMode, name);
      await refreshWatch();
    } catch (e) {
      setWatchError(e instanceof ApiError ? e.message : "추가 실패");
    }
  };

  const handleRemoveWatch = async (symbol: string) => {
    await removeWatch(symbol, viewMode).catch(() => {});
    await refreshWatch();
  };

  const handleAddStrategy = async (body: Parameters<typeof addStrategy>[0]) => {
    setStrategyError(null);
    try {
      await addStrategy(body, viewMode);
      await refreshStrategies();
    } catch (e) {
      setStrategyError(e instanceof ApiError ? e.message : "전략 추가 실패");
    }
  };

  // 실시간 시세에서 종목코드 클릭 → 전략 폼에 채운다. 이미 전략이 있으면 알림만.
  const handlePickSymbol = (sym: string) => {
    const existing = strategies.find((s) => s.symbol === sym);
    if (existing) {
      window.alert(`${sym}${existing.name ? ` ${existing.name}` : ""} — 이미 전략이 등록된 종목입니다.`);
      return;
    }
    setSymbolPreset((p) => ({ value: sym, n: p.n + 1 }));
  };

  const handleToggleStrategy = async (id: number, enabled: boolean) => {
    await setStrategyEnabled(id, enabled).catch(() => {});
    await refreshStrategies();
  };

  // 전략 수정 저장. 전략 종류가 바뀌면 새 전략을 먼저 추가한 뒤 기존 전략을 지워 교체한다.
  // (먼저 추가하므로 해당 종목엔 항상 전략이 남아 있어 칸막이는 보존된다.)
  const handleEditStrategy = async (
    oldId: number,
    body: Parameters<typeof addStrategy>[0],
  ) => {
    setStrategyError(null);
    try {
      const old = strategies.find((s) => s.id === oldId);
      await addStrategy(body, viewMode);
      if (old && old.strategy !== body.strategy) {
        await deleteStrategy(oldId);
      }
      await refreshStrategies();
    } catch (e) {
      setStrategyError(e instanceof ApiError ? e.message : "전략 수정 실패");
    }
  };

  const handleRemoveStrategy = async (id: number) => {
    const target = strategies.find((s) => s.id === id);
    await deleteStrategy(id).catch(() => {});
    const fresh = await getStrategies(viewMode);
    setStrategies(fresh);
    // 전략·칸막이는 한 쌍 → 해당 종목에 남은 전략이 없으면 칸막이도 함께 정리
    if (target && !fresh.some((s) => s.symbol === target.symbol)) {
      await deleteBudget(target.symbol, viewMode).catch(() => {});
    }
    setBudgets(await getBudgets(viewMode));
  };

  const handleBotStart = async (confirmLive: boolean) => {
    setBotError(null);
    try {
      const result = await startBot(confirmLive, viewMode);
      if (viewMode === "paper") {
        setBotPaper(result);
      } else {
        setBotLive(result);
      }
    } catch (e) {
      setBotError(e instanceof ApiError ? e.message : "봇 시작 실패");
    }
  };

  const handleBotStop = async () => {
    const r = await stopBot(viewMode);
    if (viewMode === "paper") {
      setBotPaper((b) => ({ ...b, running: r.running }));
    } else {
      setBotLive((b) => ({ ...b, running: r.running }));
    }
  };

  const handleMarketStart = async () => setMarket(await startMarket(viewMode));
  const handleMarketStop = async () => {
    const r = await stopMarket(viewMode);
    setMarket((m) => ({ ...m, running: r.running }));
  };

  const handleSetRiskLimit = async (
    maxOrders: number,
    maxAmount: number,
    maxDailyLoss: number,
  ) => {
    setRiskLimitError(null);
    try {
      setRiskLimit(await updateRiskLimits(maxOrders, maxAmount, maxDailyLoss, viewMode));
    } catch (e) {
      setRiskLimitError(e instanceof ApiError ? e.message : "한도 변경 실패");
    }
  };

  const handleSetBudget = async (symbol: string, principal: number) => {
    setBudgetError(null);
    try {
      await setBudget(symbol, principal, viewMode);
      setBudgets(await getBudgets(viewMode));
    } catch (e) {
      setBudgetError(e instanceof ApiError ? e.message : "칸막이 설정 실패");
    }
  };

  // 전략이 등록된 종목코드 집합
  const strategySymbols = new Set(strategies.map((s) => s.symbol));

  return (
    <div className="app">
      <ModeBanner
        viewMode={viewMode}
        onSwitchMode={setViewMode}
        paperBotRunning={botPaper.running}
        liveBotRunning={botLive.running}
        connected={connected}
        controls={
          <>
            <BotControl
              compact
              running={bot.running}
              mode={bot.mode}
              onStart={handleBotStart}
              onStop={handleBotStop}
              error={botError}
            />
            <MarketControl
              compact
              running={market.running}
              clients={market.dashboard_clients}
              onStart={handleMarketStart}
              onStop={handleMarketStop}
            />
          </>
        }
      />
      <nav className="tabs" aria-label="화면 전환">
        <button
          className={tab === "dashboard" ? "tab active" : "tab"}
          onClick={() => setTab("dashboard")}
        >
          대시보드
        </button>
        <button
          className={tab === "recommend" ? "tab active" : "tab"}
          onClick={() => setTab("recommend")}
        >
          분야별 추천
        </button>
        <button
          className={tab === "trade_pnl" ? "tab active" : "tab"}
          onClick={() => setTab("trade_pnl")}
        >
          기간별 손익
        </button>
      </nav>
      {tab === "recommend" ? (
        <RecommendPage
          fetchThemes={getThemes}
          subscribeRecommend={subscribeRecommend}
          fetchRecommend={getRecommend}
          onAdd={handleAddWatch}
          onSelect={(symbol, name) => setChartTarget({ symbol, name, source: "recommend" })}
          watchedSymbols={new Set(items.map((it) => it.symbol))}
        />
      ) : tab === "trade_pnl" ? (
        <TradePnlPage mode={viewMode} fetchTradePnl={getTradePnl} />
      ) : (
      <main className="layout">
        {/* 계좌잔고 : 오늘 주문한도 = 2:1 */}
        <div className="row row-2-1">
          <AccountPanel balance={account} />
          <RiskLimitBar
            data={riskLimit}
            mode={viewMode}
            onUpdate={handleSetRiskLimit}
            error={riskLimitError}
          />
        </div>
        {/* 보유 포지션(전체 폭) */}
        <PositionTable positions={positions} quotes={quotes} />
        {/* 실시간 시세(전체 폭) */}
        <WatchQuotes
          items={items}
          quotes={quotes}
          strategySymbols={strategySymbols}
          onAdd={handleAddWatch}
          onRemove={handleRemoveWatch}
          onSelect={(symbol, name) => setChartTarget({ symbol, name, source: "dashboard" })}
          onPickSymbol={handlePickSymbol}
          search={searchStocks}
          error={watchError}
        />
        {/* 전략(전체 폭 · 내부에서 추가 폼 좌 / 등록 전략 우) */}
        <section className="panel rules-panel">
          <StrategyPanel
            configs={strategies}
            budgets={budgets}
            regimes={regimes}
            perf={perf}
            items={items}
            presetSymbol={symbolPreset}
            onAdd={handleAddStrategy}
            onSetBudget={handleSetBudget}
            onToggle={handleToggleStrategy}
            onRemove={handleRemoveStrategy}
            onEditStrategy={handleEditStrategy}
            orderableCash={account?.orderable_cash ?? null}
            error={strategyError}
            budgetError={budgetError}
          />
        </section>
        {/* 전략 성과(섀도우) — 신호 기반 가상 성과 보드(전체 폭) */}
        <StrategyPerformance
          rows={perf}
          configs={strategies}
          quotes={quotes}
          period={perfPeriod}
          onPeriodChange={setPerfPeriod}
        />
        {/* 주문내역 : 매매신호 = 1:1 */}
        <div className="row row-1-1">
          <OrderLog orders={orders} />
          <SignalLog signals={signals} />
        </div>
        {/* 시스템 로그(전체 폭) */}
        <AuditLogView logs={audit} />
      </main>
      )}
      {chartTarget && (
        <Suspense fallback={null}>
          <ChartModal
            symbol={chartTarget.symbol}
            name={chartTarget.name ?? items.find((it) => it.symbol === chartTarget.symbol)?.name}
            minuteScope={chartTarget.source === "dashboard" ? "today" : "session"}
            fetchChart={getChart}
            fetchOverview={getCompanyOverview}
            onClose={() => setChartTarget(null)}
          />
        </Suspense>
      )}
    </div>
  );
}
