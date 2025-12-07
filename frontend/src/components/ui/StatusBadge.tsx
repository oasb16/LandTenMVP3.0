import * as React from "react";

type StatusBadgeProps = {
  status: string;
  type: "incident" | "job";
  className?: string;
};

const cn = (...classes: Array<string | false | null | undefined>) =>
  classes.filter(Boolean).join(" ");

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, type, className }) => {
  const getStatusColor = () => {
    if (type === "incident") {
      switch (status.toLowerCase()) {
        case "pending":
          return "bg-yellow-600/90 text-yellow-50 shadow-yellow-500/30";
        case "reviewed":
          return "bg-blue-600/90 text-blue-50 shadow-blue-500/30";
        case "job_created":
          return "bg-purple-600/90 text-purple-50 shadow-purple-500/30";
        case "resolved":
          return "bg-green-600/90 text-green-50 shadow-green-500/30";
        case "closed":
          return "bg-slate-600/90 text-slate-100 shadow-slate-500/20";
        default:
          return "bg-slate-600/90 text-slate-100 shadow-slate-500/20";
      }
    } else if (type === "job") {
      switch (status.toLowerCase()) {
        case "open":
          return "bg-blue-600/90 text-blue-50 shadow-blue-500/30";
        case "awarded":
          return "bg-emerald-600/90 text-emerald-50 shadow-emerald-500/30";
        case "in_progress":
          return "bg-cyan-600/90 text-cyan-50 shadow-cyan-500/30";
        case "completed":
          return "bg-green-600/90 text-green-50 shadow-green-500/30";
        case "cancelled":
          return "bg-red-600/90 text-red-50 shadow-red-500/30";
        default:
          return "bg-slate-600/90 text-slate-100 shadow-slate-500/20";
      }
    }
    return "bg-slate-600/90 text-slate-100 shadow-slate-500/20";
  };

  const formatStatus = (status: string) => {
    return status.replace(/_/g, " ").toUpperCase();
  };

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium uppercase tracking-wide transition shadow-sm",
        getStatusColor(),
        className,
      )}
    >
      {formatStatus(status)}
    </span>
  );
};
