import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";
import { RecommendPage } from "../components/RecommendPage";
import type { RecommendCandidate, RecommendResult, ThemeInfo } from "../types";
import type { RecommendStreamHandlers } from "../api/client";

const THEMES: ThemeInfo[] = [
  { slug: "semiconductor", label: "반도체", count: 7 },
  { slug: "auto", label: "자동차", count: 17 },
];

const CANDIDATES: RecommendCandidate[] = [
  { symbol: "000660", name: "SK하이닉스", market: "KOSPI" },
  { symbol: "005930", name: "삼성전자", market: "KOSPI" },
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

function createMockSubscribeRecommend(
  delays: { candidates?: number; quotes?: number; result?: number } = {},
) {
  return vi.fn(
    (theme: string, _limit: number, handlers: RecommendStreamHandlers) => {
      // 비동기로 이벤트 발송
      (async () => {
        await new Promise((r) => setTimeout(r, delays.candidates ?? 0));
        handlers.onCandidates({
          theme,
          base_date: "20260331",
          candidates: CANDIDATES,
        });

        await new Promise((r) => setTimeout(r, delays.quotes ?? 10));
        // 각 후보에 대해 quote 발송
        handlers.onQuote({
          symbol: "000660",
          price: 180000,
          change_rate: 3.2,
          volume: 1000000,
        });

        await new Promise((r) => setTimeout(r, 10));
        handlers.onQuote({
          symbol: "005930",
          price: 70000,
          change_rate: 1.5,
          volume: 5000000,
        });

        await new Promise((r) => setTimeout(r, delays.result ?? 10));
        handlers.onResult(RESULT);
      })();

      // unsubscribe 함수 반환
      return vi.fn();
    },
  );
}

function setup(
  options: { subscribeRecommend?: ReturnType<typeof createMockSubscribeRecommend> } = {},
) {
  const fetchThemes = vi.fn(async () => THEMES);
  const subscribeRecommend = options.subscribeRecommend ?? createMockSubscribeRecommend();
  const onAdd = vi.fn();
  const onSelect = vi.fn();
  render(
    <RecommendPage
      fetchThemes={fetchThemes}
      subscribeRecommend={subscribeRecommend}
      onAdd={onAdd}
      onSelect={onSelect}
    />,
  );
  return { fetchThemes, subscribeRecommend, onAdd, onSelect };
}

describe("RecommendPage", () => {
  test("테마 목록을 보여준다", async () => {
    setup();
    expect(await screen.findByText("반도체")).toBeInTheDocument();
    expect(screen.getByText("자동차")).toBeInTheDocument();
  });

  test("테마를 선택하면 스트리밍으로 추천 종목을 조회한다", async () => {
    const { subscribeRecommend } = setup();
    fireEvent.click(await screen.findByText("반도체"));

    // result 이벤트가 오면 최종 카드가 나타남
    expect(await screen.findByText("SK하이닉스")).toBeInTheDocument();
    expect(subscribeRecommend).toHaveBeenCalledWith(
      "semiconductor",
      10,
      expect.any(Object),
    );
  });

  test("스켈레톤은 candidates 이벤트 후 바로 나타난다", async () => {
    const subscribeRecommend = createMockSubscribeRecommend({
      candidates: 0,
      quotes: 100,
      result: 200,
    });
    setup({ subscribeRecommend });

    fireEvent.click(await screen.findByText("반도체"));

    // candidates 이벤트 후 스켈레톤이 나타나야 함
    // 스켈레톤은 skeleton 클래스가 있고, candidates의 name들이 표시됨
    expect(await screen.findByText("SK하이닉스")).toBeInTheDocument();
  });

  test("quote 이벤트로 현재가가 채워진다", async () => {
    setup();
    fireEvent.click(await screen.findByText("반도체"));

    // quote 이벤트 후 가격이 나타남
    expect(await screen.findByText("180,000")).toBeInTheDocument();
    expect(screen.getByText("+3.20%")).toBeInTheDocument();
  });

  test("result 이벤트로 최종 카드와 점수가 나타난다", async () => {
    setup();
    fireEvent.click(await screen.findByText("반도체"));

    // 최종 카드의 점수가 표시되어야 함
    expect(await screen.findByText(/87\.4/)).toBeInTheDocument();
  });

  test("카드를 클릭하면 onSelect(symbol, name)를 호출한다", async () => {
    const { onSelect } = setup();
    fireEvent.click(await screen.findByText("반도체"));
    await screen.findByText("SK하이닉스");

    // 최종 카드 클릭
    const card = screen.getByRole("button", { name: /SK하이닉스 차트 보기/ });
    fireEvent.click(card);
    expect(onSelect).toHaveBeenCalledWith("000660", "SK하이닉스");
  });

  test("관심종목 추가 버튼은 onAdd만 호출한다", async () => {
    const { onAdd, onSelect } = setup();
    fireEvent.click(await screen.findByText("반도체"));
    await screen.findByText("SK하이닉스");

    const addBtn = screen.getAllByRole("button", { name: /관심종목 추가/ })[0];
    fireEvent.click(addBtn);
    expect(onAdd).toHaveBeenCalledWith("000660", "SK하이닉스");
    expect(onSelect).not.toHaveBeenCalled();
  });

  test("로딩 중 다른 분야를 누르면 stale 결과가 화면을 덮어쓰지 않는다", async () => {
    // 반도체는 느리게(150ms), 자동차는 빠르게(50ms) result 발송
    const semiconductorSubscribe = createMockSubscribeRecommend({
      result: 150,
    });
    const autoSubscribe = createMockSubscribeRecommend({
      candidates: 0,
      quotes: 10,
      result: 50,
    });

    const subscribeRecommend2 = vi.fn((theme: string, lim: number, handlers) => {
      if (theme === "semiconductor") {
        return semiconductorSubscribe(theme, lim, handlers);
      } else {
        return autoSubscribe(theme, lim, handlers);
      }
    });

    setup({ subscribeRecommend: subscribeRecommend2 });

    fireEvent.click(await screen.findByText("반도체")); // 느린 요청 시작
    await waitFor(() => expect(screen.getByText("SK하이닉스")).toBeInTheDocument()); // 스켈레톤 나타남

    fireEvent.click(screen.getByText("자동차")); // 빠른 요청 시작

    // 빠른 요청(자동차) result가 먼저 도착하고 표시되어야 함
    await waitFor(() =>
      expect(screen.queryByText("SK하이닉스")).not.toBeInTheDocument(),
    );
  });

  test("로딩 중 선택한 분야명과 진행률을 표시한다", async () => {
    const subscribeRecommend = createMockSubscribeRecommend({
      candidates: 10,
      quotes: 100,
      result: 200,
    });
    setup({ subscribeRecommend });

    fireEvent.click(await screen.findByText("반도체"));

    // candidates 이벤트 후 로딩 문구가 "0/2" 진행률로 표시됨
    expect(await screen.findByText(/반도체 불러오는 중\.\.\. \(0\/2\)/)).toBeInTheDocument();

    // quotes가 들어오면 진행률이 업데이트됨
    await waitFor(() =>
      expect(
        screen.getByText(/반도체 불러오는 중\.\.\. \([12]\/2\)/),
      ).toBeInTheDocument(),
    );
  });
});
