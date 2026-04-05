interface MetricCardProps {
  label: string;
  value: string | number;
  helper?: string;
  accent?: "violet" | "sky" | "emerald" | "rose" | "amber";
}

const accentMap = {
  violet:  { bar: "#14b8a6", glow: "rgba(20,184,166,0.2)",  text: "#99f6e4" },
  sky:     { bar: "#38bdf8", glow: "rgba(56,189,248,0.2)",   text: "#7dd3fc" },
  emerald: { bar: "#34d399", glow: "rgba(52,211,153,0.2)",   text: "#6ee7b7" },
  rose:    { bar: "#f87171", glow: "rgba(248,113,113,0.2)",  text: "#fca5a5" },
  amber:   { bar: "#fbbf24", glow: "rgba(251,191,36,0.2)",   text: "#fde68a" },
};

export function MetricCard({ label, value, helper, accent = "violet" }: MetricCardProps) {
  const colors = accentMap[accent];
  return (
    <article
      className="relative overflow-hidden rounded-2xl p-5 transition-all duration-300 hover:-translate-y-0.5"
      style={{
        background: "rgba(10, 18, 31, 0.72)",
        border: "1px solid rgba(191,219,254,0.1)",
        backdropFilter: "blur(16px)",
        WebkitBackdropFilter: "blur(16px)",
        boxShadow: `0 4px 18px rgba(0,0,0,0.18), inset 0 1px 0 rgba(255,255,255,0.04)`,
      }}
    >
      <div className="absolute inset-x-0 top-0 h-[2px] opacity-80" style={{ background: `linear-gradient(90deg, ${colors.bar}, transparent)` }} />

      {/* Colored top accent bar */}
      {/* Background glow */}
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
        <p className="relative z-10 mt-1.5 text-[11px] text-fog">{helper}</p>
      )}
    </article>
  );
}
