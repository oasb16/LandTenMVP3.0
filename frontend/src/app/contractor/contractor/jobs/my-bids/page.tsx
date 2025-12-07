'use client';

import { useState, useEffect } from 'react';
import { BidCard } from '@/components/contractor/BidCard';
import { Card } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { FileText, AlertCircle } from 'lucide-react';

interface Bid {
  id: string;
  bid_amount: number;
  status: 'PENDING' | 'UNDER_REVIEW' | 'ACCEPTED' | 'REJECTED';
  submitted_at: string;
  job: {
    id: string;
    title: string;
    category: string;
  };
}

function BidSkeleton() {
  return (
    <Card>
      <div className="p-6 space-y-4">
        <div className="flex justify-between items-start">
          <div className="space-y-2 flex-1">
            <Skeleton className="h-6 w-3/4" />
            <Skeleton className="h-5 w-24" />
          </div>
          <Skeleton className="h-6 w-24" />
        </div>
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-4 w-1/2" />
      </div>
    </Card>
  );
}

export default function MyBidsPage() {
  const [bids, setBids] = useState<Bid[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('all');

  useEffect(() => {
    fetchMyBids();

    // Poll for updates every 30 seconds
    const interval = setInterval(() => {
      fetchMyBids();
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  const fetchMyBids = async () => {
    try {
      if (loading) setLoading(true);
      setError(null);

      const response = await fetch('/api/v1/jobs/contractor/my-bids', {
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error('Failed to fetch bids');
      }

      const data = await response.json();
      setBids(data.bids || []);
    } catch (err) {
      console.error('Error fetching bids:', err);
      setError(err instanceof Error ? err.message : 'Failed to load bids');
    } finally {
      setLoading(false);
    }
  };

  const filterBidsByStatus = (status?: string) => {
    if (!status || status === 'all') return bids;
    if (status === 'under_review') return bids.filter((bid) => bid.status === 'UNDER_REVIEW');
    return bids.filter((bid) => bid.status === status.toUpperCase());
  };

  const getTabCount = (status?: string) => {
    return filterBidsByStatus(status).length;
  };

  const EmptyState = ({ message }: { message: string }) => (
    <Card className="p-12">
      <div className="text-center">
        <FileText className="h-16 w-16 mx-auto mb-4 text-muted-foreground" />
        <h3 className="text-xl font-semibold mb-2">No bids found</h3>
        <p className="text-muted-foreground">{message}</p>
      </div>
    </Card>
  );

  const renderBidsList = (filteredBids: Bid[]) => {
    if (filteredBids.length === 0) {
      const messages = {
        all: 'You haven\'t submitted any bids yet',
        under_review: 'No bids are currently under review',
        accepted: 'You don\'t have any accepted bids yet',
        rejected: 'You don\'t have any rejected bids',
      };
      return <EmptyState message={messages[activeTab as keyof typeof messages]} />;
    }

    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredBids.map((bid) => (
          <BidCard key={bid.id} bid={bid} />
        ))}
      </div>
    );
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">My Bids</h1>
        <p className="text-muted-foreground">
          Track the status of your submitted bids
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
            <BidSkeleton key={i} />
          ))}
        </div>
      ) : (
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-4 lg:w-[600px]">
            <TabsTrigger value="all" className="relative">
              All
              {getTabCount('all') > 0 && (
                <span className="ml-2 rounded-full bg-primary/20 px-2 py-0.5 text-xs">
                  {getTabCount('all')}
                </span>
              )}
            </TabsTrigger>
            <TabsTrigger value="under_review" className="relative">
              Under Review
              {getTabCount('under_review') > 0 && (
                <span className="ml-2 rounded-full bg-blue-500/20 px-2 py-0.5 text-xs">
                  {getTabCount('under_review')}
                </span>
              )}
            </TabsTrigger>
            <TabsTrigger value="accepted" className="relative">
              Accepted
              {getTabCount('accepted') > 0 && (
                <span className="ml-2 rounded-full bg-green-500/20 px-2 py-0.5 text-xs">
                  {getTabCount('accepted')}
                </span>
              )}
            </TabsTrigger>
            <TabsTrigger value="rejected" className="relative">
              Rejected
              {getTabCount('rejected') > 0 && (
                <span className="ml-2 rounded-full bg-red-500/20 px-2 py-0.5 text-xs">
                  {getTabCount('rejected')}
                </span>
              )}
            </TabsTrigger>
          </TabsList>

          <TabsContent value="all" className="space-y-4">
            {renderBidsList(filterBidsByStatus('all'))}
          </TabsContent>

          <TabsContent value="under_review" className="space-y-4">
            {renderBidsList(filterBidsByStatus('under_review'))}
          </TabsContent>

          <TabsContent value="accepted" className="space-y-4">
            {renderBidsList(filterBidsByStatus('accepted'))}
          </TabsContent>

          <TabsContent value="rejected" className="space-y-4">
            {renderBidsList(filterBidsByStatus('rejected'))}
          </TabsContent>
        </Tabs>
      )}
    </div>
  );
}
