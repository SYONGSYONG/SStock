import { useEffect, useState } from "react";
import type { RecommendItem, RecommendResult, ThemeInfo } from "../types";

interface RecommendPageProps {
  fetchThemes: () => Promise<ThemeInfo[]>;
  fetchRecommend: (
    theme: string,
    limit?: number,
    signal?: AbortSignal,
  ) => Promise<RecommendResult>;
  onAdd: (symbol: string, name?: string) => void;
  onSelect?: (symbol: string, name?: string | null) => void;
}

export function RecommendPage({ fetchThemes, fetchRecommend, onAdd, onSelect }: RecommendPageProps) {
  const [themes, setThemes] = useState<ThemeInfo[]>([]);
  const [active, setActive] = useState<string | null>(null);
  const [result, setResult] = useState<RecommendResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchThemes()
      .then(setThemes)
      .catch(() => setError("테마 목록을 불러오지 못했습니다."));
  }, [fetchThemes]);

  // 분야 선택 시 추천을 조회한다. 로딩 중 다른 분야를 누르면 cleanup이
  // 이전 요청을 abort하고 stale 응답을 무시한다(ChartModal의 alive 패턴과 동일).
  useEffect(() => {
    if (!active) return;
    let alive = true;
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    setResult(null);
    fetchRecommend(active, undefined, controller.signal)
      .then((data) => {
        if (!alive) return;
        setResult(data);
        setLoading(false);
      })
      .catch((err) => {
        if (!alive) return;
        // 의도적 취소(AbortError)는 오류로 표시하지 않는다.
        if (err instanceof DOMException && err.name === "AbortError") return;
        setError("추천 종목을 불러오지 못했습니다.");
        setLoading(false);
      });
    return () => {
      alive = false;
      controller.abort();
    };
  }, [active, fetchRecommend]);

  const pick = (slug: string) => setActive(slug);

  return (
    <section className="panel recommend">
      <h2>분야별 추천 종목</h2>
      <p className="disclaimer muted">
        추천은 참고용이며 수익을 보장하지 않습니다. 자동 매매는 별도 설정입니다.
      </p>

      <div className="theme-chips">
        {themes.map((t) => (
          <button
            key={t.slug}
            className={"chip" + (t.slug === active ? " active" : "")}
            onClick={() => pick(t.slug)}
          >
            {t.label} <span className="count">{t.count}</span>
          </button>
        ))}
      </div>

      {error && <p className="error">{error}</p>}
      {loading && <p className="muted">불러오는 중...</p>}

      {result && !loading && (
        <>
          {result.base_date && <p className="muted base-date">기준일: {result.base_date}</p>}
          <div className="rec-grid">
            {result.items.map((it, i) => (
              <RecommendCard
                key={it.symbol}
                rank={i + 1}
                item={it}
                onAdd={onAdd}
                onSelect={onSelect}
              />
            ))}
          </div>
          {result.items.length === 0 && (
            <p className="empty">해당 분야의 추천 종목이 없습니다</p>
          )}
        </>
      )}
    </section>
  );
}

interface RecommendCardProps {
  rank: number;
  item: RecommendItem;
  onAdd: (symbol: string, name?: string) => void;
  onSelect?: (symbol: string, name?: string | null) => void;
}

function changeClass(rate: number | null): string {
  if (rate == null || rate === 0) return "muted";
  return rate > 0 ? "up" : "down";
}

function RecommendCard({ rank, item, onAdd, onSelect }: RecommendCardProps) {
  const clickable = onSelect != null;
  const openChart = () => onSelect?.(item.symbol, item.name);

  return (
    <article
      className={"rec-card" + (clickable ? " clickable" : "")}
      onClick={clickable ? openChart : undefined}
      role={clickable ? "button" : undefined}
      tabIndex={clickable ? 0 : undefined}
      aria-label={clickable ? `${item.name} 차트 보기` : undefined}
      onKeyDown={
        clickable
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                openChart();
              }
            }
          : undefined
      }
    >
      <header className="rec-head">
        <span className="rank">{rank}</span>
        <div className="rec-name">
          <strong>{item.name}</strong>
          <span className="code muted">
            {item.symbol} · {item.market}
          </span>
        </div>
        <span className="rec-score">{item.score.toFixed(1)}</span>
      </header>

      <div className="rec-price">
        <span className="now">{item.price != null ? item.price.toLocaleString() : "-"}</span>
        <span className={changeClass(item.change_rate)}>
          {item.change_rate != null
            ? `${item.change_rate > 0 ? "+" : ""}${item.change_rate.toFixed(2)}%`
            : "-"}
        </span>
      </div>

      <div className="rec-bars">
        <ScoreBar label="모멘텀" value={item.momentum} />
        <ScoreBar label="펀더멘털" value={item.fundamental} />
        <ScoreBar label="수급" value={item.supply} />
      </div>

      <div className="rec-meta muted">
        <span>ROE {item.roe != null ? item.roe.toFixed(1) : "-"}</span>
        {clickable && <span className="chart-hint">클릭 시 차트</span>}
      </div>

      <button
        type="button"
        className="add-btn"
        onClick={(e) => {
          e.stopPropagation();
          onAdd(item.symbol, item.name);
        }}
      >
        관심종목 추가
      </button>
    </article>
  );
}

function ScoreBar({ label, value }: { label: string; value: number }) {
  const pct = Math.max(0, Math.min(100, value));
  return (
    <div className="bar-row">
      <span className="bar-label">{label}</span>
      <span className="bar-track">
        <span className="bar-fill" style={{ width: `${pct}%` }} />
      </span>
      <span className="bar-val">{Math.round(value)}</span>
    </div>
  );
}
