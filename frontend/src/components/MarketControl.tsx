interface MarketControlProps {
  running: boolean;
  clients: number;
  onStart: () => void;
  onStop: () => void;
}

export function MarketControl({ running, clients, onStart, onStop }: MarketControlProps) {
  return (
    <section className="panel market-control">
      <h2>시세 수집</h2>
      <p className="muted">대시보드 연결 {clients}개</p>
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
