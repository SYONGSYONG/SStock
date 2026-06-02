import { fireEvent, render, screen } from "@testing-library/react";
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
      symbol: "000660", name: "SK하이닉스", market: "KOSPI",
      score: 87.4, momentum: 92, fundamental: 80, supply: 88,
      price: 180000, change_rate: 3.2, roe: 61.16,
    },
  ],
};

function setup() {
  const fetchThemes = vi.fn(async () => THEMES);
  const fetchRecommend = vi.fn(async () => RESULT);
  const onAdd = vi.fn();
  render(
    <RecommendPage fetchThemes={fetchThemes} fetchRecommend={fetchRecommend} onAdd={onAdd} />,
  );
  return { fetchThemes, fetchRecommend, onAdd };
}

describe("RecommendPage", () => {
  test("마운트 시 테마 목록을 표시한다", async () => {
    setup();
    expect(await screen.findByText("반도체")).toBeInTheDocument();
    expect(screen.getByText("자동차")).toBeInTheDocument();
  });

  test("테마를 선택하면 추천 종목을 조회해 표시한다", async () => {
    const { fetchRecommend } = setup();
    fireEvent.click(await screen.findByText("반도체"));
    expect(await screen.findByText("SK하이닉스")).toBeInTheDocument();
    expect(fetchRecommend).toHaveBeenCalledWith("semiconductor");
  });

  test("종합점수와 세부 축 점수를 표시한다", async () => {
    setup();
    fireEvent.click(await screen.findByText("반도체"));
    await screen.findByText("SK하이닉스");
    expect(screen.getByText("87.4")).toBeInTheDocument();
    expect(screen.getByText("모멘텀")).toBeInTheDocument();
    expect(screen.getByText("펀더멘털")).toBeInTheDocument();
    expect(screen.getByText("수급")).toBeInTheDocument();
  });

  test("관심종목 추가 버튼이 onAdd를 호출한다", async () => {
    const { onAdd } = setup();
    fireEvent.click(await screen.findByText("반도체"));
    await screen.findByText("SK하이닉스");
    fireEvent.click(screen.getByRole("button", { name: /관심종목 추가/ }));
    expect(onAdd).toHaveBeenCalledWith("000660", "SK하이닉스");
  });

  test("투자 유의 면책 문구를 표시한다", async () => {
    setup();
    await screen.findByText("반도체");
    expect(screen.getByText(/참고용/)).toBeInTheDocument();
  });
});
