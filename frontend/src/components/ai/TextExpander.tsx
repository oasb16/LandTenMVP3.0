"use client";

import React, { useState, useEffect } from 'react';
import { ChevronDown } from 'lucide-react';
import { motion } from 'framer-motion';

interface TextExpanderProps {
  text: string;
  previewText?: string; // Optional preview text to show first
  maxLength?: number;
  className?: string;
  isBot?: boolean;
}

export function TextExpander({ text, previewText, maxLength = 300, className = '', isBot = false }: TextExpanderProps) {
  // Start collapsed for AI messages to show PREVIEW first
  const [isExpanded, setIsExpanded] = useState(false);
  const [shouldTruncate, setShouldTruncate] = useState(false);

  useEffect(() => {
    // Check if text needs truncation
    const textToCheck = previewText || text;
    setShouldTruncate(textToCheck.length > maxLength || !!previewText);
  }, [text, previewText, maxLength]);

  // Don't show expander for user messages
  if (!isBot) {
    return <div className={className}>{text}</div>;
  }

  // Don't truncate short messages
  if (!shouldTruncate) {
    return <div className={className}>{text}</div>;
  }

  // Show PREVIEW by default, expand to RAW on click
  const displayText = isExpanded
    ? text
    : (previewText || text.substring(0, maxLength) + '...');

  return (
    <div className="text-expander">
      <motion.div
        initial={false}
        animate={{ height: 'auto' }}
        transition={{ duration: 0.3, ease: 'easeInOut' }}
        className={className}
      >
        <div className="whitespace-pre-wrap">{displayText}</div>
      </motion.div>

      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="see-more-btn mt-2 flex items-center gap-1 text-sm font-medium transition-all"
      >
        <span>{isExpanded ? 'See less' : 'See more'}</span>
        <ChevronDown
          className={`h-4 w-4 transition-transform duration-300 ${isExpanded ? 'rotate-180' : ''}`}
        />
      </button>

      <style jsx>{`
        .text-expander {
          position: relative;
        }

        .see-more-btn {
          color: #10b981;
          cursor: pointer;
          background: none;
          border: none;
          padding: 0.25rem 0;
        }

        .see-more-btn:hover {
          color: #059669;
        }

        :global(.str-chat__theme-dark) .see-more-btn {
          color: #6ee7b7;
        }

        :global(.str-chat__theme-dark) .see-more-btn:hover {
          color: #34d399;
        }
      `}</style>
    </div>
  );
}
