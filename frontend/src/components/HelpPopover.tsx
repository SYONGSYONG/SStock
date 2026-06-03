import { useEffect, useState } from "react";

interface HelpPopoverProps {
  /** 접근성 라벨(예: "이동평균 크로스 도움말") */
  label: string;
  children: React.ReactNode;
}

/** 물음표 버튼을 누르면 브라우저 화면 중앙에 설명 모달을 띄우는 도움말.
 *  배경 클릭 또는 Esc로 닫힌다(외부 의존성 없음). */
export function HelpPopover({ label, children }: HelpPopoverProps) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <span className="help-popover">
      <button
        type="button"
        className="help-btn"
        aria-label={label}
        aria-haspopup="dialog"
        aria-expanded={open}
        onClick={() => setOpen(true)}
      >
        ?
      </button>
      {open && (
        <div className="help-backdrop" onClick={() => setOpen(false)}>
          <div
            className="help-dialog"
            role="dialog"
            aria-modal="true"
            aria-label={label}
            onClick={(e) => e.stopPropagation()}
          >
            <button
              type="button"
              className="help-dialog-close"
              aria-label="닫기"
              onClick={() => setOpen(false)}
            >
              ✕
            </button>
            <div className="help-dialog-body">{children}</div>
          </div>
        </div>
      )}
    </span>
  );
}
