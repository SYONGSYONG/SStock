import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";
import { BotControl } from "../components/BotControl";

describe("BotControl", () => {
  test("모의투자는 즉시 시작(confirmLive=false)", () => {
    const onStart = vi.fn();
    render(<BotControl running={false} mode="paper" onStart={onStart} onStop={() => {}} />);
    fireEvent.click(screen.getByText("봇 시작"));
    expect(onStart).toHaveBeenCalledWith(false);
  });

  test("실전투자는 확인 후 시작(confirmLive=true) + 경고 문구", () => {
    const onStart = vi.fn();
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    render(<BotControl running={false} mode="live" onStart={onStart} onStop={() => {}} />);
    // 경고 문구 표시
    expect(screen.getByText(/실제 주문이 체결됩니다/)).toBeInTheDocument();
    // 실전 시작 시 확인 모달 → 승인하면 confirmLive=true로 호출
    fireEvent.click(screen.getByText("봇 시작 (실전)"));
    expect(confirmSpy).toHaveBeenCalled();
    expect(onStart).toHaveBeenCalledWith(true);
    confirmSpy.mockRestore();
  });

  test("실전 시작 확인을 취소하면 시작하지 않는다", () => {
    const onStart = vi.fn();
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);
    render(<BotControl running={false} mode="live" onStart={onStart} onStop={() => {}} />);
    fireEvent.click(screen.getByText("봇 시작 (실전)"));
    expect(confirmSpy).toHaveBeenCalled();
    expect(onStart).not.toHaveBeenCalled();
    confirmSpy.mockRestore();
  });

  test("실행 중에는 정지 버튼", () => {
    const onStop = vi.fn();
    render(<BotControl running mode="paper" onStart={() => {}} onStop={onStop} />);
    fireEvent.click(screen.getByText("봇 정지"));
    expect(onStop).toHaveBeenCalled();
  });

  test("compact 모드: 라벨 + 시작 버튼(모의)", () => {
    const onStart = vi.fn();
    render(<BotControl compact running={false} mode="paper" onStart={onStart} onStop={() => {}} />);
    expect(screen.getByText("자동매매 봇")).toBeInTheDocument();
    fireEvent.click(screen.getByText("시작"));
    expect(onStart).toHaveBeenCalledWith(false);
  });
});
