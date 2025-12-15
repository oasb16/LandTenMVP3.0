"use client";

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ChevronDown,
  AlertTriangle,
  Camera,
  ListChecks,
  DollarSign,
  Shield,
  MessageCircleQuestion,
  Stethoscope,
} from 'lucide-react';

interface DiagnosticSection {
  title: string;
  icon: React.ElementType;
  content: string | string[];
  severity?: 'low' | 'medium' | 'high' | 'urgent';
  defaultExpanded?: boolean;
}

interface DiagnosticDataCardProps {
  diagnosticResult?: {
    diagnosis?: string;
    severity?: string;
    urgency?: string;
    estimatedCost?: string;
    recommendations?: string[];
  };
  photoAnalysis?: {
    findings?: string[];
    concerns?: string[];
    caution?: string[];
  };
  nextSteps?: string[];
  safetyConsiderations?: string[];
  questions?: string[];
  severity?: 'low' | 'medium' | 'high' | 'urgent';
}

export function DiagnosticDataCard({
  diagnosticResult,
  photoAnalysis,
  nextSteps,
  safetyConsiderations,
  questions,
  severity = 'medium',
}: DiagnosticDataCardProps) {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(['diagnostic']) // Default expand diagnostic section
  );

  const toggleSection = (sectionId: string) => {
    setExpandedSections((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(sectionId)) {
        newSet.delete(sectionId);
      } else {
        newSet.add(sectionId);
      }
      return newSet;
    });
  };

  const sections: DiagnosticSection[] = [];

  // Build sections based on available data
  if (diagnosticResult) {
    const diagnosticContent = [
      diagnosticResult.diagnosis && `**Diagnosis:** ${diagnosticResult.diagnosis}`,
      diagnosticResult.severity && `**Severity:** ${diagnosticResult.severity}`,
      diagnosticResult.urgency && `**Urgency:** ${diagnosticResult.urgency}`,
      diagnosticResult.estimatedCost && `**Estimated cost:** ${diagnosticResult.estimatedCost}`,
      ...(diagnosticResult.recommendations || []).map(rec => `• ${rec}`),
    ].filter(Boolean) as string[];

    sections.push({
      title: 'Diagnostic Results',
      icon: Stethoscope,
      content: diagnosticContent,
      severity: severity,
      defaultExpanded: true,
    });
  }

  if (photoAnalysis) {
    const photoContent = [
      ...(photoAnalysis.findings || []).map(f => `✓ ${f}`),
      ...(photoAnalysis.concerns || []).map(c => `⚠ ${c}`),
      ...(photoAnalysis.caution || []).map(c => `⛔ ${c}`),
    ];

    if (photoContent.length > 0) {
      sections.push({
        title: 'Photo Analysis',
        icon: Camera,
        content: photoContent,
      });
    }
  }

  if (nextSteps && nextSteps.length > 0) {
    sections.push({
      title: 'Next Steps',
      icon: ListChecks,
      content: nextSteps,
    });
  }

  if (safetyConsiderations && safetyConsiderations.length > 0) {
    sections.push({
      title: 'Safety Considerations',
      icon: Shield,
      content: safetyConsiderations,
      severity: 'high',
    });
  }

  if (questions && questions.length > 0) {
    sections.push({
      title: 'Questions',
      icon: MessageCircleQuestion,
      content: questions,
    });
  }

  if (sections.length === 0) {
    return null;
  }

  // Severity-based color schemes
  const severityColors = {
    low: {
      border: 'border-emerald-500/30',
      bg: 'bg-emerald-900/20',
      text: 'text-emerald-300',
      accent: 'text-emerald-400',
    },
    medium: {
      border: 'border-amber-500/30',
      bg: 'bg-amber-900/20',
      text: 'text-amber-300',
      accent: 'text-amber-400',
    },
    high: {
      border: 'border-orange-500/30',
      bg: 'bg-orange-900/20',
      text: 'text-orange-300',
      accent: 'text-orange-400',
    },
    urgent: {
      border: 'border-red-500/30',
      bg: 'bg-red-900/20',
      text: 'text-red-300',
      accent: 'text-red-400',
    },
  };

  const colors = severityColors[severity];

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={`rounded-2xl border ${colors.border} ${colors.bg} backdrop-blur-sm overflow-hidden shadow-lg`}
    >
      {sections.map((section, index) => {
        const sectionId = `section-${index}`;
        const isExpanded = expandedSections.has(sectionId);
        const SectionIcon = section.icon;
        const sectionColors = section.severity ? severityColors[section.severity] : colors;

        return (
          <div key={sectionId} className={`border-b ${colors.border} last:border-b-0`}>
            {/* Section Header */}
            <button
              onClick={() => toggleSection(sectionId)}
              className={`w-full px-4 py-3 flex items-center justify-between hover:${sectionColors.bg} transition-colors`}
            >
              <div className="flex items-center gap-3">
                <SectionIcon className={`h-5 w-5 ${sectionColors.accent}`} />
                <span className={`font-semibold text-sm ${sectionColors.text}`}>
                  {section.title}
                </span>
                {section.severity === 'high' || section.severity === 'urgent' ? (
                  <AlertTriangle className="h-4 w-4 text-red-400 animate-pulse" />
                ) : null}
              </div>
              <motion.div
                animate={{ rotate: isExpanded ? 180 : 0 }}
                transition={{ duration: 0.2 }}
              >
                <ChevronDown className={`h-4 w-4 ${sectionColors.text}`} />
              </motion.div>
            </button>

            {/* Section Content */}
            <AnimatePresence initial={false}>
              {isExpanded && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="overflow-hidden"
                >
                  <div className="px-4 pb-3 pt-1 space-y-2">
                    {Array.isArray(section.content) ? (
                      <ul className="space-y-1.5 text-sm text-slate-200">
                        {section.content.map((item, idx) => (
                          <li key={idx} className="leading-relaxed">
                            {renderContent(item)}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-sm text-slate-200 leading-relaxed">
                        {renderContent(section.content)}
                      </p>
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        );
      })}
    </motion.div>
  );
}

// Helper to render markdown-like content
function renderContent(content: string) {
  // Bold text
  const parts = content.split(/\*\*(.*?)\*\*/g);
  return parts.map((part, idx) =>
    idx % 2 === 1 ? (
      <strong key={idx} className="font-semibold text-emerald-200">
        {part}
      </strong>
    ) : (
      <span key={idx}>{part}</span>
    )
  );
}
