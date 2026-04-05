import clsx from "clsx";
import { NavLink } from "react-router-dom";

const NAV_ITEMS = [
  { to: "/", label: "Home" },
  { to: "/designer", label: "Building Designer" },
  { to: "/simulation", label: "Simulation Hub" },
  { to: "/analytics", label: "Analytics Hub" },
  { to: "/scenarios", label: "Scenario Builder" },
  { to: "/operations", label: "Operations Hub" },
];

export function TopNav() {
  return (
    <header className="sticky top-0 z-40 border-b border-white/10 bg-ink/85 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-3 px-4 py-3 sm:px-6 lg:px-8">
        <div className="mr-2 flex items-center gap-3">
          <span className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-cyan/20 text-sm font-semibold text-cyan">
            PF
          </span>
          <div>
            <p className="text-sm font-semibold tracking-wide text-white">PeopleFlow</p>
            <p className="text-[11px] uppercase tracking-[0.2em] text-mist/60">Frontend v1</p>
          </div>
        </div>

        <nav className="flex flex-wrap items-center gap-2">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                clsx(
                  "rounded-md px-3 py-2 text-sm transition",
                  isActive ? "bg-cyan/20 text-cyan" : "text-mist/80 hover:bg-white/10 hover:text-white",
                )
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </div>
    </header>
  );
}
