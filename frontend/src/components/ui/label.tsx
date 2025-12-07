import * as React from "react";

export type LabelProps = React.LabelHTMLAttributes<HTMLLabelElement>;

export function Label({ className, children, ...props }: LabelProps) {
  return (
    <label
      className={["text-sm font-medium text-slate-200", className || ""].join(" ").trim()}
      {...props}
    >
      {children}
    </label>
  );
}

export default Label;
