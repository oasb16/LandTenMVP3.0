import * as React from "react";

export type InputProps = React.InputHTMLAttributes<HTMLInputElement>;

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={[
        "w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-slate-900 shadow-sm",
        "focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-blue-400",
        className || ""
      ].join(" ").trim()}
      {...props}
    />
  )
);

Input.displayName = "Input";

export default Input;
