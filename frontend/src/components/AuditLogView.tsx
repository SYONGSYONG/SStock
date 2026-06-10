import { useState } from "react";
import type { AuditLog } from "../types";
import { fmtDatetime } from "../lib/format";

interface AuditLogViewProps {
  logs: AuditLog[];
}

const CATEGORY_CLASS: Record<string, string> = {
  BOT: "cat-bot",
  ORDER: "cat-order",
  SIGNAL: "cat-signal",
  RISK: "cat-risk",
  MODE: "cat-mode",
  ERROR: "cat-error",
  REGIME: "cat-regime",
  MARKET: "cat-market",
  STRATEGY: "cat-strategy",
};

export function AuditLogView({ logs }: AuditLogViewProps) {
  const [clearedAt, setClearedAt] = useState<string | null>(null);

  // clearedAt 이후(>)에 생성된 로그만 표시(클라이언트 컷오프 — DB는 건드리지 않음)
  const filteredLogs = clearedAt
    ? logs.filter((l) => l.created_at > clearedAt)
    : logs;

  const handleClear = () => {
    if (logs.length === 0) return;
    // 배열 정렬 방향과 무관하게 '현재 보이는 로그 중 가장 최신 시각'을 컷오프로 삼는다.
    // 백엔드는 최신순(DESC)으로 내려주므로 위치 기반 인덱싱(logs[length-1])은 가장
    // 오래된 로그를 가리켜 한 줄만 지워지는 버그가 된다. created_at의 최댓값을 쓴다.
    const newest = logs.reduce((a, b) => (b.created_at > a.created_at ? b : a));
    setClearedAt(newest.created_at);
  };

  return (
    <section className="panel">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2>시스템 로그</h2>
        <button
          onClick={handleClear}
          style={{
            padding: "0.5rem 1rem",
            fontSize: "0.875rem",
            borderRadius: "0.375rem",
            border: "1px solid var(--border)",
            background: "var(--surface)",
            cursor: "pointer",
          }}
        >
          지우기
        </button>
      </div>
      <div className="table-scroll">
        <table className="quote-table">
          <thead>
            <tr>
              <th>일시</th>
              <th>구분</th>
              <th>내용</th>
            </tr>
          </thead>
          <tbody>
            {filteredLogs.map((l) => (
              <tr key={l.id}>
                <td className="muted">{fmtDatetime(l.created_at)}</td>
                <td>
                  <span className={`badge ${CATEGORY_CLASS[l.category] ?? ""}`}>{l.category}</span>
                </td>
                <td>{l.message}</td>
              </tr>
            ))}
            {filteredLogs.length === 0 && (
              <tr>
                <td colSpan={3} className="empty">
                  로그가 없습니다
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
