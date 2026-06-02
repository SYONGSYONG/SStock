import { describe, expect, test } from "vitest";
import { direction, fmt, fmtRate } from "../lib/format";

describe("format 유틸", () => {
  test("숫자는 천단위 콤마, null은 대시", () => {
    expect(fmt(1234567)).toBe("1,234,567");
    expect(fmt(null)).toBe("-");
  });

  test("등락률은 부호와 % 포함", () => {
    expect(fmtRate(1.45)).toBe("+1.45%");
    expect(fmtRate(-2.3)).toBe("-2.30%");
    expect(fmtRate(null)).toBe("-");
  });

  test("방향: 상승 up, 하락 down, 보합 neutral", () => {
    expect(direction(100)).toBe("up");
    expect(direction(-100)).toBe("down");
    expect(direction(0)).toBe("neutral");
    expect(direction(null)).toBe("neutral");
  });
});
