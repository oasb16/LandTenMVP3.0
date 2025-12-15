"use client";

import React from 'react';
import { motion } from 'framer-motion';
import {
  AlertCircle,
  Search,
  Wrench,
  CheckSquare,
  Calendar,
  CheckCircle2,
  type LucideIcon,
} from 'lucide-react';

interface TimelineStage {
  id: string;
  label: string;
  icon: LucideIcon;
  status: 'completed' | 'current' | 'pending';
}

interface IncidentTimelineProps {
  currentStage?: string;
  incidentId?: string;
  onStageClick?: (stageId: string) => void;
  compact?: boolean;
}

export function IncidentTimeline({
  currentStage = 'incident',
  incidentId,
  onStageClick,
  compact = false,
}: IncidentTimelineProps) {
  const stages: TimelineStage[] = [
    {
      id: 'incident',
      label: 'Reported',
      icon: AlertCircle,
      status: getStageStatus('incident', currentStage),
    },
    {
      id: 'discovery',
      label: 'Discovery',
      icon: Search,
      status: getStageStatus('discovery', currentStage),
    },
    {
      id: 'job',
      label: 'Job Created',
      icon: Wrench,
      status: getStageStatus('job', currentStage),
    },
    {
      id: 'approval',
      label: 'Approval',
      icon: CheckSquare,
      status: getStageStatus('approval', currentStage),
    },
    {
      id: 'scheduled',
      label: 'Scheduled',
      icon: Calendar,
      status: getStageStatus('scheduled', currentStage),
    },
    {
      id: 'completed',
      label: 'Completed',
      icon: CheckCircle2,
      status: getStageStatus('completed', currentStage),
    },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={`rounded-2xl border border-slate-700/50 bg-slate-900/60 backdrop-blur-sm p-${compact ? '3' : '4'} shadow-lg`}
    >
      {incidentId && !compact && (
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-emerald-300">Incident Progress</h3>
          <span className="text-xs text-slate-400">{incidentId}</span>
        </div>
      )}

      {/* Timeline */}
      <div className="relative">
        {/* Progress Line */}
        <div className="absolute left-0 top-[20px] h-[2px] w-full bg-slate-700/50" />
        <motion.div
          className="absolute left-0 top-[20px] h-[2px] bg-gradient-to-r from-emerald-500 to-emerald-400"
          initial={{ width: '0%' }}
          animate={{
            width: `${(stages.findIndex((s) => s.status === 'current') / (stages.length - 1)) * 100}%`,
          }}
          transition={{ duration: 0.8, delay: 0.2 }}
        />

        {/* Stages */}
        <div className={`relative flex ${compact ? 'gap-2' : 'gap-4'} justify-between`}>
          {stages.map((stage, index) => {
            const StageIcon = stage.icon;

            const statusColors = {
              completed: {
                bg: 'bg-emerald-500',
                border: 'border-emerald-400',
                text: 'text-emerald-300',
                icon: 'text-white',
              },
              current: {
                bg: 'bg-emerald-500',
                border: 'border-emerald-400',
                text: 'text-emerald-300',
                icon: 'text-white',
              },
              pending: {
                bg: 'bg-slate-800',
                border: 'border-slate-600',
                text: 'text-slate-400',
                icon: 'text-slate-500',
              },
            };

            const colors = statusColors[stage.status];

            return (
              <motion.button
                key={stage.id}
                onClick={() => onStageClick?.(stage.id)}
                className={`relative flex flex-col items-center ${compact ? 'gap-1' : 'gap-2'} group ${onStageClick ? 'cursor-pointer' : 'cursor-default'}`}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                whileHover={onStageClick ? { scale: 1.05 } : {}}
              >
                {/* Icon Circle */}
                <motion.div
                  className={`relative z-10 flex h-10 w-10 items-center justify-center rounded-full border-2 ${colors.border} ${colors.bg} shadow-lg transition-all ${onStageClick ? 'group-hover:scale-110' : ''}`}
                  animate={
                    stage.status === 'current'
                      ? {
                          scale: [1, 1.1, 1],
                          boxShadow: [
                            '0 0 0 0 rgba(16, 185, 129, 0.4)',
                            '0 0 0 8px rgba(16, 185, 129, 0)',
                            '0 0 0 0 rgba(16, 185, 129, 0)',
                          ],
                        }
                      : {}
                  }
                  transition={
                    stage.status === 'current'
                      ? {
                          duration: 2,
                          repeat: Infinity,
                          repeatType: 'loop',
                        }
                      : {}
                  }
                >
                  <StageIcon className={`h-5 w-5 ${colors.icon}`} />
                </motion.div>

                {/* Label */}
                {!compact && (
                  <span className={`text-xs font-medium ${colors.text} whitespace-nowrap`}>
                    {stage.label}
                  </span>
                )}

                {/* Tooltip on hover for compact mode */}
                {compact && onStageClick && (
                  <div className="absolute -top-10 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                    <div className="bg-slate-800 border border-slate-600 rounded-lg px-2 py-1 text-xs text-slate-200 whitespace-nowrap shadow-lg">
                      {stage.label}
                    </div>
                  </div>
                )}
              </motion.button>
            );
          })}
        </div>
      </div>

      {/* Progress percentage */}
      {!compact && (
        <div className="mt-4 flex items-center justify-between text-xs">
          <span className="text-slate-400">
            Stage {stages.findIndex((s) => s.status === 'current') + 1} of {stages.length}
          </span>
          <span className="text-emerald-400 font-semibold">
            {Math.round(
              ((stages.findIndex((s) => s.status === 'current') + 1) / stages.length) * 100
            )}
            % Complete
          </span>
        </div>
      )}
    </motion.div>
  );
}

// Helper function to determine stage status
function getStageStatus(
  stageId: string,
  currentStage: string
): 'completed' | 'current' | 'pending' {
  const stageOrder = ['incident', 'discovery', 'job', 'approval', 'scheduled', 'completed'];
  const currentIndex = stageOrder.indexOf(currentStage.toLowerCase());
  const stageIndex = stageOrder.indexOf(stageId.toLowerCase());

  if (stageIndex < currentIndex) return 'completed';
  if (stageIndex === currentIndex) return 'current';
  return 'pending';
}
