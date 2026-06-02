import { useEffect, useState } from "react";
import type { RecommendItem, RecommendResult, ThemeInfo } from "../types";

interface RecommendPageProps {
  fetchThemes: () => Promise<ThemeInfo[]>;
  fetchRecommend: (theme: string, limit?: number) => Promise<RecommendResult>;
  onAdd: (symbol: string, name?: string) => void;
  onSelect?: (symbol: string) => void; // 종목 클릭 시 차트 모달 열기
}

/** 분야(KRX 테마)별 복합 점수 추천 종목 페이지. */
export function RecommendPage({ fetchThemes, fetchRecommend, onAdd, onSelect }: RecommendPageProps) {
  const [themes, setThemes] = useState<ThemeInfo[]>([]);
  const [active, setActive] = useState<string | null>(null);
  const [result, setResult] = useState<RecommendResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchThemes()
      .then(setThemes)
      .catch(() => setError("테마 목록을 불러오지 못했습니다"));
  }, [fetchThemes]);

  const pick = async (slug: string) => {
    setActive(slug);
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      setResult(await fetchRecommend(slug));
    } catch {
      setError("추천을 불러오지 못했습니다");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="panel recommend">
      <h2>분야별 추천 종목</h2>
      <p className="disclaimer muted">
        ※ 투자 판단의 참고용이며 수익을 보장하지 않습니다. 자동 매매와는 무관합니다.
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
      {loading && <p className="muted">불러오는 중…</p>}

      {result && !loading && (
        <>
          {result.base_date && (
            <p className="muted base-date">재무 기준일: {result.base_date}</p>
          )}
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
  onSelect?: (symbol: string) => void;
}

// 국내 관례: 상승 빨강 / 하락 파랑 / 보합·없음 회색
function changeClass(rate: number | null): string {
  if (rate == null || rate === 0) return "muted";
  return rate > 0 ? "up" : "down";
}

function RecommendCard({ rank, item, onAdd, onSelect }: RecommendCardProps) {
  const clickable = onSelect != null;
  const openChart = () => onSelect?.(item.symbol);
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
        {clickable && <span className="chart-hint">클릭 → 차트</span>}
      </div>

      <button
        className="add-btn"
        onClick={(e) => {
          e.stopPropagation(); // 카드 클릭(차트)과 분리
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
