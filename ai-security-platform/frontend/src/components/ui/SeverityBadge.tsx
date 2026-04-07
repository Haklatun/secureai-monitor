import clsx from "clsx";

type Severity = "low" | "medium" | "high" | "critical";

const styles: Record<Severity, string> = {
  low:      "bg-green-50 text-green-800 border-green-200",
  medium:   "bg-yellow-50 text-yellow-800 border-yellow-200",
  high:     "bg-red-50 text-red-700 border-red-200",
  critical: "bg-red-100 text-red-900 border-red-300 font-semibold",
};

export function SeverityBadge({ severity }: { severity: string }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center px-2 py-0.5 rounded-full text-xs border",
        styles[(severity as Severity)] ?? styles.low
      )}
    >
      {severity}
    </span>
  );
}
