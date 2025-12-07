'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { useToast } from '@/hooks/use-toast';
import {
  ArrowLeft,
  DollarSign,
  Calendar,
  Clock,
  AlertCircle,
  Wrench,
  MapPin,
  CheckCircle2
} from 'lucide-react';

interface JobDetails {
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
}

interface BidFormData {
  bid_amount: string;
  materials_cost: string;
  labor_cost: string;
  estimated_hours: string;
  start_date: string;
  proposal_details: string;
}

export default function SubmitBidPage() {
  const router = useRouter();
  const params = useParams();
  const jobId = params.id as string;
  const { toast } = useToast();

  const [job, setJob] = useState<JobDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [formData, setFormData] = useState<BidFormData>({
    bid_amount: '',
    materials_cost: '',
    labor_cost: '',
    estimated_hours: '',
    start_date: '',
    proposal_details: '',
  });

  const [formErrors, setFormErrors] = useState<Partial<Record<keyof BidFormData, string>>>({});

  useEffect(() => {
    fetchJobDetails();
  }, [jobId]);

  // Auto-calculate total if materials and labor are provided
  useEffect(() => {
    const materials = parseFloat(formData.materials_cost) || 0;
    const labor = parseFloat(formData.labor_cost) || 0;

    if (materials > 0 || labor > 0) {
      const total = materials + labor;
      if (total > 0 && formData.bid_amount !== total.toString()) {
        setFormData((prev) => ({
          ...prev,
          bid_amount: total.toString(),
        }));
      }
    }
  }, [formData.materials_cost, formData.labor_cost]);

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

  const validateForm = (): boolean => {
    const errors: Partial<Record<keyof BidFormData, string>> = {};

    if (!formData.bid_amount || parseFloat(formData.bid_amount) <= 0) {
      errors.bid_amount = 'Total bid amount is required';
    }

    if (!formData.estimated_hours || parseFloat(formData.estimated_hours) <= 0) {
      errors.estimated_hours = 'Estimated hours is required';
    }

    if (!formData.start_date) {
      errors.start_date = 'Start date is required';
    } else {
      const startDate = new Date(formData.start_date);
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      if (startDate < today) {
        errors.start_date = 'Start date cannot be in the past';
      }
    }

    if (!formData.proposal_details || formData.proposal_details.length < 200) {
      errors.proposal_details = 'Proposal details must be at least 200 characters';
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      toast({
        variant: 'destructive',
        title: 'Validation Error',
        description: 'Please fix the errors in the form',
      });
      return;
    }

    try {
      setSubmitting(true);

      const bidData = {
        bid_amount: parseFloat(formData.bid_amount),
        materials_cost: formData.materials_cost ? parseFloat(formData.materials_cost) : undefined,
        labor_cost: formData.labor_cost ? parseFloat(formData.labor_cost) : undefined,
        estimated_hours: parseFloat(formData.estimated_hours),
        start_date: formData.start_date,
        proposal_details: formData.proposal_details,
      };

      const response = await fetch(`/api/v1/jobs/${jobId}/bid`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(bidData),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to submit bid');
      }

      toast({
        title: 'Success!',
        description: 'Your bid has been submitted successfully',
      });

      router.push('/contractor/jobs/my-bids');
    } catch (err) {
      console.error('Error submitting bid:', err);
      toast({
        variant: 'destructive',
        title: 'Submission Failed',
        description: err instanceof Error ? err.message : 'Failed to submit bid',
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleInputChange = (
    field: keyof BidFormData,
    value: string
  ) => {
    setFormData((prev) => ({
      ...prev,
      [field]: value,
    }));
    // Clear error when user starts typing
    if (formErrors[field]) {
      setFormErrors((prev) => ({
        ...prev,
        [field]: undefined,
      }));
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
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i}>
                  <Skeleton className="h-4 w-24 mb-2" />
                  <Skeleton className="h-10 w-full" />
                </div>
              ))}
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
          onClick={() => router.push('/contractor/jobs/available')}
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Jobs
        </Button>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <Button
        variant="ghost"
        onClick={() => router.push('/contractor/jobs/available')}
        className="mb-6"
      >
        <ArrowLeft className="h-4 w-4 mr-2" />
        Back to Available Jobs
      </Button>

      {/* Job Details Section */}
      <Card className="mb-6">
        <CardHeader>
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <CardTitle className="text-2xl mb-2">{job.title}</CardTitle>
              <div className="flex flex-wrap gap-2 mb-4">
                <Badge variant="outline" className="flex items-center gap-1">
                  <Wrench className="h-3 w-3" />
                  {job.category}
                </Badge>
                <Badge variant="outline">{job.urgency}</Badge>
              </div>
            </div>
          </div>
          <CardDescription className="text-base">{job.description}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {(job.budget_min || job.budget_max) && (
              <div className="flex items-center gap-2 text-sm">
                <DollarSign className="h-4 w-4 text-muted-foreground" />
                <span className="font-medium">Budget Range:</span>
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

      {/* Bid Form */}
      <Card>
        <CardHeader>
          <CardTitle>Submit Your Bid</CardTitle>
          <CardDescription>
            Provide detailed information about your proposal
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Pricing Section */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">Pricing</h3>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="materials_cost">
                    Materials Cost
                    <span className="text-muted-foreground text-sm ml-1">(optional)</span>
                  </Label>
                  <div className="relative">
                    <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                      id="materials_cost"
                      type="number"
                      step="0.01"
                      min="0"
                      placeholder="0.00"
                      value={formData.materials_cost}
                      onChange={(e) => handleInputChange('materials_cost', e.target.value)}
                      className="pl-9"
                    />
                  </div>
                </div>

                <div>
                  <Label htmlFor="labor_cost">
                    Labor Cost
                    <span className="text-muted-foreground text-sm ml-1">(optional)</span>
                  </Label>
                  <div className="relative">
                    <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                      id="labor_cost"
                      type="number"
                      step="0.01"
                      min="0"
                      placeholder="0.00"
                      value={formData.labor_cost}
                      onChange={(e) => handleInputChange('labor_cost', e.target.value)}
                      className="pl-9"
                    />
                  </div>
                </div>
              </div>

              <div>
                <Label htmlFor="bid_amount">
                  Total Bid Amount <span className="text-red-500">*</span>
                </Label>
                <div className="relative">
                  <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="bid_amount"
                    type="number"
                    step="0.01"
                    min="0"
                    placeholder="0.00"
                    value={formData.bid_amount}
                    onChange={(e) => handleInputChange('bid_amount', e.target.value)}
                    className={`pl-9 ${formErrors.bid_amount ? 'border-red-500' : ''}`}
                    required
                  />
                </div>
                {formErrors.bid_amount && (
                  <p className="text-sm text-red-500 mt-1">{formErrors.bid_amount}</p>
                )}
                {job.budget_min && job.budget_max && (
                  <p className="text-sm text-muted-foreground mt-1">
                    Budget range: ${job.budget_min.toLocaleString()} - $
                    {job.budget_max.toLocaleString()}
                  </p>
                )}
              </div>
            </div>

            {/* Timeline Section */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">Timeline</h3>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="estimated_hours">
                    Estimated Hours <span className="text-red-500">*</span>
                  </Label>
                  <div className="relative">
                    <Clock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                      id="estimated_hours"
                      type="number"
                      step="0.5"
                      min="0"
                      placeholder="0"
                      value={formData.estimated_hours}
                      onChange={(e) => handleInputChange('estimated_hours', e.target.value)}
                      className={`pl-9 ${formErrors.estimated_hours ? 'border-red-500' : ''}`}
                      required
                    />
                  </div>
                  {formErrors.estimated_hours && (
                    <p className="text-sm text-red-500 mt-1">{formErrors.estimated_hours}</p>
                  )}
                </div>

                <div>
                  <Label htmlFor="start_date">
                    When can you start? <span className="text-red-500">*</span>
                  </Label>
                  <div className="relative">
                    <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                      id="start_date"
                      type="date"
                      value={formData.start_date}
                      onChange={(e) => handleInputChange('start_date', e.target.value)}
                      className={`pl-9 ${formErrors.start_date ? 'border-red-500' : ''}`}
                      required
                    />
                  </div>
                  {formErrors.start_date && (
                    <p className="text-sm text-red-500 mt-1">{formErrors.start_date}</p>
                  )}
                </div>
              </div>
            </div>

            {/* Proposal Details */}
            <div>
              <Label htmlFor="proposal_details">
                Proposal Details <span className="text-red-500">*</span>
              </Label>
              <Textarea
                id="proposal_details"
                placeholder="Describe your approach to this job, your relevant experience, and why you're the best fit... (minimum 200 characters)"
                value={formData.proposal_details}
                onChange={(e) => handleInputChange('proposal_details', e.target.value)}
                className={`min-h-[150px] ${formErrors.proposal_details ? 'border-red-500' : ''}`}
                required
              />
              <div className="flex justify-between items-center mt-1">
                {formErrors.proposal_details && (
                  <p className="text-sm text-red-500">{formErrors.proposal_details}</p>
                )}
                <p
                  className={`text-sm ml-auto ${
                    formData.proposal_details.length < 200
                      ? 'text-muted-foreground'
                      : 'text-green-600'
                  }`}
                >
                  {formData.proposal_details.length} / 200 characters
                </p>
              </div>
            </div>

            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting ? (
                <>
                  <Clock className="h-4 w-4 mr-2 animate-spin" />
                  Submitting Bid...
                </>
              ) : (
                <>
                  <CheckCircle2 className="h-4 w-4 mr-2" />
                  Submit Bid
                </>
              )}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
