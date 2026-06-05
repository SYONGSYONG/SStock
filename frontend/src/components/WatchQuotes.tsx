import { useEffect, useRef, useState } from "react";
import type { Quote, StockSearchResult, WatchItem } from "../types";
import { direction, fmt, fmtRate } from "../lib/format";

interface WatchQuotesProps {
  items: WatchItem[];
  quotes: Record<string, Quote>;
  strategySymbols: Set<string>;
  onAdd: (symbol: string, name?: string) => void;
  onRemove: (symbol: string) => void;
  /** 종목명 클릭 → 차트 보기 */
  onSelect?: (symbol: string, name?: string | null) => void;
  /** 전략이동 버튼 → 전략 폼에 종목코드 복사 */
  onPickSymbol?: (symbol: string) => void;
  search: (q: string) => Promise<StockSearchResult[]>;
  error?: string | null;
}

/** 관심종목 + 실시간 시세를 한 표로 합친 패널.
 *  - 검색창(헤더 우측)으로 종목 추가
 *  - 전략이동 버튼(좌측 열) → 전략 폼에 복사
 *  - 종목명 클릭 → 차트, 삭제 버튼 → 관심종목 제거 */
export function WatchQuotes({
  items,
  quotes,
  strategySymbols,
  onAdd,
  onRemove,
  onSelect,
  onPickSymbol,
  search,
  error,
}: WatchQuotesProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<StockSearchResult[]>([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const listRef = useRef<HTMLUListElement | null>(null);

  useEffect(() => {
    if (timer.current) clearTimeout(timer.current);
    const q = query.trim();
    if (q.length < 1) {
      setResults([]);
      setActive(0);
      return;
    }
    timer.current = setTimeout(() => {
      search(q)
        .then((r) => {
          setResults(r);
          setActive(0);
          setOpen(true);
        })
        .catch(() => setResults([]));
    }, 250);
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [query, search]);

  useEffect(() => {
    if (!open || !listRef.current) return;
    const el = listRef.current.children[active] as HTMLElement | undefined;
    el?.scrollIntoView({ block: "nearest" });
  }, [active, open]);

  const pick = (r: StockSearchResult) => {
    onAdd(r.symbol, r.name);
    setQuery("");
    setResults([]);
    setOpen(false);
    setActive(0);
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!open || results.length === 0) return;
    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        setActive((i) => (i + 1) % results.length);
        break;
      case "ArrowUp":
        e.preventDefault();
        setActive((i) => (i - 1 + results.length) % results.length);
        break;
      case "Enter":
        e.preventDefault();
        if (results[active]) pick(results[active]);
        break;
      case "Escape":
        e.preventDefault();
        setOpen(false);
        break;
      default:
        break;
    }
  };

  return (
    <section className="panel">
      <div className="panel-head-row watch-quotes-head">
        <h2>실시간 시세</h2>
        <div className="search-box">
          <input
            aria-label="종목 검색"
            placeholder="종목명 또는 코드 검색 (예: 삼성전자)"
            value={query}
            role="combobox"
            aria-expanded={open && results.length > 0}
            aria-controls="stock-search-results"
            aria-activedescendant={
              open && results[active] ? `stock-opt-${results[active].symbol}` : undefined
            }
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={onKeyDown}
            onFocus={() => results.length > 0 && setOpen(true)}
            onBlur={() => setOpen(false)}
          />
          {open && results.length > 0 && (
            <ul className="search-results" id="stock-search-results" role="listbox" ref={listRef}>
              {results.map((r, i) => (
                <li
                  key={r.symbol}
                  id={`stock-opt-${r.symbol}`}
                  role="option"
                  aria-selected={i === active}
                  className={i === active ? "active" : undefined}
                  onMouseDown={() => pick(r)}
                  onMouseEnter={() => setActive(i)}
                >
                  <span className="name">{r.name}</span>
                  <span className="code muted">{r.symbol}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
      {error && <p className="error">{error}</p>}
      <div className="table-scroll">
        <table className="quote-table">
          <thead>
            <tr>
              <th aria-label="전략이동" />
              <th>종목</th>
              <th className="num">현재가</th>
              <th className="num">전일대비</th>
              <th className="num">등락률</th>
              <th className="num">거래량</th>
              <th aria-label="삭제" />
            </tr>
          </thead>
          <tbody>
            {items.map((it) => {
              const q = quotes[it.symbol];
              const dir = direction(q?.change);
              const hasStrategy = strategySymbols.has(it.symbol);
              return (
                <tr key={it.symbol} className={hasStrategy ? "with-strategy" : ""}>
                  <td>
                    <button
                      type="button"
                      className="link-action strategy-move"
                      title="전략 폼에 종목코드 복사(전략 이동)"
                      onClick={() => onPickSymbol?.(it.symbol)}
                    >
                      전략이동
                    </button>
                  </td>
                  <td>
                    <button
                      type="button"
                      className="quote-name-btn"
                      title="차트 보기"
                      onClick={() => onSelect?.(it.symbol, it.name)}
                    >
                      <span
                        className={`code ${hasStrategy ? "with-strategy" : ""}`}
                        title={hasStrategy ? "전략 등록됨" : undefined}
                      >
                        {it.symbol}
                        {hasStrategy && (
                          <span className="strategy-marker" aria-label="전략 등록됨">
                            •
                          </span>
                        )}
                      </span>{" "}
                      <span className="name">{it.name ?? ""}</span>
                    </button>
                  </td>
                  <td className={`num ${dir}`}>{fmt(q?.price)}</td>
                  <td className={`num ${dir}`}>{fmt(q?.change)}</td>
                  <td className={`num ${dir}`}>{fmtRate(q?.change_rate)}</td>
                  <td className="num">{fmt(q?.volume)}</td>
                  <td>
                    <button
                      type="button"
                      className="link-danger"
                      onClick={() => onRemove(it.symbol)}
                    >
                      삭제
                    </button>
                  </td>
                </tr>
              );
            })}
            {items.length === 0 && (
              <tr>
                <td colSpan={7} className="empty">
                  종목을 검색해 추가하세요
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
