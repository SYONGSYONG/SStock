import type {
  AccountBalance,
  AuditLog,
  BotStatus,
  Budget,
  ChartData,
  ChartInterval,
  CompanyOverview,
  MarketStatus,
  Order,
  Position,
  Quote,
  RecommendCandidates,
  RecommendQuote,
  RecommendResult,
  Signal,
  StockSearchResult,
  StrategyConfig,
  StrategyName,
  ThemeInfo,
  TradingMode,
  WatchItem,
} from "../types";

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
  }
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new ApiError(res.status, body.code ?? "ERROR", body.error ?? res.statusText);
  }
  return body.data as T;
}

/** 쿼리 파라미터에 mode를 추가합니다. */
function withMode(url: string, mode: TradingMode): string {
  const separator = url.includes("?") ? "&" : "?";
  return `${url}${separator}mode=${mode}`;
}

export const getHealth = () => api<{ status: string; mode: string }>("/health");

export const listWatchlist = (mode: TradingMode) =>
  api<WatchItem[]>(withMode("/api/watchlist", mode));

export const addWatch = (symbol: string, mode: TradingMode, name?: string) =>
  api<WatchItem>(withMode("/api/watchlist", mode), {
    method: "POST",
    body: JSON.stringify({ symbol, name: name ?? null }),
  });

export const removeWatch = (symbol: string, mode: TradingMode) =>
  api<{ symbol: string; removed: boolean }>(withMode(`/api/watchlist/${symbol}`, mode), {
    method: "DELETE",
  });

export const searchStocks = (q: string, limit = 20) =>
  api<StockSearchResult[]>(`/api/stocks/search?q=${encodeURIComponent(q)}&limit=${limit}`);

export const getQuote = (symbol: string) => api<Quote>(`/api/quotes/${symbol}`);

export const getMarketStatus = (mode: TradingMode) =>
  api<MarketStatus>(withMode("/api/market/status", mode));

export const startMarket = (mode: TradingMode) =>
  api<MarketStatus>(withMode("/api/market/start", mode), { method: "POST" });

export const stopMarket = (mode: TradingMode) =>
  api<{ running: boolean }>(withMode("/api/market/stop", mode), { method: "POST" });

export const getStrategies = (mode: TradingMode) =>
  api<StrategyConfig[]>(withMode("/api/strategies", mode));

export const addStrategy = (
  body: {
    symbol: string;
    strategy: StrategyName;
    params: Record<string, number>;
    enabled: boolean;
  },
  mode: TradingMode,
) => api<StrategyConfig>(withMode("/api/strategies", mode), {
  method: "POST",
  body: JSON.stringify(body),
});

export const setStrategyEnabled = (id: number, enabled: boolean) =>
  api<{ id: number; enabled: boolean }>(`/api/strategies/${id}/enabled`, {
    method: "PATCH",
    body: JSON.stringify({ enabled }),
  });

export const deleteStrategy = (id: number) =>
  api<{ id: number; removed: boolean }>(`/api/strategies/${id}`, { method: "DELETE" });

export const getSignals = (limit = 50) => api<Signal[]>(`/api/signals?limit=${limit}`);

export const getBotStatus = (mode: TradingMode) =>
  api<BotStatus>(withMode("/api/bot/status", mode));

export const startBot = (confirmLive = false, mode: TradingMode = "paper") =>
  api<BotStatus>(withMode("/api/bot/start", mode), {
    method: "POST",
    body: JSON.stringify({ confirm_live: confirmLive }),
  });

export const stopBot = (mode: TradingMode) =>
  api<{ running: boolean }>(withMode("/api/bot/stop", mode), { method: "POST" });

export const getOrders = (limit = 50, mode: TradingMode) =>
  api<Order[]>(withMode(`/api/orders?limit=${limit}`, mode));

export const getPositions = (mode: TradingMode) =>
  api<Position[]>(withMode("/api/positions", mode));

export const getAccountBalance = (mode: TradingMode) =>
  api<AccountBalance>(withMode("/api/account/balance", mode));

export const getChart = (
  symbol: string,
  interval: ChartInterval = "daily",
  opts?: { unit?: number; scope?: "today" | "session"; signal?: AbortSignal },
) => {
  const q = new URLSearchParams({ interval });
  if (interval === "minute" && opts?.unit) q.set("unit", String(opts.unit));
  if (interval === "minute" && opts?.scope) q.set("scope", opts.scope);
  return api<ChartData>(`/api/charts/${symbol}?${q.toString()}`, { signal: opts?.signal });
};

export const getCompanyOverview = (symbol: string) =>
  api<CompanyOverview>(`/api/company/${symbol}/overview`);

export const getAudit = (limit = 100) => api<AuditLog[]>(`/api/audit?limit=${limit}`);

export const getBudgets = (mode: TradingMode) =>
  api<Budget[]>(withMode("/api/budgets", mode));

export const setBudget = (symbol: string, principal: number, mode: TradingMode) =>
  api<Budget>(withMode("/api/budgets", mode), {
    method: "PUT",
    body: JSON.stringify({ symbol, principal }),
  });

export const deleteBudget = (symbol: string, mode: TradingMode) =>
  api<{ symbol: string; removed: boolean }>(withMode(`/api/budgets/${symbol}`, mode), {
    method: "DELETE",
  });

export const getThemes = () => api<ThemeInfo[]>("/api/recommend/themes");

export const getRecommend = (theme: string, limit = 10, signal?: AbortSignal) =>
  api<RecommendResult>(`/api/recommend/${theme}?limit=${limit}`, { signal });

export interface RecommendStreamHandlers {
  onCandidates: (c: RecommendCandidates) => void;
  onQuote: (q: RecommendQuote) => void;
  onResult: (r: RecommendResult) => void;
  onError: () => void;
}

export function subscribeRecommend(
  theme: string,
  limit: number,
  handlers: RecommendStreamHandlers,
): () => void {
  const es = new EventSource(`/api/recommend/${theme}/stream?limit=${limit}`);

  es.addEventListener("candidates", (e) => {
    const event = e as MessageEvent;
    handlers.onCandidates(JSON.parse(event.data) as RecommendCandidates);
  });

  es.addEventListener("quote", (e) => {
    const event = e as MessageEvent;
    handlers.onQuote(JSON.parse(event.data) as RecommendQuote);
  });

  es.addEventListener("result", (e) => {
    const event = e as MessageEvent;
    handlers.onResult(JSON.parse(event.data) as RecommendResult);
    es.close();
  });

  es.addEventListener("error", () => {
    handlers.onError();
    es.close();
  });

  return () => es.close();
}
