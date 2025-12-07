import * as React from "react";

export interface AlertProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "destructive";
}

export function Alert({ className, variant = "default", children, ...props }: AlertProps) {
  const base =
    "w-full rounded-md border px-4 py-3 text-sm transition bg-slate-900/60 text-slate-100 border-slate-700";
  const destructive = "border-red-500 text-red-200 bg-red-500/10";

  return (
    <div
      className={[base, variant === "destructive" ? destructive : "", className || ""]
        .join(" ")
        .trim()}
      role="alert"
      {...props}
    >
      {children}
    </div>
  );
}

export function AlertDescription({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={["text-sm leading-6", className || ""].join(" ").trim()} {...props}>
      {children}
    </div>
  );
}

export default Alert;
