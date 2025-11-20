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
    default: "bg-blue-600/90 text-blue-50 shadow-sm shadow-blue-500/30",
    secondary: "bg-slate-600/90 text-slate-100 shadow-sm shadow-slate-500/20",
    outline: "border border-blue-400 text-blue-300",
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
