import type { Page, Route } from "@playwright/test";

export interface MockApiState {
  adminKey: string;
  floorPlanId: string;
  simulationId: string;
  benchmarkJobId: string;
  uploaded: boolean;
  manualExitAdded: boolean;
  simulationStarted: boolean;
  benchmarkLaunched: boolean;
  batchStarted: boolean;
}

function envelope(path: string, data: unknown, status = 200) {
  return {
    status,
    contentType: "application/json",
    body: JSON.stringify({
      meta: {
        version: "v2",
        mode: "demo",
        path,
        correlation_id: `pw-${Math.random().toString(36).slice(2, 10)}`,
        timestamp: new Date().toISOString(),
      },
      data,
    }),
  };
}

function errorEnvelope(path: string, status: number, code: string, message: string) {
  return {
    status,
    contentType: "application/json",
    body: JSON.stringify({
      meta: {
        version: "v2",
        mode: "demo",
        path,
        correlation_id: `pw-${Math.random().toString(36).slice(2, 10)}`,
        timestamp: new Date().toISOString(),
      },
      error: {
        code,
        message,
        status_code: status,
        details: { path },
      },
    }),
  };
}

async function fulfillJson(route: Route, path: string, data: unknown, status = 200) {
  await route.fulfill(envelope(path, data, status));
}

export async function installPeopleFlowApiMocks(page: Page): Promise<MockApiState> {
  const state: MockApiState = {
    adminKey: "pw-admin-key",
    floorPlanId: "fp-e2e",
    simulationId: "sim-e2e",
    benchmarkJobId: "expjob-benchmark",
    uploaded: false,
    manualExitAdded: false,
    simulationStarted: false,
    benchmarkLaunched: false,
    batchStarted: false,
  };

  await page.route("**/api/v2/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    const method = request.method().toUpperCase();
    const headers = request.headers();

    if (path === "/api/v2/system/info" && method === "GET") {
      await fulfillJson(route, path, { service_version: "2.0.0", environment: "demo" });
      return;
    }

    if (path === "/api/v2/system/status" && method === "GET") {
      await fulfillJson(route, path, {
        status: "ok",
        database: "demo",
        unity_enabled: "available",
      });
      return;
    }

    if (path === "/api/v2/system/capabilities" && method === "GET") {
      await fulfillJson(route, path, {
        capabilities: [
          { id: "simulation.start", enabled: true },
          { id: "experiments.background", enabled: true },
        ],
      });
      return;
    }

    if (path === "/api/v2/simulations/" && method === "GET") {
      await fulfillJson(route, path, {
        simulations: state.simulationStarted
          ? [
              {
                id: state.simulationId,
                name: "Research Live Run",
                status: "running",
                emergency_type: "fire",
                num_agents: 240,
              },
            ]
          : [],
        total: state.simulationStarted ? 1 : 0,
      });
      return;
    }

    if (path === "/api/v2/simulations/upload" && method === "POST") {
      state.uploaded = true;
      await fulfillJson(route, path, {
        id: state.floorPlanId,
        building_name: "E2E Research Building",
        pipeline: "traditional",
        simulation_ready: true,
        processing_time_ms: 142,
        building_bounds: { min_x: 0, min_y: 0, max_x: 100, max_y: 100, width: 100, height: 100 },
        detected_walls: [
          { x1: 0, y1: 0, x2: 100, y2: 0, type: "boundary", length: 100 },
          { x1: 100, y1: 0, x2: 100, y2: 100, type: "boundary", length: 100 },
          { x1: 100, y1: 100, x2: 0, y2: 100, type: "boundary", length: 100 },
          { x1: 0, y1: 100, x2: 0, y2: 0, type: "boundary", length: 100 },
        ],
        boundaries: [
          { x1: 0, y1: 0, x2: 100, y2: 0, type: "boundary", length: 100 },
          { x1: 100, y1: 0, x2: 100, y2: 100, type: "boundary", length: 100 },
          { x1: 100, y1: 100, x2: 0, y2: 100, type: "boundary", length: 100 },
          { x1: 0, y1: 100, x2: 0, y2: 0, type: "boundary", length: 100 },
        ],
        exits: [{ id: "main-exit", name: "Main Exit", x: 50, y: 0, z: 0, width: 3, capacity: 120 }],
        quality_report: { simulation_ready: true, quality_score: 0.91, usable_exit_count: state.manualExitAdded ? 2 : 1 },
      });
      return;
    }

    if (path === `/api/v2/simulations/floor-plans/${state.floorPlanId}` && method === "GET") {
      await fulfillJson(route, path, {
        id: state.floorPlanId,
        building_name: "E2E Research Building",
        pipeline: "traditional",
        simulation_ready: true,
        processing_time_ms: 142,
        building_bounds: { min_x: 0, min_y: 0, max_x: 100, max_y: 100, width: 100, height: 100 },
        detected_walls: [
          { x1: 0, y1: 0, x2: 100, y2: 0, type: "boundary", length: 100 },
          { x1: 100, y1: 0, x2: 100, y2: 100, type: "boundary", length: 100 },
          { x1: 100, y1: 100, x2: 0, y2: 100, type: "boundary", length: 100 },
          { x1: 0, y1: 100, x2: 0, y2: 0, type: "boundary", length: 100 },
        ],
        boundaries: [
          { x1: 0, y1: 0, x2: 100, y2: 0, type: "boundary", length: 100 },
          { x1: 100, y1: 0, x2: 100, y2: 100, type: "boundary", length: 100 },
          { x1: 100, y1: 100, x2: 0, y2: 100, type: "boundary", length: 100 },
          { x1: 0, y1: 100, x2: 0, y2: 0, type: "boundary", length: 100 },
        ],
        exits: state.manualExitAdded
          ? [
              { id: "main-exit", name: "Main Exit", x: 50, y: 0, z: 0, width: 3, capacity: 120 },
              { id: "manual-exit-1", name: "Manual Exit 1", x: 30, y: 40, z: 40, width: 2, capacity: 100 },
            ]
          : [{ id: "main-exit", name: "Main Exit", x: 50, y: 0, z: 0, width: 3, capacity: 120 }],
        rooms: [{ name: "Main Hall", x: 10, y: 10, width: 80, height: 60 }],
        detected_obstacles: [{ x: 32, z: 44, width: 10, height: 6 }],
        quality_report: { simulation_ready: true, quality_score: 0.91, usable_exit_count: state.manualExitAdded ? 2 : 1 },
      });
      return;
    }

    if (path === `/api/v2/simulations/floor-plans/${state.floorPlanId}/pipeline` && method === "GET") {
      await fulfillJson(route, path, {
        pipeline: "traditional",
        processing_time_ms: 142,
        pipeline_steps: [
          { name: "upload", duration_ms: 20 },
          { name: "detect_geometry", duration_ms: 64 },
          { name: "validate", duration_ms: 58 },
        ],
      });
      return;
    }

    if (path === `/api/v2/simulations/floor-plans/${state.floorPlanId}/quality-report` && method === "GET") {
      await fulfillJson(route, path, {
        floor_plan_id: state.floorPlanId,
        quality_report: {
          simulation_ready: true,
          quality_score: 0.91,
          usable_exit_count: state.manualExitAdded ? 2 : 1,
          geometry_count: 4,
          room_count: 1,
          readiness_reasons: [],
          warnings: [],
        },
      });
      return;
    }

    if (path === `/api/v2/simulations/floor-plans/${state.floorPlanId}/exits` && method === "POST") {
      state.manualExitAdded = true;
      await fulfillJson(route, path, {
        floor_plan_id: state.floorPlanId,
        manual_exits: [
          { id: "main-exit", name: "Main Exit", x: 50, y: 0, z: 0, width: 3, capacity: 120 },
          { id: "manual-exit-1", name: "Manual Exit 1", x: 30, y: 40, z: 40, width: 2, capacity: 100 },
        ],
      });
      return;
    }

    if (path === "/api/v2/simulations/start" && method === "POST") {
      state.simulationStarted = true;
      await fulfillJson(route, path, {
        id: state.simulationId,
        status: "running",
        created_at: new Date().toISOString(),
      });
      return;
    }

    if (path === `/api/v2/simulations/${state.simulationId}/frames/latest` && method === "GET") {
      await fulfillJson(route, path, {
        simulation_id: state.simulationId,
        timestamp: 12,
        agents: [{ agent_id: 1, x: 14, y: 8.5, speed: 1.2, status: "moving" }],
        exits: [{ id: "main-exit", x: 50, y: 0, z: 0, width: 3, capacity: 120 }],
        stats: { flow_rate: 91, evacuated: 16, remaining: 224, density_peak: 0.44 },
      });
      return;
    }

    if (path === `/api/v2/simulations/${state.simulationId}/frames` && method === "GET") {
      await fulfillJson(route, path, {
        frames: [
          {
            simulation_id: state.simulationId,
            timestamp: 10,
            agents: [{ agent_id: 1, x: 12, y: 8, speed: 1.2, status: "moving" }],
            stats: { flow_rate: 88, evacuated: 9, remaining: 231, density_peak: 0.38 },
          },
          {
            simulation_id: state.simulationId,
            timestamp: 12,
            agents: [{ agent_id: 1, x: 14, y: 8.5, speed: 1.2, status: "moving" }],
            stats: { flow_rate: 91, evacuated: 16, remaining: 224, density_peak: 0.44 },
          },
        ],
        count: 2,
      });
      return;
    }

    if (path === `/api/v2/simulations/${state.simulationId}/summary` && method === "GET") {
      await fulfillJson(route, path, {
        simulation_id: state.simulationId,
        total_agents: 240,
        evacuated: 16,
        total_time: 87,
        final_stats: {
          throughput: 91,
          peak_density: 0.44,
          policy_winner: "Guided Evacuation",
          evac_time_ci95: "84-90s",
        },
      });
      return;
    }

    if (path === `/api/v2/simulations/${state.simulationId}/metrics` && method === "GET") {
      await fulfillJson(route, path, {
        simulation_id: state.simulationId,
        frame_count: 2,
        metrics: { policy_winner: "Guided Evacuation" },
      });
      return;
    }

    if (path === `/api/v2/simulations/${state.simulationId}/timeline` && method === "GET") {
      await fulfillJson(route, path, {
        points: [
          { timestamp: 10, evacuated: 9, flow_rate: 88, peak_density: 0.38 },
          { timestamp: 12, evacuated: 16, flow_rate: 91, peak_density: 0.44 },
        ],
        count: 2,
      });
      return;
    }

    if (path === `/api/v2/simulations/${state.simulationId}/exit-usage` && method === "GET") {
      await fulfillJson(route, path, {
        exit_usage: { "Guided Evacuation": 91, "Shortest Path": 77 },
        source: "summary",
      });
      return;
    }

    if (path === "/api/v2/simulations/batches" && method === "GET") {
      await fulfillJson(route, path, {
        batches: state.batchStarted
          ? [{ batch_id: "batch-smoke", status: "completed", runs: 3, completed_runs: 3, metrics: { best_evac_time: 82, winning_policy: "Guided Evacuation" } }]
          : [],
        total: state.batchStarted ? 1 : 0,
      });
      return;
    }

    if (path === "/api/v2/simulations/start-batch" && method === "POST") {
      if ((headers["x-admin-key"] ?? "") !== state.adminKey) {
        await route.fulfill(errorEnvelope(path, 401, "admin_key_missing", "Missing X-Admin-Key"));
        return;
      }
      state.batchStarted = true;
      await fulfillJson(route, path, { batch_id: "batch-smoke", status: "queued", runs: 3 });
      return;
    }

    if (path === "/api/v2/experiments/artifacts" && method === "GET") {
      await fulfillJson(route, path, {
        catalog_version: "peopleflow-experiment-artifact-catalog-v1",
        experiments_output: {
          run_index: { result_count: state.benchmarkLaunched ? 3 : 0 },
          artifact_index: { artifact_count: state.benchmarkLaunched ? 5 : 0 },
          suite_manifests: state.benchmarkLaunched ? [{ suite_type: "benchmark" }] : [],
        },
        publication_bundles: {
          artifact_count: state.benchmarkLaunched ? 1 : 0,
          artifacts: state.benchmarkLaunched
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
      });
      return;
    }

    if (path === "/api/v2/experiments/artifacts/records" && method === "GET") {
      await fulfillJson(route, path, {
        artifact_count: state.benchmarkLaunched ? 1 : 0,
        artifacts: state.benchmarkLaunched
          ? [
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
            ]
          : [],
      });
      return;
    }

    if (path === "/api/v2/experiments/artifacts/records/benchmark%3Acorridor" && method === "GET") {
      await fulfillJson(route, path, {
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
          metadata: { benchmark_name: "corridor", simulation_id: state.simulationId },
          provenance: { generated_at: new Date().toISOString(), engine_version: "peopleflow-sim-v1" },
          validation: { summary: { status: "passed", overall_score: 0.91 } },
        },
        manifest_path: "research/experiments/output/benchmark_corridor.manifest.json",
      });
      return;
    }

    if (path === "/api/v2/experiments/benchmarks" && method === "GET") {
      await fulfillJson(route, path, {
        catalog_version: "peopleflow-executable-benchmarks-v1",
        benchmarks: [
          {
            name: "corridor",
            description: "Single-exit corridor throughput benchmark for bottleneck and flow behavior.",
            default_num_agents: 60,
          },
        ],
      });
      return;
    }

    if (path === `/api/v2/experiments/benchmarks/corridor/run` && method === "POST") {
      state.benchmarkLaunched = true;
      await fulfillJson(route, path, {
        job_id: state.benchmarkJobId,
        execution_type: "benchmark",
        status: "queued",
        background: true,
        input_summary: { benchmark: "corridor", num_agents: 60 },
      }, 202);
      return;
    }

    if (path === "/api/v2/experiments/jobs" && method === "GET") {
      await fulfillJson(route, path, {
        job_count: state.benchmarkLaunched ? 1 : 0,
        active_count: 0,
        jobs: state.benchmarkLaunched
          ? [
              {
                job_id: state.benchmarkJobId,
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
            ]
          : [],
      });
      return;
    }

    if (path === `/api/v2/experiments/jobs/${state.benchmarkJobId}` && method === "GET") {
      await fulfillJson(route, path, {
        job_id: state.benchmarkJobId,
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
      });
      return;
    }

    if (path === "/api/v2/experiments/publication-bundles/paper-suite-1" && method === "GET") {
      await fulfillJson(route, path, {
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
          download_path: "/api/v2/experiments/publication-bundles/paper-suite-1/download",
          detail_path: "/api/v2/experiments/publication-bundles/paper-suite-1",
        },
        manifest: {
          suite_name: "Paper Suite Alpha",
          seeds: [11, 12],
          variants: ["baseline"],
        },
        manifest_path: "artifacts/paper_results/paper-suite-1/metadata/publication_manifest.json",
        download_path: "/api/v2/experiments/publication-bundles/paper-suite-1/download",
      });
      return;
    }

    await fulfillJson(route, path, {});
  });

  return state;
}
