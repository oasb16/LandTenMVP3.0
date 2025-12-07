import * as React from "react";

export type SkeletonProps = React.HTMLAttributes<HTMLDivElement>;

export function Skeleton({ className, ...props }: SkeletonProps) {
  return (
    <div
      className={[
        "animate-pulse rounded-md bg-slate-800/80",
        className || ""
      ].join(" ").trim()}
      {...props}
    />
  );
}

export default Skeleton;
