// 국내 증시 관례: 상승=빨강(up), 하락=파랑(down), 보합=중립
export function fmt(n: number | null | undefined): string {
  return n == null ? "-" : n.toLocaleString("ko-KR");
}

export function fmtRate(n: number | null | undefined): string {
  if (n == null) return "-";
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(2)}%`;
}

export type Direction = "up" | "down" | "neutral";

export function direction(change: number | null | undefined): Direction {
  if (change == null || change === 0) return "neutral";
  return change > 0 ? "up" : "down";
}
