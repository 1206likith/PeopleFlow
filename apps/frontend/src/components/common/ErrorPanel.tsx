interface ErrorPanelProps {
  error: unknown;
  title?: string;
}

export function ErrorPanel({ error, title = "Something went wrong" }: ErrorPanelProps) {
  const message =
    error instanceof Error
      ? error.message
      : typeof error === "string"
      ? error
      : "An unexpected error occurred.";

  return (
    <div
      className="flex items-start gap-3 rounded-[18px] p-4"
      role="alert"
      aria-live="assertive"
      style={{
        background: "color-mix(in srgb, var(--danger) 14%, transparent)",
        border: "1px solid color-mix(in srgb, var(--danger) 32%, transparent)",
        boxShadow: "0 16px 35px rgba(0,0,0,0.14)",
      }}
    >
      {/* Icon */}
      <div
        className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg"
        style={{ background: "color-mix(in srgb, var(--danger) 18%, transparent)" }}
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="color-mix(in srgb, var(--danger) 60%, white)" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4" aria-hidden="true">
          <circle cx="12" cy="12" r="10" />
          <path d="M12 8v4M12 16h.01" />
        </svg>
      </div>

      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold" style={{ color: "color-mix(in srgb, var(--danger) 48%, white)" }}>{title}</p>
        <p className="mt-0.5 text-xs leading-relaxed" style={{ color: "color-mix(in srgb, var(--danger) 35%, white)" }}>
          {message}
        </p>
      </div>
    </div>
  );
}
