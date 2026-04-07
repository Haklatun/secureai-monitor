"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { logsApi, authApi, loadTokens, type StatsResponse, type TimeseriesPoint, type LogOut } from "@/lib/api";
import { useAlertSocket } from "@/lib/websocket";
import { Topbar } from "@/components/ui/Topbar";
import { MetricCard } from "@/components/ui/MetricCard";
import { EventsChart } from "@/components/charts/EventsChart";
import { ThreatDonut } from "@/components/charts/ThreatDonut";
import { LogsTable } from "@/components/logs/LogsTable";
import { AlertToasts, useAlertToasts } from "@/components/ui/AlertToasts";

const EMPTY_STATS: StatsResponse = {
  total_today: 0,
  high_severity: 0,
  medium_severity: 0,
  anomaly_score_avg: 0,
  active_tenants: 1,
};

export default function DashboardPage() {
  const router = useRouter();
  const [userEmail, setUserEmail] = useState<string>();
  const [stats, setStats] = useState<StatsResponse>(EMPTY_STATS);
  const [timeseries, setTimeseries] = useState<TimeseriesPoint[]>([]);
  const [logs, setLogs] = useState<LogOut[]>([]);
  const [loading, setLoading] = useState(true);
  const { toasts, addToast, dismiss } = useAlertToasts();

  // WebSocket real-time alerts
  useAlertSocket(useCallback((alert) => {
    addToast(alert);
    // Refresh stats + logs on new alert
    fetchData();
  }, [])); // eslint-disable-line react-hooks/exhaustive-deps

  async function fetchData() {
    try {
      const [statsRes, tsRes, logsRes] = await Promise.all([
        logsApi.stats(),
        logsApi.timeseries(12),
        logsApi.list({ page_size: 50 }),
      ]);
      setStats(statsRes.data);
      setTimeseries(tsRes.data);
      setLogs(logsRes.data.items);
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (status === 401) router.replace("/login");
    }
  }

  useEffect(() => {
    loadTokens();

    // Verify auth + get current user
    authApi.me()
      .then((res) => setUserEmail(res.data.email))
      .catch(() => router.replace("/login"));

    fetchData().finally(() => setLoading(false));

    // Poll every 10 seconds
    const interval = setInterval(fetchData, 10_000);
    return () => clearInterval(interval);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  function handleResolve(id: string) {
    setLogs((prev) =>
      prev.map((l) => (l.id === id ? { ...l, resolved: true } : l))
    );
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-sm text-gray-400">Loading dashboard…</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Topbar userEmail={userEmail} isLive />

      <main className="max-w-screen-xl mx-auto px-5 py-5 space-y-5">
        {/* Metric cards */}
        <div className="grid grid-cols-4 gap-3">
          <MetricCard
            label="Total events today"
            value={stats.total_today.toLocaleString()}
          />
          <MetricCard
            label="High / critical"
            value={stats.high_severity}
            sub={stats.high_severity > 0 ? "Requires attention" : "All clear"}
            accent={stats.high_severity > 0 ? "danger" : "success"}
          />
          <MetricCard
            label="Anomaly score avg"
            value={stats.anomaly_score_avg.toFixed(2)}
            sub="threshold 0.65"
            accent={stats.anomaly_score_avg > 0.65 ? "warning" : "default"}
          />
          <MetricCard
            label="Active tenants"
            value={stats.active_tenants}
          />
        </div>

        {/* Charts row */}
        <div className="grid grid-cols-5 gap-3">
          <div className="col-span-3">
            <EventsChart data={timeseries} />
          </div>
          <div className="col-span-2">
            <ThreatDonut stats={stats} />
          </div>
        </div>

        {/* Logs feed */}
        <LogsTable logs={logs} onResolve={handleResolve} />
      </main>

      {/* Real-time alert toasts */}
      <AlertToasts alerts={toasts} onDismiss={dismiss} />
    </div>
  );
}
