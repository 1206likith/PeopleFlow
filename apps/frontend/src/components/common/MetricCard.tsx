interface MetricCardProps {
  label: string;
  value: string | number;
  helper?: string;
  accent?: "violet" | "sky" | "emerald" | "rose" | "amber";
}

const accentMap = {
  violet:  { bar: "var(--accent-3)", glow: "color-mix(in srgb, var(--accent-3) 28%, transparent)", text: "color-mix(in srgb, var(--accent-3) 58%, white)" },
  sky:     { bar: "var(--accent-2)", glow: "color-mix(in srgb, var(--accent-2) 28%, transparent)", text: "color-mix(in srgb, var(--accent-2) 55%, white)" },
  emerald: { bar: "var(--accent)", glow: "color-mix(in srgb, var(--accent) 26%, transparent)", text: "color-mix(in srgb, var(--accent) 56%, white)" },
  rose:    { bar: "var(--danger)", glow: "color-mix(in srgb, var(--danger) 26%, transparent)", text: "color-mix(in srgb, var(--danger) 52%, white)" },
  amber:   { bar: "var(--warning)", glow: "color-mix(in srgb, var(--warning) 24%, transparent)", text: "color-mix(in srgb, var(--warning) 42%, white)" },
};

export function MetricCard({ label, value, helper, accent = "violet" }: MetricCardProps) {
  const colors = accentMap[accent];
  return (
    <article
      className="relative overflow-hidden rounded-2xl p-5 transition-all duration-300 hover:-translate-y-0.5"
      aria-label={`${label} metric`}
      style={{
        background: "color-mix(in srgb, var(--bg-alt) 88%, white 12%)",
        border: "1px solid var(--border)",
        backdropFilter: "blur(16px)",
        WebkitBackdropFilter: "blur(16px)",
        boxShadow: "0 8px 24px rgba(0, 0, 0, 0.2), inset 0 1px 0 rgba(255,255,255,0.04)",
      }}
    >
      <div className="absolute inset-x-0 top-0 h-[2px] opacity-80" style={{ background: `linear-gradient(90deg, ${colors.bar}, transparent)` }} />

      {/* Colored top accent bar */}
      <div
        className="pointer-events-none absolute -right-4 -top-4 h-20 w-20 rounded-full opacity-30"
        style={{ background: colors.glow, filter: "blur(20px)" }}
      />

      <p className="label relative z-10">{label}</p>
      <p
        className="relative z-10 mt-3 text-[1.8rem] font-bold tracking-tight"
        style={{ fontFamily: "var(--font-heading)", color: colors.text }}
      >
        {value}
      </p>
      {helper && (
        <p className="relative z-10 mt-1.5 text-[11px]" style={{ color: "var(--text-soft)" }}>{helper}</p>
      )}
    </article>
  );
}
