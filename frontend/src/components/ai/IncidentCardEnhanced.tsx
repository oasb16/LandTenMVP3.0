"use client";

import React from 'react';
import { CheckCircle2, AlertCircle, Clock, Database } from 'lucide-react';

interface IncidentCardEnhancedProps {
  metadata?: {
    incident_id?: string;
    category?: string;
    severity?: string;
    urgency?: string;
    summary?: string;
    title?: string;
    type?: string;
    success?: boolean;
    created_at?: string;
  };
  text?: string;
  fallbackText?: string;
}

export function IncidentCardEnhanced({ metadata, text, fallbackText }: IncidentCardEnhancedProps) {
  // Extract data from metadata or parse from text
  const incidentId = metadata?.incident_id || extractFromText(text || fallbackText, 'ID:') || 'INC-XXXXX';
  const title = metadata?.title || extractFromText(text || fallbackText, 'Title:') || 'Incident Reported';
  const category = metadata?.category || extractFromText(text || fallbackText, 'Category:') || 'General';
  const severity = metadata?.severity || extractFromText(text || fallbackText, 'Severity:') || 'Medium';
  const urgency = metadata?.urgency || extractFromText(text || fallbackText, 'Urgency:') || 'Normal';
  const summary = metadata?.summary || text || fallbackText || 'Your incident has been logged';
  const success = metadata?.success !== false;
  const timestamp = metadata?.created_at || new Date().toISOString();

  // Color mapping for severity
  const severityColors = {
    low: 'text-green-600 bg-green-100',
    medium: 'text-yellow-600 bg-yellow-100',
    high: 'text-orange-600 bg-orange-100',
    emergency: 'text-red-600 bg-red-100',
  };

  const urgencyColors = {
    routine: 'text-blue-600 bg-blue-100',
    urgent: 'text-orange-600 bg-orange-100',
    immediate: 'text-red-600 bg-red-100',
  };

  const severityClass = severityColors[severity.toLowerCase() as keyof typeof severityColors] || severityColors.medium;
  const urgencyClass = urgencyColors[urgency.toLowerCase() as keyof typeof urgencyColors] || urgencyColors.routine;

  return (
    <div className="incident-card-enhanced bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="header bg-gradient-to-r from-emerald-50 to-green-50 px-4 py-3 border-b border-gray-200">
        <div className="flex items-start gap-3">
          <CheckCircle2 className="h-6 w-6 text-emerald-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <h3 className="text-lg font-bold text-gray-900">
              Incident Reported: {title}
            </h3>
            <p className="text-sm text-gray-600 mt-0.5">{incidentId}</p>
          </div>
        </div>
      </div>

      {/* Body */}
      <div className="body px-4 py-4 space-y-3">
        {/* Category & Severity Row */}
        <div className="grid grid-cols-2 gap-3">
          <div className="detail-item">
            <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
              Category
            </div>
            <div className="px-3 py-1.5 bg-blue-50 text-blue-700 rounded-lg text-sm font-medium inline-block">
              {category}
            </div>
          </div>

          <div className="detail-item">
            <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
              Severity
            </div>
            <div className={`px-3 py-1.5 rounded-lg text-sm font-medium inline-block ${severityClass}`}>
              {severity}
            </div>
          </div>
        </div>

        {/* Urgency & Timestamp */}
        <div className="grid grid-cols-2 gap-3">
          <div className="detail-item">
            <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
              Urgency
            </div>
            <div className={`px-3 py-1.5 rounded-lg text-sm font-medium inline-block ${urgencyClass}`}>
              {urgency}
            </div>
          </div>

          <div className="detail-item">
            <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
              Logged
            </div>
            <div className="flex items-center gap-1.5 text-sm text-gray-700">
              <Clock className="h-4 w-4 text-gray-400" />
              {formatTimestamp(timestamp)}
            </div>
          </div>
        </div>

        {/* Summary */}
        {summary && summary !== title && (
          <div className="summary pt-2 border-t border-gray-100">
            <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">
              Summary
            </div>
            <p className="text-sm text-gray-700 leading-relaxed">{summary}</p>
          </div>
        )}
      </div>

      {/* Footer */}
      {success && (
        <div className="footer bg-green-50 px-4 py-2.5 border-t border-green-100 flex items-center gap-2">
          <Database className="h-4 w-4 text-green-600" />
          <span className="text-xs font-medium text-green-700">
            ✓ Stored in DynamoDB successfully
          </span>
        </div>
      )}

      <style jsx>{`
        .incident-card-enhanced {
          animation: slideIn 0.3s ease-out;
        }

        @keyframes slideIn {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        /* Dark mode support */
        :global(.str-chat__theme-dark) .incident-card-enhanced {
          background: #1f2937;
          border-color: #374151;
        }

        :global(.str-chat__theme-dark) .header {
          background: linear-gradient(to right, #065f46, #047857);
          border-bottom-color: #374151;
        }

        :global(.str-chat__theme-dark) .header h3 {
          color: #f9fafb;
        }

        :global(.str-chat__theme-dark) .header p {
          color: #d1d5db;
        }

        :global(.str-chat__theme-dark) .body {
          color: #e5e7eb;
        }

        :global(.str-chat__theme-dark) .detail-item .text-gray-500 {
          color: #9ca3af;
        }

        :global(.str-chat__theme-dark) .summary {
          border-top-color: #374151;
        }

        :global(.str-chat__theme-dark) .summary p {
          color: #d1d5db;
        }

        :global(.str-chat__theme-dark) .footer {
          background: #064e3b;
          border-top-color: #065f46;
        }
      `}</style>
    </div>
  );
}

// Helper to extract data from text if metadata missing
function extractFromText(text: string | undefined, prefix: string): string | null {
  if (!text) return null;
  const regex = new RegExp(`${prefix}\\s*([^\\n,]+)`, 'i');
  const match = text.match(regex);
  return match ? match[1].trim() : null;
}

// Helper to format timestamp
function formatTimestamp(iso: string): string {
  try {
    const date = new Date(iso);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;

    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  } catch {
    return 'Recently';
  }
}
