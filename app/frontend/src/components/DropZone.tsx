import { useCallback, useRef, useState } from 'react';

export interface DropZoneProps {
  accept?: string;
  maxBytes?: number;
  onSelect: (file: File) => void;
  disabled?: boolean;
}

export default function DropZone({
  accept = '.ifc',
  maxBytes = 100 * 1024 * 1024,
  onSelect,
  disabled,
}: DropZoneProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [isOver, setIsOver] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const validate = (file: File): string | null => {
    if (!file.name.toLowerCase().endsWith('.ifc')) {
      return 'Only .ifc files are supported.';
    }
    if (file.size > maxBytes) {
      return `File too large. Maximum is ${Math.round(maxBytes / 1024 / 1024)} MB.`;
    }
    return null;
  };

    const handleFile = useCallback(
    (file: File) => {
      const err = validate(file);
      if (err) {
        setError(err);
        return;
      }
      setError(null);
      onSelect(file);
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [maxBytes, onSelect],
  );

  return (
    <div
      className={`dropzone ${isOver ? 'over' : ''} ${disabled ? 'disabled' : ''}`}
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setIsOver(true);
      }}
      onDragLeave={() => setIsOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setIsOver(false);
        if (disabled) return;
        const f = e.dataTransfer.files?.[0];
        if (f) handleFile(f);
      }}
      onClick={() => !disabled && inputRef.current?.click()}
      role="button"
      tabIndex={0}
      data-testid="dropzone"
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        hidden
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) handleFile(f);
          e.target.value = '';
        }}
      />
      <p className="muted">Drag and drop your .ifc file, or click to choose</p>
      {error && <div className="error">{error}</div>}
    </div>
  );
}
