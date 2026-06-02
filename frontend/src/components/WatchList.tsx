import { useEffect, useRef, useState } from "react";
import type { StockSearchResult, WatchItem } from "../types";

interface WatchListProps {
  items: WatchItem[];
  onAdd: (symbol: string, name?: string) => void;
  onRemove: (symbol: string) => void;
  onSelect?: (symbol: string) => void; // 행 클릭 → 차트 모달
  search: (q: string) => Promise<StockSearchResult[]>;
  error?: string | null;
}

export function WatchList({ items, onAdd, onRemove, onSelect, search, error }: WatchListProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<StockSearchResult[]>([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0); // 키보드 하이라이트 인덱스
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

  // 하이라이트된 항목이 보이도록 스크롤
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
    if (!open || results.length === 0) {
      return;
    }
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
      <h2>관심종목</h2>
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
      {error && <p className="error">{error}</p>}
      <ul className="watch-list">
        {items.map((it) => (
          <li key={it.symbol}>
            <button
              type="button"
              className="watch-open"
              onClick={() => onSelect?.(it.symbol)}
              title="차트 보기"
            >
              <span className="code">{it.symbol}</span>
              <span className="name">{it.name ?? "-"}</span>
            </button>
            <button className="link-danger" onClick={() => onRemove(it.symbol)}>
              삭제
            </button>
          </li>
        ))}
        {items.length === 0 && <li className="empty">등록된 종목이 없습니다</li>}
      </ul>
    </section>
  );
}
