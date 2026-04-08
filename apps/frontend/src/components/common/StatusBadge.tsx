type Tone = "good" | "bad" | "warn" | "info" | "neutral";

interface StatusBadgeProps {
  label: string;
  tone?: Tone;
  pulse?: boolean;
}

const toneMap: Record<Tone, { dot: string; bg: string; border: string; text: string }> = {
  good:    { dot: "var(--success)", bg: "color-mix(in srgb, var(--success) 18%, transparent)", border: "color-mix(in srgb, var(--success) 35%, transparent)", text: "color-mix(in srgb, var(--success) 60%, white)" },
  bad:     { dot: "var(--danger)", bg: "color-mix(in srgb, var(--danger) 18%, transparent)", border: "color-mix(in srgb, var(--danger) 35%, transparent)", text: "color-mix(in srgb, var(--danger) 52%, white)" },
  warn:    { dot: "var(--warning)", bg: "color-mix(in srgb, var(--warning) 18%, transparent)", border: "color-mix(in srgb, var(--warning) 34%, transparent)", text: "color-mix(in srgb, var(--warning) 46%, white)" },
  info:    { dot: "var(--accent-2)", bg: "color-mix(in srgb, var(--accent-2) 18%, transparent)", border: "color-mix(in srgb, var(--accent-2) 34%, transparent)", text: "color-mix(in srgb, var(--accent-2) 52%, white)" },
  neutral: { dot: "var(--text-soft)", bg: "color-mix(in srgb, var(--text-soft) 18%, transparent)", border: "color-mix(in srgb, var(--text-soft) 28%, transparent)", text: "var(--text-muted)" },
};

export function StatusBadge({ label, tone = "neutral", pulse = false }: StatusBadgeProps) {
  const c = toneMap[tone];
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[10px] font-semibold tracking-[0.12em] uppercase"
      role="status"
      aria-live="polite"
      aria-label={`Status ${label}`}
      style={{
        background: `linear-gradient(135deg, rgba(255,255,255,0.03) 0%, ${c.bg} 100%)`,
        border: `1px solid ${c.border}`,
        color: c.text,
        boxShadow: `0 0 8px ${c.bg}`,
      }}
    >
      <span className="relative flex h-1.5 w-1.5 shrink-0">
        {pulse && (
          <span
            className="absolute inline-flex h-full w-full animate-ping rounded-full opacity-60"
            style={{ background: c.dot }}
          />
        )}
        <span className="relative inline-flex h-1.5 w-1.5 rounded-full" style={{ background: c.dot }} />
      </span>
      {label}
    </span>
  );
}
