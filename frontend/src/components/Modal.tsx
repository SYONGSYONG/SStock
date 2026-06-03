import { useEffect } from "react";

interface ModalProps {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}

/** 화면 중앙에 뜨는 경량 모달(배경 클릭·Esc·✕로 닫힘). 외부 의존성 없음. */
export function Modal({ title, onClose, children }: ModalProps) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="edit-modal-backdrop" onClick={onClose}>
      <div
        className="edit-modal"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(e) => e.stopPropagation()}
      >
        <header className="edit-modal-head">
          <h3>{title}</h3>
          <button type="button" className="edit-modal-close" aria-label="닫기" onClick={onClose}>
            ✕
          </button>
        </header>
        <div className="edit-modal-body">{children}</div>
      </div>
    </div>
  );
}
