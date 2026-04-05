import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  predictBottlenecks,
  predictDeathZones,
  predictExitCollapse,
  predictSurvivalScore,
} from "@/lib/api/analytics";
import { getLatestFrame } from "@/lib/api/simulation";
import { EmptyState } from "@/components/common/EmptyState";
import { JsonPanel } from "@/components/common/JsonPanel";

interface PredictionsTabProps {
  simulationId: string;
}

export function PredictionsTab({ simulationId }: PredictionsTabProps) {
  const [timeHorizon, setTimeHorizon] = useState(30);
  const [disasterType, setDisasterType] = useState("fire");

  const frameQuery = useQuery({
    queryKey: ["analytics", "latest-frame", simulationId],
    queryFn: ({ signal }) => getLatestFrame(simulationId, signal),
    enabled: Boolean(simulationId),
  });

  const basePayload = useMemo(() => {
    const frame = frameQuery.data;
    return {
      agents: frame?.agents ?? [],
      exits: frame?.exits ?? [],
      time_horizon: timeHorizon,
    };
  }, [frameQuery.data, timeHorizon]);

  const bottleneckMutation = useMutation({ mutationFn: () => predictBottlenecks(basePayload) });
  const deathZonesMutation = useMutation({ mutationFn: () => predictDeathZones(basePayload) });
  const collapseMutation = useMutation({ mutationFn: () => predictExitCollapse(basePayload) });
  const survivalMutation = useMutation({
    mutationFn: () =>
      predictSurvivalScore({
        simulation_id: simulationId,
        agents: basePayload.agents,
        exits: basePayload.exits,
        bottlenecks: (bottleneckMutation.data?.bottlenecks as Array<Record<string, unknown>>) ?? [],
        disaster_type: disasterType,
      }),
  });

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    bottleneckMutation.mutate();
    deathZonesMutation.mutate();
    collapseMutation.mutate();
  };

  if (!simulationId) {
    return <EmptyState title="Select simulation" message="Choose a simulation to run prediction endpoints." />;
  }

  return (
    <div className="space-y-4">
      <section className="panel">
        <h3 className="section-title">Prediction Inputs</h3>
        <form className="mt-3 grid gap-3 sm:grid-cols-2" onSubmit={submit}>
          <label>
            <span className="label">Time Horizon (s)</span>
            <input
              className="input"
              type="number"
              value={timeHorizon}
              onChange={(e) => setTimeHorizon(Number(e.target.value))}
            />
          </label>

          <label>
            <span className="label">Disaster Type</span>
            <select className="input" value={disasterType} onChange={(e) => setDisasterType(e.target.value)}>
              <option value="fire">Fire</option>
              <option value="earthquake">Earthquake</option>
              <option value="flood">Flood</option>
            </select>
          </label>

          <div className="sm:col-span-2 flex flex-wrap gap-2">
            <button type="submit" className="btn-primary" disabled={frameQuery.isLoading}>
              Run Bottleneck / Death-Zone / Exit-Collapse
            </button>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => survivalMutation.mutate()}
              disabled={survivalMutation.isPending}
            >
              Run Survival Score
            </button>
          </div>
        </form>
      </section>

      <div className="surface-grid">
        <section className="panel">
          <h3 className="section-title">Bottlenecks</h3>
          <JsonPanel data={bottleneckMutation.data} />
        </section>
        <section className="panel">
          <h3 className="section-title">Death Zones</h3>
          <JsonPanel data={deathZonesMutation.data} />
        </section>
      </div>

      <div className="surface-grid">
        <section className="panel">
          <h3 className="section-title">Exit Collapse</h3>
          <JsonPanel data={collapseMutation.data} />
        </section>

        <section className="panel">
          <h3 className="section-title">Survival Score</h3>
          <JsonPanel data={survivalMutation.data} />
        </section>
      </div>
    </div>
  );
}
