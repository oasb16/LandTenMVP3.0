'use client';

import React, { useState, useEffect } from 'react';
import { Trophy, Medal, Award, TrendingUp, Star, Zap, Crown } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { getLeaderboard, LeaderboardEntry } from '@/lib/api';

const LEVEL_COLORS = {
  bronze: 'text-orange-700 bg-orange-100',
  silver: 'text-gray-600 bg-gray-200',
  gold: 'text-yellow-600 bg-yellow-100',
  platinum: 'text-purple-600 bg-purple-100',
  diamond: 'text-blue-600 bg-blue-200',
  elite: 'text-pink-600 bg-gradient-to-r from-pink-200 to-purple-200',
};

const LEVEL_ICONS = {
  bronze: <Medal className="inline" size={16} />,
  silver: <Medal className="inline" size={16} />,
  gold: <Trophy className="inline" size={16} />,
  platinum: <Award className="inline" size={16} />,
  diamond: <Star className="inline" size={16} />,
  elite: <Crown className="inline" size={16} />,
};

export default function Leaderboard() {
  const [leaders, setLeaders] = useState<LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<{
    category?: string;
    zipCode?: string;
  }>({});

  useEffect(() => {
    loadLeaderboard();
  }, [filter]);

  const loadLeaderboard = async () => {
    try {
      setLoading(true);
      const data = await getLeaderboard(filter.category, filter.zipCode, 50);
      setLeaders(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load leaderboard');
      console.error('Leaderboard error:', err);
    } finally {
      setLoading(false);
    }
  };

  const getRankIcon = (rank: number) => {
    if (rank === 1) return <Trophy className="text-yellow-500" size={24} />;
    if (rank === 2) return <Medal className="text-gray-400" size={24} />;
    if (rank === 3) return <Medal className="text-orange-600" size={24} />;
    return null;
  };

  const getRankBadge = (rank: number) => {
    if (rank === 1) return 'bg-gradient-to-r from-yellow-400 to-yellow-600 text-white';
    if (rank === 2) return 'bg-gradient-to-r from-gray-300 to-gray-500 text-white';
    if (rank === 3) return 'bg-gradient-to-r from-orange-400 to-orange-600 text-white';
    return 'bg-slate-700 text-slate-300';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-slate-900">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-yellow-500 mx-auto mb-4"></div>
          <p className="text-slate-400">Loading leaderboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-slate-900">
        <Card className="max-w-md">
          <CardHeader>
            <CardTitle className="text-red-400">Error Loading Leaderboard</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-slate-300 mb-4">{error}</p>
            <button
              onClick={loadLeaderboard}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-white font-medium"
            >
              Retry
            </button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-6">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="text-center">
          <h1 className="text-4xl font-bold text-white flex items-center justify-center gap-3 mb-2">
            <Trophy size={40} className="text-yellow-500" />
            Contractor Leaderboard
          </h1>
          <p className="text-slate-400">Top performers in the network</p>
        </div>

        {/* Top 3 Podium */}
        {leaders.length >= 3 && (
          <div className="grid grid-cols-3 gap-4 max-w-4xl mx-auto mb-8">
            {/* 2nd Place */}
            <div className="flex flex-col items-center pt-12">
              <div className="relative">
                <div className="w-20 h-20 rounded-full bg-gradient-to-br from-gray-300 to-gray-500 flex items-center justify-center mb-2 shadow-lg">
                  <span className="text-3xl font-bold text-white">2</span>
                </div>
                <Medal className="absolute -top-2 -right-2 text-gray-400" size={28} />
              </div>
              <p className="font-semibold text-white text-lg mt-2">{leaders[1].display_name}</p>
              <p className="text-sm text-slate-400 capitalize">{leaders[1].level}</p>
              <p className="text-2xl font-bold text-blue-400 mt-1">{leaders[1].score}</p>
              <p className="text-xs text-slate-500">{leaders[1].jobs_completed} jobs</p>
            </div>

            {/* 1st Place */}
            <div className="flex flex-col items-center">
              <div className="relative">
                <div className="w-24 h-24 rounded-full bg-gradient-to-br from-yellow-400 to-yellow-600 flex items-center justify-center mb-2 shadow-xl shadow-yellow-500/50">
                  <span className="text-4xl font-bold text-white">1</span>
                </div>
                <Crown className="absolute -top-6 left-1/2 transform -translate-x-1/2 text-yellow-400" size={36} />
              </div>
              <p className="font-bold text-white text-xl mt-2">{leaders[0].display_name}</p>
              <p className="text-sm text-yellow-400 capitalize font-semibold">{leaders[0].level}</p>
              <p className="text-3xl font-bold text-yellow-400 mt-1">{leaders[0].score}</p>
              <p className="text-xs text-slate-400">{leaders[0].jobs_completed} jobs completed</p>
            </div>

            {/* 3rd Place */}
            <div className="flex flex-col items-center pt-12">
              <div className="relative">
                <div className="w-20 h-20 rounded-full bg-gradient-to-br from-orange-400 to-orange-600 flex items-center justify-center mb-2 shadow-lg">
                  <span className="text-3xl font-bold text-white">3</span>
                </div>
                <Medal className="absolute -top-2 -right-2 text-orange-600" size={28} />
              </div>
              <p className="font-semibold text-white text-lg mt-2">{leaders[2].display_name}</p>
              <p className="text-sm text-slate-400 capitalize">{leaders[2].level}</p>
              <p className="text-2xl font-bold text-blue-400 mt-1">{leaders[2].score}</p>
              <p className="text-xs text-slate-500">{leaders[2].jobs_completed} jobs</p>
            </div>
          </div>
        )}

        {/* Full Leaderboard Table */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp size={20} />
              Full Rankings
            </CardTitle>
            <CardDescription>{leaders.length} contractors on the leaderboard</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {leaders.map((entry, index) => (
                <div
                  key={entry.contractor_id}
                  className={`flex items-center gap-4 p-4 rounded-lg transition ${
                    entry.rank <= 3
                      ? 'bg-gradient-to-r from-blue-900/30 to-purple-900/30 border border-blue-500/30'
                      : 'bg-slate-800/50 hover:bg-slate-800'
                  }`}
                >
                  {/* Rank */}
                  <div className="w-16 flex items-center justify-center">
                    {getRankIcon(entry.rank) || (
                      <div
                        className={`w-10 h-10 rounded-full ${getRankBadge(entry.rank)} flex items-center justify-center font-bold`}
                      >
                        {entry.rank}
                      </div>
                    )}
                  </div>

                  {/* Name & Level */}
                  <div className="flex-1">
                    <p className="font-semibold text-white">{entry.display_name}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <span
                        className={`text-xs px-2 py-1 rounded-full capitalize ${
                          LEVEL_COLORS[entry.level as keyof typeof LEVEL_COLORS]
                        }`}
                      >
                        {LEVEL_ICONS[entry.level as keyof typeof LEVEL_ICONS]} {entry.level}
                      </span>
                      <span className="text-xs text-slate-500">{entry.badges_count} badges</span>
                    </div>
                  </div>

                  {/* Stats */}
                  <div className="text-right">
                    <p className="text-2xl font-bold text-blue-400">{entry.score}</p>
                    <p className="text-xs text-slate-500">score</p>
                  </div>

                  <div className="text-right">
                    <p className="text-lg font-semibold text-white">{entry.jobs_completed}</p>
                    <p className="text-xs text-slate-500">jobs</p>
                  </div>

                  <div className="text-right">
                    <div className="flex items-center gap-1">
                      <Star size={16} className="text-yellow-500 fill-yellow-500" />
                      <span className="font-semibold text-white">{entry.rating.toFixed(1)}</span>
                    </div>
                    <p className="text-xs text-slate-500">rating</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Stats Summary */}
        <div className="grid grid-cols-3 gap-4">
          <Card>
            <CardContent className="pt-6 text-center">
              <Trophy className="mx-auto mb-2 text-yellow-500" size={32} />
              <p className="text-2xl font-bold text-white">{leaders.length}</p>
              <p className="text-sm text-slate-400">Total Contractors</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6 text-center">
              <Zap className="mx-auto mb-2 text-blue-500" size={32} />
              <p className="text-2xl font-bold text-white">
                {leaders[0]?.score || 0}
              </p>
              <p className="text-sm text-slate-400">Top Score</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6 text-center">
              <Star className="mx-auto mb-2 text-purple-500" size={32} />
              <p className="text-2xl font-bold text-white">
                {(leaders.reduce((sum, l) => sum + l.rating, 0) / leaders.length || 0).toFixed(1)}
              </p>
              <p className="text-sm text-slate-400">Avg Rating</p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
