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
  name?: string | null;
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
  name?: string | null;
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
  name?: string | null;
  qty: number;
  avg_price?: number | null;
  price?: number | null;
  eval_amount?: number | null;
  pl_amount?: number | null;
  pl_rate?: number | null;
}

export interface AuditLog {
  id: number;
  category: string;
  message: string;
  created_at: string;
}

export type ChartInterval = "daily" | "weekly" | "minute";

export interface Candle {
  time: string | number; // 일봉: "YYYY-MM-DD", 분봉: UNIX 초
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface ChartData {
  symbol: string;
  interval: ChartInterval;
  candles: Candle[];
}

export interface AccountBalance {
  mode: TradingMode;
  available: boolean; // KIS 조회 성공 여부(false면 모든 값 null)
  deposit: number | null; // 예수금총금액
  orderable_cash: number | null; // 주문가능현금(가수도정산금액)
  purchase_amount: number | null; // 매입금액합계
  eval_amount: number | null; // 평가금액합계
  eval_pnl: number | null; // 평가손익합계
  total_eval: number | null; // 총평가금액
  net_asset: number | null; // 순자산금액
}

export interface Budget {
  symbol: string;
  principal: number;
  realized_pnl: number;
  holding_cost: number;
  ceiling: number;
  available: number;
}

export interface ThemeInfo {
  slug: string;
  label: string;
  count: number;
}

export interface RecommendItem {
  symbol: string;
  name: string;
  market: string;
  score: number;
  momentum: number;
  fundamental: number;
  supply: number;
  price: number | null;
  change_rate: number | null;
  roe: number | null;
}

export interface RecommendResult {
  theme: string;
  base_date: string | null;
  price_date?: string | null;
  items: RecommendItem[];
}

export interface RecommendCandidate {
  symbol: string;
  name: string | null;
  market: string | null;
}

export interface RecommendCandidates {
  theme: string;
  base_date: string | null;
  candidates: RecommendCandidate[];
}

export interface RecommendQuote {
  symbol: string;
  price: number | null;
  change_rate: number | null;
  volume: number | null;
}
