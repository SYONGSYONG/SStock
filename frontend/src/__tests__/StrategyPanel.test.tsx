import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import { StrategyPanel } from "../components/StrategyPanel";
import { describeStrategy } from "../lib/strategy";
import type { Budget, StrategyConfig, WatchItem } from "../types";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("describeStrategy", () => {
  test("이동평균 크로스는 틱봉/단기/장기로 표기", () => {
    expect(describeStrategy("ma_cross", { short: 5, long: 20, bar_ticks: 50 })).toBe(
      "이동평균 크로스 · 50틱봉 · 단기 5 / 장기 20",
    );
  });

  test("RSI+MA는 틱봉/RSI/과매도/과매수/MA로 표기", () => {
    expect(
      describeStrategy("rsi_ma", { rsi_period: 14, low: 30, high: 70, ma_period: 50, bar_ticks: 50 }),
    ).toBe("RSI + MA · 50틱봉 · RSI 14 · 과매도 30 / 과매수 70 · MA 50");
  });
});

describe("StrategyPanel", () => {
  test("원시 JSON이 아니라 한글 라벨로 렌더링", () => {
    const configs: StrategyConfig[] = [
      { id: 1, symbol: "077360", strategy: "ma_cross", params: { short: 5, long: 20, bar_ticks: 50 }, enabled: true, max_qty: 10, max_amount: null },
    ];
    render(
      <StrategyPanel
        budgets={[]}
        configs={configs}
        onAdd={() => {}}
        onToggle={() => {}}
        onRemove={() => {}}
        onSetBudget={() => {}}
      />,
    );
    expect(screen.getByText("이동평균 크로스 · 50틱봉 · 단기 5 / 장기 20")).toBeInTheDocument();
    expect(screen.queryByText(/\{"short"/)).toBeNull();
  });

  test("종목코드 입력 시 옆에 종목명을 표시", () => {
    const items: WatchItem[] = [{ id: 1, symbol: "005930", name: "삼성전자", created_at: "" }];
    render(
      <StrategyPanel items={items} budgets={[]} configs={[]} onAdd={() => {}} onToggle={() => {}} onRemove={() => {}} onSetBudget={() => {}} />,
    );
    fireEvent.change(screen.getByLabelText("전략 종목코드"), { target: { value: "005930" } });
    expect(screen.getByText("삼성전자")).toBeInTheDocument();
  });

  test("presetSymbol(n 변화)로 종목코드가 채워진다(시세 클릭 복사)", () => {
    const common = { budgets: [], configs: [], onAdd: () => {}, onToggle: () => {}, onRemove: () => {}, onSetBudget: () => {} };
    const { rerender } = render(<StrategyPanel presetSymbol={{ value: "", n: 0 }} {...common} />);
    expect((screen.getByLabelText("전략 종목코드") as HTMLInputElement).value).toBe("");
    rerender(<StrategyPanel presetSymbol={{ value: "000660", n: 1 }} {...common} />);
    expect((screen.getByLabelText("전략 종목코드") as HTMLInputElement).value).toBe("000660");
  });

  test("전략 목록에 종목번호와 종목명을 함께 표기", () => {
    const configs: StrategyConfig[] = [
      { id: 1, symbol: "005930", name: "삼성전자", strategy: "ma_cross", params: { short: 5, long: 20 }, enabled: true, max_qty: null, max_amount: null },
    ];
    render(
      <StrategyPanel budgets={[]} configs={configs} onAdd={() => {}} onToggle={() => {}} onRemove={() => {}} onSetBudget={() => {}} />,
    );
    const item = screen.getByText("005930").closest("li") as HTMLElement;
    expect(within(item).getByText("005930")).toBeInTheDocument();
    expect(within(item).getByText("삼성전자")).toBeInTheDocument();
  });

  test("전략 항목 아래 가용/한도 표기 + 칸막이 수정 모달", () => {
    const onSetBudget = vi.fn();
    const configs: StrategyConfig[] = [
      { id: 1, symbol: "005930", name: "삼성전자", strategy: "ma_cross", params: { short: 5, long: 20 }, enabled: false, max_qty: null, max_amount: null },
    ];
    const budgets: Budget[] = [
      { symbol: "005930", principal: 1000000, realized_pnl: 0, holding_cost: 0, ceiling: 1000000, available: 1000000 },
    ];
    render(
      <StrategyPanel budgets={budgets} configs={configs} onAdd={() => {}} onToggle={() => {}} onRemove={() => {}} onSetBudget={onSetBudget} />,
    );
    const item = screen.getByText("005930").closest("li") as HTMLElement;
    expect(within(item).getByText(/가용/)).toBeInTheDocument();
    expect(within(item).getByText(/1,000,000원/)).toBeInTheDocument();

    fireEvent.click(within(item).getByRole("button", { name: "칸막이 수정" }));
    const dialog = screen.getByRole("dialog");
    // 입력은 천단위 콤마로 표시된다
    expect((within(dialog).getByLabelText("칸막이 수정 원금") as HTMLInputElement).value).toBe("1,000,000");
    fireEvent.change(within(dialog).getByLabelText("칸막이 수정 원금"), { target: { value: "2000000" } });
    fireEvent.click(within(dialog).getByText("저장"));
    expect(onSetBudget).toHaveBeenCalledWith("005930", 2000000);
  });

  test("칸막이 수정 모달 +버튼도 설정가능(=설정가능+현재원금)을 넘으면 고정", () => {
    const configs: StrategyConfig[] = [
      { id: 1, symbol: "005930", name: "삼성전자", strategy: "ma_cross", params: { short: 5, long: 20 }, enabled: false, max_qty: null, max_amount: null },
    ];
    const budgets: Budget[] = [
      { symbol: "005930", principal: 1000000, realized_pnl: 0, holding_cost: 0, ceiling: 1000000, available: 1000000 },
    ];
    render(
      <StrategyPanel budgets={budgets} configs={configs} onAdd={() => {}} onToggle={() => {}} onRemove={() => {}} onSetBudget={() => {}} orderableCash={8000000} />,
    );
    const item = screen.getByText("005930").closest("li") as HTMLElement;
    fireEvent.click(within(item).getByRole("button", { name: "칸막이 수정" }));
    const dialog = screen.getByRole("dialog");
    // 설정가능 = (8,000,000 − 1,000,000 가용) + 1,000,000 현재원금 = 8,000,000
    fireEvent.click(within(dialog).getByText("+천만")); // 1,000,000 + 10,000,000 → 상한 8,000,000으로 고정
    expect((within(dialog).getByLabelText("칸막이 수정 원금") as HTMLInputElement).value).toBe(
      "8,000,000",
    );
  });

  test("원금 ± 도움 버튼: +천만/−백만/초기화", () => {
    render(
      <StrategyPanel budgets={[]} configs={[]} onAdd={() => {}} onToggle={() => {}} onRemove={() => {}} onSetBudget={() => {}} />,
    );
    const input = screen.getByLabelText("자본 칸막이 원금") as HTMLInputElement;
    // 자본 칸막이 원금 필드의 ± 버튼(첫 번째 그룹)
    const field = input.closest(".param-field") as HTMLElement;
    fireEvent.click(within(field).getByText("+천만"));
    expect(input.value).toBe("10,000,000");
    fireEvent.click(within(field).getByText("+백만"));
    expect(input.value).toBe("11,000,000");
    fireEvent.click(within(field).getByText("−백만"));
    expect(input.value).toBe("10,000,000");
    fireEvent.click(within(field).getByText("초기화"));
    expect(input.value).toBe("");
    // 0 미만으로는 내려가지 않는다(0에서 멈춤)
    fireEvent.click(within(field).getByText("−천만"));
    expect(input.value).toBe("0");
  });

  test("+버튼이 설정가능금액(최대)을 넘으면 최대로 고정", () => {
    // 주문가능현금 8,000,000, 칸막이 없음 → 설정가능 8,000,000
    render(
      <StrategyPanel budgets={[]} configs={[]} onAdd={() => {}} onToggle={() => {}} onRemove={() => {}} onSetBudget={() => {}} orderableCash={8000000} />,
    );
    const input = screen.getByLabelText("자본 칸막이 원금") as HTMLInputElement;
    const field = input.closest(".param-field") as HTMLElement;
    fireEvent.click(within(field).getByText("+천만")); // 10,000,000 → 상한 8,000,000으로 고정
    expect(input.value).toBe("8,000,000");
  });

  test("수정 버튼 → 모달에서 파라미터를 고쳐 저장하면 enabled 유지하며 onAdd 호출", () => {
    const onAdd = vi.fn();
    const configs: StrategyConfig[] = [
      { id: 7, symbol: "005930", name: "삼성전자", strategy: "ma_cross", params: { short: 5, long: 20, bar_ticks: 50 }, enabled: true, max_qty: null, max_amount: null },
    ];
    render(
      <StrategyPanel budgets={[]} configs={configs} onAdd={onAdd} onToggle={() => {}} onRemove={() => {}} onSetBudget={() => {}} />,
    );
    fireEvent.click(screen.getByRole("button", { name: "전략 수정" }));
    const dialog = screen.getByRole("dialog");
    // 현재 파라미터가 채워져 있다
    expect((within(dialog).getByLabelText("단기") as HTMLInputElement).value).toBe("5");

    fireEvent.change(within(dialog).getByLabelText("장기"), { target: { value: "60" } });
    fireEvent.click(within(dialog).getByText("저장"));

    // upsert: 같은 종목·전략, 새 파라미터, enabled 유지(true), 확인창 없음
    // (onEditStrategy 미전달 → onAdd로 폴백)
    expect(onAdd).toHaveBeenCalledWith({
      symbol: "005930",
      strategy: "ma_cross",
      params: { short: 5, long: 60, bar_ticks: 50 },
      enabled: true,
    });
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  test("수정 모달에서 다른 전략으로 교체하면 onEditStrategy로 새 전략을 전달", () => {
    const onEditStrategy = vi.fn();
    const configs: StrategyConfig[] = [
      { id: 7, symbol: "005930", name: "삼성전자", strategy: "ma_cross", params: { short: 5, long: 20, bar_ticks: 50 }, enabled: true, max_qty: null, max_amount: null },
    ];
    render(
      <StrategyPanel budgets={[]} configs={configs} onAdd={() => {}} onToggle={() => {}} onRemove={() => {}} onSetBudget={() => {}} onEditStrategy={onEditStrategy} />,
    );
    fireEvent.click(screen.getByRole("button", { name: "전략 수정" }));
    const dialog = screen.getByRole("dialog");
    // 전략 종류를 RSI + MA 필터로 변경 → 교체 안내 + 기본 파라미터로 초기화
    fireEvent.change(within(dialog).getByLabelText("수정 전략 선택"), { target: { value: "rsi_ma" } });
    expect(within(dialog).getByText(/교체됩니다/)).toBeInTheDocument();
    fireEvent.click(within(dialog).getByText("저장"));

    // 기존 id(7)와 새 전략(rsi_ma)·enabled 유지로 onEditStrategy 호출
    expect(onEditStrategy).toHaveBeenCalledWith(
      7,
      expect.objectContaining({ symbol: "005930", strategy: "rsi_ma", enabled: true }),
    );
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  test("ON 토글 시 확인 팝업을 거쳐야 활성화된다(인터락)", () => {
    const onToggle = vi.fn();
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    const configs: StrategyConfig[] = [
      { id: 3, symbol: "005930", name: "삼성전자", strategy: "ma_cross", params: { short: 5, long: 20 }, enabled: false, max_qty: null, max_amount: null },
    ];
    render(
      <StrategyPanel budgets={[]} configs={configs} onAdd={() => {}} onToggle={onToggle} onRemove={() => {}} onSetBudget={() => {}} />,
    );
    fireEvent.click(screen.getByRole("checkbox"));
    expect(confirmSpy).toHaveBeenCalledTimes(1);
    expect(onToggle).toHaveBeenCalledWith(3, true);
  });

  test("ON 토글 확인 취소 시 활성화하지 않는다", () => {
    const onToggle = vi.fn();
    vi.spyOn(window, "confirm").mockReturnValue(false);
    const configs: StrategyConfig[] = [
      { id: 3, symbol: "005930", name: "삼성전자", strategy: "ma_cross", params: { short: 5, long: 20 }, enabled: false, max_qty: null, max_amount: null },
    ];
    render(
      <StrategyPanel budgets={[]} configs={configs} onAdd={() => {}} onToggle={onToggle} onRemove={() => {}} onSetBudget={() => {}} />,
    );
    fireEvent.click(screen.getByRole("checkbox"));
    expect(onToggle).not.toHaveBeenCalled();
  });

  test("OFF 토글은 확인 없이 즉시 적용", () => {
    const onToggle = vi.fn();
    const confirmSpy = vi.spyOn(window, "confirm");
    const configs: StrategyConfig[] = [
      { id: 3, symbol: "005930", name: "삼성전자", strategy: "ma_cross", params: { short: 5, long: 20 }, enabled: true, max_qty: null, max_amount: null },
    ];
    render(
      <StrategyPanel budgets={[]} configs={configs} onAdd={() => {}} onToggle={onToggle} onRemove={() => {}} onSetBudget={() => {}} />,
    );
    fireEvent.click(screen.getByRole("checkbox")); // ON → OFF
    expect(confirmSpy).not.toHaveBeenCalled();
    expect(onToggle).toHaveBeenCalledWith(3, false);
  });

  test("수정 모달에서 잘못된 값이면 저장 비활성화", () => {
    const onAdd = vi.fn();
    const configs: StrategyConfig[] = [
      { id: 7, symbol: "005930", name: "삼성전자", strategy: "ma_cross", params: { short: 5, long: 20 }, enabled: false, max_qty: null, max_amount: null },
    ];
    render(
      <StrategyPanel budgets={[]} configs={configs} onAdd={onAdd} onToggle={() => {}} onRemove={() => {}} onSetBudget={() => {}} />,
    );
    fireEvent.click(screen.getByRole("button", { name: "전략 수정" }));
    const dialog = screen.getByRole("dialog");
    fireEvent.change(within(dialog).getByLabelText("단기"), { target: { value: "30" } }); // 30 ≥ 20
    expect(within(dialog).getByText("저장")).toBeDisabled();
  });

  test("도움말 버튼을 누르면 중앙 모달로 전략 설명·5/20 의미가 뜬다", () => {
    render(
      <StrategyPanel budgets={[]} configs={[]} onAdd={() => {}} onToggle={() => {}} onRemove={() => {}} onSetBudget={() => {}} />,
    );
    // 닫힌 상태에서는 모달이 없다
    expect(screen.queryByRole("dialog")).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "이동평균 크로스 도움말" }));

    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveTextContent("골든크로스");
    expect(dialog).toHaveTextContent("틱봉");
    // 설정값(5/20)의 의미 설명
    expect(dialog).toHaveTextContent("단기 5 = 틱봉 5개");
    expect(dialog).toHaveTextContent("장기 20 = 틱봉 20개");
  });

  test("배경 클릭으로 도움말 모달이 닫힌다", () => {
    render(
      <StrategyPanel budgets={[]} configs={[]} onAdd={() => {}} onToggle={() => {}} onRemove={() => {}} onSetBudget={() => {}} />,
    );
    fireEvent.click(screen.getByRole("button", { name: "이동평균 크로스 도움말" }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    // 배경(닫기) 클릭
    fireEvent.click(screen.getByRole("button", { name: "닫기" }));
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  test("전략 수정 모달은 배경 클릭으로 닫히지 않는다(취소/저장 버튼으로만 닫힘)", () => {
    const configs: StrategyConfig[] = [
      { id: 7, symbol: "005930", name: "삼성전자", strategy: "ma_cross", params: { short: 5, long: 20, bar_ticks: 50 }, enabled: true, max_qty: null, max_amount: null },
    ];
    render(
      <StrategyPanel budgets={[]} configs={configs} onAdd={() => {}} onToggle={() => {}} onRemove={() => {}} onSetBudget={() => {}} />,
    );
    fireEvent.click(screen.getByRole("button", { name: "전략 수정" }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    // 배경 영역(모달 backdrop) 클릭 — 모달이 닫히지 않음
    const backdrop = screen.getByRole("dialog").parentElement as HTMLElement;
    fireEvent.click(backdrop);
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    // 취소 버튼으로만 닫힐 수 있음
    fireEvent.click(screen.getByRole("button", { name: "취소" }));
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  test("칸막이 수정 모달은 배경 클릭으로 닫히지 않는다(취소/저장 버튼으로만 닫힘)", () => {
    const configs: StrategyConfig[] = [
      { id: 1, symbol: "005930", name: "삼성전자", strategy: "ma_cross", params: { short: 5, long: 20 }, enabled: false, max_qty: null, max_amount: null },
    ];
    const budgets: Budget[] = [
      { symbol: "005930", principal: 1000000, realized_pnl: 0, holding_cost: 0, ceiling: 1000000, available: 1000000 },
    ];
    render(
      <StrategyPanel budgets={budgets} configs={configs} onAdd={() => {}} onToggle={() => {}} onRemove={() => {}} onSetBudget={() => {}} />,
    );
    const item = screen.getByText("005930").closest("li") as HTMLElement;
    fireEvent.click(within(item).getByRole("button", { name: "칸막이 수정" }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    // 배경 영역(모달 backdrop) 클릭 — 모달이 닫히지 않음
    const backdrop = screen.getByRole("dialog").parentElement as HTMLElement;
    fireEvent.click(backdrop);
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    // 취소 버튼으로만 닫힐 수 있음
    fireEvent.click(screen.getByRole("button", { name: "취소" }));
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  test("전략 비교 버튼을 누르면 비교표 팝업이 뜬다", () => {
    render(
      <StrategyPanel budgets={[]} configs={[]} onAdd={() => {}} onToggle={() => {}} onRemove={() => {}} onSetBudget={() => {}} />,
    );
    fireEvent.click(screen.getByRole("button", { name: "전략 비교" }));
    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveTextContent("추세 전환 / 추세 추종");
    expect(dialog).toHaveTextContent("추세 필터 + 눌림목 반등");
    expect(dialog).toHaveTextContent("횡보장에서 가짜 신호 많음");
  });

  test("전략 비교 모달은 배경 클릭으로 닫힌다(dismissable=true)", () => {
    render(
      <StrategyPanel budgets={[]} configs={[]} onAdd={() => {}} onToggle={() => {}} onRemove={() => {}} onSetBudget={() => {}} />,
    );
    fireEvent.click(screen.getByRole("button", { name: "전략 비교" }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    // 배경 영역 클릭 — 모달이 닫힘
    const backdrop = screen.getByRole("dialog").parentElement as HTMLElement;
    fireEvent.click(backdrop);
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  test("파라미터 입력이 기본값으로 채워져 있다(단기 5 / 장기 20)", () => {
    render(
      <StrategyPanel budgets={[]} configs={[]} onAdd={() => {}} onToggle={() => {}} onRemove={() => {}} onSetBudget={() => {}} />,
    );
    expect((screen.getByLabelText("단기") as HTMLInputElement).value).toBe("5");
    expect((screen.getByLabelText("장기") as HTMLInputElement).value).toBe("20");
    // 거버너 추천 기본값도 채워져 있다
    expect((screen.getByLabelText("확인봉") as HTMLInputElement).value).toBe("2");
    expect((screen.getByLabelText("쿨다운봉") as HTMLInputElement).value).toBe("10");
    // 기본값 안내도 함께 노출("기본 5"는 단기·최소보유봉 등 복수 가능)
    expect(screen.getAllByText("기본 5").length).toBeGreaterThan(0);
    expect(screen.getByText("기본 20")).toBeInTheDocument();
  });

  test("RSI+MA 선택 시 5개 파라미터(기본값)와 도움말이 뜬다", () => {
    render(
      <StrategyPanel budgets={[]} configs={[]} onAdd={() => {}} onToggle={() => {}} onRemove={() => {}} onSetBudget={() => {}} />,
    );
    fireEvent.change(screen.getByLabelText("전략 선택"), { target: { value: "rsi_ma" } });
    expect((screen.getByLabelText("RSI 기간") as HTMLInputElement).value).toBe("14");
    expect((screen.getByLabelText("과매도") as HTMLInputElement).value).toBe("30");
    expect((screen.getByLabelText("과매수") as HTMLInputElement).value).toBe("70");
    expect((screen.getByLabelText("추세 MA") as HTMLInputElement).value).toBe("50");
    expect((screen.getByLabelText("틱봉") as HTMLInputElement).value).toBe("50");

    fireEvent.click(screen.getByRole("button", { name: "RSI + MA 필터 도움말" }));
    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveTextContent("상승추세일 때만");
    expect(dialog).toHaveTextContent("추세 이탈");
    expect(dialog).toHaveTextContent("틱봉 50");
  });

  test("RSI+MA로 바꾸면 파라미터 입력도 RSI+MA 기본값으로 초기화", () => {
    render(
      <StrategyPanel budgets={[]} configs={[]} onAdd={() => {}} onToggle={() => {}} onRemove={() => {}} onSetBudget={() => {}} />,
    );
    fireEvent.change(screen.getByLabelText("전략 선택"), { target: { value: "rsi_ma" } });
    expect((screen.getByLabelText("RSI 기간") as HTMLInputElement).value).toBe("14");
    expect((screen.getByLabelText("추세 MA") as HTMLInputElement).value).toBe("50");
    // 이동평균 크로스로 되돌리면 다시 단기/장기/틱봉
    fireEvent.change(screen.getByLabelText("전략 선택"), { target: { value: "ma_cross" } });
    expect((screen.getByLabelText("단기") as HTMLInputElement).value).toBe("5");
    expect((screen.getByLabelText("틱봉") as HTMLInputElement).value).toBe("50");
  });

  test("잘못된 파라미터(단기≥장기)면 오류 표시 + 추가 비활성화", () => {
    render(
      <StrategyPanel budgets={[]} configs={[]} onAdd={() => {}} onToggle={() => {}} onRemove={() => {}} onSetBudget={() => {}} />,
    );
    fireEvent.change(screen.getByLabelText("전략 종목코드"), { target: { value: "005930" } });
    fireEvent.change(screen.getByLabelText("단기"), { target: { value: "30" } }); // 30 ≥ 20
    expect(screen.getByText("단기는 장기보다 작아야 합니다")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "추가" })).toBeDisabled();
  });

  test("추가 시 확인 창 승인하면 전략(OFF) + 자본 칸막이를 함께 등록", () => {
    const onAdd = vi.fn();
    const onSetBudget = vi.fn();
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    render(
      <StrategyPanel budgets={[]} configs={[]} onAdd={onAdd} onToggle={() => {}} onRemove={() => {}} onSetBudget={onSetBudget} />,
    );
    fireEvent.change(screen.getByLabelText("전략 종목코드"), { target: { value: "005930" } });
    fireEvent.change(screen.getByLabelText("단기"), { target: { value: "3" } });
    fireEvent.change(screen.getByLabelText("장기"), { target: { value: "10" } });
    fireEvent.change(screen.getByLabelText("자본 칸막이 원금"), { target: { value: "1000000" } });
    fireEvent.click(screen.getByRole("button", { name: "추가" }));

    expect(confirmSpy).toHaveBeenCalledTimes(1);
    // 사용자 입력(단기3/장기10) + 거버너 추천 기본값이 함께 등록된다
    expect(onAdd).toHaveBeenCalledWith(
      expect.objectContaining({
        symbol: "005930",
        strategy: "ma_cross",
        enabled: false,
        params: expect.objectContaining({
          short: 3,
          long: 10,
          bar_ticks: 50,
          confirm_bars: 2,
          cooldown_bars: 10,
        }),
      }),
    );
    expect(onSetBudget).toHaveBeenCalledWith("005930", 1000000);
  });

  test("원금 입력 아래에 주문가능현금·설정가능을 표시", () => {
    const budgets: Budget[] = [
      { symbol: "005930", principal: 500000, realized_pnl: 0, holding_cost: 0, ceiling: 500000, available: 500000 },
    ];
    const { container } = render(
      <StrategyPanel budgets={budgets} configs={[]} onAdd={() => {}} onToggle={() => {}} onRemove={() => {}} onSetBudget={() => {}} orderableCash={1000000} />,
    );
    const cash = container.querySelector(".budget-cash") as HTMLElement;
    // 주문가능현금 1,000,000 · 칸막이 합계 500,000 · 설정가능 = 1,000,000 − 500,000 = 500,000
    expect(cash.textContent).toContain("주문가능현금 1,000,000원");
    expect(cash.textContent).toContain("칸막이 합계 500,000원");
    expect(cash.textContent).toContain("설정가능");
  });

  test("주문가능현금 아래에 칸막이 합계를 표시", () => {
    const budgets: Budget[] = [
      { symbol: "005930", principal: 1000000, realized_pnl: 0, holding_cost: 0, ceiling: 1000000, available: 1000000 },
      { symbol: "000660", principal: 2000000, realized_pnl: 0, holding_cost: 0, ceiling: 2000000, available: 2000000 },
    ];
    const { container } = render(
      <StrategyPanel budgets={budgets} configs={[]} onAdd={() => {}} onToggle={() => {}} onRemove={() => {}} onSetBudget={() => {}} orderableCash={9523230} />,
    );
    const cash = container.querySelector(".budget-cash") as HTMLElement;
    expect(cash.textContent).toContain("주문가능현금 9,523,230원");
    // 칸막이 합계 = 1,000,000 + 2,000,000 = 3,000,000
    expect(cash.textContent).toContain("칸막이 합계 3,000,000원");
    // 설정가능 = 9,523,230 − 3,000,000 = 6,523,230
    expect(cash.textContent).toContain("6,523,230");
  });

  test("원금 미입력이면 추가 비활성화(전략·칸막이는 한 쌍)", () => {
    render(
      <StrategyPanel budgets={[]} configs={[]} onAdd={() => {}} onToggle={() => {}} onRemove={() => {}} onSetBudget={() => {}} />,
    );
    fireEvent.change(screen.getByLabelText("전략 종목코드"), { target: { value: "005930" } });
    // 파라미터는 기본값으로 유효하지만 원금이 없으면 추가 불가
    expect(screen.getByRole("button", { name: "추가" })).toBeDisabled();
  });

  test("추가 확인 창에서 취소하면 아무것도 등록하지 않음", () => {
    const onAdd = vi.fn();
    const onSetBudget = vi.fn();
    vi.spyOn(window, "confirm").mockReturnValue(false);
    render(
      <StrategyPanel budgets={[]} configs={[]} onAdd={onAdd} onToggle={() => {}} onRemove={() => {}} onSetBudget={onSetBudget} />,
    );
    fireEvent.change(screen.getByLabelText("전략 종목코드"), { target: { value: "005930" } });
    fireEvent.change(screen.getByLabelText("자본 칸막이 원금"), { target: { value: "1000000" } });
    fireEvent.click(screen.getByRole("button", { name: "추가" }));

    expect(onAdd).not.toHaveBeenCalled();
    expect(onSetBudget).not.toHaveBeenCalled();
  });
});
