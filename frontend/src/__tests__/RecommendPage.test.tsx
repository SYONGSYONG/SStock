import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";
import { RecommendPage } from "../components/RecommendPage";
import type { RecommendResult, ThemeInfo } from "../types";

const THEMES: ThemeInfo[] = [
  { slug: "semiconductor", label: "반도체", count: 7 },
  { slug: "auto", label: "자동차", count: 17 },
];

const RESULT: RecommendResult = {
  theme: "semiconductor",
  base_date: "20260331",
  items: [
    {
      symbol: "000660",
      name: "SK하이닉스",
      market: "KOSPI",
      score: 87.4,
      momentum: 92,
      fundamental: 80,
      supply: 88,
      price: 180000,
      change_rate: 3.2,
      roe: 61.16,
    },
  ],
};

function setup() {
  const fetchThemes = vi.fn(async () => THEMES);
  const fetchRecommend = vi.fn(async () => RESULT);
  const onAdd = vi.fn();
  const onSelect = vi.fn();
  render(
    <RecommendPage
      fetchThemes={fetchThemes}
      fetchRecommend={fetchRecommend}
      onAdd={onAdd}
      onSelect={onSelect}
    />,
  );
  return { fetchThemes, fetchRecommend, onAdd, onSelect };
}

describe("RecommendPage", () => {
  test("테마 목록을 보여준다", async () => {
    setup();
    expect(await screen.findByText("반도체")).toBeInTheDocument();
    expect(screen.getByText("자동차")).toBeInTheDocument();
  });

  test("테마를 선택하면 추천 종목을 조회한다", async () => {
    const { fetchRecommend } = setup();
    fireEvent.click(await screen.findByText("반도체"));
    expect(await screen.findByText("SK하이닉스")).toBeInTheDocument();
    expect(fetchRecommend).toHaveBeenCalledWith(
      "semiconductor",
      undefined,
      expect.any(AbortSignal),
    );
  });

  test("추천 카드에 현재가와 등락률을 보여준다", async () => {
    setup();
    fireEvent.click(await screen.findByText("반도체"));
    await screen.findByText("SK하이닉스");
    expect(screen.getByText("180,000")).toBeInTheDocument();
    expect(screen.getByText("+3.20%")).toBeInTheDocument();
  });

  test("카드를 클릭하면 onSelect(symbol, name)를 호출한다", async () => {
    const { onSelect } = setup();
    fireEvent.click(await screen.findByText("반도체"));
    await screen.findByText("SK하이닉스");
    fireEvent.click(screen.getByRole("button", { name: /SK하이닉스 차트 보기/ }));
    expect(onSelect).toHaveBeenCalledWith("000660", "SK하이닉스");
  });

  test("관심종목 추가 버튼은 onAdd만 호출한다", async () => {
    const { onAdd, onSelect } = setup();
    fireEvent.click(await screen.findByText("반도체"));
    await screen.findByText("SK하이닉스");
    fireEvent.click(screen.getByRole("button", { name: /관심종목 추가/ }));
    expect(onAdd).toHaveBeenCalledWith("000660", "SK하이닉스");
    expect(onSelect).not.toHaveBeenCalled();
  });

  test("로딩 중 다른 분야를 누르면 늦게 온 이전 응답이 새 분야를 덮어쓰지 않는다", async () => {
    const AUTO: RecommendResult = {
      theme: "auto",
      base_date: "20260331",
      items: [
        {
          symbol: "005380",
          name: "현대차",
          market: "KOSPI",
          score: 70,
          momentum: 70,
          fundamental: 70,
          supply: 70,
          price: 250000,
          change_rate: 1.0,
          roe: 10,
        },
      ],
    };
    const fetchThemes = vi.fn(async () => THEMES);
    // 반도체는 느리게(120ms), 자동차는 빠르게(20ms) 응답 → 완료 순서가 뒤집힘
    const fetchRecommend = vi.fn(
      (theme: string) =>
        new Promise<RecommendResult>((resolve) => {
          if (theme === "semiconductor") setTimeout(() => resolve(RESULT), 120);
          else setTimeout(() => resolve(AUTO), 20);
        }),
    );
    render(
      <RecommendPage
        fetchThemes={fetchThemes}
        fetchRecommend={fetchRecommend}
        onAdd={vi.fn()}
        onSelect={vi.fn()}
      />,
    );

    fireEvent.click(await screen.findByText("반도체")); // 느린 요청 시작
    fireEvent.click(screen.getByText("자동차")); // 빠른 요청 시작(이전 요청 abort)

    // 최신 선택(자동차) 결과가 표시되어야 한다
    expect(await screen.findByText("현대차")).toBeInTheDocument();

    // 늦게 도착하는 반도체 응답(120ms)이 화면을 덮어쓰면 안 된다
    await waitFor(() => expect(fetchRecommend).toHaveBeenCalledTimes(2));
    await new Promise((r) => setTimeout(r, 200));
    expect(screen.queryByText("SK하이닉스")).not.toBeInTheDocument();
    expect(screen.getByText("현대차")).toBeInTheDocument();
  });
});
