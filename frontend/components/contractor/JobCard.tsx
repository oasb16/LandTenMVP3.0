'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Calendar, DollarSign, MapPin, Wrench } from 'lucide-react';
import { useRouter } from 'next/navigation';

interface JobCardProps {
  job: {
    id: string;
    title: string;
    description: string;
    category: string;
    urgency: 'LOW' | 'MEDIUM' | 'HIGH' | 'EMERGENCY';
    budget_min?: number;
    budget_max?: number;
    created_at: string;
    property?: {
      address: string;
      city: string;
      state: string;
    };
  };
}

const urgencyColors = {
  LOW: 'bg-blue-500',
  MEDIUM: 'bg-yellow-500',
  HIGH: 'bg-orange-500',
  EMERGENCY: 'bg-red-500',
};

const urgencyTextColors = {
  LOW: 'text-blue-700 bg-blue-50 border-blue-200',
  MEDIUM: 'text-yellow-700 bg-yellow-50 border-yellow-200',
  HIGH: 'text-orange-700 bg-orange-50 border-orange-200',
  EMERGENCY: 'text-red-700 bg-red-50 border-red-200',
};

export function JobCard({ job }: JobCardProps) {
  const router = useRouter();

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now.getTime() - date.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    return date.toLocaleDateString();
  };

  const truncateDescription = (text: string, lines: number = 3) => {
    const lineHeight = 24; // approximate line height
    const maxLength = 150; // approximate characters for 3 lines
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };

  return (
    <Card className="hover:shadow-lg transition-shadow">
      <CardHeader>
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1">
            <CardTitle className="text-lg mb-2">{job.title}</CardTitle>
            <div className="flex flex-wrap gap-2 mb-2">
              <Badge variant="outline" className="flex items-center gap-1">
                <Wrench className="h-3 w-3" />
                {job.category}
              </Badge>
              <Badge
                variant="outline"
                className={`border ${urgencyTextColors[job.urgency]}`}
              >
                {job.urgency}
              </Badge>
            </div>
          </div>
        </div>
        <CardDescription className="line-clamp-3 min-h-[72px]">
          {job.description}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {(job.budget_min || job.budget_max) && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <DollarSign className="h-4 w-4" />
              <span>
                {job.budget_min && job.budget_max
                  ? `$${job.budget_min.toLocaleString()} - $${job.budget_max.toLocaleString()}`
                  : job.budget_min
                  ? `From $${job.budget_min.toLocaleString()}`
                  : `Up to $${job.budget_max?.toLocaleString()}`}
              </span>
            </div>
          )}

          {job.property && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <MapPin className="h-4 w-4" />
              <span>
                {job.property.city}, {job.property.state}
              </span>
            </div>
          )}

          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Calendar className="h-4 w-4" />
            <span>Posted {formatDate(job.created_at)}</span>
          </div>

          <Button
            className="w-full mt-4"
            onClick={() => router.push(`/contractor/jobs/${job.id}/bid`)}
          >
            Submit Bid
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
