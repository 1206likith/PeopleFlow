import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { normalizeScenarioPreset, normalizeSimulationSessionConfig } from "@/lib/api/adapters";
import { createCustomScenario, getScenarioPreset, listScenarioPresets, startScenario } from "@/lib/api/scenarios";
import { ErrorPanel } from "@/components/common/ErrorPanel";
import { EmptyState } from "@/components/common/EmptyState";
import { useSimulationStore } from "@/lib/state/simulationStore";
import { useWorkspaceStore } from "@/lib/state/workspaceStore";

export function ScenarioBuilderPage() {
  const navigate = useNavigate();
  const [selectedPresetId, setSelectedPresetId] = useState("");
  const [customName, setCustomName] = useState("Custom Fire Drill");
  const [customEmergency, setCustomEmergency] = useState("fire");
  const [customBuildingType, setCustomBuildingType] = useState("office");
  const [customPanicLevel, setCustomPanicLevel] = useState(0.5);
  const activeFloorPlanId = useWorkspaceStore((state) => state.activeFloorPlanId);
  const setActiveFloorPlanId = useWorkspaceStore((state) => state.setActiveFloorPlanId);
  const [floorPlanId, setFloorPlanId] = useState(activeFloorPlanId);
  const setDraftConfig = useSimulationStore((state) => state.setDraftConfig);

  const resolvedFloorPlanId = useMemo(() => {
    const explicit = floorPlanId.trim();
    if (explicit) {
      return explicit;
    }
    const fallback = activeFloorPlanId.trim();
    return fallback || "";
  }, [activeFloorPlanId, floorPlanId]);

  const presetsQuery = useQuery({
    queryKey: ["scenarios", "presets"],
    queryFn: ({ signal }) => listScenarioPresets(signal),
  });

  const presetDetailQuery = useQuery({
    queryKey: ["scenarios", "preset", selectedPresetId],
    queryFn: ({ signal }) => getScenarioPreset(selectedPresetId, signal),
    enabled: Boolean(selectedPresetId),
  });

  const createCustomMutation = useMutation({
    mutationFn: () =>
      createCustomScenario({
        name: customName,
        emergency_type: customEmergency,
        building_type: customBuildingType,
        panic_level: customPanicLevel,
      }),
  });

  const startScenarioMutation = useMutation({
    mutationFn: () =>
      startScenario({
        name: selectedPresetId ? `Scenario from ${selectedPresetId}` : "Web Scenario",
        runs: [
          {
            floor_plan_id: resolvedFloorPlanId,
            emergency_type: customEmergency,
            panic_level: customPanicLevel,
          },
        ],
      }),
  });

  const presets = useMemo(
    () => (presetsQuery.data?.presets ?? []).map(normalizeScenarioPreset),
    [presetsQuery.data?.presets],
  );

  const selectedPreset = useMemo(() => {
    if (!presetDetailQuery.data) {
      return null;
    }
    return normalizeScenarioPreset(presetDetailQuery.data);
  }, [presetDetailQuery.data]);

  const prefillSimulation = () => {
    const normalized = normalizeSimulationSessionConfig({
      floor_plan_ref: resolvedFloorPlanId,
      emergency_type: selectedPreset?.emergencyType ?? customEmergency,
      panic_level: selectedPreset?.panicLevel ?? customPanicLevel,
      routing_policy: "guided_evacuation",
      num_agents: 260,
      mode: "studio",
    });
    setDraftConfig(normalized);
    if (resolvedFloorPlanId) {
      setActiveFloorPlanId(resolvedFloorPlanId);
    }
    navigate("/simulation");
  };

  const submitCustom = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    createCustomMutation.mutate();
  };

  const submitStart = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    startScenarioMutation.mutate();
  };

  return (
    <motion.div
      className="legacy-page space-y-6"
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.34, ease: [0.16, 1, 0.3, 1] }}
    >
      <header className="workspace-hero">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="label">Scenario Builder</p>
            <h1 className="mt-3 text-3xl font-bold text-snow" style={{ fontFamily: "var(--font-heading)" }}>Preset and custom evacuation planning</h1>
            <p className="mt-3 max-w-2xl text-sm leading-relaxed text-fog">
              Build research scenarios from presets or custom parameters, then hand them directly into the simulation workspace or launch a backend-managed batch run.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button type="button" className="btn-primary" onClick={prefillSimulation} disabled={!resolvedFloorPlanId}>
              Prefill Simulation Hub
            </button>
            <button type="button" className="btn-secondary" onClick={() => navigate("/experiments")}>
              Open Experiments
            </button>
          </div>
        </div>
      </header>

      <section className="grid gap-6 xl:grid-cols-[1.2fr_0.9fr]">
        <div className="workspace-pane space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="section-title">Preset library</h3>
            <span className="theme-fixed-pill">{presets.length} presets</span>
          </div>
          {presetsQuery.isLoading && <p className="text-sm text-fog">Loading preset library...</p>}
          {presetsQuery.error && <ErrorPanel error={presetsQuery.error} />}
          {!presetsQuery.isLoading && !presets.length && (
            <EmptyState title="No presets available" message="The backend did not return any scenario presets." />
          )}
          <div className="grid gap-4 md:grid-cols-2">
            {presets.map((preset) => (
              <button
                key={preset.id}
                type="button"
                className={`rounded-[20px] border p-5 text-left transition-all duration-200 ${selectedPresetId === preset.id ? "border-cyan-400 bg-cyan-500/10 shadow-[0_18px_40px_rgba(0,229,200,0.12)]" : "border-white/10 bg-white/5 hover:border-white/20 hover:-translate-y-1"}`}
                onClick={() => setSelectedPresetId(preset.id)}
              >
                <p className="label">{preset.buildingType}</p>
                <h4 className="mt-3 text-lg font-semibold text-white">{preset.name}</h4>
                <p className="mt-2 text-sm leading-relaxed text-slate-300">{preset.description || "Preset scenario for evacuation testing."}</p>
                <div className="mt-4 grid grid-cols-3 gap-2 text-xs text-slate-400">
                  <div>
                    <p className="uppercase tracking-[0.14em] text-slate-500">Emergency</p>
                    <p className="mt-1 text-slate-200">{preset.emergencyType}</p>
                  </div>
                  <div>
                    <p className="uppercase tracking-[0.14em] text-slate-500">Panic</p>
                    <p className="mt-1 text-slate-200">{preset.panicLevel.toFixed(2)}</p>
                  </div>
                  <div>
                    <p className="uppercase tracking-[0.14em] text-slate-500">Exits</p>
                    <p className="mt-1 text-slate-200">{preset.recommendedExitCount}</p>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-6">
          <section className="workspace-pane space-y-4">
            <h3 className="section-title">Scenario handoff</h3>
            <label>
              <span className="label">Target floor plan</span>
              <input
                className="input mt-2"
                value={floorPlanId}
                onChange={(event) => {
                  const value = event.target.value;
                  setFloorPlanId(value);
                  setActiveFloorPlanId(value);
                }}
                placeholder="Use active designer floor plan"
              />
            </label>
            {selectedPreset && (
              <div className="rounded-[18px] border border-white/10 bg-white/5 p-4">
                <p className="label">Selected preset</p>
                <h4 className="mt-3 text-lg font-semibold text-white">{selectedPreset.name}</h4>
                <p className="mt-2 text-sm text-slate-300">{selectedPreset.description || "Preset ready to prefill simulation parameters."}</p>
              </div>
            )}
            <form className="space-y-3" onSubmit={submitStart}>
              <button type="submit" className="scenario-launch-btn w-full py-3" disabled={startScenarioMutation.isPending || !resolvedFloorPlanId}>
                {startScenarioMutation.isPending ? "Launching scenario batch..." : "Launch backend scenario batch"}
              </button>
            </form>
            {startScenarioMutation.error && <ErrorPanel error={startScenarioMutation.error} />}
            {startScenarioMutation.data && (
              <pre className="code-panel">{JSON.stringify(startScenarioMutation.data, null, 2)}</pre>
            )}
          </section>

          <section className="workspace-pane space-y-4">
            <h3 className="section-title">Create custom scenario</h3>
            <form className="grid gap-3" onSubmit={submitCustom}>
              <label>
                <span className="label">Scenario name</span>
                <input className="input mt-2" value={customName} onChange={(e) => setCustomName(e.target.value)} />
              </label>
              <label>
                <span className="label">Emergency type</span>
                <input className="input mt-2" value={customEmergency} onChange={(e) => setCustomEmergency(e.target.value)} />
              </label>
              <label>
                <span className="label">Building type</span>
                <input className="input mt-2" value={customBuildingType} onChange={(e) => setCustomBuildingType(e.target.value)} />
              </label>
              <label>
                <span className="label">Panic level</span>
                <input
                  className="input mt-2"
                  type="range"
                  min={0}
                  max={1}
                  step={0.01}
                  value={customPanicLevel}
                  onChange={(e) => setCustomPanicLevel(Number(e.target.value))}
                />
              </label>
              <button type="submit" className="btn-secondary" disabled={createCustomMutation.isPending}>
                {createCustomMutation.isPending ? "Saving custom scenario..." : "Save custom scenario"}
              </button>
            </form>
            {createCustomMutation.error && <ErrorPanel error={createCustomMutation.error} />}
            {createCustomMutation.data && (
              <pre className="code-panel">{JSON.stringify(createCustomMutation.data, null, 2)}</pre>
            )}
          </section>
        </div>
      </section>
    </motion.div>
  );
}
