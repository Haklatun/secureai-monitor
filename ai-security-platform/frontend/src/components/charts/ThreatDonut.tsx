"use client";

import { useEffect, useRef } from "react";
import type { StatsResponse } from "@/lib/api";

interface Props {
  stats: StatsResponse;
}

export function ThreatDonut({ stats }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const chartRef = useRef<unknown>(null);

  const low = stats.total_today - stats.high_severity - stats.medium_severity;

  useEffect(() => {
    if (!canvasRef.current) return;
    import("chart.js/auto").then(({ default: Chart }) => {
      if (chartRef.current) (chartRef.current as { destroy: () => void }).destroy();
      chartRef.current = new Chart(canvasRef.current!, {
        type: "doughnut",
        data: {
          labels: ["High / critical", "Medium", "Low"],
          datasets: [{
            data: [stats.high_severity, stats.medium_severity, Math.max(low, 0)],
            backgroundColor: ["#E24B4A", "#BA7517", "#639922"],
            borderWidth: 0,
            hoverOffset: 4,
          }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          cutout: "68%",
          plugins: { legend: { display: false } },
        },
      });
    });
    return () => {
      if (chartRef.current) (chartRef.current as { destroy: () => void }).destroy();
    };
  }, [stats, low]);

  return (
    <div className="bg-white border border-gray-100 rounded-2xl p-4">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-medium text-gray-700">Threat breakdown</span>
        <span className="text-xs text-gray-400">today</span>
      </div>
      <div className="relative h-36">
        <canvas ref={canvasRef} />
      </div>
      <div className="flex gap-3 mt-3 flex-wrap">
        {[
          { color: "#E24B4A", label: "High", val: stats.high_severity },
          { color: "#BA7517", label: "Medium", val: stats.medium_severity },
          { color: "#639922", label: "Low", val: Math.max(low, 0) },
        ].map(({ color, label, val }) => (
          <span key={label} className="flex items-center gap-1.5 text-xs text-gray-400">
            <span className="w-2.5 h-2.5 rounded-sm inline-block" style={{ background: color }} />
            {label} <strong className="text-gray-600">{val}</strong>
          </span>
        ))}
      </div>
    </div>
  );
}
