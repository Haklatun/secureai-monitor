"use client";

import { useState } from "react";
import { formatDistanceToNow } from "date-fns";
import { CheckCircle, AlertTriangle } from "lucide-react";
import { SeverityBadge } from "@/components/ui/SeverityBadge";
import { logsApi, type LogOut } from "@/lib/api";
import clsx from "clsx";

interface Props {
  logs: LogOut[];
  onResolve?: (id: string) => void;
}

const FILTERS = ["all", "high", "medium", "low"] as const;
type Filter = (typeof FILTERS)[number];

export function LogsTable({ logs, onResolve }: Props) {
  const [filter, setFilter] = useState<Filter>("all");
  const [resolving, setResolving] = useState<string | null>(null);

  const visible = filter === "all" ? logs : logs.filter((l) => l.severity === filter);

  async function handleResolve(id: string) {
    setResolving(id);
    try {
      await logsApi.resolve(id);
      onResolve?.(id);
    } finally {
      setResolving(null);
    }
  }

  function scoreColor(score: number | null) {
    if (score === null) return "text-gray-400";
    if (score >= 0.7) return "text-red-600";
    if (score >= 0.4) return "text-yellow-700";
    return "text-green-700";
  }

  return (
    <div>
      {/* Filter row */}
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xs font-medium text-gray-700 mr-1">Live feed</span>
        {FILTERS.map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={clsx(
              "text-xs px-3 py-1 rounded-full border transition-colors",
              filter === f
                ? "bg-gray-900 text-white border-gray-900"
                : "text-gray-500 border-gray-200 hover:border-gray-400"
            )}
          >
            {f}
          </button>
        ))}
        <span className="ml-auto text-xs text-gray-400">{visible.length} events</span>
      </div>

      {/* Table */}
      <div className="bg-white border border-gray-100 rounded-2xl overflow-hidden">
        <table className="w-full text-xs" style={{ tableLayout: "fixed" }}>
          <colgroup>
            <col style={{ width: "80px" }} />
            <col style={{ width: "78px" }} />
            <col />
            <col style={{ width: "110px" }} />
            <col style={{ width: "56px" }} />
            <col style={{ width: "74px" }} />
          </colgroup>
          <thead>
            <tr className="border-b border-gray-100">
              {["Time", "Severity", "Event", "Source IP", "Score", "Action"].map((h) => (
                <th key={h} className="text-left text-gray-400 font-normal px-3 py-2.5">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visible.length === 0 && (
              <tr>
                <td colSpan={6} className="text-center text-gray-400 py-8">
                  No events match this filter
                </td>
              </tr>
            )}
            {visible.map((log) => (
              <tr
                key={log.id}
                className={clsx(
                  "border-b border-gray-50 last:border-0 hover:bg-gray-50 transition-colors",
                  log.is_anomaly && !log.resolved && "bg-red-50/40"
                )}
              >
                <td className="px-3 py-2.5 font-mono text-gray-400">
                  {formatDistanceToNow(new Date(log.created_at), { addSuffix: true })}
                </td>
                <td className="px-3 py-2.5">
                  <SeverityBadge severity={log.severity} />
                </td>
                <td className="px-3 py-2.5 text-gray-800 truncate">
                  {log.event_type}
                  {log.is_anomaly && (
                    <AlertTriangle
                      size={11}
                      className="inline ml-1.5 text-red-500 -translate-y-px"
                    />
                  )}
                </td>
                <td className="px-3 py-2.5 font-mono text-gray-500 truncate">
                  {log.source_ip ?? "—"}
                </td>
                <td className={clsx("px-3 py-2.5 font-mono font-medium", scoreColor(log.anomaly_score))}>
                  {log.anomaly_score !== null ? log.anomaly_score.toFixed(2) : "—"}
                </td>
                <td className="px-3 py-2.5">
                  {log.resolved ? (
                    <span className="flex items-center gap-1 text-green-600">
                      <CheckCircle size={12} /> Done
                    </span>
                  ) : (
                    <button
                      onClick={() => handleResolve(log.id)}
                      disabled={resolving === log.id}
                      className="text-blue-600 hover:text-blue-800 disabled:opacity-40 transition-colors"
                    >
                      {resolving === log.id ? "…" : "Resolve"}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
