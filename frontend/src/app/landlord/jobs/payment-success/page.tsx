'use client';

import { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  CheckCircle2,
  AlertCircle,
  DollarSign,
  User,
  Briefcase,
  ArrowRight,
  Clock,
} from 'lucide-react';

interface PaymentDetails {
  job: {
    id: string;
    title: string;
  };
  contractor: {
    first_name: string;
    last_name: string;
  };
  amount: number;
  payment_intent_id: string;
  paid_at: string;
}

export default function PaymentSuccessPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-slate-200">Loading payment details...</div>}>
      <PaymentSuccessContent />
    </Suspense>
  );
}

function PaymentSuccessContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const jobId = searchParams.get('job_id');
  const paymentIntentId = searchParams.get('payment_intent');

  const [paymentDetails, setPaymentDetails] = useState<PaymentDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (paymentIntentId) {
      verifyPayment();
    } else {
      setError('Missing payment information');
      setLoading(false);
    }
  }, [paymentIntentId]);

  const verifyPayment = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(
        `/api/v1/payments/verify?payment_intent=${paymentIntentId}&job_id=${jobId}`,
        {
          credentials: 'include',
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to verify payment');
      }

      const data = await response.json();
      setPaymentDetails(data);
    } catch (err) {
      console.error('Error verifying payment:', err);
      setError(err instanceof Error ? err.message : 'Failed to verify payment');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-2xl">
        <Card className="p-12">
          <div className="text-center">
            <Skeleton className="h-20 w-20 rounded-full mx-auto mb-4" />
            <Skeleton className="h-8 w-64 mx-auto mb-2" />
            <Skeleton className="h-4 w-96 mx-auto mb-8" />
            <div className="space-y-4 max-w-md mx-auto">
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-16 w-full" />
            </div>
          </div>
        </Card>
      </div>
    );
  }

  if (error || !paymentDetails) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-2xl">
        <Card className="p-12">
          <div className="text-center">
            <AlertCircle className="h-20 w-20 text-red-500 mx-auto mb-4" />
            <h1 className="text-3xl font-bold mb-2">Payment Verification Failed</h1>
            <p className="text-muted-foreground mb-6">
              {error || 'Unable to verify your payment. Please contact support if you were charged.'}
            </p>
            <Button onClick={() => router.push('/landlord/jobs')}>
              Back to Jobs
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-2xl">
      <Card className="overflow-hidden">
        {/* Success Header with Green Background */}
        <div className="bg-green-50 border-b border-green-100 p-12">
          <div className="text-center">
            <div className="relative inline-block">
              <div className="absolute inset-0 bg-green-500 rounded-full animate-ping opacity-25" />
              <CheckCircle2 className="h-20 w-20 text-green-600 mx-auto relative" />
            </div>
            <h1 className="text-3xl font-bold text-green-900 mt-4 mb-2">
              Payment Successful!
            </h1>
            <p className="text-green-700">
              Your payment has been processed successfully
            </p>
          </div>
        </div>

        <CardContent className="p-8">
          {/* Payment Details */}
          <div className="space-y-6">
            {/* Amount Paid */}
            <div className="bg-muted rounded-lg p-6 text-center">
              <p className="text-sm text-muted-foreground mb-1">Amount Paid</p>
              <div className="flex items-center justify-center gap-2">
                <DollarSign className="h-8 w-8 text-primary" />
                <span className="text-4xl font-bold text-primary">
                  {paymentDetails.amount.toLocaleString()}
                </span>
              </div>
            </div>

            {/* Job Details */}
            <div className="border rounded-lg p-4 space-y-3">
              <div className="flex items-start gap-3">
                <Briefcase className="h-5 w-5 text-muted-foreground mt-0.5" />
                <div className="flex-1">
                  <p className="text-sm text-muted-foreground">Job</p>
                  <p className="font-semibold">{paymentDetails.job.title}</p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <User className="h-5 w-5 text-muted-foreground mt-0.5" />
                <div className="flex-1">
                  <p className="text-sm text-muted-foreground">Contractor</p>
                  <p className="font-semibold">
                    {paymentDetails.contractor.first_name}{' '}
                    {paymentDetails.contractor.last_name}
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <Clock className="h-5 w-5 text-muted-foreground mt-0.5" />
                <div className="flex-1">
                  <p className="text-sm text-muted-foreground">Payment Date</p>
                  <p className="font-semibold">
                    {new Date(paymentDetails.paid_at).toLocaleString('en-US', {
                      month: 'long',
                      day: 'numeric',
                      year: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </p>
                </div>
              </div>
            </div>

            {/* Payment Reference */}
            <div className="bg-blue-50 border border-blue-100 rounded-lg p-4">
              <p className="text-sm text-blue-900 font-medium mb-1">
                Payment Reference
              </p>
              <p className="text-xs text-blue-700 font-mono break-all">
                {paymentDetails.payment_intent_id}
              </p>
            </div>

            {/* Payout Info */}
            <Alert>
              <Clock className="h-4 w-4" />
              <AlertDescription>
                <strong>Contractor Payout Timeline</strong>
                <p className="text-sm mt-1">
                  The contractor will receive their payment within 24 hours. You'll
                  receive a confirmation email with your receipt shortly.
                </p>
              </AlertDescription>
            </Alert>

            {/* Action Buttons */}
            <div className="flex flex-col sm:flex-row gap-3 pt-4">
              <Button
                variant="outline"
                onClick={() => router.push(`/landlord/jobs/${paymentDetails.job.id}`)}
                className="flex-1"
              >
                View Job Details
              </Button>
              <Button
                onClick={() => router.push('/landlord/jobs')}
                className="flex-1"
              >
                Back to Jobs
                <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Additional Info */}
      <div className="mt-6 text-center text-sm text-muted-foreground">
        <p>
          Need help? Contact our support team at{' '}
          <a href="mailto:support@landten.com" className="text-primary hover:underline">
            support@landten.com
          </a>
        </p>
      </div>
    </div>
  );
}
