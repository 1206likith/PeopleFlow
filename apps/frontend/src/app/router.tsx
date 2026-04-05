import { Suspense, lazy } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { PageShell } from "@/components/layout/PageShell";
import { useSessionStore } from "@/lib/state/sessionStore";

const HomePage = lazy(() => import("@/features/home/HomePage").then((module) => ({ default: module.HomePage })));
const DesignerPage = lazy(() => import("@/features/designer/DesignerPage").then((module) => ({ default: module.DesignerPage })));
const SimulationHubPage = lazy(() => import("@/features/simulation/SimulationHubPage").then((module) => ({ default: module.SimulationHubPage })));
const AnalyticsHubPage = lazy(() => import("@/features/analytics/AnalyticsHubPage").then((module) => ({ default: module.AnalyticsHubPage })));
const ScenarioBuilderPage = lazy(() => import("@/features/scenarios/ScenarioBuilderPage").then((module) => ({ default: module.ScenarioBuilderPage })));
const OperationsPage = lazy(() => import("@/features/operations/OperationsPage").then((module) => ({ default: module.OperationsPage })));
const ExperimentsPage = lazy(() => import("@/features/experiments/ExperimentsPage").then((module) => ({ default: module.ExperimentsPage })));

const routeTransition = {
  initial: { opacity: 0, x: 24, scale: 0.985 },
  animate: { opacity: 1, x: 0, scale: 1 },
  exit: { opacity: 0, x: -18, scale: 0.96 },
  transition: { duration: 0.22, ease: [0.16, 1, 0.3, 1] as [number, number, number, number] },
};

export function AppRouter() {
  const location = useLocation();
  const reducedMotion = useSessionStore((state) => state.reducedMotion);
  const transition = reducedMotion
    ? {
        initial: { opacity: 0 },
        animate: { opacity: 1 },
        exit: { opacity: 0 },
        transition: { duration: 0.12, ease: "linear" as const },
      }
    : routeTransition;

  return (
    <PageShell>
      <AnimatePresence mode="wait">
        <motion.div
          key={location.pathname}
          initial={transition.initial}
          animate={transition.animate}
          exit={transition.exit}
          transition={transition.transition}
        >
          <Suspense
            fallback={(
              <div className="route-loading-shell">
                <div className="route-loading-spinner" />
                <p>Loading module...</p>
              </div>
            )}
          >
            <Routes location={location}>
              <Route path="/" element={<HomePage />} />

              <Route path="/designer" element={<DesignerPage />} />
              <Route path="/simulation" element={<SimulationHubPage />} />
              <Route path="/scenarios" element={<ScenarioBuilderPage />} />
              <Route path="/operations" element={<OperationsPage />} />

              <Route path="/dashboard" element={<HomePage />} />
              <Route path="/simulate" element={<SimulationHubPage />} />
              <Route path="/analytics" element={<AnalyticsHubPage />} />
              <Route path="/experiments" element={<ExperimentsPage />} />

              <Route path="/upload" element={<Navigate to="/designer" replace />} />
              <Route path="/design" element={<Navigate to="/designer" replace />} />

              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
        </motion.div>
      </AnimatePresence>
    </PageShell>
  );
}
