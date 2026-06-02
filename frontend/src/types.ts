export interface WatchItem {
  id: number;
  symbol: string;
  name: string | null;
  created_at: string;
}

export interface Quote {
  symbol: string;
  price: number | null;
  change: number | null;
  change_rate: number | null;
  sign: string | null;
  volume: number | null;
  open?: number | null;
  high?: number | null;
  low?: number | null;
}

export interface MarketStatus {
  running: boolean;
  symbols: string[];
  dashboard_clients: number;
}

export type TradingMode = "paper" | "live";
