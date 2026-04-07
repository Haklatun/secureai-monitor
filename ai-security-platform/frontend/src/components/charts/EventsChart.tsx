"use client";

import { useEffect, useRef } from "react";
import type { TimeseriesPoint } from "@/lib/api";

interface Props {
  data: TimeseriesPoint[];
}

export function EventsChart({ data }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const chartRef = useRef<unknown>(null);

  useEffect(() => {
    if (!canvasRef.current || typeof window === "undefined") return;

    // Dynamically import Chart.js
    import("chart.js/auto").then(({ default: Chart }) => {
      if (chartRef.current) {
        (chartRef.current as InstanceType<typeof Chart>).destroy();
      }

      const labels = data.map((d) => d.hour);
      const totals = data.map((d) => d.total);
      const highs  = data.map((d) => d.high);

      chartRef.current = new Chart(canvasRef.current!, {
        type: "line",
        data: {
          labels,
          datasets: [
            {
              label: "All events",
              data: totals,
              borderColor: "#378ADD",
              backgroundColor: "rgba(55,138,221,0.07)",
              fill: true,
              tension: 0.4,
              pointRadius: 2,
              borderWidth: 1.5,
            },
            {
              label: "High / critical",
              data: highs,
              borderColor: "#E24B4A",
              backgroundColor: "rgba(226,75,74,0.06)",
              fill: true,
              tension: 0.4,
              pointRadius: 2,
              borderWidth: 1.5,
              yAxisID: "y2",
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: {
              ticks: { font: { size: 10 }, color: "#9ca3af", maxRotation: 0 },
              grid: { color: "rgba(156,163,175,0.12)" },
            },
            y: {
              ticks: { font: { size: 10 }, color: "#9ca3af" },
              grid: { color: "rgba(156,163,175,0.12)" },
            },
            y2: {
              position: "right",
              ticks: { font: { size: 10 }, color: "#E24B4A" },
              grid: { display: false },
            },
          },
        },
      });
    });

    return () => {
      if (chartRef.current) {
        (chartRef.current as { destroy: () => void }).destroy();
      }
    };
  }, [data]);

  return (
    <div className="bg-white border border-gray-100 rounded-2xl p-4">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-medium text-gray-700">Events over time</span>
        <span className="text-xs text-gray-400">last 12 hours</span>
      </div>
      <div className="relative h-36">
        <canvas ref={canvasRef} />
      </div>
      <div className="flex gap-4 mt-3">
        {[
          { color: "#378ADD", label: "All events" },
          { color: "#E24B4A", label: "High / critical" },
        ].map(({ color, label }) => (
          <span key={label} className="flex items-center gap-1.5 text-xs text-gray-400">
            <span className="w-2.5 h-2.5 rounded-sm inline-block" style={{ background: color }} />
            {label}
          </span>
        ))}
      </div>
    </div>
  );
}
