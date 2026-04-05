type Tone = "good" | "bad" | "warn" | "info" | "neutral";

interface StatusBadgeProps {
  label: string;
  tone?: Tone;
  pulse?: boolean;
}

const toneMap: Record<Tone, { dot: string; bg: string; border: string; text: string }> = {
  good:    { dot: "#34d399", bg: "rgba(52,211,153,0.1)",  border: "rgba(52,211,153,0.25)",  text: "#6ee7b7" },
  bad:     { dot: "#f87171", bg: "rgba(248,113,113,0.1)", border: "rgba(248,113,113,0.25)", text: "#fca5a5" },
  warn:    { dot: "#fbbf24", bg: "rgba(251,191,36,0.1)",  border: "rgba(251,191,36,0.25)",  text: "#fde68a" },
  info:    { dot: "#38bdf8", bg: "rgba(56,189,248,0.1)",  border: "rgba(56,189,248,0.25)",  text: "#7dd3fc" },
  neutral: { dot: "#5a6f85", bg: "rgba(90,111,133,0.1)",  border: "rgba(90,111,133,0.25)",  text: "#a8b8cc" },
};

export function StatusBadge({ label, tone = "neutral", pulse = false }: StatusBadgeProps) {
  const c = toneMap[tone];
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[10px] font-semibold tracking-[0.12em] uppercase"
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
