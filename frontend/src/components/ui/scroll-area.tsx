import * as React from "react";

type ScrollAreaProps = React.HTMLAttributes<HTMLDivElement>;

export const ScrollArea = React.forwardRef<HTMLDivElement, ScrollAreaProps>(function ScrollArea(
  { className, children, ...props },
  ref,
) {
  return (
    <div
      ref={ref}
      className={`relative h-full overflow-hidden ${className ?? ""}`}
      {...props}
    >
      <div className="h-full overflow-y-auto pr-2">{children}</div>
    </div>
  );
});
