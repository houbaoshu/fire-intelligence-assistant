import { useCallback, useId, useRef, useState, type DragEvent } from "react";
import { UploadCloud, X, File as FileIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export type FileUploadProps = {
  /** MIME or extension list, comma-separated. e.g. "video/mp4,.mov" */
  accept?: string;
  /** Max size in bytes. */
  maxSize?: number;
  /** Allow multi-selection. Defaults false. */
  multiple?: boolean;
  disabled?: boolean;
  label?: string;
  hint?: string;
  value?: File | File[] | null;
  onChange: (files: File | File[] | null) => void;
  className?: string;
};

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`;
}

function toArray(v: File | File[] | null | undefined): File[] {
  if (!v) return [];
  return Array.isArray(v) ? v : [v];
}

export function FileUpload({
  accept,
  maxSize,
  multiple = false,
  disabled,
  label = "选择或拖入文件",
  hint,
  value,
  onChange,
  className,
}: FileUploadProps) {
  const id = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const files = toArray(value);

  const handleFiles = useCallback(
    (list: FileList | null) => {
      if (!list || list.length === 0) return;
      setError(null);
      const picked = Array.from(list);
      if (maxSize) {
        const bad = picked.find((f) => f.size > maxSize);
        if (bad) {
          setError(`文件过大: ${bad.name}(超过 ${formatSize(maxSize)})`);
          return;
        }
      }
      if (multiple) onChange(picked);
      else onChange(picked[0] ?? null);
    },
    [maxSize, multiple, onChange],
  );

  const onDrop = (e: DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    setDragOver(false);
    if (disabled) return;
    handleFiles(e.dataTransfer.files);
  };

  const clearOne = (idx: number) => {
    if (multiple) {
      const next = files.filter((_, i) => i !== idx);
      onChange(next.length ? next : null);
    } else {
      onChange(null);
    }
    if (inputRef.current) inputRef.current.value = "";
  };

  return (
    <div className={cn("space-y-2", className)}>
      <label
        htmlFor={id}
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled) setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed border-border bg-card/50 px-6 py-8 text-center transition",
          "hover:border-primary/50 hover:bg-accent/40",
          dragOver && "border-primary bg-accent/60",
          disabled && "pointer-events-none opacity-60",
        )}
      >
        <UploadCloud className="h-6 w-6 text-muted-foreground" />
        <div className="text-sm font-medium text-foreground">{label}</div>
        {hint && <div className="text-xs text-muted-foreground">{hint}</div>}
        <input
          id={id}
          ref={inputRef}
          type="file"
          accept={accept}
          multiple={multiple}
          disabled={disabled}
          className="sr-only"
          onChange={(e) => handleFiles(e.target.files)}
        />
      </label>

      {error && <div className="text-xs text-destructive">{error}</div>}

      {files.length > 0 && (
        <ul className="space-y-1">
          {files.map((f, idx) => (
            <li
              key={`${f.name}-${idx}`}
              className="flex items-center justify-between rounded-md border border-border bg-card px-3 py-2 text-sm"
            >
              <div className="flex min-w-0 items-center gap-2">
                <FileIcon className="h-4 w-4 shrink-0 text-muted-foreground" />
                <span className="truncate">{f.name}</span>
                <span className="shrink-0 text-xs text-muted-foreground">{formatSize(f.size)}</span>
              </div>
              <Button
                type="button"
                size="icon"
                variant="ghost"
                onClick={() => clearOne(idx)}
                aria-label="移除文件"
              >
                <X className="h-4 w-4" />
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
