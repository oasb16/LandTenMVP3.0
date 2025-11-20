import * as React from "react";

type CardProps = React.HTMLAttributes<HTMLDivElement>;

const cn = (...classes: Array<string | false | null | undefined>) =>
  classes.filter(Boolean).join(" ");

export const Card = React.forwardRef<HTMLDivElement, CardProps>(function Card(
  { className, ...props },
  ref,
) {
  return (
    <div
      ref={ref}
      className={cn(
        "rounded-2xl border border-blue-500/50 bg-slate-700/90 text-slate-50 shadow-lg shadow-blue-500/20 backdrop-blur-md",
        className,
      )}
      {...props}
    />
  );
});

export const CardHeader = React.forwardRef<HTMLDivElement, CardProps>(function CardHeader(
  { className, ...props },
  ref,
) {
  return (
    <div
      ref={ref}
      className={cn("space-y-1.5 p-4", className)}
      {...props}
    />
  );
});

export const CardTitle = React.forwardRef<HTMLHeadingElement, React.HTMLAttributes<HTMLHeadingElement>>(
  function CardTitle({ className, ...props }, ref) {
    return (
      <h3
        ref={ref}
        className={cn("text-base font-semibold leading-none tracking-tight", className)}
        {...props}
      />
    );
  },
);

export const CardDescription = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLParagraphElement>>(
  function CardDescription({ className, ...props }, ref) {
    return (
      <p
        ref={ref}
        className={cn("text-sm text-slate-200", className)}
        {...props}
      />
    );
  },
);

export const CardContent = React.forwardRef<HTMLDivElement, CardProps>(function CardContent(
  { className, ...props },
  ref,
) {
  return (
    <div
      ref={ref}
      className={cn("p-4 pt-0", className)}
      {...props}
    />
  );
});
