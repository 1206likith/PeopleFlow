import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { downloadPdfReport, getHeatmapData } from "@/lib/api/analytics";
import { ErrorPanel } from "@/components/common/ErrorPanel";
import { EmptyState } from "@/components/common/EmptyState";
import { JsonPanel } from "@/components/common/JsonPanel";

interface ReportsTabProps {
  simulationId: string;
}

export function ReportsTab({ simulationId }: ReportsTabProps) {
  const heatmapQuery = useQuery({
    queryKey: ["analytics", "heatmap", simulationId],
    queryFn: ({ signal }) => getHeatmapData(simulationId, signal),
    enabled: Boolean(simulationId),
  });

  const points = useMemo(() => {
    const data = heatmapQuery.data?.heatmap_data;
    return Array.isArray(data) ? data : [];
  }, [heatmapQuery.data]);

  const download = async () => {
    const blob = await downloadPdfReport(simulationId);
    const href = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = href;
    link.download = `peopleflow-report-${simulationId}.pdf`;
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(href);
  };

  if (!simulationId) {
    return <EmptyState title="Select simulation" message="Choose a simulation to load report outputs." />;
  }

  return (
    <div className="surface-grid">
      <section className="panel">
        <h3 className="section-title">PDF Report</h3>
        <p className="mt-2 text-sm text-mist/75">Exports full report from `/api/v2/reports/{'{simulation_id}'}/pdf`.</p>
        <button type="button" className="btn-primary mt-4" onClick={download}>
          Download PDF
        </button>
      </section>

      <section className="panel">
        <h3 className="section-title">Heatmap Points</h3>
        {heatmapQuery.isLoading && <p className="mt-3 text-sm text-mist/70">Loading heatmap...</p>}
        {heatmapQuery.error && <ErrorPanel error={heatmapQuery.error} />}
        {heatmapQuery.data && (
          <>
            <p className="mt-2 text-sm text-mist/75">Total points: {String(heatmapQuery.data.total_points ?? points.length)}</p>
            <JsonPanel data={points.slice(0, 200)} maxHeightClassName="max-h-[280px]" />
          </>
        )}
      </section>
    </div>
  );
}
