import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";
import { ModeBanner } from "../components/ModeBanner";

describe("ModeBanner", () => {
  test("모의 모드: 토글 + 모의봇 상태 표시", () => {
    render(
      <ModeBanner
        viewMode="paper"
        onSwitchMode={() => {}}
        paperBotRunning={false}
        liveBotRunning={false}
        connected={false}
      />,
    );
    expect(screen.getByText("모의")).toBeInTheDocument();
    expect(screen.getByText(/모의 봇 ○/)).toBeInTheDocument();
    expect(screen.getByText(/실전 봇 ○/)).toBeInTheDocument();
  });

  test("실전 모드: 경고 + 토글 + 양쪽 봇 상태", () => {
    const { container } = render(
      <ModeBanner
        viewMode="live"
        onSwitchMode={() => {}}
        paperBotRunning={true}
        liveBotRunning={false}
        connected={true}
      />,
    );
    expect(screen.getByText(/실전투자 — 실제 주문/)).toBeInTheDocument();
    expect(container.querySelector(".mode-banner.live")).not.toBeNull();
    expect(screen.getByText(/모의 봇 ●/)).toBeInTheDocument();
    expect(screen.getByText(/실전 봇 ○/)).toBeInTheDocument();
    expect(screen.getByText(/실시간 연결됨/)).toBeInTheDocument();
  });

  test("모드 토글 클릭 시 onSwitchMode 호출", () => {
    const onSwitch = vi.fn();
    render(
      <ModeBanner
        viewMode="paper"
        onSwitchMode={onSwitch}
        paperBotRunning={false}
        liveBotRunning={false}
        connected={false}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "실전" }));
    expect(onSwitch).toHaveBeenCalledWith("live");
  });

  test("controls 슬롯(봇/시세 컨트롤)을 렌더한다", () => {
    render(
      <ModeBanner
        viewMode="paper"
        onSwitchMode={() => {}}
        paperBotRunning={false}
        liveBotRunning={false}
        connected={false}
        controls={<span>봇/시세 컨트롤</span>}
      />,
    );
    expect(screen.getByText("봇/시세 컨트롤")).toBeInTheDocument();
  });

  test("양쪽 봇 상태를 동시에 표시", () => {
    render(
      <ModeBanner
        viewMode="paper"
        onSwitchMode={() => {}}
        paperBotRunning={true}
        liveBotRunning={true}
        connected={true}
      />,
    );
    expect(screen.getByText(/모의 봇 ●/)).toBeInTheDocument();
    expect(screen.getByText(/실전 봇 ●/)).toBeInTheDocument();
  });
});
