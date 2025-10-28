"use client";

import React from 'react';
import { ChannelHeader } from 'stream-chat-react';
import { AgentToggleButton } from './AgentToggleButton';

interface CustomChannelHeaderProps {
  agentEnabled: boolean;
  onAgentToggle: (enabled: boolean) => void;
}

/**
 * Custom Channel Header with AI Agent toggle
 *
 * Extends Stream Chat's ChannelHeader with PropertyAI agent control
 */
export const CustomChannelHeader: React.FC<CustomChannelHeaderProps> = ({
  agentEnabled,
  onAgentToggle
}) => {
  return (
    <div className="custom-channel-header">
      <div className="header-content">
        <ChannelHeader live />
      </div>

      <div className="header-controls">
        {/* AI Active Badge */}
        <div className="ai-status-badge">
          <div className={`status-indicator ${agentEnabled ? 'active' : 'inactive'}`}>
            <div className="status-dot" />
            <span className="status-text">
              AI {agentEnabled ? 'Active' : 'Paused'}
            </span>
          </div>
        </div>

        {/* Agent Toggle */}
        <AgentToggleButton
          initialEnabled={agentEnabled}
          onToggle={onAgentToggle}
        />
      </div>

      <style jsx>{`
        .custom-channel-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 0.75rem 1rem;
          background: #1e293b;
          border-bottom: 1px solid #334155;
        }

        .header-content {
          flex: 1;
          min-width: 0;
        }

        .header-content :global(.str-chat__header-livestream) {
          padding: 0;
          border-bottom: none;
        }

        .header-controls {
          display: flex;
          align-items: center;
          gap: 1rem;
          margin-left: 1rem;
        }

        .ai-status-badge {
          display: flex;
          align-items: center;
        }

        .status-indicator {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.375rem 0.75rem;
          border-radius: 9999px;
          font-size: 0.875rem;
          font-weight: 600;
          transition: all 0.2s ease;
        }

        .status-indicator.active {
          background: rgba(16, 185, 129, 0.1);
          color: #10b981;
        }

        .status-indicator.inactive {
          background: rgba(148, 163, 184, 0.1);
          color: #94a3b8;
        }

        .status-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          transition: all 0.2s ease;
        }

        .status-indicator.active .status-dot {
          background: #10b981;
          box-shadow: 0 0 8px rgba(16, 185, 129, 0.6);
          animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
        }

        .status-indicator.inactive .status-dot {
          background: #64748b;
        }

        .status-text {
          user-select: none;
        }

        @keyframes pulse {
          0%, 100% {
            opacity: 1;
          }
          50% {
            opacity: 0.5;
          }
        }

        /* Mobile responsive */
        @media (max-width: 640px) {
          .status-text {
            display: none;
          }

          .header-controls {
            gap: 0.5rem;
          }
        }
      `}</style>
    </div>
  );
};
