import type { Candle } from "../types";
import { formatCandleTime } from "./chartMarkers";

/**
 * 단순이동평균(SMA)을 롤링 합산으로 계산한다. 백엔드 `rolling_sma`와 동일한 규칙:
 * - 워밍업 구간(인덱스 < period-1)은 `null`
 * - period-1 인덱스부터 직전 period개 평균
 *
 * 새 값을 더하고 범위를 벗어난 값을 빼는 단일 패스(O(n))라 봉이 많아도 가볍다.
 */
export function rollingSma(values: number[], period: number): (number | null)[] {
  const out: (number | null)[] = new Array(values.length).fill(null);
  if (period < 1) return out;
  let running = 0;
  for (let i = 0; i < values.length; i++) {
    running += values[i];
    if (i >= period) running -= values[i - period];
    if (i >= period - 1) out[i] = running / period;
  }
  return out;
}

/** 직전 값 대비 변화율(%). prev가 null·0이면 null(0으로 나누기 방지). */
export function pctChange(cur: number, prev: number | null): number | null {
  if (prev == null || prev === 0) return null;
  return ((cur - prev) / prev) * 100;
}

/** 이동평균선 구성: 기간 + 라인 색상(범례) */
export interface MaConfig {
  period: number;
  color: string;
}

export const MA_CONFIGS: MaConfig[] = [
  { period: 5, color: "#f59e0b" },
  { period: 20, color: "#2563eb" },
  { period: 60, color: "#16a34a" },
  { period: 120, color: "#9333ea" },
];

/** lightweight-charts 라인 시리즈 한 점 */
export interface LinePoint {
  time: string | number;
  value: number;
}

/**
 * 캔들 종가로 이평선 라인 데이터를 만든다. 워밍업(null) 구간은 점을 만들지 않아
 * 선이 데이터가 충분한 구간부터 그려진다.
 */
export function buildMaLineData(candles: Candle[], period: number): LinePoint[] {
  const sma = rollingSma(candles.map((c) => c.close), period);
  const points: LinePoint[] = [];
  for (let i = 0; i < candles.length; i++) {
    const v = sma[i];
    if (v != null) points.push({ time: candles[i].time, value: v });
  }
  return points;
}

export type ChangeDir = "up" | "down" | "flat";

/** tooltip 한 행: 라벨·값(포맷됨)·등락(직전 봉 대비)·방향 */
export interface TooltipRow {
  label: string;
  value: string;
  change: string | null;
  dir: ChangeDir | null;
}

/** 마우스가 가리키는 봉의 정보 박스 데이터 */
export interface TooltipData {
  time: string;
  rows: TooltipRow[];
}

/** 정수(반올림) + 천단위 콤마. */
function fmtInt(n: number): string {
  return Math.round(n).toLocaleString("ko-KR");
}

/** 변화율(%)을 부호 붙은 문자열과 방향으로. null이면 둘 다 비활성. */
function fmtChange(pct: number | null): { change: string | null; dir: ChangeDir | null } {
  if (pct == null) return { change: null, dir: null };
  const sign = pct > 0 ? "+" : ""; // 음수는 toFixed가 '-'를 붙인다
  const change = `${sign}${pct.toFixed(2)}%`;
  const dir: ChangeDir = pct > 0 ? "up" : pct < 0 ? "down" : "flat";
  return { change, dir };
}

/**
 * `index` 봉의 tooltip 데이터를 만든다. 등락 기준은 **직전 봉 대비**:
 * - 시·고·저·종: 직전 봉 종가 대비
 * - 거래량: 직전 봉 거래량 대비
 * - 이평 5/20/60/120: 직전 봉 이평 대비(데이터 부족 시 값 '-', 등락 없음)
 *
 * 인덱스가 범위를 벗어나거나 캔들이 비면 null.
 */
export function buildTooltipData(candles: Candle[], index: number): TooltipData | null {
  if (index < 0 || index >= candles.length) return null;
  const cur = candles[index];
  const prev = index > 0 ? candles[index - 1] : null;
  const prevClose = prev ? prev.close : null;

  const priceRow = (label: string, value: number): TooltipRow => {
    const { change, dir } = fmtChange(pctChange(value, prevClose));
    return { label, value: fmtInt(value), change, dir };
  };

  const rows: TooltipRow[] = [
    priceRow("시", cur.open),
    priceRow("고", cur.high),
    priceRow("저", cur.low),
    priceRow("종가", cur.close),
  ];

  // 거래량
  {
    const { change, dir } = fmtChange(pctChange(cur.volume, prev ? prev.volume : null));
    rows.push({ label: "거래량", value: fmtInt(cur.volume), change, dir });
  }

  // 이동평균 — 전체 종가로 SMA를 구해 현재/직전 인덱스 값을 읽는다.
  const closes = candles.map((c) => c.close);
  for (const { period } of MA_CONFIGS) {
    const sma = rollingSma(closes, period);
    const curMa = sma[index];
    const prevMa = index > 0 ? sma[index - 1] : null;
    if (curMa == null) {
      rows.push({ label: `이평${period}`, value: "-", change: null, dir: null });
      continue;
    }
    const { change, dir } = fmtChange(pctChange(curMa, prevMa));
    rows.push({ label: `이평${period}`, value: fmtInt(curMa), change, dir });
  }

  return { time: formatCandleTime(cur.time), rows };
}
