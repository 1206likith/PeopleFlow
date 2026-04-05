interface JsonPanelProps {
  data: unknown;
  className?: string;
  maxHeightClassName?: string;
}

export function JsonPanel({ data, className = "", maxHeightClassName = "max-h-[260px]" }: JsonPanelProps) {
  return (
    <pre
      className={`mt-3 overflow-auto rounded-md bg-ink/70 p-3 text-xs text-mist/80 ${maxHeightClassName} ${className}`.trim()}
    >
      {JSON.stringify(data ?? {}, null, 2)}
    </pre>
  );
}
