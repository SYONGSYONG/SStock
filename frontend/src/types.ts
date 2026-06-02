export interface WatchItem {
  id: number;
  symbol: string;
  name: string | null;
  created_at: string;
}

export interface StockSearchResult {
  symbol: string;
  name: string;
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

export type StrategyName = "ma_cross" | "rsi";

export interface StrategyConfig {
  id: number;
  symbol: string;
  strategy: StrategyName;
  params: Record<string, number>;
  enabled: boolean;
  max_qty: number | null;
  max_amount: number | null;
}

export interface Signal {
  id: number;
  symbol: string;
  strategy: string;
  side: "BUY" | "SELL";
  price: number | null;
  reason: string;
  created_at: string;
}

export interface BotStatus {
  running: boolean;
  market_running: boolean;
  mode: TradingMode;
}

export interface Order {
  id: number;
  symbol: string;
  side: "BUY" | "SELL";
  qty: number;
  price: number | null;
  mode: string;
  status: string;
  kis_order_no: string | null;
  created_at: string;
}

export interface Position {
  symbol: string;
  qty: number;
}

export interface AuditLog {
  id: number;
  category: string;
  message: string;
  created_at: string;
}

export interface Budget {
  symbol: string;
  principal: number;
  realized_pnl: number;
  holding_cost: number;
  ceiling: number;
  available: number;
}
