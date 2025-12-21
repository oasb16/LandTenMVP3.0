"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { CheckCircle2, Lock, TrendingUp, Users, Zap, Trophy, DollarSign, Target, Star, Award } from "lucide-react";

interface OnboardingStatus {
  contractor_id: string;
  onboarding_license_submitted: boolean;
  onboarding_license_verified: boolean;
  onboarding_identity_verified: boolean;
  onboarding_payment_setup: boolean;
  onboarding_complete: boolean;
  onboarding_current_step: string;
}

interface Props {
  onboardingStatus: OnboardingStatus | null;
  contractorEmail: string | null;
}

export default function ContractorOnboardingDashboardPro({ onboardingStatus, contractorEmail }: Props) {
  // Calculate progress percentage
  const calculateProgress = () => {
    if (!onboardingStatus) return 0;
    let progress = 0;
    if (onboardingStatus.onboarding_license_submitted) progress += 25;
    if (onboardingStatus.onboarding_identity_verified) progress += 25;
    if (onboardingStatus.onboarding_payment_setup) progress += 25;
    if (onboardingStatus.onboarding_complete) progress += 25;
    return progress;
  };

  const progress = calculateProgress();
  const isUnlocked = onboardingStatus?.onboarding_complete || false;

  return (
    <div className={`flex-1 overflow-y-auto p-6 transition-opacity duration-300 ${!isUnlocked ? 'opacity-40 pointer-events-none' : ''}`}>
      <div className="max-w-6xl mx-auto space-y-6">

        {/* Header with Progress */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Contractor Dashboard</h1>
            <p className="text-gray-600 mt-1">Welcome to HomeAI Pro - Your Path to Financial Freedom</p>
          </div>
          {!isUnlocked && (
            <div className="flex flex-col items-end gap-2">
              <div className="flex items-center gap-2 text-amber-600 bg-amber-50 px-4 py-2 rounded-lg">
                <Lock className="h-5 w-5" />
                <span className="font-medium">Complete onboarding to unlock</span>
              </div>
              <div className="text-sm text-gray-600">
                {progress}% Complete - Almost there! 🎯
              </div>
            </div>
          )}
        </div>

        {/* Progress Bar */}
        {!isUnlocked && (
          <div className="bg-gradient-to-r from-blue-50 to-purple-50 p-6 rounded-xl border-2 border-blue-200">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-semibold text-gray-700">Onboarding Progress</span>
              <span className="text-sm font-bold text-blue-600">{progress}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-3 mb-4">
              <div
                className="bg-gradient-to-r from-blue-500 to-purple-500 h-3 rounded-full transition-all duration-500"
                style={{ width: `${progress}%` }}
              />
            </div>
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <Zap className="h-4 w-4 text-yellow-500" />
              <span className="font-medium">Speed Bonus Active: Complete in 5 minutes, get $50 on first job!</span>
            </div>
          </div>
        )}

        {/* Success Stories / Social Proof */}
        {!isUnlocked && (
          <Card className="bg-gradient-to-br from-green-50 to-emerald-50 border-green-200">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Trophy className="h-5 w-5 text-green-600" />
                Success Stories - Contractors Like You
              </CardTitle>
              <CardDescription>See what's possible on HomeAI Pro</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-white p-4 rounded-lg shadow-sm">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center text-white font-bold">
                      M
                    </div>
                    <div>
                      <p className="font-semibold text-sm">Mike R.</p>
                      <p className="text-xs text-gray-500">Plumbing • SF</p>
                    </div>
                  </div>
                  <div className="text-2xl font-bold text-green-600">$18,500</div>
                  <p className="text-xs text-gray-600">First 3 months</p>
                  <div className="flex items-center gap-1 mt-2">
                    <Star className="h-3 w-3 text-yellow-500 fill-yellow-500" />
                    <span className="text-xs font-semibold">4.9 • 47 jobs</span>
                  </div>
                </div>

                <div className="bg-white p-4 rounded-lg shadow-sm">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-10 h-10 rounded-full bg-purple-600 flex items-center justify-center text-white font-bold">
                      S
                    </div>
                    <div>
                      <p className="font-semibold text-sm">Sarah C.</p>
                      <p className="text-xs text-gray-500">Electrical • TX</p>
                    </div>
                  </div>
                  <div className="text-2xl font-bold text-green-600">$6,800/wk</div>
                  <p className="text-xs text-gray-600">6 months on platform</p>
                  <div className="flex items-center gap-1 mt-2">
                    <Star className="h-3 w-3 text-yellow-500 fill-yellow-500" />
                    <span className="text-xs font-semibold">5.0 • 124 jobs</span>
                  </div>
                </div>

                <div className="bg-white p-4 rounded-lg shadow-sm">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-10 h-10 rounded-full bg-orange-600 flex items-center justify-center text-white font-bold">
                      J
                    </div>
                    <div>
                      <p className="font-semibold text-sm">James T.</p>
                      <p className="text-xs text-gray-500">HVAC • AZ</p>
                    </div>
                  </div>
                  <div className="text-2xl font-bold text-green-600">$112K</div>
                  <p className="text-xs text-gray-600">First year total</p>
                  <div className="flex items-center gap-1 mt-2">
                    <Star className="h-3 w-3 text-yellow-500 fill-yellow-500" />
                    <span className="text-xs font-semibold">4.8 • 284 jobs</span>
                  </div>
                </div>
              </div>
              <div className="mt-4 p-3 bg-white rounded-lg">
                <p className="text-sm italic text-gray-700">
                  "I was skeptical at first, but after my first week earning $2,400, I quit my old job. Best decision ever!" - Mike R.
                </p>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Earnings Potential */}
        {!isUnlocked && (
          <Card className="bg-gradient-to-br from-blue-50 to-indigo-50 border-blue-200">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <DollarSign className="h-5 w-5 text-blue-600" />
                Your Earning Potential
              </CardTitle>
              <CardDescription>Based on contractors in your area</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-4 gap-4">
                <div className="text-center p-4 bg-white rounded-lg shadow-sm">
                  <TrendingUp className="h-6 w-6 text-green-500 mx-auto mb-2" />
                  <p className="text-sm text-gray-600">Average Weekly</p>
                  <p className="text-2xl font-bold text-gray-900">$4,200</p>
                </div>
                <div className="text-center p-4 bg-white rounded-lg shadow-sm">
                  <Target className="h-6 w-6 text-blue-500 mx-auto mb-2" />
                  <p className="text-sm text-gray-600">Top 10% Weekly</p>
                  <p className="text-2xl font-bold text-blue-600">$8,500</p>
                </div>
                <div className="text-center p-4 bg-white rounded-lg shadow-sm">
                  <Zap className="h-6 w-6 text-yellow-500 mx-auto mb-2" />
                  <p className="text-sm text-gray-600">Jobs Available</p>
                  <p className="text-2xl font-bold text-yellow-600">47</p>
                </div>
                <div className="text-center p-4 bg-white rounded-lg shadow-sm">
                  <Users className="h-6 w-6 text-purple-500 mx-auto mb-2" />
                  <p className="text-sm text-gray-600">Avg Job Value</p>
                  <p className="text-2xl font-bold text-purple-600">$385</p>
                </div>
              </div>
              <div className="mt-4 p-4 bg-gradient-to-r from-green-500 to-emerald-500 text-white rounded-lg">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm opacity-90">Projected Annual Earnings</p>
                    <p className="text-3xl font-bold">$218,400</p>
                    <p className="text-xs opacity-75">Based on average weekly performance</p>
                  </div>
                  <Trophy className="h-12 w-12 opacity-50" />
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Live Stats / Social Proof */}
        <div className="grid grid-cols-3 gap-4">
          <Card className="bg-gradient-to-br from-purple-50 to-pink-50">
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <Users className="h-8 w-8 text-purple-600" />
                <div>
                  <p className="text-2xl font-bold text-purple-600">2,847</p>
                  <p className="text-sm text-gray-600">Contractors joined this month</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-green-50 to-teal-50">
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <CheckCircle2 className="h-8 w-8 text-green-600" />
                <div>
                  <p className="text-2xl font-bold text-green-600">95%</p>
                  <p className="text-sm text-gray-600">Get first job in 24 hours</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-yellow-50 to-orange-50">
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <DollarSign className="h-8 w-8 text-yellow-600" />
                <div>
                  <p className="text-2xl font-bold text-yellow-600">$45M</p>
                  <p className="text-sm text-gray-600">Paid to contractors in 2024</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Profile Section */}
        <Card className={onboardingStatus?.onboarding_license_verified ? 'border-green-200 shadow-lg shadow-green-100' : ''}>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                Profile
                {onboardingStatus?.onboarding_license_verified && (
                  <>
                    <CheckCircle2 className="h-5 w-5 text-green-600" />
                    <span className="text-sm font-normal text-green-600">Verified ✓</span>
                  </>
                )}
              </CardTitle>
              {onboardingStatus?.onboarding_license_verified && (
                <Award className="h-6 w-6 text-yellow-500" />
              )}
            </div>
            <CardDescription>Your business information</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-gray-600">Business Name</p>
                <p className="font-medium">Your Business Name</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">License Number</p>
                <p className="font-medium">License #XXXXX</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Email</p>
                <p className="font-medium">{contractorEmail}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Service Areas</p>
                <p className="font-medium">ZIP codes</p>
              </div>
            </div>
            {onboardingStatus?.onboarding_license_verified && (
              <div className="mt-4 p-3 bg-green-50 rounded-lg border border-green-200">
                <p className="text-sm text-green-800 font-medium">
                  🏆 Achievement Unlocked: Verified Professional Badge (+40% job win rate)
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Jobs Section */}
        <Card className={onboardingStatus?.onboarding_identity_verified ? 'border-green-200 shadow-lg shadow-green-100' : ''}>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                Available Jobs
                {onboardingStatus?.onboarding_identity_verified && (
                  <>
                    <CheckCircle2 className="h-5 w-5 text-green-600" />
                    <span className="text-sm font-normal text-green-600">Unlocked ✓</span>
                  </>
                )}
              </CardTitle>
              {!onboardingStatus?.onboarding_identity_verified && (
                <div className="px-3 py-1 bg-red-100 text-red-700 text-xs font-semibold rounded-full">
                  🔥 47 Hot Jobs Waiting
                </div>
              )}
            </div>
            <CardDescription>Jobs you can bid on</CardDescription>
          </CardHeader>
          <CardContent>
            {isUnlocked ? (
              <div className="space-y-3">
                <div className="p-4 bg-gradient-to-r from-blue-50 to-blue-100 rounded-lg border-2 border-blue-300">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-semibold text-blue-900">Emergency Plumbing - Broken Pipe</span>
                    <span className="text-xl font-bold text-green-600">$450</span>
                  </div>
                  <p className="text-sm text-gray-700 mb-2">Urgent: Water leak in kitchen, need immediate assistance</p>
                  <div className="flex items-center gap-4 text-xs text-gray-600">
                    <span>📍 2.3 miles away</span>
                    <span>⏰ Posted 15 min ago</span>
                    <span className="text-red-600 font-semibold">🔥 3 bids already</span>
                  </div>
                </div>
                <div className="p-4 bg-white rounded-lg border border-gray-200">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-semibold">HVAC Maintenance Check</span>
                    <span className="text-xl font-bold text-green-600">$285</span>
                  </div>
                  <p className="text-sm text-gray-700 mb-2">Annual maintenance for 3-ton AC unit</p>
                  <div className="flex items-center gap-4 text-xs text-gray-600">
                    <span>📍 4.7 miles away</span>
                    <span>⏰ Posted 1 hour ago</span>
                    <span>1 bid</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                <Lock className="h-12 w-12 mx-auto mb-3 text-gray-400" />
                <p className="font-medium">47 jobs waiting for you!</p>
                <p className="text-sm mt-2">Complete identity verification to see and bid on jobs</p>
                <div className="mt-4 p-3 bg-yellow-50 rounded-lg border border-yellow-200">
                  <p className="text-sm text-yellow-800 font-medium">
                    ⚡ Speed up! 12 jobs posted in the last hour alone
                  </p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Payments Section */}
        <Card className={onboardingStatus?.onboarding_payment_setup ? 'border-green-200 shadow-lg shadow-green-100' : ''}>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                Payments
                {onboardingStatus?.onboarding_payment_setup && (
                  <>
                    <CheckCircle2 className="h-5 w-5 text-green-600" />
                    <span className="text-sm font-normal text-green-600">Ready ✓</span>
                  </>
                )}
              </CardTitle>
            </div>
            <CardDescription>Your earnings and payouts</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-4">
              <div className="text-center p-4 bg-gradient-to-br from-green-50 to-emerald-50 rounded-lg border border-green-200">
                <DollarSign className="h-6 w-6 text-green-600 mx-auto mb-1" />
                <p className="text-sm text-gray-600">Total Earnings</p>
                <p className="text-2xl font-bold text-green-600">$0</p>
                <p className="text-xs text-gray-500 mt-1">Start your first job!</p>
              </div>
              <div className="text-center p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-600">Pending</p>
                <p className="text-2xl font-bold text-gray-900">$0</p>
              </div>
              <div className="text-center p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-600">Paid Out</p>
                <p className="text-2xl font-bold text-gray-900">$0</p>
              </div>
            </div>
            {onboardingStatus?.onboarding_payment_setup && (
              <div className="mt-4 p-4 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-lg">
                <div className="flex items-center gap-3">
                  <Zap className="h-8 w-8" />
                  <div>
                    <p className="font-bold">First Job Bonus Active!</p>
                    <p className="text-sm opacity-90">Complete your first job and earn an extra $50 bonus</p>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Onboarding Complete Celebration */}
        {isUnlocked && (
          <Card className="bg-gradient-to-r from-green-500 to-emerald-600 text-white">
            <CardContent className="pt-6">
              <div className="text-center">
                <Trophy className="h-16 w-16 mx-auto mb-4" />
                <h2 className="text-3xl font-bold mb-2">🎉 Congratulations! You're LIVE!</h2>
                <p className="text-lg opacity-90 mb-6">Your contractor dashboard is now fully unlocked</p>

                <div className="grid grid-cols-3 gap-4 mb-6">
                  <div className="bg-white/20 backdrop-blur rounded-lg p-4">
                    <p className="text-sm opacity-75">Your Level</p>
                    <p className="text-2xl font-bold">Bronze 1</p>
                  </div>
                  <div className="bg-white/20 backdrop-blur rounded-lg p-4">
                    <p className="text-sm opacity-75">Contractor Score</p>
                    <p className="text-2xl font-bold">85/100</p>
                  </div>
                  <div className="bg-white/20 backdrop-blur rounded-lg p-4">
                    <p className="text-sm opacity-75">Jobs Available</p>
                    <p className="text-2xl font-bold">47</p>
                  </div>
                </div>

                <div className="bg-white/10 backdrop-blur rounded-lg p-4">
                  <p className="font-bold mb-2">Your Bonuses & Perks:</p>
                  <ul className="text-sm space-y-1 text-left max-w-md mx-auto">
                    <li>✅ $50 bonus on first completed job</li>
                    <li>✅ First job guaranteed within 48 hours</li>
                    <li>✅ 30 days free premium listing ($29 value)</li>
                    <li>✅ Refer 3 friends = $150 bonus</li>
                    <li>✅ Priority customer support</li>
                  </ul>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
