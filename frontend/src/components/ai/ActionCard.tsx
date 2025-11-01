import React from "react";
import type { LucideIcon } from "lucide-react";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

type Props = {
  icon: LucideIcon;
  title: string;
  desc?: string;
  index?: number;
};

export function ActionCard({ icon: Icon, title, desc, index }: Props) {
  return (
    <Card
      className="group transform border-slate-800 bg-slate-900/80 text-slate-50 shadow-lg ring-1 ring-transparent transition hover:-translate-y-1 hover:shadow-emerald-500/20 hover:ring-emerald-400/50"
      style={
        typeof index === "number"
          ? { transitionDelay: `${Math.min(index, 6) * 50}ms` }
          : undefined
      }
    >
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm font-semibold tracking-tight">
          <Icon className="h-4 w-4 text-emerald-400 transition group-hover:scale-110" />
          <span>{title}</span>
        </CardTitle>
        {desc && (
          <CardDescription className="text-slate-300 text-sm leading-snug">
            {desc}
          </CardDescription>
        )}
      </CardHeader>
    </Card>
  );
}
