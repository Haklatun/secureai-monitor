import clsx from "clsx";

interface MetricCardProps {
  label: string;
  value: string | number;
  sub?: string;
  accent?: "default" | "danger" | "warning" | "success";
}

const accents = {
  default: "text-gray-900",
  danger:  "text-red-600",
  warning: "text-yellow-700",
  success: "text-green-700",
};

export function MetricCard({ label, value, sub, accent = "default" }: MetricCardProps) {
  return (
    <div className="bg-gray-50 rounded-xl p-4">
      <p className="text-xs text-gray-400 mb-1">{label}</p>
      <p className={clsx("text-2xl font-medium leading-none", accents[accent])}>{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-1.5">{sub}</p>}
    </div>
  );
}
