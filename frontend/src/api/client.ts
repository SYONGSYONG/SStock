import type {
  AccountBalance,
  AuditLog,
  BotStatus,
  Budget,
  ChartData,
  ChartInterval,
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

export const getHealth = () => api<{ status: string; mode: string }>("/health");

export const listWatchlist = () => api<WatchItem[]>("/api/watchlist");

export const addWatch = (symbol: string, name?: string) =>
  api<WatchItem>("/api/watchlist", {
    method: "POST",
    body: JSON.stringify({ symbol, name: name ?? null }),
  });

export const removeWatch = (symbol: string) =>
  api<{ symbol: string; removed: boolean }>(`/api/watchlist/${symbol}`, { method: "DELETE" });

export const searchStocks = (q: string, limit = 20) =>
  api<StockSearchResult[]>(`/api/stocks/search?q=${encodeURIComponent(q)}&limit=${limit}`);

export const getQuote = (symbol: string) => api<Quote>(`/api/quotes/${symbol}`);

export const getMarketStatus = () => api<MarketStatus>("/api/market/status");

export const startMarket = () => api<MarketStatus>("/api/market/start", { method: "POST" });

export const stopMarket = () => api<{ running: boolean }>("/api/market/stop", { method: "POST" });

export const getStrategies = () => api<StrategyConfig[]>("/api/strategies");

export const addStrategy = (body: {
  symbol: string;
  strategy: StrategyName;
  params: Record<string, number>;
  enabled: boolean;
}) => api<StrategyConfig>("/api/strategies", { method: "POST", body: JSON.stringify(body) });

export const setStrategyEnabled = (id: number, enabled: boolean) =>
  api<{ id: number; enabled: boolean }>(`/api/strategies/${id}/enabled`, {
    method: "PATCH",
    body: JSON.stringify({ enabled }),
  });

export const deleteStrategy = (id: number) =>
  api<{ id: number; removed: boolean }>(`/api/strategies/${id}`, { method: "DELETE" });

export const getSignals = (limit = 50) => api<Signal[]>(`/api/signals?limit=${limit}`);

export const getBotStatus = () => api<BotStatus>("/api/bot/status");

export const startBot = (confirmLive = false) =>
  api<BotStatus>("/api/bot/start", {
    method: "POST",
    body: JSON.stringify({ confirm_live: confirmLive }),
  });

export const stopBot = () => api<{ running: boolean }>("/api/bot/stop", { method: "POST" });

export const getOrders = (limit = 50) => api<Order[]>(`/api/orders?limit=${limit}`);

export const getPositions = () => api<Position[]>("/api/positions");

export const getAccountBalance = () => api<AccountBalance>("/api/account/balance");

export const getChart = (symbol: string, interval: ChartInterval = "daily", signal?: AbortSignal) =>
  api<ChartData>(`/api/charts/${symbol}?interval=${interval}`, { signal });

export const getAudit = (limit = 100) => api<AuditLog[]>(`/api/audit?limit=${limit}`);

export const getBudgets = () => api<Budget[]>("/api/budgets");

export const setBudget = (symbol: string, principal: number) =>
  api<Budget>("/api/budgets", {
    method: "PUT",
    body: JSON.stringify({ symbol, principal }),
  });

export const deleteBudget = (symbol: string) =>
  api<{ symbol: string; removed: boolean }>(`/api/budgets/${symbol}`, { method: "DELETE" });

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
