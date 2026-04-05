import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { SimulationFrame } from "@/lib/api/types";

interface TimelineStripProps {
  frames: SimulationFrame[];
}

export function TimelineStrip({ frames }: TimelineStripProps) {
  const points = frames.map((frame, index) => {
    const stats = frame.stats ?? {};
    return {
      step: index + 1,
      evacuated: Number((stats as { evacuated?: number }).evacuated ?? 0),
      remaining: Number((stats as { remaining?: number }).remaining ?? Math.max((frame.agents?.length ?? 0), 0)),
      completion: Number((stats as { completion_percentage?: number }).completion_percentage ?? 0),
    };
  });

  return (
    <div className="panel">
      <h3 className="section-title">Timeline</h3>
      <div className="chart-wrap mt-3">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={points}>
            <XAxis dataKey="step" stroke="#9cb2c7" />
            <YAxis stroke="#9cb2c7" />
            <Tooltip />
            <Line type="monotone" dataKey="evacuated" stroke="#39d353" dot={false} strokeWidth={2} />
            <Line type="monotone" dataKey="remaining" stroke="#ffb347" dot={false} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
