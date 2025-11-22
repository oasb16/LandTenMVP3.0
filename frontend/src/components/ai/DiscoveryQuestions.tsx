"use client";

import React from 'react';
import { Search, CheckCircle2 } from 'lucide-react';

interface DiscoveryQuestionsProps {
  text: string;
  title?: string;
}

export function DiscoveryQuestions({ text, title = 'Discovery Session' }: DiscoveryQuestionsProps) {
  // Parse numbered questions from text
  const questions = parseQuestions(text);

  if (questions.length === 0) {
    // Fallback to regular text if no questions detected
    return <div className="whitespace-pre-wrap">{text}</div>;
  }

  return (
    <div className="discovery-questions bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-4 shadow-md border border-blue-200">
      {/* Header */}
      <div className="header flex items-center gap-2 mb-3 pb-3 border-b border-blue-200">
        <Search className="h-5 w-5 text-blue-600" />
        <h3 className="text-base font-bold text-gray-900">🔎 {title}</h3>
      </div>

      {/* Intro text if present */}
      {getIntroText(text) && (
        <p className="intro-text text-sm text-gray-700 mb-3">
          {getIntroText(text)}
        </p>
      )}

      {/* Questions list */}
      <div className="questions-list space-y-2.5">
        {questions.map((question, index) => (
          <div
            key={index}
            className="question-item flex items-start gap-3 bg-white rounded-lg p-3 shadow-sm border border-gray-100 hover:border-blue-300 transition-all"
          >
            <div className="question-number flex items-center justify-center h-6 w-6 rounded-full bg-blue-600 text-white text-xs font-bold flex-shrink-0 mt-0.5">
              {index + 1}
            </div>
            <div className="question-text text-sm text-gray-800 font-medium flex-1">
              {question}
            </div>
          </div>
        ))}
      </div>

      <style jsx>{`
        .discovery-questions {
          animation: fadeIn 0.4s ease-out;
        }

        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: scale(0.98);
          }
          to {
            opacity: 1;
            transform: scale(1);
          }
        }

        .question-item {
          animation: slideInLeft 0.3s ease-out;
          animation-fill-mode: backwards;
        }

        .question-item:nth-child(1) { animation-delay: 0.05s; }
        .question-item:nth-child(2) { animation-delay: 0.1s; }
        .question-item:nth-child(3) { animation-delay: 0.15s; }
        .question-item:nth-child(4) { animation-delay: 0.2s; }
        .question-item:nth-child(5) { animation-delay: 0.25s; }

        @keyframes slideInLeft {
          from {
            opacity: 0;
            transform: translateX(-10px);
          }
          to {
            opacity: 1;
            transform: translateX(0);
          }
        }

        /* Dark mode */
        :global(.str-chat__theme-dark) .discovery-questions {
          background: linear-gradient(to bottom right, #1e3a8a, #3730a3);
          border-color: #4f46e5;
        }

        :global(.str-chat__theme-dark) .header {
          border-bottom-color: #4f46e5;
        }

        :global(.str-chat__theme-dark) .header h3 {
          color: #e0e7ff;
        }

        :global(.str-chat__theme-dark) .intro-text {
          color: #c7d2fe;
        }

        :global(.str-chat__theme-dark) .question-item {
          background: #1e293b;
          border-color: #334155;
        }

        :global(.str-chat__theme-dark) .question-item:hover {
          border-color: #6366f1;
        }

        :global(.str-chat__theme-dark) .question-text {
          color: #e2e8f0;
        }
      `}</style>
    </div>
  );
}

// Helper to parse numbered questions from text
function parseQuestions(text: string): string[] {
  const lines = text.split('\n');
  const questions: string[] = [];

  for (const line of lines) {
    const trimmed = line.trim();
    // Match patterns like "1.", "1)", "Q1:", etc.
    const match = trimmed.match(/^(\d+[\.):]|Q\d+:)\s*(.+)/i);
    if (match && match[2]) {
      questions.push(match[2].trim());
    }
  }

  return questions;
}

// Helper to extract intro text before questions
function getIntroText(text: string): string | null {
  const lines = text.split('\n');
  const introLines: string[] = [];

  for (const line of lines) {
    const trimmed = line.trim();
    // Stop when we hit first numbered question
    if (trimmed.match(/^(\d+[\.):]|Q\d+:)/i)) {
      break;
    }
    if (trimmed && !trimmed.match(/^(Please answer|Answer the following)/i)) {
      introLines.push(trimmed);
    }
  }

  const intro = introLines.join(' ').trim();
  return intro.length > 0 && intro.length < 200 ? intro : null;
}
