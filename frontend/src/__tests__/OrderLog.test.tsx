import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { OrderLog } from "../components/OrderLog";
import type { Order } from "../types";

const sample: Order[] = [
  {
    id: 1,
    symbol: "005930",
    name: "삼성전자",
    side: "BUY",
    qty: 10,
    price: 70000,
    mode: "paper",
    status: "filled",
    kis_order_no: "12345678",
    created_at: "2026-06-03 09:05:00",
  },
];

describe("OrderLog", () => {
  test("주문이 없으면 안내 문구", () => {
    render(<OrderLog orders={[]} />);
    expect(screen.getByText(/주문 내역이 없습니다/)).toBeInTheDocument();
  });

  test("주문 행을 매수/매도로 표시", () => {
    render(<OrderLog orders={sample} />);
    expect(screen.getByText("005930")).toBeInTheDocument();
    expect(screen.getByText("매수")).toBeInTheDocument();
  });

  test("날짜+시각을 MM-DD HH:MM:SS 형태로 표시", () => {
    render(<OrderLog orders={sample} />);
    expect(screen.getByText("06-03 09:05:00")).toBeInTheDocument();
  });

  test("서로 다른 날짜의 주문들도 각각 날짜를 표시", () => {
    const multiday: Order[] = [
      {
        id: 1,
        symbol: "005930",
        name: "삼성전자",
        side: "BUY",
        qty: 10,
        price: 70000,
        mode: "paper",
        status: "filled",
        kis_order_no: "12345678",
        created_at: "2026-06-03 09:05:00",
      },
      {
        id: 2,
        symbol: "000660",
        name: "SK하이닉스",
        side: "SELL",
        qty: 5,
        price: 80000,
        mode: "paper",
        status: "filled",
        kis_order_no: "12345679",
        created_at: "2026-06-04 14:30:15",
      },
    ];
    render(<OrderLog orders={multiday} />);
    expect(screen.getByText("06-03 09:05:00")).toBeInTheDocument();
    expect(screen.getByText("06-04 14:30:15")).toBeInTheDocument();
  });

  test("created_at이 null이면 '-' 표시", () => {
    const nullDateOrder: Order[] = [
      {
        id: 1,
        symbol: "005930",
        name: "삼성전자",
        side: "BUY",
        qty: 10,
        price: 70000,
        mode: "paper",
        status: "filled",
        kis_order_no: "12345678",
        created_at: "",
      },
    ];
    render(<OrderLog orders={nullDateOrder} />);
    expect(screen.getByText("-")).toBeInTheDocument();
  });

  test("주문 상태를 한글로 표시", () => {
    render(<OrderLog orders={sample} />);
    expect(screen.getByText("체결")).toBeInTheDocument();
  });
});
