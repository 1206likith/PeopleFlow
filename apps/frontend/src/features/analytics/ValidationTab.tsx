import { useMutation, useQuery } from "@tanstack/react-query";
import {
  getReplayDeathZones,
  getReplayDensityEvolution,
  getReplayTimeline,
  getValidationBenchmarks,
  validateSimulation,
} from "@/lib/api/analytics";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorPanel } from "@/components/common/ErrorPanel";
import { JsonPanel } from "@/components/common/JsonPanel";

interface ValidationTabProps {
  simulationId: string;
}

export function ValidationTab({ simulationId }: ValidationTabProps) {
  const benchmarksQuery = useQuery({
    queryKey: ["analytics", "benchmarks"],
    queryFn: ({ signal }) => getValidationBenchmarks(signal),
  });

  const validateMutation = useMutation({
    mutationFn: () => validateSimulation(simulationId),
  });

  const replayTimelineQuery = useQuery({
    queryKey: ["analytics", "replay-timeline", simulationId],
    queryFn: ({ signal }) => getReplayTimeline(simulationId, signal),
    enabled: Boolean(simulationId),
  });

  const replayDensityQuery = useQuery({
    queryKey: ["analytics", "replay-density", simulationId],
    queryFn: ({ signal }) => getReplayDensityEvolution(simulationId, signal),
    enabled: Boolean(simulationId),
  });

  const replayDeathZonesQuery = useQuery({
    queryKey: ["analytics", "replay-death-zones", simulationId],
    queryFn: ({ signal }) => getReplayDeathZones(simulationId, signal),
    enabled: Boolean(simulationId),
  });

  if (!simulationId) {
    return <EmptyState title="Select simulation" message="Choose a simulation before validation and replay analysis." />;
  }

  return (
    <div className="space-y-4">
      <section className="panel">
        <h3 className="section-title">Benchmarks</h3>
        {benchmarksQuery.isLoading && <p className="mt-3 text-sm text-mist/70">Loading benchmark list...</p>}
        {benchmarksQuery.error && <ErrorPanel error={benchmarksQuery.error} />}
        {benchmarksQuery.data && <JsonPanel data={benchmarksQuery.data} maxHeightClassName="max-h-[220px]" />}
        <button type="button" className="btn-primary mt-4" onClick={() => validateMutation.mutate()} disabled={validateMutation.isPending}>
          Validate Simulation
        </button>
        {validateMutation.error && <p className="mt-2 text-sm text-rose-300">{String((validateMutation.error as Error).message)}</p>}
        {validateMutation.data && <JsonPanel data={validateMutation.data} maxHeightClassName="max-h-[220px]" />}
      </section>

      <div className="surface-grid">
        <section className="panel">
          <h3 className="section-title">Replay Timeline</h3>
          {replayTimelineQuery.error && <ErrorPanel error={replayTimelineQuery.error} />}
          {replayTimelineQuery.data && <JsonPanel data={replayTimelineQuery.data} maxHeightClassName="max-h-[220px]" />}
        </section>

        <section className="panel">
          <h3 className="section-title">Density Evolution</h3>
          {replayDensityQuery.error && <ErrorPanel error={replayDensityQuery.error} />}
          {replayDensityQuery.data && <JsonPanel data={replayDensityQuery.data} maxHeightClassName="max-h-[220px]" />}
        </section>
      </div>

      <section className="panel">
        <h3 className="section-title">Death Zones</h3>
        {replayDeathZonesQuery.error && <ErrorPanel error={replayDeathZonesQuery.error} />}
        {replayDeathZonesQuery.data && <JsonPanel data={replayDeathZonesQuery.data} maxHeightClassName="max-h-[220px]" />}
      </section>
    </div>
  );
}
