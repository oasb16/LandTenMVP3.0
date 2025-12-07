'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useToast } from '@/hooks/use-toast';
import {
  Briefcase,
  AlertCircle,
  Calendar,
  DollarSign,
  MapPin,
  CheckCircle2,
  Clock,
  Play,
  Upload,
} from 'lucide-react';

interface ActiveJob {
  id: string;
  title: string;
  description: string;
  category: string;
  status: 'AWARDED' | 'SCHEDULED' | 'IN_PROGRESS' | 'COMPLETED' | 'PAID';
  scheduled_date?: string;
  awarded_bid: {
    bid_amount: number;
  };
  property?: {
    address: string;
    city: string;
    state: string;
  };
}

const statusConfig = {
  AWARDED: {
    label: 'Awarded',
    color: 'bg-blue-100 text-blue-700 border-blue-200',
    description: 'Schedule an appointment to start work',
    nextAction: 'Schedule Appointment',
  },
  SCHEDULED: {
    label: 'Scheduled',
    color: 'bg-purple-100 text-purple-700 border-purple-200',
    description: 'Ready to begin work',
    nextAction: 'Start Work',
  },
  IN_PROGRESS: {
    label: 'In Progress',
    color: 'bg-yellow-100 text-yellow-700 border-yellow-200',
    description: 'Work is ongoing',
    nextAction: 'Complete Job',
  },
  COMPLETED: {
    label: 'Completed',
    color: 'bg-orange-100 text-orange-700 border-orange-200',
    description: 'Upload completion photos',
    nextAction: 'Upload Photos',
  },
  PAID: {
    label: 'Payment Received',
    color: 'bg-green-100 text-green-700 border-green-200',
    description: 'Job complete and paid',
    nextAction: null,
  },
};

function JobSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-6 w-3/4 mb-2" />
        <Skeleton className="h-4 w-full" />
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          <Skeleton className="h-4 w-1/2" />
          <Skeleton className="h-4 w-2/3" />
          <Skeleton className="h-10 w-full" />
        </div>
      </CardContent>
    </Card>
  );
}

export default function ActiveJobsPage() {
  const router = useRouter();
  const { toast } = useToast();
  const [jobs, setJobs] = useState<ActiveJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  useEffect(() => {
    fetchActiveJobs();
  }, []);

  const fetchActiveJobs = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch('/api/v1/jobs/contractor/active-jobs', {
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error('Failed to fetch active jobs');
      }

      const data = await response.json();
      setJobs(data.jobs || []);
    } catch (err) {
      console.error('Error fetching jobs:', err);
      setError(err instanceof Error ? err.message : 'Failed to load jobs');
    } finally {
      setLoading(false);
    }
  };

  const handleScheduleAppointment = async (jobId: string) => {
    // For now, navigate to a scheduling page (to be implemented)
    // In a real app, this might open a modal or dedicated scheduling flow
    toast({
      title: 'Coming Soon',
      description: 'Scheduling functionality will be implemented',
    });
  };

  const handleStartWork = async (jobId: string) => {
    try {
      setActionLoading(jobId);

      const response = await fetch(`/api/v1/contractors/jobs/${jobId}/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to start work');
      }

      toast({
        title: 'Work Started',
        description: 'Job status updated to In Progress',
      });

      fetchActiveJobs();
    } catch (err) {
      console.error('Error starting work:', err);
      toast({
        variant: 'destructive',
        title: 'Error',
        description: err instanceof Error ? err.message : 'Failed to start work',
      });
    } finally {
      setActionLoading(null);
    }
  };

  const handleCompleteJob = (jobId: string) => {
    router.push(`/contractor/jobs/${jobId}/complete`);
  };

  const handleUploadPhotos = (jobId: string) => {
    router.push(`/contractor/jobs/${jobId}/complete`);
  };

  const handleAction = (job: ActiveJob) => {
    const { status, id } = job;

    switch (status) {
      case 'AWARDED':
        handleScheduleAppointment(id);
        break;
      case 'SCHEDULED':
        handleStartWork(id);
        break;
      case 'IN_PROGRESS':
        handleCompleteJob(id);
        break;
      case 'COMPLETED':
        handleUploadPhotos(id);
        break;
      default:
        break;
    }
  };

  const getActionButton = (job: ActiveJob) => {
    const config = statusConfig[job.status];
    const isLoading = actionLoading === job.id;

    if (!config.nextAction) {
      return (
        <div className="flex items-center gap-2 text-green-600 font-medium">
          <CheckCircle2 className="h-5 w-5" />
          <span>Payment Received</span>
        </div>
      );
    }

    const icons = {
      AWARDED: Calendar,
      SCHEDULED: Play,
      IN_PROGRESS: CheckCircle2,
      COMPLETED: Upload,
    };

    const Icon = icons[job.status as keyof typeof icons];

    return (
      <Button
        onClick={() => handleAction(job)}
        disabled={isLoading}
        className="w-full"
      >
        {isLoading ? (
          <>
            <Clock className="h-4 w-4 mr-2 animate-spin" />
            Processing...
          </>
        ) : (
          <>
            <Icon className="h-4 w-4 mr-2" />
            {config.nextAction}
          </>
        )}
      </Button>
    );
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Active Jobs</h1>
        <p className="text-muted-foreground">
          Manage your ongoing and completed jobs
        </p>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <JobSkeleton key={i} />
          ))}
        </div>
      ) : jobs.length === 0 ? (
        <Card className="p-12">
          <div className="text-center">
            <Briefcase className="h-16 w-16 mx-auto mb-4 text-muted-foreground" />
            <h3 className="text-xl font-semibold mb-2">No active jobs</h3>
            <p className="text-muted-foreground mb-4">
              You don't have any active jobs at the moment
            </p>
            <Button onClick={() => router.push('/contractor/jobs/available')}>
              Browse Available Jobs
            </Button>
          </div>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {jobs.map((job) => {
            const config = statusConfig[job.status];
            return (
              <Card key={job.id} className="hover:shadow-md transition-shadow">
                <CardHeader>
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <CardTitle className="text-lg">{job.title}</CardTitle>
                    <Badge variant="outline" className={`border ${config.color}`}>
                      {config.label}
                    </Badge>
                  </div>
                  <CardDescription className="line-clamp-2">
                    {job.description}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="space-y-2">
                      <div className="flex items-center gap-2 text-sm">
                        <DollarSign className="h-4 w-4 text-muted-foreground" />
                        <span className="font-semibold">
                          ${job.awarded_bid.bid_amount.toLocaleString()}
                        </span>
                      </div>

                      {job.property && (
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          <MapPin className="h-4 w-4" />
                          <span>
                            {job.property.city}, {job.property.state}
                          </span>
                        </div>
                      )}

                      {job.scheduled_date && (
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          <Calendar className="h-4 w-4" />
                          <span>
                            Scheduled:{' '}
                            {new Date(job.scheduled_date).toLocaleDateString('en-US', {
                              month: 'short',
                              day: 'numeric',
                              year: 'numeric',
                            })}
                          </span>
                        </div>
                      )}
                    </div>

                    <div className="pt-2 border-t">
                      <p className="text-xs text-muted-foreground mb-3">
                        {config.description}
                      </p>
                      {getActionButton(job)}
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
