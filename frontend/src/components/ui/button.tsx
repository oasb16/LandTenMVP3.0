import * as React from "react";

export type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement>;

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, children, ...props }, ref) => (
    <button
      ref={ref}
      className={
        [
          "inline-flex items-center justify-center rounded-md px-4 py-2 font-semibold transition focus:outline-none focus:ring-2 focus:ring-offset-2",
          "bg-blue-600 text-white hover:bg-blue-500 focus:ring-blue-400",
          className || ""
        ].join(" ").trim()
      }
      {...props}
    >
      {children}
    </button>
  )
);

Button.displayName = "Button";

export default Button;
