interface EmptyStateProps {
  title: string;
  message?: string;
  icon?: "inbox" | "search" | "chart" | "sim";
}

const icons = {
  inbox: (
    <svg viewBox="0 0 48 48" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" className="h-12 w-12">
      <rect x="6" y="10" width="36" height="28" rx="4" />
      <path d="M6 28h10l4 6h8l4-6h10" />
    </svg>
  ),
  search: (
    <svg viewBox="0 0 48 48" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" className="h-12 w-12">
      <circle cx="20" cy="20" r="12" /><path d="M28.5 28.5L42 42" />
    </svg>
  ),
  chart: (
    <svg viewBox="0 0 48 48" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" className="h-12 w-12">
      <path d="M6 6v36h36" /><path d="M14 28l8-10 8 8 10-14" />
    </svg>
  ),
  sim: (
    <svg viewBox="0 0 48 48" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" className="h-12 w-12">
      <circle cx="24" cy="24" r="6" />
      <path d="M24 4v8M24 36v8M4 24h8M36 24h8M8.69 8.69l5.66 5.66M33.66 33.66l5.66 5.66M8.69 39.31l5.66-5.66M33.66 14.34l5.66-5.66" />
    </svg>
  ),
};

export function EmptyState({ title, message, icon = "inbox" }: EmptyStateProps) {
  return (
    <div className="empty-state-wrap flex flex-col items-center justify-center px-6 py-16 text-center">
      <div className="empty-state-icon mb-5 flex h-20 w-20 items-center justify-center rounded-2xl">
        {icons[icon]}
      </div>
      <p className="text-lg font-semibold text-snow" style={{ fontFamily: "var(--font-heading)" }}>
        {title}
      </p>
      {message && (
        <p className="mt-2 max-w-sm text-sm leading-relaxed text-fog">{message}</p>
      )}
    </div>
  );
}
