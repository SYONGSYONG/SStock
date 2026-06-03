import { useEffect, useState } from "react";
import type { RecommendCandidate, RecommendItem, RecommendQuote, RecommendResult, ThemeInfo } from "../types";
import type { RecommendStreamHandlers } from "../api/client";

interface RecommendPageProps {
  fetchThemes: () => Promise<ThemeInfo[]>;
  subscribeRecommend?: (theme: string, limit: number, handlers: RecommendStreamHandlers) => () => void;
  fetchRecommend?: (
    theme: string,
    limit?: number,
    signal?: AbortSignal,
  ) => Promise<RecommendResult>;
  onAdd: (symbol: string, name?: string) => void;
  onSelect?: (symbol: string, name?: string | null) => void;
}

export function RecommendPage({
  fetchThemes,
  subscribeRecommend,
  fetchRecommend,
  onAdd,
  onSelect,
}: RecommendPageProps) {
  const [themes, setThemes] = useState<ThemeInfo[]>([]);
  const [active, setActive] = useState<string | null>(null);
  const [candidates, setCandidates] = useState<RecommendCandidate[]>([]);
  const [quotes, setQuotes] = useState<Record<string, RecommendQuote>>({});
  const [result, setResult] = useState<RecommendResult | null>(null);
  const [baseDate, setBaseDate] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchThemes()
      .then(setThemes)
      .catch(() => setError("테마 목록을 불러오지 못했습니다."));
  }, [fetchThemes]);

  // 분야 선택 시 추천을 조회한다.
  // subscribeRecommend가 있으면 스트리밍, 아니면 폴백으로 fetchRecommend 사용.
  useEffect(() => {
    if (!active) return;
    let alive = true;

    // 상태 초기화
    setCandidates([]);
    setQuotes({});
    setResult(null);
    setBaseDate(null);
    setLoading(true);
    setError(null);

    // subscribeRecommend가 있으면 스트리밍 사용
    if (subscribeRecommend) {
      const unsub = subscribeRecommend(active, 10, {
        onCandidates: (c) => {
          if (!alive) return;
          setCandidates(c.candidates);
          setBaseDate(c.base_date);
        },
        onQuote: (q) => {
          if (!alive) return;
          setQuotes((prev) => ({ ...prev, [q.symbol]: q }));
        },
        onResult: (r) => {
          if (!alive) return;
          setResult(r);
          setLoading(false);
        },
        onError: () => {
          if (!alive) return;
          setError("추천 종목을 불러오지 못했습니다.");
          setLoading(false);
        },
      });

      return () => {
        alive = false;
        unsub();
      };
    }

    // 폴백: fetchRecommend 사용 (스트리밍이 없을 때)
    if (fetchRecommend) {
      const controller = new AbortController();
      fetchRecommend(active, undefined, controller.signal)
        .then((data) => {
          if (!alive) return;
          setResult(data);
          setBaseDate(data.base_date);
          setLoading(false);
        })
        .catch((err) => {
          if (!alive) return;
          if (err instanceof DOMException && err.name === "AbortError") return;
          setError("추천 종목을 불러오지 못했습니다.");
          setLoading(false);
        });

      return () => {
        alive = false;
        controller.abort();
      };
    }
  }, [active, subscribeRecommend, fetchRecommend]);

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

      {result && !loading ? (
        <>
          {baseDate && <p className="muted base-date">기준일: {baseDate}</p>}
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
      ) : candidates.length > 0 ? (
        <>
          {baseDate && <p className="muted base-date">기준일: {baseDate}</p>}
          {loading && (
            <p className="muted">
              {themes.find((t) => t.slug === active)?.label || "분야"} 불러오는 중...{" "}
              ({Object.keys(quotes).length}/{candidates.length})
            </p>
          )}
          <div className="rec-grid">
            {candidates.map((cand, i) => (
              <RecommendSkeletonCard
                key={cand.symbol}
                rank={i + 1}
                candidate={cand}
                quote={quotes[cand.symbol] || null}
                onAdd={onAdd}
                onSelect={onSelect}
              />
            ))}
          </div>
        </>
      ) : loading ? (
        <p className="muted">
          {themes.find((t) => t.slug === active)?.label || "분야"} 불러오는 중...
        </p>
      ) : null}
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

interface RecommendSkeletonCardProps {
  rank: number;
  candidate: RecommendCandidate;
  quote: RecommendQuote | null;
  onAdd: (symbol: string, name?: string) => void;
  onSelect?: (symbol: string, name?: string | null) => void;
}

function RecommendSkeletonCard({
  rank,
  candidate,
  quote,
  onAdd,
  onSelect,
}: RecommendSkeletonCardProps) {
  const clickable = onSelect != null;
  const openChart = () => onSelect?.(candidate.symbol, candidate.name);

  return (
    <article
      className={"rec-card skeleton" + (clickable ? " clickable" : "")}
      onClick={clickable ? openChart : undefined}
      role={clickable ? "button" : undefined}
      tabIndex={clickable ? 0 : undefined}
      aria-label={clickable ? `${candidate.name} 차트 보기` : undefined}
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
          <strong>{candidate.name || candidate.symbol}</strong>
          <span className="code muted">
            {candidate.symbol} · {candidate.market}
          </span>
        </div>
        <span className="rec-score" style={{ color: "#ddd" }}>
          ...
        </span>
      </header>

      <div className="rec-price">
        <span className="now">
          {quote?.price != null ? quote.price.toLocaleString() : "—"}
        </span>
        <span className={quote?.change_rate != null ? changeClass(quote.change_rate) : "muted"}>
          {quote?.change_rate != null
            ? `${quote.change_rate > 0 ? "+" : ""}${quote.change_rate.toFixed(2)}%`
            : "—"}
        </span>
      </div>

      <div className="rec-bars">
        <div className="bar-row" style={{ opacity: 0.4 }}>
          <span className="bar-label">모멘텀</span>
          <span className="bar-track">
            <span className="bar-fill" style={{ width: "0%" }} />
          </span>
          <span className="bar-val">...</span>
        </div>
        <div className="bar-row" style={{ opacity: 0.4 }}>
          <span className="bar-label">펀더멘털</span>
          <span className="bar-track">
            <span className="bar-fill" style={{ width: "0%" }} />
          </span>
          <span className="bar-val">...</span>
        </div>
        <div className="bar-row" style={{ opacity: 0.4 }}>
          <span className="bar-label">수급</span>
          <span className="bar-track">
            <span className="bar-fill" style={{ width: "0%" }} />
          </span>
          <span className="bar-val">...</span>
        </div>
      </div>

      <div className="rec-meta muted" style={{ opacity: 0.5 }}>
        <span>ROE —</span>
        {clickable && <span className="chart-hint">클릭 시 차트</span>}
      </div>

      <button
        type="button"
        className="add-btn"
        onClick={(e) => {
          e.stopPropagation();
          onAdd(candidate.symbol, candidate.name ?? undefined);
        }}
      >
        관심종목 추가
      </button>
    </article>
  );
}
