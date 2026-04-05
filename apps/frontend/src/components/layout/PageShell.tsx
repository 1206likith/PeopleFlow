import { PropsWithChildren } from "react";
import { SideNav } from "@/components/layout/SideNav";
import { TopUtilityBar } from "@/components/layout/TopUtilityBar";

export function PageShell({ children }: PropsWithChildren) {
  return (
    <div className="app-shell">
      <div className="bg-orb bg-orb-1" aria-hidden="true" />
      <div className="bg-orb bg-orb-2" aria-hidden="true" />
      <div className="bg-orb bg-orb-3" aria-hidden="true" />

      <SideNav />

      <div className="main-content">
        <TopUtilityBar />
        <main className="page-body">
          {children}
        </main>
      </div>
    </div>
  );
}
