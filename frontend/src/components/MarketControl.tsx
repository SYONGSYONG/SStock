interface MarketControlProps {
  running: boolean;
  clients: number;
  onStart: () => void;
  onStop: () => void;
  /** 상단 배너용 컴팩트(라벨 + 버튼만) 렌더 */
  compact?: boolean;
}

export function MarketControl({ running, clients, onStart, onStop, compact }: MarketControlProps) {
  if (compact) {
    return (
      <div className="banner-control" title={`대시보드 ${clients}개 연결`}>
        <span className="banner-control-label">시세 수집</span>
        {running ? (
          <button className="btn-stop btn-sm" onClick={onStop}>
            정지
          </button>
        ) : (
          <button className="btn-start btn-sm" onClick={onStart}>
            시작
          </button>
        )}
      </div>
    );
  }

  return (
    <section className="panel market-control">
      <h2>시세 수집</h2>
      <p className="muted">대시보드 {clients}개 연결되었습니다.</p>
      {running ? (
        <button className="btn-stop" onClick={onStop}>
          정지
        </button>
      ) : (
        <button className="btn-start" onClick={onStart}>
          시작
        </button>
      )}
    </section>
  );
}
