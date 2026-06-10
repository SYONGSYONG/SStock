import type { Order } from "../types";
import { fmt, fmtDatetime } from "../lib/format";

interface OrderLogProps {
  orders: Order[];
}

const STATUS_LABEL: Record<string, string> = {
  requested: "접수",
  filled: "체결",
  cancelled: "취소",
  rejected: "거부",
};

export function OrderLog({ orders }: OrderLogProps) {
  return (
    <section className="panel">
      <h2>주문 내역</h2>
      <div className="table-scroll">
      <table className="quote-table">
        <thead>
          <tr>
            <th>일시</th>
            <th>종목</th>
            <th>구분</th>
            <th className="num">수량</th>
            <th className="num">가격</th>
            <th>상태</th>
          </tr>
        </thead>
        <tbody>
          {orders.map((o) => (
            <tr key={o.id}>
              <td className="muted">{fmtDatetime(o.created_at)}</td>
              <td>
                <span className="code">{o.symbol}</span>{" "}
                <span className="name">{o.name ?? ""}</span>
              </td>
              <td className={o.side === "BUY" ? "up" : "down"}>
                {o.side === "BUY" ? "매수" : "매도"}
              </td>
              <td className="num">{fmt(o.qty)}</td>
              <td className="num">{fmt(o.price)}</td>
              <td className={o.status === "rejected" ? "down" : "muted"}>
                {STATUS_LABEL[o.status] ?? o.status}
              </td>
            </tr>
          ))}
          {orders.length === 0 && (
            <tr>
              <td colSpan={6} className="empty">
                주문 내역이 없습니다
              </td>
            </tr>
          )}
        </tbody>
      </table>
      </div>
    </section>
  );
}
