'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { FileUpload } from '@/components/ui/FileUpload';
import { useToast } from '@/hooks/use-toast';
import {
  ArrowLeft,
  CheckCircle2,
  Upload,
  AlertCircle,
  Clock,
  DollarSign,
  MapPin,
} from 'lucide-react';

interface JobDetails {
  id: string;
  title: string;
  description: string;
  category: string;
  status: string;
  awarded_bid: {
    bid_amount: number;
  };
  property?: {
    address: string;
    city: string;
    state: string;
  };
}

type CompletionStep = 'mark_complete' | 'upload_photos' | 'done';

export default function CompleteJobPage() {
  const router = useRouter();
  const params = useParams();
  const jobId = params.id as string;
  const { toast } = useToast();

  const [job, setJob] = useState<JobDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState<CompletionStep>('mark_complete');

  const [completionNotes, setCompletionNotes] = useState('');
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploadProgress, setUploadProgress] = useState<number>(0);

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

      // If job is already completed, go to upload step
      if (data.status === 'COMPLETED') {
        setCurrentStep('upload_photos');
      }
    } catch (err) {
      console.error('Error fetching job:', err);
      setError(err instanceof Error ? err.message : 'Failed to load job');
    } finally {
      setLoading(false);
    }
  };

  const handleMarkComplete = async () => {
    if (completionNotes.trim().length < 50) {
      toast({
        variant: 'destructive',
        title: 'Validation Error',
        description: 'Completion notes must be at least 50 characters',
      });
      return;
    }

    try {
      setSubmitting(true);

      const response = await fetch(`/api/v1/contractors/jobs/${jobId}/complete`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          completion_notes: completionNotes,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to mark job as complete');
      }

      toast({
        title: 'Success',
        description: 'Job marked as complete',
      });

      setCurrentStep('upload_photos');
    } catch (err) {
      console.error('Error completing job:', err);
      toast({
        variant: 'destructive',
        title: 'Error',
        description: err instanceof Error ? err.message : 'Failed to mark job as complete',
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleUploadPhotos = async () => {
    if (selectedFiles.length === 0) {
      toast({
        variant: 'destructive',
        title: 'Validation Error',
        description: 'Please select at least one photo to upload',
      });
      return;
    }

    try {
      setSubmitting(true);
      setUploadProgress(0);

      const uploadPromises = selectedFiles.map(async (file, index) => {
        const formData = new FormData();
        formData.append('photo', file);

        const response = await fetch(`/api/v1/contractors/jobs/${jobId}/completion-photos`, {
          method: 'POST',
          credentials: 'include',
          body: formData,
        });

        if (!response.ok) {
          throw new Error(`Failed to upload ${file.name}`);
        }

        // Update progress
        setUploadProgress(((index + 1) / selectedFiles.length) * 100);

        return response.json();
      });

      await Promise.all(uploadPromises);

      toast({
        title: 'Success!',
        description: 'All photos uploaded successfully',
      });

      setCurrentStep('done');
    } catch (err) {
      console.error('Error uploading photos:', err);
      toast({
        variant: 'destructive',
        title: 'Upload Failed',
        description: err instanceof Error ? err.message : 'Failed to upload photos',
      });
    } finally {
      setSubmitting(false);
      setUploadProgress(0);
    }
  };

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        <Skeleton className="h-8 w-64 mb-8" />
        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-3/4 mb-2" />
            <Skeleton className="h-20 w-full" />
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <Skeleton className="h-32 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error || !job) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error || 'Job not found'}</AlertDescription>
        </Alert>
        <Button
          variant="outline"
          className="mt-4"
          onClick={() => router.push('/contractor/jobs/active')}
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Active Jobs
        </Button>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <Button
        variant="ghost"
        onClick={() => router.push('/contractor/jobs/active')}
        className="mb-6"
      >
        <ArrowLeft className="h-4 w-4 mr-2" />
        Back to Active Jobs
      </Button>

      {/* Job Details Section */}
      <Card className="mb-6">
        <CardHeader>
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <CardTitle className="text-2xl mb-2">{job.title}</CardTitle>
              <Badge variant="outline" className="mb-4">
                {job.category}
              </Badge>
            </div>
          </div>
          <CardDescription className="text-base">{job.description}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex items-center gap-2 text-sm">
              <DollarSign className="h-4 w-4 text-muted-foreground" />
              <span className="font-medium">Bid Amount:</span>
              <span>${job.awarded_bid.bid_amount.toLocaleString()}</span>
            </div>
            {job.property && (
              <div className="flex items-center gap-2 text-sm">
                <MapPin className="h-4 w-4 text-muted-foreground" />
                <span className="font-medium">Location:</span>
                <span>
                  {job.property.city}, {job.property.state}
                </span>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Progress Indicators */}
      <div className="flex items-center justify-center mb-8">
        <div className="flex items-center gap-4">
          <div
            className={`flex items-center gap-2 ${
              currentStep === 'mark_complete' ? 'text-primary' : 'text-green-600'
            }`}
          >
            {currentStep !== 'mark_complete' ? (
              <CheckCircle2 className="h-6 w-6" />
            ) : (
              <div className="h-6 w-6 rounded-full border-2 border-primary flex items-center justify-center">
                <div className="h-3 w-3 rounded-full bg-primary" />
              </div>
            )}
            <span className="font-medium">Mark Complete</span>
          </div>

          <div className="h-0.5 w-16 bg-border" />

          <div
            className={`flex items-center gap-2 ${
              currentStep === 'upload_photos'
                ? 'text-primary'
                : currentStep === 'done'
                ? 'text-green-600'
                : 'text-muted-foreground'
            }`}
          >
            {currentStep === 'done' ? (
              <CheckCircle2 className="h-6 w-6" />
            ) : currentStep === 'upload_photos' ? (
              <div className="h-6 w-6 rounded-full border-2 border-primary flex items-center justify-center">
                <div className="h-3 w-3 rounded-full bg-primary" />
              </div>
            ) : (
              <div className="h-6 w-6 rounded-full border-2 border-muted-foreground" />
            )}
            <span className="font-medium">Upload Photos</span>
          </div>
        </div>
      </div>

      {/* Step 1: Mark Complete */}
      {currentStep === 'mark_complete' && (
        <Card>
          <CardHeader>
            <CardTitle>Step 1: Mark Job as Complete</CardTitle>
            <CardDescription>
              Provide details about the work you've completed
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <Label htmlFor="completion_notes">
                  Completion Notes <span className="text-red-500">*</span>
                </Label>
                <Textarea
                  id="completion_notes"
                  placeholder="Describe the work completed, any challenges faced, and final results... (minimum 50 characters)"
                  value={completionNotes}
                  onChange={(e) => setCompletionNotes(e.target.value)}
                  className="min-h-[150px]"
                  required
                />
                <p
                  className={`text-sm mt-1 ${
                    completionNotes.length < 50 ? 'text-muted-foreground' : 'text-green-600'
                  }`}
                >
                  {completionNotes.length} / 50 characters
                </p>
              </div>

              <Button
                onClick={handleMarkComplete}
                disabled={submitting || completionNotes.length < 50}
                className="w-full"
              >
                {submitting ? (
                  <>
                    <Clock className="h-4 w-4 mr-2 animate-spin" />
                    Marking Complete...
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="h-4 w-4 mr-2" />
                    Mark as Complete
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 2: Upload Photos */}
      {currentStep === 'upload_photos' && (
        <Card>
          <CardHeader>
            <CardTitle>Step 2: Upload Completion Photos</CardTitle>
            <CardDescription>
              Upload photos showing the completed work (at least 1 photo required)
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              <FileUpload
                onFilesSelected={setSelectedFiles}
                maxFiles={10}
                multiple={true}
              />

              {uploadProgress > 0 && uploadProgress < 100 && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span>Uploading photos...</span>
                    <span>{Math.round(uploadProgress)}%</span>
                  </div>
                  <div className="h-2 bg-muted rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary transition-all duration-300"
                      style={{ width: `${uploadProgress}%` }}
                    />
                  </div>
                </div>
              )}

              <Button
                onClick={handleUploadPhotos}
                disabled={submitting || selectedFiles.length === 0}
                className="w-full"
              >
                {submitting ? (
                  <>
                    <Clock className="h-4 w-4 mr-2 animate-spin" />
                    Uploading {selectedFiles.length} photo{selectedFiles.length !== 1 ? 's' : ''}
                    ...
                  </>
                ) : (
                  <>
                    <Upload className="h-4 w-4 mr-2" />
                    Submit All Photos ({selectedFiles.length})
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 3: Done */}
      {currentStep === 'done' && (
        <Card>
          <CardContent className="pt-12 pb-12">
            <div className="text-center">
              <CheckCircle2 className="h-20 w-20 text-green-600 mx-auto mb-4" />
              <h2 className="text-2xl font-bold mb-2">Work Submitted!</h2>
              <p className="text-muted-foreground mb-6">
                Your completed work and photos have been submitted to the landlord for review.
                You'll be notified once they approve and process payment.
              </p>
              <div className="flex gap-4 justify-center">
                <Button
                  variant="outline"
                  onClick={() => router.push('/contractor/jobs/active')}
                >
                  View Active Jobs
                </Button>
                <Button onClick={() => router.push('/contractor/jobs/available')}>
                  Browse More Jobs
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
