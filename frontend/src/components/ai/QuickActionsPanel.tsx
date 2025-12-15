"use client";

import React from 'react';
import { motion } from 'framer-motion';
import {
  Upload,
  Phone,
  CheckCircle,
  Camera,
  MessageSquare,
  FileText,
  Clock,
  AlertCircle,
  type LucideIcon,
} from 'lucide-react';

interface QuickAction {
  id: string;
  label: string;
  icon: LucideIcon;
  category: 'upload' | 'contact' | 'review' | 'respond' | 'other';
  variant?: 'primary' | 'secondary' | 'danger';
}

interface QuickActionsPanelProps {
  actions?: string[];
  stage?: string;
  onActionClick?: (action: string) => void;
}

export function QuickActionsPanel({ actions, stage, onActionClick }: QuickActionsPanelProps) {
  // Parse actions into categorized quick actions
  const quickActions = parseActions(actions, stage);

  if (quickActions.length === 0) {
    return null;
  }

  // Group actions by category
  const categories = ['upload', 'respond', 'review', 'contact', 'other'] as const;
  const groupedActions: Record<string, QuickAction[]> = {};

  categories.forEach((cat) => {
    groupedActions[cat] = quickActions.filter((a) => a.category === cat);
  });

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="rounded-2xl border border-emerald-500/20 bg-gradient-to-br from-slate-900/80 via-slate-900 to-slate-950 p-4 shadow-xl backdrop-blur-sm"
    >
      <h4 className="text-sm font-semibold text-emerald-300 mb-3 flex items-center gap-2">
        <AlertCircle className="h-4 w-4" />
        Quick Actions
      </h4>

      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4">
        {quickActions.map((action, index) => {
          const Icon = action.icon;

          // Variant styling
          const variantStyles = {
            primary:
              'bg-gradient-to-br from-emerald-600 to-emerald-700 hover:from-emerald-500 hover:to-emerald-600 text-white border-emerald-400/30',
            secondary:
              'bg-gradient-to-br from-slate-700 to-slate-800 hover:from-slate-600 hover:to-slate-700 text-slate-200 border-slate-600/30',
            danger:
              'bg-gradient-to-br from-red-600 to-red-700 hover:from-red-500 hover:to-red-600 text-white border-red-400/30',
          };

          const styles = variantStyles[action.variant || 'secondary'];

          return (
            <motion.button
              key={action.id}
              onClick={() => onActionClick?.(action.label)}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: index * 0.05 }}
              whileHover={{ scale: 1.05, y: -2 }}
              whileTap={{ scale: 0.95 }}
              className={`flex flex-col items-center gap-2 rounded-xl border p-3 shadow-lg transition-all ${styles}`}
            >
              <Icon className="h-5 w-5" />
              <span className="text-xs font-medium text-center leading-tight">
                {action.label}
              </span>
            </motion.button>
          );
        })}
      </div>
    </motion.div>
  );
}

// Helper: Parse action strings into structured quick actions
function parseActions(actions?: string[], stage?: string): QuickAction[] {
  const quickActions: QuickAction[] = [];

  if (!actions || actions.length === 0) {
    // Generate default actions based on stage
    return getDefaultActionsForStage(stage);
  }

  actions.forEach((action, index) => {
    const lowerAction = action.toLowerCase();

    // Upload actions
    if (
      lowerAction.includes('upload') ||
      lowerAction.includes('photo') ||
      lowerAction.includes('image') ||
      lowerAction.includes('attach')
    ) {
      quickActions.push({
        id: `action-${index}`,
        label: action,
        icon: lowerAction.includes('photo') || lowerAction.includes('image') ? Camera : Upload,
        category: 'upload',
        variant: 'primary',
      });
    }
    // Contact actions
    else if (
      lowerAction.includes('call') ||
      lowerAction.includes('contact') ||
      lowerAction.includes('notify') ||
      lowerAction.includes('landlord')
    ) {
      quickActions.push({
        id: `action-${index}`,
        label: action,
        icon: Phone,
        category: 'contact',
        variant: 'secondary',
      });
    }
    // Review/Approval actions
    else if (
      lowerAction.includes('review') ||
      lowerAction.includes('approve') ||
      lowerAction.includes('check') ||
      lowerAction.includes('bid')
    ) {
      quickActions.push({
        id: `action-${index}`,
        label: action,
        icon: CheckCircle,
        category: 'review',
        variant: 'primary',
      });
    }
    // Response actions
    else if (
      lowerAction.includes('answer') ||
      lowerAction.includes('provide') ||
      lowerAction.includes('details') ||
      lowerAction.includes('question')
    ) {
      quickActions.push({
        id: `action-${index}`,
        label: action,
        icon: MessageSquare,
        category: 'respond',
        variant: 'secondary',
      });
    }
    // Default
    else {
      quickActions.push({
        id: `action-${index}`,
        label: action,
        icon: FileText,
        category: 'other',
        variant: 'secondary',
      });
    }
  });

  return quickActions;
}

// Helper: Get default actions based on stage
function getDefaultActionsForStage(stage?: string): QuickAction[] {
  const normalizedStage = stage?.toLowerCase() || '';

  if (normalizedStage.includes('incident')) {
    return [
      {
        id: 'upload-photo',
        label: 'Upload Photo',
        icon: Camera,
        category: 'upload',
        variant: 'primary',
      },
      {
        id: 'add-details',
        label: 'Add Details',
        icon: MessageSquare,
        category: 'respond',
        variant: 'secondary',
      },
      {
        id: 'check-status',
        label: 'Check Status',
        icon: Clock,
        category: 'review',
        variant: 'secondary',
      },
    ];
  }

  if (normalizedStage.includes('discovery')) {
    return [
      {
        id: 'answer-questions',
        label: 'Answer Questions',
        icon: MessageSquare,
        category: 'respond',
        variant: 'primary',
      },
      {
        id: 'upload-more',
        label: 'Upload More Photos',
        icon: Camera,
        category: 'upload',
        variant: 'secondary',
      },
    ];
  }

  if (normalizedStage.includes('job') || normalizedStage.includes('approval')) {
    return [
      {
        id: 'review-bids',
        label: 'Review Bids',
        icon: FileText,
        category: 'review',
        variant: 'primary',
      },
      {
        id: 'approve-work',
        label: 'Approve Work',
        icon: CheckCircle,
        category: 'review',
        variant: 'primary',
      },
      {
        id: 'contact-contractor',
        label: 'Contact Contractor',
        icon: Phone,
        category: 'contact',
        variant: 'secondary',
      },
    ];
  }

  return [];
}
