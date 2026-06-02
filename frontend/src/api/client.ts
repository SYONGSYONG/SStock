import type { MarketStatus, Quote, WatchItem } from "../types";

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

export const getQuote = (symbol: string) => api<Quote>(`/api/quotes/${symbol}`);

export const getMarketStatus = () => api<MarketStatus>("/api/market/status");

export const startMarket = () => api<MarketStatus>("/api/market/start", { method: "POST" });

export const stopMarket = () => api<{ running: boolean }>("/api/market/stop", { method: "POST" });
