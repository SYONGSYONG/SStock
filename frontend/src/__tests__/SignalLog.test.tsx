import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { SignalLog } from "../components/SignalLog";
import type { Signal } from "../types";

const sample: Signal[] = [
  {
    id: 1,
    symbol: "005930",
    strategy: "ma_cross",
    side: "BUY",
    price: 70000,
    reason: "골든크로스",
    created_at: "2026-06-03 09:05:00",
  },
];

describe("SignalLog", () => {
  test("신호가 없으면 안내 문구", () => {
    render(<SignalLog signals={[]} />);
    expect(screen.getByText(/아직 신호가 없습니다/)).toBeInTheDocument();
  });

  test("신호 행을 매수/매도로 표시", () => {
    render(<SignalLog signals={sample} />);
    expect(screen.getByText("005930")).toBeInTheDocument();
    expect(screen.getByText("매수")).toBeInTheDocument();
    expect(screen.getByText("골든크로스")).toBeInTheDocument();
  });

  test("전략은 원시 식별자가 아니라 한글 라벨로 표시", () => {
    render(<SignalLog signals={sample} />);
    expect(screen.getByText("이동평균 크로스")).toBeInTheDocument();
    expect(screen.queryByText("ma_cross")).toBeNull();
  });

  test("OFF 전략의 관찰 신호에는 '관찰' 배지를 표시", () => {
    render(<SignalLog signals={[{ ...sample[0], observe: 1 }]} />);
    expect(screen.getByText("관찰")).toBeInTheDocument();
  });

  test("일반 신호에는 관찰 배지가 없음", () => {
    render(<SignalLog signals={sample} />);
    expect(screen.queryByText("관찰")).toBeNull();
  });

  test("날짜+시각을 MM-DD HH:MM:SS 형태로 표시", () => {
    render(<SignalLog signals={sample} />);
    expect(screen.getByText("06-03 09:05:00")).toBeInTheDocument();
  });

  test("서로 다른 날짜의 신호들도 각각 날짜를 표시", () => {
    const multiday: Signal[] = [
      {
        id: 1,
        symbol: "005930",
        strategy: "ma_cross",
        side: "BUY",
        price: 70000,
        reason: "골든크로스",
        created_at: "2026-06-03 09:05:00",
      },
      {
        id: 2,
        symbol: "000660",
        strategy: "rsi_ma",
        side: "SELL",
        price: 80000,
        reason: "RSI 과매도",
        created_at: "2026-06-04 14:30:15",
      },
    ];
    render(<SignalLog signals={multiday} />);
    expect(screen.getByText("06-03 09:05:00")).toBeInTheDocument();
    expect(screen.getByText("06-04 14:30:15")).toBeInTheDocument();
  });

  test("created_at이 null이면 '-' 표시", () => {
    const nullDateSignal: Signal[] = [
      {
        id: 1,
        symbol: "005930",
        strategy: "ma_cross",
        side: "BUY",
        price: 70000,
        reason: "골든크로스",
        created_at: "",
      },
    ];
    render(<SignalLog signals={nullDateSignal} />);
    expect(screen.getByText("-")).toBeInTheDocument();
  });
});
