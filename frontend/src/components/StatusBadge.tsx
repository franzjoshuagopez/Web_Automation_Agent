import { cn } from "@/lib/utils";

type Status = "running" | "idle" | "error";

interface StatusBadgeProps {
  status: Status;
  className?: string;
}

const statusConfig = {
  running: {
    label: "Running",
    className: "status-running",
  },
  idle: {
    label: "Idle",
    className: "status-idle",
  },
  error: {
    label: "Error",
    className: "status-error",
  },
};

export default function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = statusConfig[status];

  return (
    <span
      className={cn(
        "inline-flex items-center px-3 py-1 rounded-full text-xs font-medium",
        config.className,
        className
      )}
    >
      <span className="w-2 h-2 rounded-full bg-current mr-2 animate-pulse-slow" />
      {config.label}
    </span>
  );
}
