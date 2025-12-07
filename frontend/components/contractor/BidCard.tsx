'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Calendar, DollarSign, CheckCircle2, XCircle, Clock } from 'lucide-react';
import { useRouter } from 'next/navigation';

interface BidCardProps {
  bid: {
    id: string;
    bid_amount: number;
    status: 'PENDING' | 'UNDER_REVIEW' | 'ACCEPTED' | 'REJECTED';
    submitted_at: string;
    job: {
      id: string;
      title: string;
      category: string;
    };
  };
}

const statusConfig = {
  PENDING: {
    label: 'Pending',
    color: 'bg-gray-100 text-gray-700 border-gray-200',
    icon: Clock,
  },
  UNDER_REVIEW: {
    label: 'Under Review',
    color: 'bg-blue-100 text-blue-700 border-blue-200',
    icon: Clock,
  },
  ACCEPTED: {
    label: 'Accepted',
    color: 'bg-green-100 text-green-700 border-green-200',
    icon: CheckCircle2,
  },
  REJECTED: {
    label: 'Rejected',
    color: 'bg-red-100 text-red-700 border-red-200',
    icon: XCircle,
  },
};

export function BidCard({ bid }: BidCardProps) {
  const router = useRouter();
  const config = statusConfig[bid.status];
  const StatusIcon = config.icon;

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader>
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <CardTitle className="text-lg mb-2">{bid.job.title}</CardTitle>
            <Badge variant="outline" className="text-xs">
              {bid.job.category}
            </Badge>
          </div>
          <Badge variant="outline" className={`border ${config.color} flex items-center gap-1`}>
            <StatusIcon className="h-3 w-3" />
            {config.label}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-lg font-semibold text-primary">
            <DollarSign className="h-5 w-5" />
            <span>${bid.bid_amount.toLocaleString()}</span>
          </div>

          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Calendar className="h-4 w-4" />
            <span>Submitted {formatDate(bid.submitted_at)}</span>
          </div>

          {bid.status === 'ACCEPTED' && (
            <Button
              className="w-full mt-2"
              onClick={() => router.push(`/contractor/jobs/active`)}
            >
              View Job Details
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
