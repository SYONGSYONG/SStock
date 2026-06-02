import { useEffect, useRef, useState } from "react";
import type { StockSearchResult, WatchItem } from "../types";

interface WatchListProps {
  items: WatchItem[];
  onAdd: (symbol: string, name?: string) => void;
  onRemove: (symbol: string) => void;
  search: (q: string) => Promise<StockSearchResult[]>;
  error?: string | null;
}

export function WatchList({ items, onAdd, onRemove, search, error }: WatchListProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<StockSearchResult[]>([]);
  const [open, setOpen] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (timer.current) clearTimeout(timer.current);
    const q = query.trim();
    if (q.length < 1) {
      setResults([]);
      return;
    }
    timer.current = setTimeout(() => {
      search(q)
        .then((r) => {
          setResults(r);
          setOpen(true);
        })
        .catch(() => setResults([]));
    }, 250);
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [query, search]);

  const pick = (r: StockSearchResult) => {
    onAdd(r.symbol, r.name);
    setQuery("");
    setResults([]);
    setOpen(false);
  };

  return (
    <section className="panel">
      <h2>관심종목</h2>
      <div className="search-box">
        <input
          aria-label="종목 검색"
          placeholder="종목명 또는 코드 검색 (예: 삼성전자)"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => results.length > 0 && setOpen(true)}
        />
        {open && results.length > 0 && (
          <ul className="search-results">
            {results.map((r) => (
              <li key={r.symbol} onMouseDown={() => pick(r)}>
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
            <span className="code">{it.symbol}</span>
            <span className="name">{it.name ?? "-"}</span>
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
