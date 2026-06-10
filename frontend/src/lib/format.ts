// 국내 증시 관례: 상승=빨강(up), 하락=파랑(down), 보합=중립
export function fmt(n: number | null | undefined): string {
  return n == null ? "-" : n.toLocaleString("ko-KR");
}

export function fmtRate(n: number | null | undefined): string {
  if (n == null) return "-";
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(2)}%`;
}

/**
 * 백엔드에서 받은 created_at (KST 문자열 "YYYY-MM-DD HH:MM:SS")을 "MM-DD HH:MM:SS" 형태로 포맷
 * @param isoString - "YYYY-MM-DD HH:MM:SS" 형태의 문자열
 * @returns "MM-DD HH:MM:SS" 형태의 문자열, null/undefined면 "-"
 */
export function fmtDatetime(isoString: string | null | undefined): string {
  if (isoString == null || isoString === "") return "-";
  // "YYYY-MM-DD HH:MM:SS"에서 슬라이스
  // 위치: 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19
  //       Y Y Y Y - M M - D D    H  H  :  M  M  :  S  S
  // MM-DD HH:MM:SS = slice(5, 19) 또는 slice(5)
  return isoString.slice(5);
}

export type Direction = "up" | "down" | "neutral";

export function direction(change: number | null | undefined): Direction {
  if (change == null || change === 0) return "neutral";
  return change > 0 ? "up" : "down";
}
