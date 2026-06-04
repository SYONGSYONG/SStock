import { useState } from "react";

interface HelpPopoverProps {
  /** 접근성 라벨(예: "이동평균 크로스 도움말") */
  label: string;
  children: React.ReactNode;
}

/** 물음표 버튼을 누르면 브라우저 화면 중앙에 설명 모달을 띄우는 도움말.
 *  우상단 ✕ 버튼으로만 닫힌다(배경 클릭·Esc로는 닫히지 않음 — 실수 닫힘 방지). */
export function HelpPopover({ label, children }: HelpPopoverProps) {
  const [open, setOpen] = useState(false);

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
        <div className="help-backdrop">
          <div
            className="help-dialog"
            role="dialog"
            aria-modal="true"
            aria-label={label}
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
