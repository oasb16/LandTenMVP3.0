import * as React from "react";

type BadgeProps = React.HTMLAttributes<HTMLSpanElement> & {
  variant?: "default" | "secondary" | "outline";
};

const cn = (...classes: Array<string | false | null | undefined>) =>
  classes.filter(Boolean).join(" ");

export const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(function Badge(
  { variant = "default", className, ...props },
  ref,
) {
  const variants: Record<NonNullable<BadgeProps["variant"]>, string> = {
    default: "bg-emerald-600/80 text-emerald-50",
    secondary: "bg-slate-800/80 text-slate-200",
    outline: "border border-slate-700 text-slate-300",
  };

  return (
    <span
      ref={ref}
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium uppercase tracking-wide transition",
        variants[variant],
        className,
      )}
      {...props}
    />
  );
});
