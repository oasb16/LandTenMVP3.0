import React from "react";
import Link from "next/link";
import { Badge } from "../ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../ui/card";
import { Button } from "../ui/button";

type Job = {
  id: string;
  title: string;
  description: string;
  category: string;
  urgency: "LOW" | "MEDIUM" | "HIGH" | "EMERGENCY";
  budget_min?: number;
  budget_max?: number;
  property?: {
    address: string;
    city: string;
    state: string;
  };
};

const urgencyColors: Record<Job["urgency"], string> = {
  LOW: "bg-emerald-500/20 text-emerald-200",
  MEDIUM: "bg-amber-500/20 text-amber-200",
  HIGH: "bg-orange-500/20 text-orange-200",
  EMERGENCY: "bg-red-600/20 text-red-200",
};

export function JobCard({ job }: { job: Job }) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-2">
          <div>
            <CardTitle className="text-xl">{job.title}</CardTitle>
            <CardDescription className="flex gap-2 mt-2 flex-wrap">
              <Badge className={urgencyColors[job.urgency]}>{job.urgency}</Badge>
              <Badge variant="outline">{job.category}</Badge>
            </CardDescription>
          </div>
          {(job.budget_min || job.budget_max) && (
            <div className="text-right text-sm text-slate-200">
              <div className="font-semibold text-white">
                ${job.budget_min ?? job.budget_max} - ${job.budget_max ?? job.budget_min}
              </div>
              <div className="text-slate-400">Budget</div>
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-slate-200">{job.description}</p>
        {job.property && (
          <div className="text-sm text-slate-400">
            {job.property.address}, {job.property.city}, {job.property.state}
          </div>
        )}
        <div className="flex justify-end">
          <Link href={`/contractor/jobs/${job.id}/bid`}>
            <Button>Submit Bid</Button>
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}

export default JobCard;
