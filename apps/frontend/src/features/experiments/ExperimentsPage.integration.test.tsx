import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import userEvent from "@testing-library/user-event";
import { screen, waitFor } from "@testing-library/react";
import { ExperimentsPage } from "@/features/experiments/ExperimentsPage";
import { renderWithProviders } from "@/test/renderWithProviders";
import { mswServer } from "@/test/mswServer";
import { useWorkspaceStore } from "@/lib/state/workspaceStore";
import { API_BASE_URL } from "@/lib/api/client";

const API = API_BASE_URL;

describe("ExperimentsPage integration", () => {
  it("launches a batch and refreshes history", async () => {
    let launchedBatch = false;
    useWorkspaceStore.setState({ activeFloorPlanId: "fp-experiment" });

    mswServer.use(
      http.get(`${API}/api/v2/simulations/batches`, async () =>
        HttpResponse.json({
          meta: { version: "v2", mode: "demo", path: "/api/v2/simulations/batches", correlation_id: "e1", timestamp: new Date().toISOString() },
          data: launchedBatch
            ? {
                batches: [{ batch_id: "batch-1", status: "completed", runs: 4, completed_runs: 4, metrics: { best_evac_time: 82, winning_policy: "Guided Evacuation" } }],
                total: 1,
              }
            : { batches: [], total: 0 },
        }),
      ),
      http.get(`${API}/api/v2/experiments/artifacts`, async () =>
        HttpResponse.json({
          meta: { version: "v2", mode: "demo", path: "/api/v2/experiments/artifacts", correlation_id: "e2", timestamp: new Date().toISOString() },
          data: {
            catalog_version: "peopleflow-experiment-artifact-catalog-v1",
            experiments_output: {
              run_index: { result_count: launchedBatch ? 1 : 0 },
              artifact_index: { artifact_count: launchedBatch ? 1 : 0 },
              suite_manifests: [],
            },
            publication_bundles: { artifact_count: 0, artifacts: [] },
          },
        }),
      ),
      http.get(`${API}/api/v2/experiments/artifacts/records`, async () =>
        HttpResponse.json({
          meta: { version: "v2", mode: "demo", path: "/api/v2/experiments/artifacts/records", correlation_id: "e2a", timestamp: new Date().toISOString() },
          data: { artifact_count: 0, artifacts: [] },
        }),
      ),
      http.get(`${API}/api/v2/experiments/jobs`, async () =>
        HttpResponse.json({
          meta: { version: "v2", mode: "demo", path: "/api/v2/experiments/jobs", correlation_id: "e2b", timestamp: new Date().toISOString() },
          data: { job_count: 0, active_count: 0, jobs: [] },
        }),
      ),
      http.get(`${API}/api/v2/experiments/benchmarks`, async () =>
        HttpResponse.json({
          meta: { version: "v2", mode: "demo", path: "/api/v2/experiments/benchmarks", correlation_id: "e3", timestamp: new Date().toISOString() },
          data: {
            catalog_version: "peopleflow-executable-benchmarks-v1",
            benchmarks: [
              {
                name: "corridor",
                description: "Single-exit corridor throughput benchmark for bottleneck and flow behavior.",
                default_num_agents: 60,
              },
            ],
          },
        }),
      ),
      http.post(`${API}/api/v2/simulations/start-batch`, async () => {
        launchedBatch = true;
        return HttpResponse.json({
          meta: { version: "v2", mode: "demo", path: "/api/v2/simulations/start-batch", correlation_id: "e4", timestamp: new Date().toISOString() },
          data: { batch_id: "batch-1", status: "queued", runs: 4 },
        });
      }),
    );

    renderWithProviders(<ExperimentsPage />);

    await userEvent.click(await screen.findByRole("button", { name: /Run experiment batch/i }));

    await waitFor(() => {
      expect(screen.getByText(/batch-1/i)).toBeInTheDocument();
      expect(screen.getByText(/Guided Evacuation/i)).toBeInTheDocument();
    });
  });

  it("runs a research benchmark and surfaces artifact status", async () => {
    let launchedBenchmark = false;
    useWorkspaceStore.setState({ activeFloorPlanId: "fp-research" });

    mswServer.use(
      http.get(`${API}/api/v2/simulations/batches`, async () =>
        HttpResponse.json({
          meta: { version: "v2", mode: "demo", path: "/api/v2/simulations/batches", correlation_id: "e5", timestamp: new Date().toISOString() },
          data: { batches: [], total: 0 },
        }),
      ),
      http.get(`${API}/api/v2/experiments/benchmarks`, async () =>
        HttpResponse.json({
          meta: { version: "v2", mode: "demo", path: "/api/v2/experiments/benchmarks", correlation_id: "e6", timestamp: new Date().toISOString() },
          data: {
            catalog_version: "peopleflow-executable-benchmarks-v1",
            benchmarks: [
              {
                name: "corridor",
                description: "Single-exit corridor throughput benchmark for bottleneck and flow behavior.",
                default_num_agents: 60,
              },
              {
                name: "multi_exit",
                description: "Multi-exit room benchmark for load balancing and exit utilization behavior.",
                default_num_agents: 80,
              },
            ],
          },
        }),
      ),
      http.get(`${API}/api/v2/experiments/artifacts`, async () =>
        HttpResponse.json({
          meta: { version: "v2", mode: "demo", path: "/api/v2/experiments/artifacts", correlation_id: "e7", timestamp: new Date().toISOString() },
          data: {
            catalog_version: "peopleflow-experiment-artifact-catalog-v1",
            experiments_output: {
              run_index: { result_count: launchedBenchmark ? 3 : 0 },
              artifact_index: { artifact_count: launchedBenchmark ? 5 : 0 },
              suite_manifests: launchedBenchmark ? [{ suite_type: "benchmark" }] : [],
            },
            publication_bundles: {
              artifact_count: launchedBenchmark ? 1 : 0,
              artifacts: launchedBenchmark
                ? [
                    {
                      bundle_id: "paper-suite-1",
                      artifact_id: "publication_bundle:paper-suite-1",
                      generated_at: new Date().toISOString(),
                      metadata: {
                        bundle_id: "paper-suite-1",
                        suite_name: "Paper Suite Alpha",
                        run_count: 4,
                        validation_enabled: true,
                      },
                    },
                  ]
                : [],
            },
          },
        }),
      ),
      http.get(`${API}/api/v2/experiments/artifacts/records`, async () =>
        HttpResponse.json({
          meta: { version: "v2", mode: "demo", path: "/api/v2/experiments/artifacts/records", correlation_id: "e7c", timestamp: new Date().toISOString() },
          data: launchedBenchmark
            ? {
                artifact_count: 1,
                artifacts: [
                  {
                    artifact_id: "benchmark:corridor",
                    artifact_kind: "benchmark",
                    artifact_type: "json",
                    generated_at: new Date().toISOString(),
                    output_path: "research/experiments/output/benchmark_corridor.json",
                    metadata: { benchmark_name: "corridor" },
                    provenance: { generated_at: new Date().toISOString() },
                    validation: { status: "passed", overall_score: 0.91 },
                    detail_path: "/api/v2/experiments/artifacts/records/benchmark:corridor",
                    download_path: "/api/v2/experiments/artifacts/records/benchmark:corridor/download",
                  },
                ],
              }
            : { artifact_count: 0, artifacts: [] },
        }),
      ),
      http.get(`${API}/api/v2/experiments/artifacts/records/benchmark%3Acorridor`, async () =>
        HttpResponse.json({
          meta: {
            version: "v2",
            mode: "demo",
            path: "/api/v2/experiments/artifacts/records/benchmark:corridor",
            correlation_id: "e7d",
            timestamp: new Date().toISOString(),
          },
          data: {
            artifact_id: "benchmark:corridor",
            summary: {
              artifact_id: "benchmark:corridor",
              artifact_kind: "benchmark",
              artifact_type: "json",
              generated_at: new Date().toISOString(),
              output_path: "research/experiments/output/benchmark_corridor.json",
              metadata: { benchmark_name: "corridor" },
              provenance: { generated_at: new Date().toISOString() },
              validation: { status: "passed", overall_score: 0.91 },
              detail_path: "/api/v2/experiments/artifacts/records/benchmark:corridor",
            },
            record: {
              artifact_id: "benchmark:corridor",
              artifact_kind: "benchmark",
              artifact_type: "json",
              generated_at: new Date().toISOString(),
              output_path: "research/experiments/output/benchmark_corridor.json",
              metadata: { benchmark_name: "corridor", simulation_id: "sim-benchmark" },
              provenance: { generated_at: new Date().toISOString(), engine_version: "peopleflow-sim-v1" },
              validation: { summary: { status: "passed", overall_score: 0.91 } },
            },
            manifest_path: "research/experiments/output/benchmark_corridor.manifest.json",
          },
        }),
      ),
      http.get(`${API}/api/v2/experiments/jobs`, async () =>
        HttpResponse.json({
          meta: { version: "v2", mode: "demo", path: "/api/v2/experiments/jobs", correlation_id: "e7a", timestamp: new Date().toISOString() },
          data: launchedBenchmark
            ? {
                job_count: 1,
                active_count: 0,
                jobs: [
                  {
                    job_id: "expjob-benchmark",
                    execution_type: "benchmark",
                    status: "completed",
                    requested_by: "web-dashboard",
                    background: true,
                    input_summary: { benchmark: "corridor", num_agents: 60 },
                    result_summary: {
                      title: "Benchmark corridor",
                      detail: "Single-exit corridor throughput benchmark for bottleneck and flow behavior.",
                    },
                    submitted_at: new Date().toISOString(),
                    updated_at: new Date().toISOString(),
                  },
                ],
              }
            : { job_count: 0, active_count: 0, jobs: [] },
        }),
      ),
      http.get(`${API}/api/v2/experiments/jobs/expjob-benchmark`, async () =>
        HttpResponse.json({
          meta: { version: "v2", mode: "demo", path: "/api/v2/experiments/jobs/expjob-benchmark", correlation_id: "e7b", timestamp: new Date().toISOString() },
          data: {
            job_id: "expjob-benchmark",
            execution_type: "benchmark",
            status: "completed",
            requested_by: "web-dashboard",
            background: true,
            input_summary: { benchmark: "corridor", num_agents: 60 },
            result_summary: {
              title: "Benchmark corridor",
              detail: "Single-exit corridor throughput benchmark for bottleneck and flow behavior.",
            },
            submitted_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            completed_at: new Date().toISOString(),
            result: {
              execution_type: "benchmark",
              benchmark: "corridor",
              description: "Single-exit corridor throughput benchmark for bottleneck and flow behavior.",
              result: { name: "corridor", metrics: { total_evacuation_time: 61 } },
            },
          },
        }),
      ),
      http.get(`${API}/api/v2/experiments/publication-bundles/paper-suite-1`, async () =>
        HttpResponse.json({
          meta: {
            version: "v2",
            mode: "demo",
            path: "/api/v2/experiments/publication-bundles/paper-suite-1",
            correlation_id: "e7e",
            timestamp: new Date().toISOString(),
          },
          data: {
            bundle_id: "paper-suite-1",
            record: {
              bundle_id: "paper-suite-1",
              artifact_id: "publication_bundle:paper-suite-1",
              artifact_kind: "publication_bundle",
              generated_at: new Date().toISOString(),
              metadata: {
                bundle_id: "paper-suite-1",
                suite_name: "Paper Suite Alpha",
                run_count: 4,
                validation_enabled: true,
              },
            },
            manifest: {
              suite_name: "Paper Suite Alpha",
              seeds: [11, 12],
              variants: ["baseline"],
            },
            manifest_path: "artifacts/paper_results/paper-suite-1/metadata/publication_manifest.json",
            download_path: "/api/v2/experiments/publication-bundles/paper-suite-1/download",
          },
        }),
      ),
      http.post(`${API}/api/v2/experiments/benchmarks/corridor/run`, async () => {
        launchedBenchmark = true;
        return HttpResponse.json({
          meta: { version: "v2", mode: "demo", path: "/api/v2/experiments/benchmarks/corridor/run", correlation_id: "e8", timestamp: new Date().toISOString() },
          data: {
            job_id: "expjob-benchmark",
            execution_type: "benchmark",
            status: "queued",
            background: true,
            input_summary: { benchmark: "corridor", num_agents: 60 },
          },
        }, { status: 202 });
      }),
    );

    renderWithProviders(<ExperimentsPage />);

    await userEvent.click(await screen.findByRole("button", { name: "Benchmark" }));
    await userEvent.click(await screen.findByRole("button", { name: /Run corridor/i }));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /Benchmark corridor/i, level: 4 })).toBeInTheDocument();
      expect(screen.getAllByText(/Paper Suite Alpha/i).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/paper-suite-1/i).length).toBeGreaterThan(0);
      expect(screen.getAllByRole("button", { name: /Benchmark corridor/i }).length).toBeGreaterThan(0);
      expect(screen.getByRole("link", { name: /Download artifact/i })).toBeInTheDocument();
      expect(screen.getAllByText(/expjob-benchmark/i).length).toBeGreaterThan(0);
    });
  });

  it("runs a calibration workflow with a repo-backed config path", async () => {
    let launchedCalibration = false;
    useWorkspaceStore.setState({ activeFloorPlanId: "fp-calibration" });

    mswServer.use(
      http.get(`${API}/api/v2/simulations/batches`, async () =>
        HttpResponse.json({
          meta: { version: "v2", mode: "demo", path: "/api/v2/simulations/batches", correlation_id: "e9", timestamp: new Date().toISOString() },
          data: { batches: [], total: 0 },
        }),
      ),
      http.get(`${API}/api/v2/experiments/benchmarks`, async () =>
        HttpResponse.json({
          meta: { version: "v2", mode: "demo", path: "/api/v2/experiments/benchmarks", correlation_id: "e10", timestamp: new Date().toISOString() },
          data: {
            catalog_version: "peopleflow-executable-benchmarks-v1",
            benchmarks: [
              {
                name: "corridor",
                description: "Single-exit corridor throughput benchmark for bottleneck and flow behavior.",
                default_num_agents: 60,
              },
            ],
          },
        }),
      ),
      http.get(`${API}/api/v2/experiments/artifacts`, async () =>
        HttpResponse.json({
          meta: { version: "v2", mode: "demo", path: "/api/v2/experiments/artifacts", correlation_id: "e11", timestamp: new Date().toISOString() },
          data: {
            catalog_version: "peopleflow-experiment-artifact-catalog-v1",
            experiments_output: {
              run_index: { result_count: launchedCalibration ? 6 : 0 },
              artifact_index: { artifact_count: launchedCalibration ? 8 : 0 },
              suite_manifests: launchedCalibration ? [{ suite_type: "calibration" }] : [],
            },
            publication_bundles: { artifact_count: 0, artifacts: [] },
          },
        }),
      ),
      http.get(`${API}/api/v2/experiments/artifacts/records`, async () =>
        HttpResponse.json({
          meta: { version: "v2", mode: "demo", path: "/api/v2/experiments/artifacts/records", correlation_id: "e11c", timestamp: new Date().toISOString() },
          data: { artifact_count: 0, artifacts: [] },
        }),
      ),
      http.get(`${API}/api/v2/experiments/jobs`, async () =>
        HttpResponse.json({
          meta: { version: "v2", mode: "demo", path: "/api/v2/experiments/jobs", correlation_id: "e11a", timestamp: new Date().toISOString() },
          data: launchedCalibration
            ? {
                job_count: 1,
                active_count: 0,
                jobs: [
                  {
                    job_id: "expjob-calibration",
                    execution_type: "calibration",
                    status: "completed",
                    requested_by: "web-dashboard",
                    background: true,
                    input_summary: { name: "research-baseline", calibration_config_path: "research/experiments/calibration.json" },
                    result_summary: { title: "Calibration Suite", detail: "Best calib-trial-02 (0.91)" },
                    submitted_at: new Date().toISOString(),
                    updated_at: new Date().toISOString(),
                  },
                ],
              }
            : { job_count: 0, active_count: 0, jobs: [] },
        }),
      ),
      http.get(`${API}/api/v2/experiments/jobs/expjob-calibration`, async () =>
        HttpResponse.json({
          meta: { version: "v2", mode: "demo", path: "/api/v2/experiments/jobs/expjob-calibration", correlation_id: "e11b", timestamp: new Date().toISOString() },
          data: {
            job_id: "expjob-calibration",
            execution_type: "calibration",
            status: "completed",
            requested_by: "web-dashboard",
            background: true,
            input_summary: { name: "research-baseline", calibration_config_path: "research/experiments/calibration.json" },
            result_summary: { title: "Calibration Suite", detail: "Best calib-trial-02 (0.91)" },
            submitted_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            completed_at: new Date().toISOString(),
            result: {
              execution_type: "calibration",
              summary: {
                suite_type: "calibration",
                source_config_path: "research/experiments/calibration.json",
                best: { name: "calib-trial-02", score: 0.91 },
              },
            },
          },
        }),
      ),
      http.post(`${API}/api/v2/experiments/calibrations`, async () => {
        launchedCalibration = true;
        return HttpResponse.json({
          meta: { version: "v2", mode: "demo", path: "/api/v2/experiments/calibrations", correlation_id: "e12", timestamp: new Date().toISOString() },
          data: {
            job_id: "expjob-calibration",
            execution_type: "calibration",
            status: "queued",
            background: true,
            input_summary: { name: "research-baseline", calibration_config_path: "research/experiments/calibration.json" },
          },
        }, { status: 202 });
      }),
    );

    renderWithProviders(<ExperimentsPage />);

    await userEvent.click(await screen.findByRole("button", { name: "Calibration" }));
    await userEvent.click(await screen.findByRole("button", { name: /Run calibration search/i }));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /Calibration Suite/i, level: 4 })).toBeInTheDocument();
      expect(screen.getAllByText(/Best calib-trial-02 \(0.91\)/i).length).toBeGreaterThan(0);
      expect(screen.getByText(/Calibration and optimization score every candidate/i)).toBeInTheDocument();
      expect(screen.getAllByText(/expjob-calibration/i).length).toBeGreaterThan(0);
    });
  });

  it("runs an optimization workflow with a repo-backed config path", async () => {
    let launchedOptimization = false;
    useWorkspaceStore.setState({ activeFloorPlanId: "fp-optimization" });

    mswServer.use(
      http.get(`${API}/api/v2/simulations/batches`, async () =>
        HttpResponse.json({
          meta: { version: "v2", mode: "demo", path: "/api/v2/simulations/batches", correlation_id: "e13", timestamp: new Date().toISOString() },
          data: { batches: [], total: 0 },
        }),
      ),
      http.get(`${API}/api/v2/experiments/benchmarks`, async () =>
        HttpResponse.json({
          meta: { version: "v2", mode: "demo", path: "/api/v2/experiments/benchmarks", correlation_id: "e14", timestamp: new Date().toISOString() },
          data: {
            catalog_version: "peopleflow-executable-benchmarks-v1",
            benchmarks: [
              {
                name: "corridor",
                description: "Single-exit corridor throughput benchmark for bottleneck and flow behavior.",
                default_num_agents: 60,
              },
            ],
          },
        }),
      ),
      http.get(`${API}/api/v2/experiments/artifacts`, async () =>
        HttpResponse.json({
          meta: { version: "v2", mode: "demo", path: "/api/v2/experiments/artifacts", correlation_id: "e15", timestamp: new Date().toISOString() },
          data: {
            catalog_version: "peopleflow-experiment-artifact-catalog-v1",
            experiments_output: {
              run_index: { result_count: launchedOptimization ? 9 : 0 },
              artifact_index: { artifact_count: launchedOptimization ? 12 : 0 },
              suite_manifests: launchedOptimization ? [{ suite_type: "optimization" }] : [],
            },
            publication_bundles: { artifact_count: 0, artifacts: [] },
          },
        }),
      ),
      http.get(`${API}/api/v2/experiments/artifacts/records`, async () =>
        HttpResponse.json({
          meta: { version: "v2", mode: "demo", path: "/api/v2/experiments/artifacts/records", correlation_id: "e15c", timestamp: new Date().toISOString() },
          data: { artifact_count: 0, artifacts: [] },
        }),
      ),
      http.get(`${API}/api/v2/experiments/jobs`, async () =>
        HttpResponse.json({
          meta: { version: "v2", mode: "demo", path: "/api/v2/experiments/jobs", correlation_id: "e15a", timestamp: new Date().toISOString() },
          data: launchedOptimization
            ? {
                job_count: 1,
                active_count: 0,
                jobs: [
                  {
                    job_id: "expjob-optimization",
                    execution_type: "optimization",
                    status: "completed",
                    requested_by: "web-dashboard",
                    background: true,
                    input_summary: { name: "research-baseline", optimization_config_path: "research/experiments/optimization.json" },
                    result_summary: { title: "Optimization Suite", detail: "Best opt-trial-07 (0.97)" },
                    submitted_at: new Date().toISOString(),
                    updated_at: new Date().toISOString(),
                  },
                ],
              }
            : { job_count: 0, active_count: 0, jobs: [] },
        }),
      ),
      http.get(`${API}/api/v2/experiments/jobs/expjob-optimization`, async () =>
        HttpResponse.json({
          meta: { version: "v2", mode: "demo", path: "/api/v2/experiments/jobs/expjob-optimization", correlation_id: "e15b", timestamp: new Date().toISOString() },
          data: {
            job_id: "expjob-optimization",
            execution_type: "optimization",
            status: "completed",
            requested_by: "web-dashboard",
            background: true,
            input_summary: { name: "research-baseline", optimization_config_path: "research/experiments/optimization.json" },
            result_summary: { title: "Optimization Suite", detail: "Best opt-trial-07 (0.97)" },
            submitted_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            completed_at: new Date().toISOString(),
            result: {
              execution_type: "optimization",
              summary: {
                suite_type: "optimization",
                source_config_path: "research/experiments/optimization.json",
                best: { name: "opt-trial-07", score: 0.97 },
              },
            },
          },
        }),
      ),
      http.post(`${API}/api/v2/experiments/optimizations`, async () => {
        launchedOptimization = true;
        return HttpResponse.json({
          meta: { version: "v2", mode: "demo", path: "/api/v2/experiments/optimizations", correlation_id: "e16", timestamp: new Date().toISOString() },
          data: {
            job_id: "expjob-optimization",
            execution_type: "optimization",
            status: "queued",
            background: true,
            input_summary: { name: "research-baseline", optimization_config_path: "research/experiments/optimization.json" },
          },
        }, { status: 202 });
      }),
    );

    renderWithProviders(<ExperimentsPage />);

    await userEvent.click(await screen.findByRole("button", { name: "Optimization" }));
    await userEvent.click(await screen.findByRole("button", { name: /Run optimization search/i }));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /Optimization Suite/i, level: 4 })).toBeInTheDocument();
      expect(screen.getAllByText(/Best opt-trial-07 \(0.97\)/i).length).toBeGreaterThan(0);
      expect(screen.getByDisplayValue(/research\/experiments\/optimization\.json/i)).toBeInTheDocument();
      expect(screen.getAllByText(/expjob-optimization/i).length).toBeGreaterThan(0);
    });
  });
});
