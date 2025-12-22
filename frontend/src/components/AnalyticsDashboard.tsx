'use client';

import React, { useState, useEffect } from 'react';
import { BarChart3, Users, TrendingUp, TrendingDown, Activity, AlertCircle, CheckCircle, XCircle, Minus } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { getAnalyticsDashboard, AnalyticsDashboard } from '@/lib/api';

export default function AnalyticsDashboardComponent() {
  const [data, setData] = useState<AnalyticsDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const dashboardData = await getAnalyticsDashboard();
      setData(dashboardData);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load analytics');
      console.error('Analytics error:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-slate-900">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-slate-400">Loading analytics...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-slate-900">
        <Card className="max-w-md">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-red-400">
              <AlertCircle size={20} />
              Error Loading Analytics
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-slate-300 mb-4">{error}</p>
            <button
              onClick={loadData}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-white font-medium"
            >
              Retry
            </button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!data) return null;

  const { summary, trends, satisfaction, personas } = data;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white flex items-center gap-3">
              <BarChart3 size={32} className="text-blue-400" />
              Analytics Dashboard
            </h1>
            <p className="text-slate-400 mt-1">AI Support Performance Metrics</p>
          </div>
          <button
            onClick={loadData}
            className="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-white font-medium transition"
          >
            Refresh
          </button>
        </div>

        {/* Summary Stats */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Total Sessions</CardDescription>
              <CardTitle className="text-3xl">{summary.total_sessions || 0}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-slate-400 flex items-center gap-1">
                <Activity size={14} />
                All personas combined
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Completion Rate</CardDescription>
              <CardTitle className="text-3xl text-green-400">
                {((summary.completion_rate || 0) * 100).toFixed(1)}%
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-slate-400 flex items-center gap-1">
                <TrendingUp size={14} />
                Successfully completed
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Satisfaction Score</CardDescription>
              <CardTitle className="text-3xl text-blue-400">
                {satisfaction.overall_score || 0}/100
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex gap-2 text-xs">
                <span className="text-green-400">😊 {satisfaction.satisfied || 0}</span>
                <span className="text-yellow-400">😐 {satisfaction.neutral || 0}</span>
                <span className="text-red-400">😞 {satisfaction.unsatisfied || 0}</span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Abandoned Sessions</CardDescription>
              <CardTitle className="text-3xl text-orange-400">
                {satisfaction.abandoned || 0}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-slate-400 flex items-center gap-1">
                <XCircle size={14} />
                Users left mid-flow
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Persona Breakdown */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users size={20} />
              Sessions by Persona
            </CardTitle>
            <CardDescription>Distribution across user roles</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {Object.entries(summary.personas || {}).map(([persona, count]) => (
                <div key={persona} className="text-center p-4 bg-slate-800/50 rounded-lg">
                  <p className="text-sm text-slate-400 capitalize mb-1">{persona}</p>
                  <p className="text-2xl font-bold text-white">{count}</p>
                  <p className="text-xs text-slate-500 mt-1">
                    {summary.total_sessions > 0
                      ? ((count / summary.total_sessions) * 100).toFixed(1)
                      : 0}%
                  </p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Issue Trends */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp size={20} />
              Top Issue Reasons
            </CardTitle>
            <CardDescription>
              {trends.total_issues || 0} total issues reported
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {(trends.reasons || []).slice(0, 10).map((reason, index) => (
                <div key={index} className="flex items-center gap-3">
                  <div className="w-32 text-sm text-slate-300 truncate" title={reason.name}>
                    {reason.name}
                  </div>
                  <div className="flex-1 bg-slate-700/50 rounded-full h-6 overflow-hidden">
                    <div
                      className="bg-gradient-to-r from-blue-500 to-purple-500 h-full flex items-center justify-end pr-2"
                      style={{ width: `${reason.percentage || 0}%` }}
                    >
                      <span className="text-xs text-white font-medium">
                        {reason.percentage?.toFixed(1)}%
                      </span>
                    </div>
                  </div>
                  <div className="w-12 text-right text-sm text-slate-400">
                    {reason.count}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Top Actions & CTAs */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Top User Actions</CardTitle>
              <CardDescription>Most common completion actions</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {(summary.top_actions || []).slice(0, 5).map((action, index) => (
                  <div key={index} className="flex justify-between items-center p-2 bg-slate-800/50 rounded-lg">
                    <span className="text-sm text-slate-300">{action.name}</span>
                    <span className="text-sm font-semibold text-blue-400">{action.count}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Top CTAs</CardTitle>
              <CardDescription>Most clicked call-to-actions</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {(summary.top_ctas || []).slice(0, 5).map((cta, index) => (
                  <div key={index} className="flex justify-between items-center p-2 bg-slate-800/50 rounded-lg">
                    <span className="text-sm text-slate-300">{cta.name}</span>
                    <span className="text-sm font-semibold text-purple-400">{cta.count}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Persona Detailed Stats */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {['tenant', 'landlord', 'contractor', 'property_manager'].map((personaKey) => {
            const personaData = personas[personaKey as keyof typeof personas];
            if (!personaData) return null;

            return (
              <Card key={personaKey}>
                <CardHeader>
                  <CardTitle className="capitalize flex items-center gap-2">
                    <Users size={18} />
                    {personaKey} Analytics
                  </CardTitle>
                  <CardDescription>
                    {personaData.total_sessions || 0} sessions •{' '}
                    {((personaData.completion_rate || 0) * 100).toFixed(1)}% completion
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <p className="text-xs text-slate-400 mb-2">Top Reasons</p>
                    <div className="space-y-1">
                      {(personaData.top_reasons || []).slice(0, 3).map((reason, index) => (
                        <div key={index} className="flex justify-between text-sm">
                          <span className="text-slate-300">{reason.name}</span>
                          <span className="text-slate-500">{reason.count}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div>
                    <p className="text-xs text-slate-400 mb-2">Top Actions</p>
                    <div className="space-y-1">
                      {(personaData.top_actions || []).slice(0, 3).map((action, index) => (
                        <div key={index} className="flex justify-between text-sm">
                          <span className="text-slate-300">{action.name}</span>
                          <span className="text-slate-500">{action.count}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* Dropoff Stages */}
        {Object.keys(summary.dropoff_stages || {}).length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingDown size={20} />
                Dropoff Stages
              </CardTitle>
              <CardDescription>Where users abandon the flow</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {Object.entries(summary.dropoff_stages || {}).map(([stage, count]) => (
                  <div key={stage} className="text-center p-4 bg-red-900/20 rounded-lg border border-red-500/30">
                    <p className="text-sm text-slate-400 mb-1">{stage}</p>
                    <p className="text-2xl font-bold text-red-400">{count}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
