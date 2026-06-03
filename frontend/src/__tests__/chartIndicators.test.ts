import { describe, expect, test } from "vitest";
import {
  MA_CONFIGS,
  buildMaLineData,
  buildTooltipData,
  pctChange,
  rollingSma,
} from "../lib/chartIndicators";
import type { Candle } from "../types";

describe("차트지표: 이동평균 + tooltip", () => {
  describe("rollingSma: 단순이동평균(백엔드 rolling_sma와 동일)", () => {
    test("워밍업 구간은 null, period-1 인덱스부터 값 존재", () => {
      const out = rollingSma([1, 2, 3, 4, 5], 3);
      // i=0,1 → null, i=2 → (1+2+3)/3=2, i=3 → (2+3+4)/3=3, i=4 → (3+4+5)/3=4
      expect(out).toEqual([null, null, 2, 3, 4]);
    });

    test("period=1이면 입력과 동일", () => {
      expect(rollingSma([10, 20, 30], 1)).toEqual([10, 20, 30]);
    });

    test("데이터가 period보다 적으면 전부 null", () => {
      expect(rollingSma([1, 2], 5)).toEqual([null, null]);
    });

    test("빈 배열은 빈 배열", () => {
      expect(rollingSma([], 5)).toEqual([]);
    });

    test("롤링 합산이 일괄 평균과 일치(부동소수 누적 안전)", () => {
      const values = [100, 105, 102, 108, 110, 107, 109];
      const period = 4;
      const out = rollingSma(values, period);
      for (let i = period - 1; i < values.length; i++) {
        const slice = values.slice(i - period + 1, i + 1);
        const expected = slice.reduce((a, b) => a + b, 0) / period;
        expect(out[i]).toBeCloseTo(expected, 10);
      }
    });
  });

  describe("pctChange: 직전 값 대비 변화율(%)", () => {
    test("상승은 양수", () => {
      expect(pctChange(110, 100)).toBeCloseTo(10, 10);
    });

    test("하락은 음수", () => {
      expect(pctChange(90, 100)).toBeCloseTo(-10, 10);
    });

    test("prev가 null이면 null", () => {
      expect(pctChange(100, null)).toBeNull();
    });

    test("prev가 0이면 null(0으로 나누기 방지)", () => {
      expect(pctChange(100, 0)).toBeNull();
    });
  });

  describe("buildMaLineData: 이평선 라인 데이터", () => {
    const candles: Candle[] = Array.from({ length: 6 }, (_, i) => ({
      time: `2026-06-0${i + 1}`,
      open: 100,
      high: 110,
      low: 90,
      close: 100 + i * 10, // 100,110,120,130,140,150
      volume: 1000,
    }));

    test("워밍업(null) 구간은 제외하고 값 있는 점만 반환", () => {
      const line = buildMaLineData(candles, 3);
      // close=[100,110,120,130,140,150], sma3는 i>=2부터
      // i2=(100+110+120)/3=110, i3=120, i4=130, i5=140
      expect(line).toHaveLength(4);
      expect(line[0]).toEqual({ time: "2026-06-03", value: 110 });
      expect(line[3]).toEqual({ time: "2026-06-06", value: 140 });
    });

    test("데이터 부족 시 빈 배열", () => {
      expect(buildMaLineData(candles, 120)).toEqual([]);
    });
  });

  describe("MA_CONFIGS: 이평 구성", () => {
    test("5/20/60/120 4개 + 색상 지정", () => {
      expect(MA_CONFIGS.map((c) => c.period)).toEqual([5, 20, 60, 120]);
      for (const c of MA_CONFIGS) {
        expect(c.color).toMatch(/^#[0-9a-f]{6}$/i);
      }
    });
  });

  describe("buildTooltipData: 시점 정보 박스", () => {
    const candles: Candle[] = [
      { time: "2026-05-28", open: 13000, high: 13500, low: 12800, close: 13000, volume: 500000 },
      { time: "2026-05-29", open: 13245, high: 13245, low: 9650, close: 10954, volume: 4165000 },
    ];

    test("첫 봉은 등락 없음(직전 봉 없음)", () => {
      const data = buildTooltipData(candles, 0)!;
      const close = data.rows.find((r) => r.label === "종가");
      expect(close?.value).toBe("13,000");
      expect(close?.change).toBeNull();
    });

    test("둘째 봉: 시·고·저·종 직전봉 종가(13,000) 대비 등락", () => {
      const data = buildTooltipData(candles, 1)!;
      const get = (label: string) => data.rows.find((r) => r.label === label);

      // 종가 10954 vs prevClose 13000 → (10954-13000)/13000 = -15.74%
      const close = get("종가");
      expect(close?.value).toBe("10,954");
      expect(close?.change).toContain("-15.7");
      expect(close?.dir).toBe("down");

      // 고가 13245 vs 13000 → +1.88% (상승)
      const high = get("고");
      expect(high?.dir).toBe("up");
      expect(high?.change?.startsWith("+")).toBe(true);

      // 저가 9650 → 하락
      expect(get("저")?.dir).toBe("down");
    });

    test("거래량 행: 직전 봉 대비 증감률", () => {
      const data = buildTooltipData(candles, 1)!;
      const vol = data.rows.find((r) => r.label === "거래량");
      expect(vol?.value).toBe("4,165,000");
      // (4165000-500000)/500000 = +733.0%
      expect(vol?.change).toContain("+733");
      expect(vol?.dir).toBe("up");
    });

    test("날짜 행 포맷(일봉 YY.MM.DD)", () => {
      const data = buildTooltipData(candles, 1)!;
      expect(data.time).toBe("26.05.29");
    });

    test("이평 행 포함: 데이터 충분하면 값, 부족하면 '-'", () => {
      // 5봉짜리 → ma5는 마지막 봉에서만 값
      const five: Candle[] = Array.from({ length: 5 }, (_, i) => ({
        time: `2026-06-0${i + 1}`,
        open: 100,
        high: 110,
        low: 90,
        close: 100 + i * 10,
        volume: 1000,
      }));
      const data = buildTooltipData(five, 4)!;
      const ma5 = data.rows.find((r) => r.label === "이평5");
      // close=[100,110,120,130,140] → ma5=(100+...+140)/5=120
      expect(ma5?.value).toBe("120");
      // ma20은 데이터 부족 → "-"
      const ma20 = data.rows.find((r) => r.label === "이평20");
      expect(ma20?.value).toBe("-");
      expect(ma20?.change).toBeNull();
    });

    test("범위를 벗어난 인덱스는 null 반환", () => {
      expect(buildTooltipData(candles, 99)).toBeNull();
      expect(buildTooltipData([], 0)).toBeNull();
    });

    test("분봉 time(UNIX 초)도 시각 포맷", () => {
      const minute: Candle[] = [
        { time: 1717320000, open: 11000, high: 11500, low: 10800, close: 11200, volume: 5000 },
        { time: 1717323600, open: 11200, high: 12000, low: 11100, close: 11800, volume: 6000 },
      ];
      const data = buildTooltipData(minute, 1);
      expect(data?.time).toMatch(/^\d{2}\.\d{2} \d{2}:\d{2}$/);
    });
  });
});
