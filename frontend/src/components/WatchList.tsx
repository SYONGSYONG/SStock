import { useState } from "react";
import type { WatchItem } from "../types";

interface WatchListProps {
  items: WatchItem[];
  onAdd: (symbol: string, name?: string) => void;
  onRemove: (symbol: string) => void;
  error?: string | null;
}

export function WatchList({ items, onAdd, onRemove, error }: WatchListProps) {
  const [symbol, setSymbol] = useState("");
  const [name, setName] = useState("");

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!/^\d{6}$/.test(symbol)) return;
    onAdd(symbol, name || undefined);
    setSymbol("");
    setName("");
  };

  return (
    <section className="panel">
      <h2>관심종목</h2>
      <form className="watch-form" onSubmit={submit}>
        <input
          aria-label="종목코드"
          placeholder="종목코드 6자리"
          value={symbol}
          maxLength={6}
          onChange={(e) => setSymbol(e.target.value.replace(/\D/g, ""))}
        />
        <input
          aria-label="종목명"
          placeholder="종목명(선택)"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <button type="submit" disabled={!/^\d{6}$/.test(symbol)}>
          추가
        </button>
      </form>
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
