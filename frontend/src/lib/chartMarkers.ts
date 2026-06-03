import type { Candle } from "../types";
import type { SeriesMarker, Time } from "lightweight-charts";

/**
 * 캔들 시간을 포맷팅한다.
 * - 일봉/주봉 문자열 (YYYY-MM-DD): YY.MM.DD 형식
 * - 분봉 UNIX 초 (number): MM.DD HH:mm 형식 (KST)
 *
 * 분봉 `time` 값은 백엔드(charts.py)에서 이미 KST(+9h)가 더해진 상태로 내려온다
 * (lightweight-charts가 UTC로 표시하면 축이 KST 벽시계가 되도록). 따라서 라벨도
 * +9h를 다시 더하지 않고 `getUTC*`로 그대로 읽어야 한다(이중 적용 금지).
 */
export function formatCandleTime(time: string | number): string {
  if (typeof time === "string") {
    // YYYY-MM-DD → YY.MM.DD
    const parts = time.split("-");
    if (parts.length !== 3) return time;
    const [year, month, day] = parts;
    const yy = year.slice(-2);
    return `${yy}.${month}.${day}`;
  }

  // number (UNIX 초, 이미 KST 보정됨) → UTC 필드로 읽으면 KST 벽시계
  const d = new Date(time * 1000);
  const month = String(d.getUTCMonth() + 1).padStart(2, "0");
  const date = String(d.getUTCDate()).padStart(2, "0");
  const hours = String(d.getUTCHours()).padStart(2, "0");
  const minutes = String(d.getUTCMinutes()).padStart(2, "0");
  return `${month}.${date} ${hours}:${minutes}`;
}

/** 차트 위에 표시할 극점(최고/최저) 한 지점 */
export interface ExtremaPoint {
  kind: "high" | "low";
  time: string | number;
  price: number;
  label: string;
}

interface MarkerLabelParams {
  price: number;
  time: string | number;
  currentClose: number;
}

/**
 * 마커 라벨을 생성한다.
 * 형식: "가격(천단위 콤마) (날짜) 부호붙은등락률%"
 * 예: "21,100 (26.05.04) +82.70%"
 */
export function buildMarkerLabel({
  price,
  time,
  currentClose,
}: MarkerLabelParams): string {
  const formattedPrice = price.toLocaleString("ko-KR");
  const formattedTime = formatCandleTime(time);
  const changeRate =
    currentClose === 0 ? 0 : ((price - currentClose) / currentClose) * 100;
  const sign = changeRate > 0 ? "+" : "";
  const formattedRate = `${sign}${changeRate.toFixed(2)}%`;
  return `${formattedPrice} (${formattedTime}) ${formattedRate}`;
}

/**
 * 캔들 배열에서 최고가/최저가 봉을 찾아 극점 정보를 반환한다.
 * 라벨은 `가격 (날짜) 부호등락률%` 형식. 최고가와 최저가가 같은 봉이면 low는 null.
 * 캔들이 비면 null.
 */
export function findExtrema(
  candles: Candle[] | null | undefined
): { high: ExtremaPoint; low: ExtremaPoint | null } | null {
  if (!candles || candles.length === 0) {
    return null;
  }

  let maxHigh = candles[0].high;
  let minLow = candles[0].low;
  let maxHighIdx = 0;
  let minLowIdx = 0;
  for (let i = 0; i < candles.length; i++) {
    if (candles[i].high > maxHigh) {
      maxHigh = candles[i].high;
      maxHighIdx = i;
    }
    if (candles[i].low < minLow) {
      minLow = candles[i].low;
      minLowIdx = i;
    }
  }

  // 현재가 = 마지막 캔들의 close
  const currentClose = candles[candles.length - 1].close;
  const highCandle = candles[maxHighIdx];
  const high: ExtremaPoint = {
    kind: "high",
    time: highCandle.time,
    price: maxHigh,
    label: buildMarkerLabel({ price: maxHigh, time: highCandle.time, currentClose }),
  };

  let low: ExtremaPoint | null = null;
  if (minLowIdx !== maxHighIdx) {
    const lowCandle = candles[minLowIdx];
    low = {
      kind: "low",
      time: lowCandle.time,
      price: minLow,
      label: buildMarkerLabel({ price: minLow, time: lowCandle.time, currentClose }),
    };
  }

  return { high, low };
}

/**
 * 캔들 배열에서 최고가/최저가 봉을 찾아 마커(화살표)를 생성한다.
 * @param candles 캔들 배열
 * @param upColor 상승(최고가) 마커 색상
 * @param downColor 하락(최저가) 마커 색상
 * @returns SeriesMarker 배열 (최고가, 최저가 각 최대 1개)
 */
export function buildExtremaMarkers(
  candles: Candle[] | null | undefined,
  upColor: string,
  downColor: string
): SeriesMarker<Time>[] {
  const extrema = findExtrema(candles);
  if (!extrema) {
    return [];
  }

  const markers: SeriesMarker<Time>[] = [
    {
      time: extrema.high.time as Time,
      position: "aboveBar",
      color: upColor,
      shape: "arrowDown",
      text: extrema.high.label,
    },
  ];
  if (extrema.low) {
    markers.push({
      time: extrema.low.time as Time,
      position: "belowBar",
      color: downColor,
      shape: "arrowUp",
      text: extrema.low.label,
    });
  }
  return markers;
}
