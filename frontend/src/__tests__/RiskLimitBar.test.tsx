import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";
import { RiskLimitBar } from "../components/RiskLimitBar";
import type { RiskLimit } from "../types";

const DATA: RiskLimit = {
  mode: "paper",
  max_orders: 100,
  max_amount: 1_000_000,
  max_daily_loss: 0,
  order_count: 20,
  order_amount: 300_000,
  realized_pnl: 0,
};

describe("RiskLimitBar", () => {
  test("사용량과 한도를 표시한다", () => {
    render(<RiskLimitBar data={DATA} mode="paper" onUpdate={() => {}} />);
    // 주문 횟수 20 / 100건, 금액 300,000 / 1,000,000원
    expect(screen.getByText("20")).toBeInTheDocument();
    expect(screen.getByText(/100건/)).toBeInTheDocument();
    expect(screen.getByText("300,000")).toBeInTheDocument();
    expect(screen.getByText(/1,000,000원/)).toBeInTheDocument();
  });

  test("데이터 로딩 전에는 안내 + 변경 버튼 비활성", () => {
    render(<RiskLimitBar data={null} mode="paper" onUpdate={() => {}} />);
    expect(screen.getByText(/불러오는 중/)).toBeInTheDocument();
    expect(screen.getByText("제한 변경")).toBeDisabled();
  });

  test("제한 변경은 재확인 후 새 값으로 onUpdate 호출", () => {
    const onUpdate = vi.fn();
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    render(<RiskLimitBar data={DATA} mode="paper" onUpdate={onUpdate} />);

    fireEvent.click(screen.getByText("제한 변경"));
    fireEvent.change(screen.getByLabelText(/일일 주문 횟수/), { target: { value: "50" } });
    fireEvent.change(screen.getByLabelText(/일일 주문 금액/), { target: { value: "5000000" } });
    fireEvent.click(screen.getByText("저장"));

    expect(confirmSpy).toHaveBeenCalled();
    expect(onUpdate).toHaveBeenCalledWith(50, 5_000_000, 0);
    confirmSpy.mockRestore();
  });

  test("재확인을 취소하면 onUpdate를 호출하지 않는다", () => {
    const onUpdate = vi.fn();
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);
    render(<RiskLimitBar data={DATA} mode="paper" onUpdate={onUpdate} />);

    fireEvent.click(screen.getByText("제한 변경"));
    fireEvent.click(screen.getByText("저장"));

    expect(confirmSpy).toHaveBeenCalled();
    expect(onUpdate).not.toHaveBeenCalled();
    confirmSpy.mockRestore();
  });

  test("1 미만 값은 검증 알림 후 차단", () => {
    const onUpdate = vi.fn();
    const alertSpy = vi.spyOn(window, "alert").mockImplementation(() => {});
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    render(<RiskLimitBar data={DATA} mode="paper" onUpdate={onUpdate} />);

    fireEvent.click(screen.getByText("제한 변경"));
    fireEvent.change(screen.getByLabelText(/일일 주문 횟수/), { target: { value: "0" } });
    fireEvent.click(screen.getByText("저장"));

    expect(alertSpy).toHaveBeenCalled();
    expect(onUpdate).not.toHaveBeenCalled();
    alertSpy.mockRestore();
    confirmSpy.mockRestore();
  });
});
