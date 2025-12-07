import React from "react";

export function Separator({ className }: { className?: string }) {
  return <hr className={["border-slate-800", className || ""].join(" ").trim()} />;
}

export default Separator;
