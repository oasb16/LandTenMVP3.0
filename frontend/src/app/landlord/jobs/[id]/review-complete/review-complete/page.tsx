'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import {
  ArrowLeft,
  CheckCircle2,
  AlertCircle,
  DollarSign,
  Calendar,
  User,
  Image as ImageIcon,
  CreditCard,
} from 'lucide-react';

interface JobDetails {
  id: string;
  title: string;
  description: string;
  category: string;
  status: string;
  completion_notes?: string;
  completion_photos?: Array<{
    id: string;
    photo_url: string;
    uploaded_at: string;
  }>;
  awarded_bid: {
    id: string;
    bid_amount: number;
    contractor: {
      id: string;
      user: {
        first_name: string;
        last_name: string;
      };
    };
  };
  completed_at?: string;
}

export default function ReviewCompletePage() {
  const router = useRouter();
  const params = useParams();
  const jobId = params.id as string;

  const [job, setJob] = useState<JobDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPhoto, setSelectedPhoto] = useState<string | null>(null);

  useEffect(() => {
    fetchJobDetails();
  }, [jobId]);

  const fetchJobDetails = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/v1/jobs/${jobId}`, {
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error('Failed to fetch job details');
      }

      const data = await response.json();
      setJob(data);
    } catch (err) {
      console.error('Error fetching job:', err);
      setError(err instanceof Error ? err.message : 'Failed to load job');
    } finally {
      setLoading(false);
    }
  };

  const handleApproveAndPay = () => {
    router.push(`/landlord/jobs/${jobId}/payment`);
  };

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        <Skeleton className="h-8 w-64 mb-8" />
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <Skeleton className="h-6 w-3/4 mb-2" />
              <Skeleton className="h-20 w-full" />
            </CardHeader>
          </Card>
          <Card>
            <CardHeader>
              <Skeleton className="h-6 w-48" />
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-4">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="aspect-square" />
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  if (error || !job) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error || 'Job not found'}</AlertDescription>
        </Alert>
        <Button
          variant="outline"
          className="mt-4"
          onClick={() => router.push('/landlord/jobs')}
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Jobs
        </Button>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      <Button
        variant="ghost"
        onClick={() => router.push('/landlord/jobs')}
        className="mb-6"
      >
        <ArrowLeft className="h-4 w-4 mr-2" />
        Back to Jobs
      </Button>

      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">Review Completed Work</h1>
        <p className="text-muted-foreground">
          Review the contractor's work and approve payment
        </p>
      </div>

      {/* Job Details Card */}
      <Card className="mb-6">
        <CardHeader>
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <CardTitle className="text-2xl mb-2">{job.title}</CardTitle>
              <Badge variant="outline" className="mb-4">
                {job.category}
              </Badge>
            </div>
            <Badge className="bg-green-100 text-green-700 border-green-200">
              Awaiting Payment
            </Badge>
          </div>
          <CardDescription className="text-base">{job.description}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="flex items-center gap-2">
              <User className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-xs text-muted-foreground">Contractor</p>
                <p className="font-medium">
                  {job.awarded_bid.contractor.user.first_name}{' '}
                  {job.awarded_bid.contractor.user.last_name}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <DollarSign className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-xs text-muted-foreground">Approved Amount</p>
                <p className="font-medium">
                  ${job.awarded_bid.bid_amount.toLocaleString()}
                </p>
              </div>
            </div>

            {job.completed_at && (
              <div className="flex items-center gap-2">
                <Calendar className="h-4 w-4 text-muted-foreground" />
                <div>
                  <p className="text-xs text-muted-foreground">Completed On</p>
                  <p className="font-medium">
                    {new Date(job.completed_at).toLocaleDateString('en-US', {
                      month: 'short',
                      day: 'numeric',
                      year: 'numeric',
                    })}
                  </p>
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Completion Notes */}
      {job.completion_notes && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Completion Notes</CardTitle>
            <CardDescription>Details from the contractor</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm whitespace-pre-wrap">{job.completion_notes}</p>
          </CardContent>
        </Card>
      )}

      {/* Photo Gallery */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ImageIcon className="h-5 w-5" />
            Completion Photos
            {job.completion_photos && (
              <Badge variant="outline">{job.completion_photos.length}</Badge>
            )}
          </CardTitle>
          <CardDescription>Photos of the completed work</CardDescription>
        </CardHeader>
        <CardContent>
          {!job.completion_photos || job.completion_photos.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <ImageIcon className="h-12 w-12 mx-auto mb-2 opacity-50" />
              <p>No completion photos uploaded</p>
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {job.completion_photos.map((photo) => (
                <div
                  key={photo.id}
                  className="group relative aspect-square rounded-lg overflow-hidden cursor-pointer hover:opacity-90 transition-opacity"
                  onClick={() => setSelectedPhoto(photo.photo_url)}
                >
                  <img
                    src={photo.photo_url}
                    alt="Completion photo"
                    className="w-full h-full object-cover"
                  />
                  <div className="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-colors" />
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Payment Summary */}
      <Card className="mb-6 border-primary">
        <CardHeader>
          <CardTitle>Payment Summary</CardTitle>
          <CardDescription>
            Review the payment details before proceeding
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex items-center justify-between text-lg">
              <span className="font-medium">Total Amount</span>
              <span className="font-bold text-primary">
                ${job.awarded_bid.bid_amount.toLocaleString()}
              </span>
            </div>
            <div className="text-sm text-muted-foreground">
              <p>• Contractor will receive 85% (${(job.awarded_bid.bid_amount * 0.85).toFixed(2)})</p>
              <p>• Platform fee 15% (${(job.awarded_bid.bid_amount * 0.15).toFixed(2)})</p>
              <p className="mt-2">Payment will be processed via Stripe</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Action Button */}
      <div className="flex gap-4">
        <Button
          variant="outline"
          onClick={() => router.push('/landlord/jobs')}
          className="flex-1"
        >
          Review Later
        </Button>
        <Button onClick={handleApproveAndPay} className="flex-1">
          <CreditCard className="h-4 w-4 mr-2" />
          Approve & Pay ${job.awarded_bid.bid_amount.toLocaleString()}
        </Button>
      </div>

      {/* Photo Modal */}
      {selectedPhoto && (
        <div
          className="fixed inset-0 bg-black/90 z-50 flex items-center justify-center p-4"
          onClick={() => setSelectedPhoto(null)}
        >
          <button
            className="absolute top-4 right-4 text-white text-4xl hover:text-gray-300"
            onClick={() => setSelectedPhoto(null)}
          >
            ×
          </button>
          <img
            src={selectedPhoto}
            alt="Full size"
            className="max-w-full max-h-full object-contain"
          />
        </div>
      )}
    </div>
  );
}
