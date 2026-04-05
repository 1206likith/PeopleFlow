import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  normalizeExecutableBenchmarks,
  normalizeExperimentArtifactDetail,
  normalizeExperimentArtifactCatalog,
  normalizeExperimentArtifactSummary,
  normalizeExperimentBatch,
  normalizeExperimentJobDetail,
  normalizeExperimentJobSummary,
  normalizeExperimentExecutionResult,
  normalizePublicationBundleDetail,
} from "@/lib/api/adapters";
import {
  buildExperimentArtifactDownloadUrl,
  buildPublicationBundleDownloadUrl,
  createPublicationBundle,
  getExperimentArtifactRecord,
  getExperimentJob,
  getPublicationBundleDetail,
  getExperimentArtifactCatalog,
  listExperimentArtifactRecords,
  listExperimentJobs,
  listExecutableBenchmarks,
  runResearchAblation,
  runResearchCalibration,
  runResearchBenchmark,
  runResearchExperiment,
  runResearchOptimization,
} from "@/lib/api/experiments";
import { listSimulationBatches, startBatchSimulation } from "@/lib/api/simulation";
import { useWorkspaceStore } from "@/lib/state/workspaceStore";

type ResearchMode = "single" | "ablation" | "benchmark" | "calibration" | "optimization" | "bundle";

const DEFAULT_CALIBRATION_CONFIG_PATH = "research/experiments/calibration.json";
const DEFAULT_OPTIMIZATION_CONFIG_PATH = "research/experiments/optimization.json";
const DEFAULT_BUNDLE_CONFIG_PATH = "research/experiments/batches/paper_baseline_suite.json";

const RESEARCH_MODE_OPTIONS: Array<{ id: ResearchMode; label: string; helper: string }> = [
  { id: "single", label: "Single Run", helper: "One reproducible run with optional validation." },
  { id: "ablation", label: "Ablation", helper: "Toggle core subsystems to measure contribution." },
  { id: "benchmark", label: "Benchmark", helper: "Execute named literature-style validation scenarios." },
  { id: "calibration", label: "Calibration", helper: "Search parameter ranges against validation targets." },
  { id: "optimization", label: "Optimization", helper: "Run multi-trial tuning for best composite score." },
  { id: "bundle", label: "Bundle", helper: "Assemble publication-ready research artifacts." },
];

function formatTimestamp(value?: string) {
  if (!value) {
    return "Not recorded";
  }
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

function formatErrorMessage(error: unknown, fallback: string) {
  if (error instanceof Error && error.message.trim().length > 0) {
    return error.message;
  }
  if (typeof error === "string" && error.trim().length > 0) {
    return error;
  }
  return fallback;
}

function summarizeObject(
  payload: Record<string, unknown>,
  limit = 6,
): Array<{ key: string; value: string }> {
  return Object.entries(payload)
    .slice(0, limit)
    .map(([key, value]) => {
      if (Array.isArray(value)) {
        return { key, value: `${value.length} items` };
      }
      if (value && typeof value === "object") {
        return { key, value: `${Object.keys(value as Record<string, unknown>).length} fields` };
      }
      return { key, value: String(value) };
    })
    .filter((entry) => entry.value.trim().length > 0);
}

export function ExperimentsPage() {
  const activeFloorPlanId = useWorkspaceStore((state) => state.activeFloorPlanId);
  const [runs, setRuns] = useState(10);
  const [agentBase, setAgentBase] = useState(240);
  const [panicBase, setPanicBase] = useState(0.4);
  const [seedStart, setSeedStart] = useState(100);
  const [researchMode, setResearchMode] = useState<ResearchMode>("single");
  const [experimentName, setExperimentName] = useState("research-baseline");
  const [validationEnabled, setValidationEnabled] = useState(true);
  const [selectedBenchmark, setSelectedBenchmark] = useState("corridor");
  const [calibrationConfigPath, setCalibrationConfigPath] = useState(DEFAULT_CALIBRATION_CONFIG_PATH);
  const [optimizationConfigPath, setOptimizationConfigPath] = useState(DEFAULT_OPTIMIZATION_CONFIG_PATH);
  const [bundleConfigPath, setBundleConfigPath] = useState(DEFAULT_BUNDLE_CONFIG_PATH);
  const [copyRunOutputs, setCopyRunOutputs] = useState(true);
  const [activeJobId, setActiveJobId] = useState("");
  const [selectedArtifactId, setSelectedArtifactId] = useState("");
  const [selectedBundleId, setSelectedBundleId] = useState("");
  const completedRefreshRef = useRef("");

  const batchesQuery = useQuery({
    queryKey: ["experiments", "batches"],
    queryFn: ({ signal }) => listSimulationBatches({ limit: 24 }, signal),
    refetchInterval: 8_000,
  });

  const artifactCatalogQuery = useQuery({
    queryKey: ["experiments", "artifact-catalog"],
    queryFn: ({ signal }) => getExperimentArtifactCatalog(signal),
    refetchInterval: 12_000,
  });

  const artifactRecordsQuery = useQuery({
    queryKey: ["experiments", "artifact-records"],
    queryFn: ({ signal }) => listExperimentArtifactRecords(signal),
    refetchInterval: 12_000,
  });

  const benchmarkCatalogQuery = useQuery({
    queryKey: ["experiments", "benchmark-catalog"],
    queryFn: ({ signal }) => listExecutableBenchmarks(signal),
    staleTime: 60_000,
  });

  const jobListQuery = useQuery({
    queryKey: ["experiments", "jobs"],
    queryFn: ({ signal }) => listExperimentJobs({ limit: 10 }, signal),
    refetchInterval: 6_000,
  });

  const activeJobQuery = useQuery({
    queryKey: ["experiments", "jobs", activeJobId],
    queryFn: ({ signal }) => getExperimentJob(activeJobId, signal),
    enabled: Boolean(activeJobId),
    refetchInterval: (query) => {
      const root = (query.state.data ?? {}) as Record<string, unknown>;
      const status = String(root.status ?? "").toLowerCase();
      return status === "queued" || status === "running" ? 3_000 : false;
    },
  });

  const artifactDetailQuery = useQuery({
    queryKey: ["experiments", "artifact-record", selectedArtifactId],
    queryFn: ({ signal }) => getExperimentArtifactRecord(selectedArtifactId, signal),
    enabled: Boolean(selectedArtifactId),
  });

  const bundleDetailQuery = useQuery({
    queryKey: ["experiments", "publication-bundle", selectedBundleId],
    queryFn: ({ signal }) => getPublicationBundleDetail(selectedBundleId, signal),
    enabled: Boolean(selectedBundleId),
  });

  const refreshAll = () => {
    batchesQuery.refetch();
    artifactCatalogQuery.refetch();
    artifactRecordsQuery.refetch();
    benchmarkCatalogQuery.refetch();
    jobListQuery.refetch();
    if (activeJobId) {
      activeJobQuery.refetch();
    }
    if (selectedArtifactId) {
      artifactDetailQuery.refetch();
    }
    if (selectedBundleId) {
      bundleDetailQuery.refetch();
    }
  };

  const batchMutation = useMutation({
    mutationFn: () =>
      startBatchSimulation({
        config: {
          floor_plan_id: activeFloorPlanId || undefined,
          num_agents: agentBase,
          emergency_type: "fire",
          panic_level: panicBase,
        },
        runs,
        seed_start: seedStart,
        seed_step: 1,
      }),
    onSuccess: refreshAll,
  });

  const researchMutation = useMutation({
    mutationFn: async () => {
      const baseConfig = {
        name: experimentName.trim() || "research-baseline",
        floor_plan_id: activeFloorPlanId || undefined,
        num_agents: agentBase,
        emergency_type: "fire",
        seed: seedStart,
        metadata: {
          launched_from: "frontend_dashboard",
          research_mode: researchMode,
          panic_baseline: panicBase,
        },
      };

      if (researchMode === "single") {
        return runResearchExperiment({
          config: baseConfig,
          validate: validationEnabled,
        });
      }

      if (researchMode === "ablation") {
        return runResearchAblation({
          base_config: baseConfig,
          validate: validationEnabled,
          background: true,
        });
      }

      if (researchMode === "benchmark") {
        return runResearchBenchmark(selectedBenchmark, {
          num_agents: selectedBenchmarkDetails?.defaultNumAgents ?? agentBase,
          background: true,
        });
      }

      if (researchMode === "calibration") {
        return runResearchCalibration({
          base_config: baseConfig,
          calibration_config_path: calibrationConfigPath.trim() || DEFAULT_CALIBRATION_CONFIG_PATH,
          background: true,
        });
      }

      if (researchMode === "optimization") {
        return runResearchOptimization({
          base_config: baseConfig,
          optimization_config_path: optimizationConfigPath.trim() || DEFAULT_OPTIMIZATION_CONFIG_PATH,
          background: true,
        });
      }

      return createPublicationBundle({
        batch_config_path: bundleConfigPath.trim() || DEFAULT_BUNDLE_CONFIG_PATH,
        validate: validationEnabled,
        copy_run_outputs: copyRunOutputs,
        background: true,
      });
    },
    onSuccess: (payload) => {
      const submittedJobId = typeof payload.job_id === "string" ? payload.job_id : "";
      if (submittedJobId) {
        setActiveJobId(submittedJobId);
      }
      refreshAll();
    },
  });

  const batches = useMemo(
    () => (batchesQuery.data?.batches ?? []).map(normalizeExperimentBatch),
    [batchesQuery.data?.batches],
  );

  const artifactCatalog = useMemo(
    () => normalizeExperimentArtifactCatalog(artifactCatalogQuery.data ?? {}),
    [artifactCatalogQuery.data],
  );

  const artifactRecords = useMemo(() => {
    const root = (artifactRecordsQuery.data ?? {}) as Record<string, unknown>;
    const rows = Array.isArray(root.artifacts) ? root.artifacts : [];
    return rows.map(normalizeExperimentArtifactSummary).filter((artifact) => artifact.artifactId.length > 0);
  }, [artifactRecordsQuery.data]);

  const executableBenchmarks = useMemo(
    () => normalizeExecutableBenchmarks(benchmarkCatalogQuery.data ?? {}),
    [benchmarkCatalogQuery.data],
  );

  const recentJobs = useMemo(() => {
    const root = (jobListQuery.data ?? {}) as Record<string, unknown>;
    const rows = Array.isArray(root.jobs) ? root.jobs : [];
    return rows.map(normalizeExperimentJobSummary).filter((job) => job.jobId.length > 0);
  }, [jobListQuery.data]);

  const activeJob = useMemo(
    () => (activeJobQuery.data ? normalizeExperimentJobDetail(activeJobQuery.data) : null),
    [activeJobQuery.data],
  );

  const selectedArtifact = useMemo(
    () => (artifactDetailQuery.data ? normalizeExperimentArtifactDetail(artifactDetailQuery.data) : null),
    [artifactDetailQuery.data],
  );

  const selectedBundle = useMemo(
    () => (bundleDetailQuery.data ? normalizePublicationBundleDetail(bundleDetailQuery.data) : null),
    [bundleDetailQuery.data],
  );

  const selectedBenchmarkDetails = useMemo(
    () => executableBenchmarks.find((benchmark) => benchmark.name === selectedBenchmark) ?? executableBenchmarks[0] ?? null,
    [executableBenchmarks, selectedBenchmark],
  );

  const selectedMode = useMemo(
    () => RESEARCH_MODE_OPTIONS.find((option) => option.id === researchMode) ?? RESEARCH_MODE_OPTIONS[0],
    [researchMode],
  );

  const latestExecution = useMemo(() => {
    if (activeJob?.result) {
      return normalizeExperimentExecutionResult(activeJob.result);
    }
    if (researchMutation.data && typeof researchMutation.data.job_id !== "string") {
      return normalizeExperimentExecutionResult(researchMutation.data);
    }
    return null;
  }, [activeJob?.result, researchMutation.data]);

  const completion = useMemo(() => {
    if (!batches.length) {
      return 0;
    }
    const ratio = batches.reduce((sum, batch) => sum + batch.completionPercent, 0) / batches.length;
    return Math.round(ratio);
  }, [batches]);

  const comparison = useMemo(
    () =>
      [...batches]
        .filter((batch) => typeof batch.bestEvacTime === "number")
        .sort((a, b) => Number(a.bestEvacTime) - Number(b.bestEvacTime))
        .slice(0, 3),
    [batches],
  );

  const researchActionLabel = useMemo(() => {
    if (researchMode === "single") return "Run research experiment";
    if (researchMode === "ablation") return "Run ablation suite";
    if (researchMode === "benchmark") return `Run ${selectedBenchmarkDetails?.name ?? "benchmark"}`;
    if (researchMode === "calibration") return "Run calibration search";
    if (researchMode === "optimization") return "Run optimization search";
    return "Build publication bundle";
  }, [researchMode, selectedBenchmarkDetails?.name]);

  const researchPendingLabel = useMemo(() => {
    if (researchMode === "single") return "Running single experiment...";
    if (researchMode === "ablation") return "Launching ablation suite...";
    if (researchMode === "benchmark") return `Launching ${selectedBenchmarkDetails?.name ?? "benchmark"}...`;
    if (researchMode === "calibration") return "Launching calibration...";
    if (researchMode === "optimization") return "Launching optimization...";
    return "Building publication bundle...";
  }, [researchMode, selectedBenchmarkDetails?.name]);

  const validationControlMessage =
    researchMode === "calibration" || researchMode === "optimization"
      ? "Calibration and optimization score every candidate against backend validation targets automatically."
      : "Run validation when the selected workflow supports it";

  const researchErrorMessage = researchMutation.error
    ? formatErrorMessage(researchMutation.error, "Research workflow failed.")
    : "";

  const researchStatusMessage = researchMutation.isPending
    ? "Submitting research workflow..."
    : researchErrorMessage
      ? researchErrorMessage
    : activeJob?.status === "queued"
      ? `${activeJob.title}: queued in the background.`
      : activeJob?.status === "running"
        ? `${activeJob.title}: running in the background.`
        : activeJob?.status === "failed"
          ? `${activeJob.title}: ${activeJob.error ?? activeJob.detail}`
          : latestExecution
            ? `${latestExecution.title}: ${latestExecution.detail}`
            : "No research workflow launched in this session.";

  useEffect(() => {
    if (!activeJobId && recentJobs.length > 0) {
      setActiveJobId(recentJobs[0].jobId);
    }
  }, [activeJobId, recentJobs]);

  useEffect(() => {
    if (!selectedArtifactId && artifactRecords.length > 0) {
      setSelectedArtifactId(artifactRecords[0].artifactId);
    }
  }, [selectedArtifactId, artifactRecords]);

  useEffect(() => {
    if (!selectedBundleId && artifactCatalog.publicationBundles.length > 0) {
      setSelectedBundleId(artifactCatalog.publicationBundles[0].bundleId);
    }
  }, [selectedBundleId, artifactCatalog.publicationBundles]);

  useEffect(() => {
    if (!activeJob || (activeJob.status !== "completed" && activeJob.status !== "failed")) {
      return;
    }
    const refreshKey = `${activeJob.jobId}:${activeJob.status}:${activeJob.updatedAt ?? ""}`;
    if (completedRefreshRef.current === refreshKey) {
      return;
    }
    completedRefreshRef.current = refreshKey;
    refreshAll();
  }, [activeJob, activeJobId]);

  return (
    <div className="experiments-page">
      <header className="experiments-header p-6">
        <div>
          <p className="experiments-kicker">Experiments</p>
          <h1>Research Execution Console</h1>
          <p className="mt-3 max-w-3xl">
            Coordinate fast operational batches and publication-grade research workflows from one surface. The page now tracks canonical
            experiment artifacts, benchmark runs, and publication bundles alongside the existing batch runner.
          </p>
        </div>
      </header>

      <section className="experiments-layout">
        <aside className="experiments-config">
          <h3 className="section-title">Simulation batches</h3>

          <label>
            Active floor plan <span>{activeFloorPlanId || "none"}</span>
          </label>
          <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-300">
            {activeFloorPlanId || "Select or upload a floor plan in Designer to tie research runs to geometry."}
          </div>

          <label>
            Runs <span>{runs}</span>
          </label>
          <input type="range" min={2} max={60} value={runs} onChange={(event) => setRuns(Number(event.target.value))} />

          <label>
            Base agent count <span>{agentBase}</span>
          </label>
          <input type="range" min={50} max={2000} step={10} value={agentBase} onChange={(event) => setAgentBase(Number(event.target.value))} />

          <label>
            Panic baseline <span>{panicBase.toFixed(2)}</span>
          </label>
          <input type="range" min={0.05} max={1} step={0.01} value={panicBase} onChange={(event) => setPanicBase(Number(event.target.value))} />

          <label>
            Seed start <span>{seedStart}</span>
          </label>
          <input className="input" type="number" value={seedStart} onChange={(event) => setSeedStart(Number(event.target.value))} />

          <button type="button" className="btn-primary mt-4" onClick={() => batchMutation.mutate()} disabled={batchMutation.isPending}>
            {batchMutation.isPending ? "Launching batch..." : "Run experiment batch"}
          </button>

          {batchMutation.error && <p className="mt-3 text-sm text-rose-300">Failed to launch batch. Check backend status and try again.</p>}
          {batchesQuery.error && <p className="mt-3 text-sm text-rose-300">Failed to fetch experiment batches.</p>}

          <div className="experiments-progress-wrap">
            <svg viewBox="0 0 120 120" className="experiments-progress-ring">
              <circle cx="60" cy="60" r="48" className="ring-track" />
              <circle cx="60" cy="60" r="48" className="ring-fill" style={{ strokeDashoffset: 302 - (302 * completion) / 100 }} />
            </svg>
            <div className="experiments-progress-text">{completion}%</div>
          </div>

          <div className="mt-8 rounded-3xl border border-white/10 bg-black/20 p-5">
            <div className="flex items-center justify-between">
              <h3 className="section-title">Research execution</h3>
              <span className="theme-fixed-pill">{researchMode}</span>
            </div>

            <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-3">
              {RESEARCH_MODE_OPTIONS.map((option) => (
                <button
                  key={option.id}
                  type="button"
                  className={researchMode === option.id ? "btn-primary" : "btn-secondary"}
                  onClick={() => setResearchMode(option.id)}
                >
                  {option.label}
                </button>
              ))}
            </div>

            <div className="mt-4 rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
              <p className="text-xs uppercase tracking-[0.24em] text-slate-400">{selectedMode.label}</p>
              <p className="mt-2 text-sm text-slate-300">{selectedMode.helper}</p>
            </div>

            <label className="mt-4 block">
              Experiment name <span>{experimentName}</span>
            </label>
            <input className="input mt-2" type="text" value={experimentName} onChange={(event) => setExperimentName(event.target.value)} />

            {researchMode === "benchmark" && (
              <>
                <label className="mt-4 block">
                  Benchmark <span>{selectedBenchmarkDetails?.name ?? "none"}</span>
                </label>
                <select className="input mt-2" value={selectedBenchmark} onChange={(event) => setSelectedBenchmark(event.target.value)}>
                  {executableBenchmarks.length ? (
                    executableBenchmarks.map((benchmark) => (
                      <option key={benchmark.name} value={benchmark.name}>
                        {benchmark.name}
                      </option>
                    ))
                  ) : (
                    <option value="corridor">corridor</option>
                  )}
                </select>
                <p className="mt-2 text-sm text-slate-400">
                  {selectedBenchmarkDetails?.description ?? "Benchmarks are loaded from the backend research execution catalog."}
                </p>
                <p className="mt-2 text-xs text-slate-500">
                  Benchmarks use the backend-recommended population size of {selectedBenchmarkDetails?.defaultNumAgents ?? agentBase} agents so
                  live validation stays closer to the authored research scenario.
                </p>
              </>
            )}

            {researchMode === "calibration" && (
              <>
                <label className="mt-4 block">
                  Calibration config <span>repo path</span>
                </label>
                <input
                  className="input mt-2"
                  type="text"
                  value={calibrationConfigPath}
                  onChange={(event) => setCalibrationConfigPath(event.target.value)}
                />
                <p className="mt-2 text-sm text-slate-400">
                  Use a checked-in calibration config so searches remain reproducible across researchers and CI.
                </p>
              </>
            )}

            {researchMode === "optimization" && (
              <>
                <label className="mt-4 block">
                  Optimization config <span>repo path</span>
                </label>
                <input
                  className="input mt-2"
                  type="text"
                  value={optimizationConfigPath}
                  onChange={(event) => setOptimizationConfigPath(event.target.value)}
                />
                <p className="mt-2 text-sm text-slate-400">
                  Optimization uses the backend search method and trial budget defined in the selected config file.
                </p>
              </>
            )}

            {researchMode === "bundle" && (
              <>
                <label className="mt-4 block">
                  Paper bundle config <span>repo path</span>
                </label>
                <input className="input mt-2" type="text" value={bundleConfigPath} onChange={(event) => setBundleConfigPath(event.target.value)} />
                <label className="mt-4 flex items-center gap-3 text-sm text-slate-300">
                  <input type="checkbox" checked={copyRunOutputs} onChange={(event) => setCopyRunOutputs(event.target.checked)} />
                  Copy raw run outputs into the publication bundle
                </label>
              </>
            )}

            {researchMode === "calibration" || researchMode === "optimization" ? (
              <div className="mt-4 rounded-2xl border border-cyan-400/20 bg-cyan-400/5 px-4 py-3 text-sm text-slate-300">
                {validationControlMessage}
              </div>
            ) : (
              <label className="mt-4 flex items-center gap-3 text-sm text-slate-300">
                <input type="checkbox" checked={validationEnabled} onChange={(event) => setValidationEnabled(event.target.checked)} />
                {validationControlMessage}
              </label>
            )}

            <button
              type="button"
              className="btn-primary mt-4 w-full"
              onClick={() => researchMutation.mutate()}
              disabled={researchMutation.isPending}
            >
              {researchMutation.isPending ? researchPendingLabel : researchActionLabel}
            </button>

            {researchMutation.error && (
              <p className="mt-3 text-sm text-rose-300">{researchErrorMessage}</p>
            )}
          </div>
        </aside>

        <main className="experiments-results">
          <div className="grid gap-4 md:grid-cols-4">
            {[
              { label: "Run Records", value: artifactCatalog.runCount },
              { label: "Artifacts", value: artifactCatalog.artifactCount },
              { label: "Suites", value: artifactCatalog.suiteManifestCount },
              { label: "Bundles", value: artifactCatalog.publicationBundleCount },
            ].map((card) => (
              <div key={card.label} className="rounded-3xl border border-white/10 bg-white/5 p-4">
                <p className="text-xs uppercase tracking-[0.24em] text-slate-400">{card.label}</p>
                <strong className="mt-3 block font-mono text-3xl text-cyan-200">{card.value}</strong>
              </div>
            ))}
          </div>

          <div className="mt-6 grid gap-6 xl:grid-cols-[1.3fr_0.9fr]">
            <section className="rounded-3xl border border-white/10 bg-white/5 p-5">
              <div className="flex items-center justify-between">
                <h3 className="section-title">Batch history</h3>
                <span className="theme-fixed-pill">{batches.length} batches</span>
              </div>

              <div className="experiments-table">
                {(batches.length
                  ? batches
                  : [{ id: "No batch yet", status: "standby", runs: 0, completedRuns: 0, completionPercent: 0 }]).map((batch, index) => (
                  <motion.article
                    key={`${String(batch.id)}-${index}`}
                    initial={{ opacity: 0, x: 24 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.04, duration: 0.18 }}
                  >
                    <div className="min-w-0 pr-4">
                      <p className="break-all text-sm font-semibold text-white">{String(batch.id)}</p>
                      <span className="text-xs text-slate-400">
                        {String(batch.status)} | {batch.completedRuns}/{batch.runs} runs
                      </span>
                    </div>
                    <strong className="shrink-0 font-mono text-cyan-200">{batch.completionPercent}%</strong>
                  </motion.article>
                ))}
              </div>

              {comparison.length > 0 && (
                <div className="experiments-compare-split">
                  {comparison.map((batch, index) => (
                    <motion.div key={batch.id} initial={{ opacity: 0, x: index === 0 ? -28 : 28 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.26 }}>
                      <h4 className="text-base font-semibold text-white">{index === 0 ? "Top Batch" : index === 1 ? "Runner-Up" : "Third Place"}</h4>
                      <p className="mt-2 text-sm text-slate-300">{batch.winningPolicy ?? "Policy not reported"}</p>
                      <strong className="mt-3 block font-mono text-cyan-200">
                        {typeof batch.bestEvacTime === "number" ? `Best ${Math.round(batch.bestEvacTime)}s` : "No timing data"}
                      </strong>
                    </motion.div>
                  ))}
                </div>
              )}
            </section>

            <section className="rounded-3xl border border-white/10 bg-white/5 p-5">
              <div className="flex items-center justify-between">
                <h3 className="section-title">Research artifacts</h3>
                <span className="theme-fixed-pill">{artifactCatalog.latestSuiteType ?? "catalog"}</span>
              </div>

              <div className="mt-4 rounded-2xl border border-cyan-400/20 bg-cyan-400/5 p-4">
                <p className="text-xs uppercase tracking-[0.24em] text-cyan-200">Latest execution</p>
                <h4 className="mt-3 text-lg font-semibold text-white">{latestExecution?.title ?? "Research pipeline idle"}</h4>
                <p className="mt-2 text-sm text-slate-300">{researchStatusMessage}</p>
              </div>

              <div className="mt-4 rounded-2xl border border-white/10 bg-black/20 p-4">
                <div className="flex items-center justify-between">
                  <h4 className="text-base font-semibold text-white">Recent research jobs</h4>
                  <span className="text-xs text-slate-400">{recentJobs.length} tracked</span>
                </div>
                {jobListQuery.error && <p className="mt-3 text-xs text-rose-300">Background job feed unavailable.</p>}
                <div className="mt-3 space-y-3">
                  {(recentJobs.length
                    ? recentJobs.slice(0, 4)
                    : [{ jobId: "none", title: "No background jobs yet", detail: "Long-running research runs will appear here.", status: "idle" }]).map((job) => (
                    <button
                      key={job.jobId}
                      type="button"
                      className={`w-full rounded-2xl border px-4 py-3 text-left transition-colors ${job.jobId === activeJobId ? "border-cyan-300/40 bg-cyan-400/10" : "border-white/10 bg-white/5"}`}
                      onClick={() => job.jobId !== "none" && setActiveJobId(job.jobId)}
                    >
                      <div className="flex items-center justify-between gap-4">
                        <p className="text-sm font-semibold text-white">{job.title}</p>
                        <span className="text-[11px] uppercase tracking-[0.16em] text-cyan-200">{job.status}</span>
                      </div>
                      <p className="mt-2 text-xs text-slate-400">{job.detail}</p>
                      {job.jobId !== "none" && <p className="mt-2 font-mono text-[11px] text-slate-500">{job.jobId}</p>}
                    </button>
                  ))}
                </div>
                {activeJob && (
                  <div className="mt-3 rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
                    <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Selected job</p>
                    <p className="mt-2 text-sm font-semibold text-white">{activeJob.title}</p>
                    <p className="mt-1 text-xs text-slate-400">
                      {activeJob.jobId} | {activeJob.status} | {activeJob.requestedBy ?? "unknown actor"}
                    </p>
                    {activeJob.error && <p className="mt-2 text-xs text-rose-300">{activeJob.error}</p>}
                  </div>
                )}
              </div>

              <div className="mt-4 rounded-2xl border border-white/10 bg-black/20 p-4">
                <div className="flex items-center justify-between">
                  <h4 className="text-base font-semibold text-white">Artifact browser</h4>
                  <span className="text-xs text-slate-400">{artifactRecords.length} indexed</span>
                </div>
                {artifactRecordsQuery.error && <p className="mt-3 text-xs text-rose-300">Artifact record listing unavailable.</p>}
                <div className="mt-3 grid gap-3 xl:grid-cols-[0.92fr_1.08fr]">
                  <div className="space-y-3">
                    {(artifactRecords.length
                      ? artifactRecords.slice(0, 6)
                      : [
                          {
                            artifactId: "none",
                            artifactKind: "artifact",
                            artifactType: "unknown",
                            title: "No indexed artifacts yet",
                            detail: "Run a research workflow to populate downloadable records.",
                          },
                        ]).map((artifact) => (
                      <button
                        key={artifact.artifactId}
                        type="button"
                        className={`w-full rounded-2xl border px-4 py-3 text-left transition-colors ${
                          artifact.artifactId === selectedArtifactId ? "border-cyan-300/40 bg-cyan-400/10" : "border-white/10 bg-white/5"
                        }`}
                        onClick={() => artifact.artifactId !== "none" && setSelectedArtifactId(artifact.artifactId)}
                      >
                        <div className="flex items-center justify-between gap-4">
                          <p className="text-sm font-semibold text-white">{artifact.title}</p>
                          <span className="text-[11px] uppercase tracking-[0.16em] text-cyan-200">{artifact.artifactKind}</span>
                        </div>
                        <p className="mt-2 text-xs text-slate-400">{artifact.detail}</p>
                        {artifact.artifactId !== "none" && <p className="mt-2 font-mono text-[11px] text-slate-500">{artifact.artifactId}</p>}
                      </button>
                    ))}
                  </div>

                  <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                    {artifactDetailQuery.isLoading && selectedArtifactId ? (
                      <p className="text-sm text-slate-300">Loading artifact detail...</p>
                    ) : selectedArtifact ? (
                      <>
                        <div className="flex items-start justify-between gap-4">
                          <div>
                            <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Selected artifact</p>
                            <h5 className="mt-2 text-lg font-semibold text-white">{selectedArtifact.title}</h5>
                            <p className="mt-2 text-sm text-slate-300">{selectedArtifact.detail}</p>
                          </div>
                          <span className="theme-fixed-pill">{selectedArtifact.artifactType}</span>
                        </div>

                        <div className="mt-4 grid gap-3 md:grid-cols-2">
                          {[
                            { label: "Generated", value: formatTimestamp(selectedArtifact.generatedAt) },
                            { label: "Validation", value: selectedArtifact.validationStatus ?? "not reported" },
                            { label: "Output path", value: selectedArtifact.outputPath ?? "not recorded" },
                            { label: "Manifest path", value: selectedArtifact.manifestPath ?? "not recorded" },
                          ].map((row) => (
                            <div key={row.label} className="rounded-2xl border border-white/10 bg-black/20 px-4 py-3">
                              <p className="text-[11px] uppercase tracking-[0.16em] text-slate-500">{row.label}</p>
                              <p className="mt-2 text-sm text-slate-200">{row.value}</p>
                            </div>
                          ))}
                        </div>

                        <div className="mt-4 flex flex-wrap gap-3">
                          <a
                            className="btn-secondary"
                            href={buildExperimentArtifactDownloadUrl(selectedArtifact.artifactId, "artifact")}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Download artifact
                          </a>
                          <a
                            className="btn-secondary"
                            href={buildExperimentArtifactDownloadUrl(selectedArtifact.artifactId, "manifest")}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Download manifest
                          </a>
                        </div>

                        <div className="mt-4 grid gap-3 md:grid-cols-3">
                          {[
                            { title: "Metadata", rows: summarizeObject(selectedArtifact.metadata) },
                            { title: "Provenance", rows: summarizeObject(selectedArtifact.provenance) },
                            { title: "Validation", rows: summarizeObject(selectedArtifact.validation) },
                          ].map((group) => (
                            <div key={group.title} className="rounded-2xl border border-white/10 bg-black/20 px-4 py-3">
                              <p className="text-[11px] uppercase tracking-[0.16em] text-slate-500">{group.title}</p>
                              <div className="mt-3 space-y-2">
                                {(group.rows.length ? group.rows : [{ key: "status", value: "Not recorded" }]).map((row) => (
                                  <div key={`${group.title}-${row.key}`} className="flex items-center justify-between gap-3 text-xs">
                                    <span className="text-slate-500">{row.key}</span>
                                    <span className="text-right text-slate-200">{row.value}</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          ))}
                        </div>
                      </>
                    ) : (
                      <p className="text-sm text-slate-300">Select an artifact to inspect its canonical manifest, provenance, and download links.</p>
                    )}
                  </div>
                </div>
              </div>

              <div className="mt-4 rounded-2xl border border-white/10 bg-black/20 p-4">
                <div className="flex items-center justify-between">
                  <h4 className="text-base font-semibold text-white">Publication bundles</h4>
                  <span className="text-xs text-slate-400">{artifactCatalog.publicationBundles.length} indexed</span>
                </div>
                <div className="mt-3 grid gap-3 xl:grid-cols-[0.92fr_1.08fr]">
                  <div className="space-y-3">
                    {(artifactCatalog.publicationBundles.length
                      ? artifactCatalog.publicationBundles.slice(0, 4)
                      : [{ bundleId: "none", suiteName: "No bundle yet", runCount: 0, validationEnabled: false }]).map((bundle) => (
                      <button
                        key={bundle.bundleId}
                        type="button"
                        className={`w-full rounded-2xl border px-4 py-3 text-left transition-colors ${
                          bundle.bundleId === selectedBundleId ? "border-cyan-300/40 bg-cyan-400/10" : "border-white/10 bg-white/5"
                        }`}
                        onClick={() => bundle.bundleId !== "none" && setSelectedBundleId(bundle.bundleId)}
                      >
                        <p className="text-sm font-semibold text-white">{bundle.suiteName}</p>
                        <p className="mt-1 text-xs text-slate-400">
                          {bundle.bundleId} | {bundle.runCount} runs | {bundle.validationEnabled ? "validated" : "not validated"}
                        </p>
                      </button>
                    ))}
                  </div>

                  <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                    {bundleDetailQuery.isLoading && selectedBundleId ? (
                      <p className="text-sm text-slate-300">Loading bundle detail...</p>
                    ) : selectedBundle ? (
                      <>
                        <div className="flex items-start justify-between gap-4">
                          <div>
                            <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Selected bundle</p>
                            <h5 className="mt-2 text-lg font-semibold text-white">{selectedBundle.suiteName}</h5>
                            <p className="mt-2 text-sm text-slate-300">
                              {selectedBundle.bundleId} | {selectedBundle.runCount} runs | {selectedBundle.validationEnabled ? "validated" : "not validated"}
                            </p>
                          </div>
                          <span className="theme-fixed-pill">bundle</span>
                        </div>

                        <div className="mt-4 grid gap-3 md:grid-cols-2">
                          {[
                            { label: "Generated", value: formatTimestamp(selectedBundle.generatedAt) },
                            { label: "Manifest path", value: selectedBundle.manifestPath ?? "not recorded" },
                            { label: "Seeds", value: selectedBundle.seeds.length ? selectedBundle.seeds.join(", ") : "not recorded" },
                            { label: "Variants", value: selectedBundle.variants.length ? selectedBundle.variants.join(", ") : "not recorded" },
                          ].map((row) => (
                            <div key={row.label} className="rounded-2xl border border-white/10 bg-black/20 px-4 py-3">
                              <p className="text-[11px] uppercase tracking-[0.16em] text-slate-500">{row.label}</p>
                              <p className="mt-2 text-sm text-slate-200">{row.value}</p>
                            </div>
                          ))}
                        </div>

                        <div className="mt-4 flex flex-wrap gap-3">
                          <a
                            className="btn-secondary"
                            href={buildPublicationBundleDownloadUrl(selectedBundle.bundleId)}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Download manifest
                          </a>
                        </div>

                        <div className="mt-4 rounded-2xl border border-white/10 bg-black/20 px-4 py-3">
                          <p className="text-[11px] uppercase tracking-[0.16em] text-slate-500">Bundle metadata</p>
                          <div className="mt-3 space-y-2">
                            {(summarizeObject(selectedBundle.metadata).length
                              ? summarizeObject(selectedBundle.metadata)
                              : [{ key: "status", value: "Not recorded" }]).map((row) => (
                              <div key={`bundle-${row.key}`} className="flex items-center justify-between gap-3 text-xs">
                                <span className="text-slate-500">{row.key}</span>
                                <span className="text-right text-slate-200">{row.value}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      </>
                    ) : (
                      <p className="text-sm text-slate-300">Select a publication bundle to inspect its manifest-backed metadata.</p>
                    )}
                  </div>
                </div>
              </div>

              <div className="mt-4 rounded-2xl border border-white/10 bg-black/20 p-4">
                <h4 className="text-base font-semibold text-white">Benchmarks</h4>
                <div className="mt-3 space-y-3">
                  {(executableBenchmarks.length
                    ? executableBenchmarks
                    : [{ name: "corridor", description: "Benchmark catalog unavailable.", defaultNumAgents: agentBase }]).map((benchmark) => (
                    <div key={benchmark.name} className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
                      <div className="flex items-center justify-between gap-4">
                        <p className="text-sm font-semibold text-white">{benchmark.name}</p>
                        <span className="text-xs text-cyan-200">{benchmark.defaultNumAgents} agents</span>
                      </div>
                      <p className="mt-2 text-xs text-slate-400">{benchmark.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            </section>
          </div>
        </main>
      </section>
    </div>
  );
}
