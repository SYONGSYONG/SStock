import { describe, expect, test } from "vitest";
import { direction, fmt, fmtRate, fmtDatetime } from "../lib/format";

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

  test("일시는 MM-DD HH:MM:SS 형태로 포맷", () => {
    expect(fmtDatetime("2026-06-03 09:05:00")).toBe("06-03 09:05:00");
    expect(fmtDatetime("2026-12-25 23:59:59")).toBe("12-25 23:59:59");
  });

  test("일시가 null/undefined면 대시", () => {
    expect(fmtDatetime(null)).toBe("-");
    expect(fmtDatetime(undefined)).toBe("-");
  });

  test("일시가 빈 문자열이면 대시", () => {
    expect(fmtDatetime("")).toBe("-");
  });
});
