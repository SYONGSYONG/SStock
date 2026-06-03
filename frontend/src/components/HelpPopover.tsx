import { useEffect, useId, useRef, useState } from "react";

interface HelpPopoverProps {
  /** 접근성 라벨(예: "이동평균 크로스 도움말") */
  label: string;
  children: React.ReactNode;
}

/** 물음표 버튼을 누르면 설명 말풍선을 띄우는 경량 도움말 팝오버.
 *  외부 클릭 또는 Esc로 닫힌다(외부 의존성 없음). */
export function HelpPopover({ label, children }: HelpPopoverProps) {
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLSpanElement>(null);
  const bubbleId = useId();

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <span className="help-popover" ref={wrapRef}>
      <button
        type="button"
        className="help-btn"
        aria-label={label}
        aria-expanded={open}
        aria-controls={bubbleId}
        onClick={() => setOpen((v) => !v)}
      >
        ?
      </button>
      {open && (
        <span id={bubbleId} role="tooltip" className="help-bubble">
          {children}
        </span>
      )}
    </span>
  );
}
