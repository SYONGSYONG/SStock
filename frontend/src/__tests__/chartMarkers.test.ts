import { describe, expect, test } from "vitest";
import {
  buildExtremaMarkers,
  findExtrema,
  formatCandleTime,
  buildMarkerLabel,
} from "../lib/chartMarkers";
import type { Candle } from "../types";

const UP = "#d12e2e";
const DOWN = "#1f5fd1";

describe("차트마커: 최고가·최저가", () => {
  describe("formatCandleTime: 시간 포맷팅", () => {
    test("일봉 문자열 YYYY-MM-DD를 YY.MM.DD로 변환", () => {
      expect(formatCandleTime("2026-05-04")).toBe("26.05.04");
      expect(formatCandleTime("2025-12-31")).toBe("25.12.31");
    });

    test("분봉 UNIX 초(number)를 MM.DD HH:mm로 변환", () => {
      const formatted = formatCandleTime(1717384200);
      expect(formatted).toMatch(/^\d{2}\.\d{2} \d{2}:\d{2}$/);
    });

    test("분봉 time은 이미 KST 보정 → +9h 이중 적용하지 않는다", () => {
      // 백엔드가 KST(+9h) 보정해 내려준 값이므로 UTC 필드로 그대로 읽어야 한다.
      // 2026-06-02 16:00:00(보정된 벽시계)을 나타내는 epoch.
      const t = Date.UTC(2026, 5, 2, 16, 0, 0) / 1000;
      expect(formatCandleTime(t)).toBe("06.02 16:00");
    });

    test("분봉 형식: 유효한 MM.DD HH:mm 패턴", () => {
      const formatted = formatCandleTime(1717375199);
      expect(formatted).toMatch(/^\d{2}\.\d{2} \d{2}:\d{2}$/);
    });
  });

  describe("buildMarkerLabel: 라벨 문자열 생성", () => {
    test("최고가 라벨: 가격(콤마), 날짜, +부호 + %", () => {
      const label = buildMarkerLabel({
        price: 21100,
        time: "2026-05-04",
        currentClose: 12795,
      });
      // (21100 - 12795) / 12795 * 100 = +64.91%
      expect(label).toContain("21,100");
      expect(label).toContain("(26.05.04)");
      expect(label).toMatch(/\+\d+\.\d{2}%$/);
    });

    test("최저가 라벨: 가격(콤마), 날짜, -부호 + %", () => {
      const label = buildMarkerLabel({
        price: 10900,
        time: "2026-06-02",
        currentClose: 11550,
      });
      // (10900 - 11550) / 11550 * 100 = -5.63%
      expect(label).toContain("10,900");
      expect(label).toContain("(26.06.02)");
      expect(label).toMatch(/-\d+\.\d{2}%$/);
    });

    test("현재가와 동일가: 0% (부호 없음)", () => {
      const label = buildMarkerLabel({
        price: 15000,
        time: "2026-06-01",
        currentClose: 15000,
      });
      expect(label).toContain("15,000");
      expect(label).toContain("(26.06.01)");
      expect(label).toContain("0.00%");
    });

    test("분봉 시간 포함 라벨", () => {
      const label = buildMarkerLabel({
        price: 15000,
        time: 1717384200,
        currentClose: 15000,
      });
      expect(label).toContain("15,000");
      expect(label).toMatch(/\d{2}\.\d{2} \d{2}:\d{2}/);
      expect(label).toContain("0.00%");
    });

    test("% 항상 소수 2자리", () => {
      const label1 = buildMarkerLabel({
        price: 10001,
        time: "2026-06-01",
        currentClose: 10000,
      });
      // (10001 - 10000) / 10000 * 100 = +0.01%
      expect(label1).toMatch(/\+0\.\d{2}%$/);

      const label2 = buildMarkerLabel({
        price: 10000,
        time: "2026-06-01",
        currentClose: 10100,
      });
      // (10000 - 10100) / 10100 * 100 = -0.99%
      expect(label2).toMatch(/-0\.\d{2}%$/);
    });
  });

  describe("buildExtremaMarkers: 최고/최저 마커 추출", () => {
    const testCandles: Candle[] = [
      {
        time: "2026-05-01",
        open: 12000,
        high: 13000,
        low: 11500,
        close: 12500,
        volume: 100000,
      },
      {
        time: "2026-05-02",
        open: 12500,
        high: 14000,
        low: 12000,
        close: 13500,
        volume: 120000,
      },
      {
        time: "2026-05-04",
        open: 13500,
        high: 21100, // ← 최고가
        low: 13000,
        close: 20000,
        volume: 150000,
      },
      {
        time: "2026-05-05",
        open: 20000,
        high: 20500,
        low: 11000,
        close: 15000,
        volume: 110000,
      },
      {
        time: "2026-06-02",
        open: 12000,
        high: 12500,
        low: 10900, // ← 최저가
        close: 11550,
        volume: 130000,
      },
      {
        time: "2026-06-03",
        open: 11550,
        high: 12000,
        low: 11400,
        close: 11550,
        volume: 95000,
      },
    ];

    test("최고가/최저가 각각 1개 마커", () => {
      const markers = buildExtremaMarkers(testCandles, UP, DOWN);
      expect(markers).toHaveLength(2);
    });

    test("최고가 마커: position aboveBar, shape arrowDown, color UP", () => {
      const markers = buildExtremaMarkers(testCandles, UP, DOWN);
      const highMarker = markers.find((m) => m.position === "aboveBar");
      expect(highMarker).toBeDefined();
      expect(highMarker?.shape).toBe("arrowDown");
      expect(highMarker?.color).toBe(UP);
      expect(highMarker?.text).toContain("21,100");
      expect(highMarker?.time).toBe("2026-05-04");
    });

    test("최저가 마커: position belowBar, shape arrowUp, color DOWN", () => {
      const markers = buildExtremaMarkers(testCandles, UP, DOWN);
      const lowMarker = markers.find((m) => m.position === "belowBar");
      expect(lowMarker).toBeDefined();
      expect(lowMarker?.shape).toBe("arrowUp");
      expect(lowMarker?.color).toBe(DOWN);
      expect(lowMarker?.text).toContain("10,900");
      expect(lowMarker?.time).toBe("2026-06-02");
    });

    test("현재가(마지막 close)는 11550이어야 함", () => {
      const markers = buildExtremaMarkers(testCandles, UP, DOWN);
      // 최고가 마커: (21100 - 11550) / 11550 * 100 = +82.68%
      const highMarker = markers.find((m) => m.position === "aboveBar");
      expect(highMarker?.text).toContain("+82.68%");

      // 최저가 마커: (10900 - 11550) / 11550 * 100 = -5.63%
      const lowMarker = markers.find((m) => m.position === "belowBar");
      expect(lowMarker?.text).toContain("-5.63%");
    });

    test("캔들 1개일 때 최고/최저가 동일하면 2개 마커(위아래 모두)", () => {
      const singleCandle: Candle[] = [
        {
          time: "2026-06-03",
          open: 12000,
          high: 15000,
          low: 15000, // high === low
          close: 15000,
          volume: 100000,
        },
      ];
      const markers = buildExtremaMarkers(singleCandle, UP, DOWN);
      expect(markers.length).toBeGreaterThanOrEqual(1);
      // 최소 1개는 있어야 함 (극값이 1개이므로)
    });

    test("캔들 배열이 비어있으면 마커 없음", () => {
      const markers = buildExtremaMarkers([], UP, DOWN);
      expect(markers).toHaveLength(0);
    });

    test("캔들 배열이 null/undefined면 마커 없음", () => {
      expect(buildExtremaMarkers(null as any, UP, DOWN)).toHaveLength(0);
      expect(buildExtremaMarkers(undefined as any, UP, DOWN)).toHaveLength(0);
    });

    test("분봉 시간(number UNIX 초) 마커도 정상 생성", () => {
      const minuteCandles: Candle[] = [
        {
          time: 1717320000, // 2026-06-02 16:00:00 KST
          open: 11000,
          high: 11500,
          low: 10800,
          close: 11200,
          volume: 5000,
        },
        {
          time: 1717323600, // 2026-06-02 17:00:00 KST
          open: 11200,
          high: 12000, // ← 최고가
          low: 11100,
          close: 11800,
          volume: 6000,
        },
        {
          time: 1717327200, // 2026-06-02 18:00:00 KST
          open: 11800,
          high: 11900,
          low: 10700, // ← 최저가
          close: 10900,
          volume: 5500,
        },
      ];
      const markers = buildExtremaMarkers(minuteCandles, UP, DOWN);
      expect(markers).toHaveLength(2);

      const highMarker = markers.find((m) => m.position === "aboveBar");
      expect(highMarker?.text).toMatch(/\d{2}\.\d{2} \d{2}:\d{2}/); // MM.DD HH:mm
      expect(highMarker?.text).toContain("12,000");
    });

    test("현재가가 최고가/최저가보다 사이에 있으면 +/- 부호 정확", () => {
      const candles: Candle[] = [
        { time: "2026-01-01", open: 100, high: 200, low: 50, close: 100, volume: 1 },
        { time: "2026-01-02", open: 100, high: 150, low: 75, close: 150, volume: 1 }, // 최고가=200
        { time: "2026-01-03", open: 150, high: 160, low: 40, close: 100, volume: 1 }, // 최저가=40, 현재가=100
      ];
      const markers = buildExtremaMarkers(candles, UP, DOWN);
      // 최고가=200, 현재가=100 → (200-100)/100 = +100.00%
      // 최저가=40, 현재가=100 → (40-100)/100 = -60.00%
      const highMarker = markers.find((m) => m.position === "aboveBar");
      const lowMarker = markers.find((m) => m.position === "belowBar");
      expect(highMarker?.text).toContain("+100.00%");
      expect(lowMarker?.text).toContain("-60.00%");
    });
  });

  describe("findExtrema: 극점 좌표/라벨", () => {
    test("최고가/최저가 지점의 time·price·label·kind 반환", () => {
      const candles: Candle[] = [
        { time: "2026-01-01", open: 100, high: 200, low: 50, close: 100, volume: 1 },
        { time: "2026-01-02", open: 100, high: 150, low: 75, close: 100, volume: 1 },
        { time: "2026-01-03", open: 150, high: 160, low: 40, close: 100, volume: 1 },
      ];
      const ex = findExtrema(candles);
      expect(ex).not.toBeNull();
      expect(ex!.high).toMatchObject({ kind: "high", time: "2026-01-01", price: 200 });
      expect(ex!.high.label).toContain("+100.00%");
      expect(ex!.low).toMatchObject({ kind: "low", time: "2026-01-03", price: 40 });
      expect(ex!.low!.label).toContain("-60.00%");
    });

    test("캔들이 비면 null", () => {
      expect(findExtrema([])).toBeNull();
      expect(findExtrema(undefined)).toBeNull();
    });

    test("최고가와 최저가가 같은 봉이면 low는 null", () => {
      const candles: Candle[] = [
        { time: "2026-01-01", open: 100, high: 300, low: 10, close: 100, volume: 1 },
      ];
      const ex = findExtrema(candles);
      expect(ex!.high.price).toBe(300);
      expect(ex!.low).toBeNull();
    });
  });
});
