import React from "react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../ui/card";
import { Badge } from "../ui/badge";

type Bid = {
  id: string;
  bid_amount: number;
  status: "PENDING" | "UNDER_REVIEW" | "ACCEPTED" | "REJECTED";
  submitted_at: string;
  job: {
    id: string;
    title: string;
    category: string;
  };
};

const statusColor: Record<Bid["status"], string> = {
  PENDING: "bg-slate-700 text-slate-100",
  UNDER_REVIEW: "bg-amber-500/20 text-amber-200",
  ACCEPTED: "bg-emerald-500/20 text-emerald-200",
  REJECTED: "bg-red-600/20 text-red-200",
};

export function BidCard({ bid }: { bid: Bid }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between">
        <div>
          <CardTitle className="text-lg">{bid.job.title}</CardTitle>
          <CardDescription className="mt-1">Category: {bid.job.category}</CardDescription>
        </div>
        <Badge className={statusColor[bid.status]}>{bid.status.replace("_", " ")}</Badge>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="text-2xl font-semibold text-white">${bid.bid_amount.toFixed(2)}</div>
        <div className="text-sm text-slate-400">
          Submitted: {new Date(bid.submitted_at).toLocaleString()}
        </div>
        <Link
          href={`/contractor/jobs/${bid.job.id}/bid`}
          className="text-blue-300 hover:underline text-sm inline-flex items-center gap-1"
        >
          View bid →
        </Link>
      </CardContent>
    </Card>
  );
}

export default BidCard;
