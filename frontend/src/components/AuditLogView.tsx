import type { AuditLog } from "../types";

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
  return (
    <section className="panel">
      <h2>시스템 로그</h2>
      <div className="table-scroll">
      <table className="quote-table">
        <thead>
          <tr>
            <th>시각</th>
            <th>구분</th>
            <th>내용</th>
          </tr>
        </thead>
        <tbody>
          {logs.map((l) => (
            <tr key={l.id}>
              <td className="muted">{l.created_at?.slice(11, 19) ?? "-"}</td>
              <td>
                <span className={`badge ${CATEGORY_CLASS[l.category] ?? ""}`}>{l.category}</span>
              </td>
              <td>{l.message}</td>
            </tr>
          ))}
          {logs.length === 0 && (
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
