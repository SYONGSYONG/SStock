import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { ModeBanner } from "../components/ModeBanner";

describe("ModeBanner", () => {
  test("모의투자 모드 표시", () => {
    render(<ModeBanner mode="paper" botRunning={false} connected={false} />);
    expect(screen.getByText(/모의투자/)).toBeInTheDocument();
    expect(screen.getByText(/봇 ○ OFF/)).toBeInTheDocument();
  });

  test("실전투자 모드는 경고 표시 + live 클래스", () => {
    const { container } = render(<ModeBanner mode="live" botRunning connected />);
    expect(screen.getByText(/실전투자/)).toBeInTheDocument();
    expect(container.querySelector(".mode-banner.live")).not.toBeNull();
    expect(screen.getByText(/봇 ● ON/)).toBeInTheDocument();
    expect(screen.getByText(/실시간 연결됨/)).toBeInTheDocument();
  });
});
