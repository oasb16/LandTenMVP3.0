"use client";

import React, { useState } from 'react';
import { StreamMessage } from 'stream-chat';

interface CardAction {
  name: string;
  text: string;
  style?: string;
  type: string;
  value: string;
}

interface CardField {
  title: string;
  value: string;
  short?: boolean;
}

interface MessageCardsProps {
  message: StreamMessage;
  onActionClick: (actionValue: string) => void;
}

export function MessageCards({ message, onActionClick }: MessageCardsProps) {
  const attachments = message.attachments || [];
  const [loadingAction, setLoadingAction] = useState<string | null>(null);

  if (attachments.length === 0) {
    return null;
  }

  const handleActionClick = async (actionValue: string) => {
    console.log('[MessageCards] Button clicked:', actionValue);
    setLoadingAction(actionValue);
    try {
      if (onActionClick) onActionClick(actionValue);
      console.log('[MessageCards] Button action completed:', actionValue);
    } catch (error) {
      console.error('[MessageCards] Button action failed:', actionValue, error);
    } finally {
      // Clear loading state after a short delay
      setTimeout(() => setLoadingAction(null), 500);
    }
  };

  return (
    <div className="message-cards-container">
      {attachments.map((attachment: any, index: number) => {
        const cardType = attachment.type;
        console.log('[MessageCards] Rendering card:', { type: cardType, hasButtons: !!(attachment.buttons || attachment.actions) });

        switch (cardType) {
          case 'incident':
            console.log('[MessageCards] Incident card data:', attachment);
            return <IncidentCard key={index} data={attachment} onActionClick={handleActionClick} loadingAction={loadingAction} />;
          case 'custom_card' : 
            console.log('[MessageCards] Custom Actions card data:', attachment);
            return <IncidentCard key={index} data={attachment} onActionClick={handleActionClick} loadingAction={loadingAction} />;            
          case 'custom_actions':
            console.log('[MessageCards] Custom Actions card data:', attachment);
            return <IncidentCard key={index} data={attachment} onActionClick={handleActionClick} loadingAction={loadingAction} />;
          case 'discovery':
            console.log('[MessageCards] Discovery card data:', attachment);
            return <DiscoveryCard key={index} data={attachment} onActionClick={handleActionClick} loadingAction={loadingAction} />;
          case 'job':
            return <JobCard key={index} data={attachment} onActionClick={handleActionClick} loadingAction={loadingAction} />;
          case 'bids':
            return <BidsCard key={index} data={attachment} onActionClick={handleActionClick} loadingAction={loadingAction} />;
          case 'approval':
            return <ApprovalCard key={index} data={attachment} onActionClick={handleActionClick} loadingAction={loadingAction} />;
          case 'completion':
            return <CompletionCard key={index} data={attachment} onActionClick={handleActionClick} loadingAction={loadingAction} />;
          case 'actions':
            return <BaseCard key={index} data={attachment} onActionClick={handleActionClick} loadingAction={loadingAction} />;
          default:
            return null;
        }
      })}

      <style jsx>{`
        .message-cards-container {
          margin: 0;
          width: 100%;
          max-width: 100%;
        }
      `}</style>
    </div>
  );
}

interface CardProps {
  data: any;
  onActionClick: (value: string) => void;
  loadingAction: string | null;
}

function BaseCard({ data, children, onActionClick, loadingAction }: CardProps & { children: React.ReactNode }) {
  // Support both "buttons" and "actions" field names for backward compatibility
  const buttons = data.buttons || data.actions || [];
  console.log('[BaseCard] Rendering card with data:', data);
  return (
    <div className="card" style={{ borderLeftColor: data.color || '#6b7280' }}>
      {children}

      {buttons && buttons.length > 0 ? (
        <div className="card-actions">
          {buttons.map((btn: any, idx: number) => (
            <button
              key={idx}
              onClick={() => onActionClick(data.type)}
              disabled={loadingAction !== null}
              className={`card-button card-button-${btn.style || 'default'}`}
              style={{
                position: 'relative',
                opacity: loadingAction !== null ? 0.7 : 1,
                cursor: loadingAction !== null ? 'wait' : 'pointer'
              }}
            >
              {loadingAction === btn.value && <span className="button-spinner" />}
              <span style={{ visibility: loadingAction === btn.value ? 'hidden' : 'visible' }}>
                {btn.label || btn.text}
              </span>
            </button>
          ))}
        </div>
      ) : null}


      {data.footer && (
        <div className="card-footer">
          {data.footer}
        </div>
      )}

      <style jsx>{`
        .card {
          background: #ffffff;
          border-radius: 12px;
          border-left: 4px solid #6b7280;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
          overflow: hidden;
          margin: 0.5rem 0;
          max-width: 100%;
          transition: all 0.2s ease;
        }

        .card:hover {
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
          transform: translateY(-1px);
        }

        .card-actions {
          display: flex;
          gap: 0.5rem;
          padding: 0.75rem 1rem 1rem 1rem;
          flex-wrap: wrap;
        }

        .card-button {
          padding: 0.625rem 1.25rem;
          border: none;
          border-radius: 8px;
          font-size: 0.875rem;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s ease;
          flex: 1;
          min-width: fit-content;
          position: relative;
          overflow: hidden;
        }

        .card-button:disabled {
          cursor: wait;
        }

        .card-button-primary {
          background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
          color: white;
          box-shadow: 0 2px 4px rgba(59, 130, 246, 0.2);
        }

        .card-button-primary:hover:not(:disabled) {
          background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
          transform: translateY(-2px);
          box-shadow: 0 4px 8px rgba(59, 130, 246, 0.3);
        }

        .card-button-primary:active:not(:disabled) {
          transform: translateY(0);
        }

        .card-button-default {
          background: #f3f4f6;
          color: #374151;
          border: 1px solid #d1d5db;
        }

        .card-button-default:hover:not(:disabled) {
          background: #e5e7eb;
          border-color: #9ca3af;
          transform: translateY(-1px);
        }

        .card-button-danger {
          background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
          color: white;
          box-shadow: 0 2px 4px rgba(239, 68, 68, 0.2);
        }

        .card-button-danger:hover:not(:disabled) {
          background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
          transform: translateY(-2px);
          box-shadow: 0 4px 8px rgba(239, 68, 68, 0.3);
        }

        .button-spinner {
          position: absolute;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          width: 16px;
          height: 16px;
          border: 2px solid rgba(255, 255, 255, 0.3);
          border-top-color: white;
          border-radius: 50%;
          animation: spin 0.6s linear infinite;
        }

        @keyframes spin {
          to {
            transform: translate(-50%, -50%) rotate(360deg);
          }
        }

        .card-footer {
          padding: 0.75rem 1rem;
          background: #f9fafb;
          border-top: 1px solid #e5e7eb;
          font-size: 0.75rem;
          color: #6b7280;
        }

        /* Dark mode */
        :global(.str-chat__theme-dark) .card {
          background: #1f2937;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
        }

        :global(.str-chat__theme-dark) .card-footer {
          background: #111827;
          border-top-color: #374151;
          color: #9ca3af;
        }

        :global(.str-chat__theme-dark) .card-button-default {
          background: #374151;
          color: #f3f4f6;
          border-color: #4b5563;
        }

        :global(.str-chat__theme-dark) .card-button-default:hover:not(:disabled) {
          background: #4b5563;
          border-color: #6b7280;
        }
      `}</style>
    </div>
  );
}

function IncidentCard({ data, onActionClick, loadingAction }: CardProps) {
  return (
    <BaseCard data={data} onActionClick={onActionClick} loadingAction={loadingAction}>
      <div className="card-header">
        <h3 className="card-title">{data.title}</h3>
      </div>

      {data.image_url && (
        <div className="card-image">
          <img src={data.image_url} alt="Incident" />
        </div>
      )}

      <div className="card-body">
        <p className="card-text">{data.text}</p>

        {data.fields && data.fields.length > 0 && (
          <div className="card-fields">
            {data.fields.map((field: CardField, idx: number) => (
              <div key={idx} className={`card-field ${field.short ? 'card-field-short' : 'card-field-full'}`}>
                <div className="field-title">{field.title}</div>
                <div className="field-value">{field.value}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      <style jsx>{`
        .card-header {
          padding: 1rem 1rem 0.5rem 1rem;
        }

        .card-title {
          font-size: 1rem;
          font-weight: 600;
          color: #111827;
          margin: 0;
        }

        .card-image {
          width: 100%;
          max-height: 200px;
          overflow: hidden;
        }

        .card-image img {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }

        .card-body {
          padding: 0.75rem 1rem;
        }

        .card-text {
          color: #4b5563;
          font-size: 0.875rem;
          line-height: 1.5;
          margin: 0 0 0.75rem 0;
        }

        .card-fields {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 0.75rem;
          margin-top: 0.75rem;
        }

        .card-field {
          padding: 0.5rem;
          background: #f9fafb;
          border-radius: 6px;
        }

        .card-field-full {
          grid-column: 1 / -1;
        }

        .field-title {
          font-size: 0.75rem;
          font-weight: 600;
          color: #6b7280;
          text-transform: uppercase;
          letter-spacing: 0.025em;
          margin-bottom: 0.25rem;
        }

        .field-value {
          font-size: 0.875rem;
          color: #111827;
          font-weight: 500;
          white-space: pre-line;
        }

        :global(.str-chat__theme-dark) .card-title {
          color: #f9fafb;
        }

        :global(.str-chat__theme-dark) .card-text {
          color: #d1d5db;
        }

        :global(.str-chat__theme-dark) .card-field {
          background: #111827;
        }

        :global(.str-chat__theme-dark) .field-title {
          color: #9ca3af;
        }

        :global(.str-chat__theme-dark) .field-value {
          color: #f3f4f6;
        }

        @media (max-width: 640px) {
          .card-fields {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </BaseCard>
  );
}

function DiscoveryCard({ data, onActionClick, loadingAction }: CardProps) {
  const discoveryData = data.discovery_data || {};
  const progress = discoveryData.progress || 0;

  return (
    <BaseCard data={data} onActionClick={onActionClick} loadingAction={loadingAction}>
      <div className="card-header">
        <h3 className="card-title">{data.title}</h3>
      </div>

      <div className="card-body">
        <div className="discovery-progress">
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${progress}%` }} />
          </div>
          <div className="progress-text">{Math.round(progress)}% Complete</div>
        </div>

        {data.text && <p className="card-text">{data.text}</p>}

        {data.fields && data.fields.length > 0 && (
          <div className="card-fields">
            {data.fields.map((field: CardField, idx: number) => (
              <div key={idx} className={`card-field ${field.short ? 'card-field-short' : 'card-field-full'}`}>
                <div className="field-title">{field.title}</div>
                <div className="field-value">{field.value}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      <style jsx>{`
        .card-header {
          padding: 1rem 1rem 0.5rem 1rem;
        }

        .card-title {
          font-size: 1rem;
          font-weight: 600;
          color: #111827;
          margin: 0;
        }

        .card-body {
          padding: 0.75rem 1rem;
        }

        .card-text {
          color: #4b5563;
          font-size: 0.875rem;
          line-height: 1.5;
          margin: 0 0 0.75rem 0;
        }

        .discovery-progress {
          margin-bottom: 1rem;
        }

        .progress-bar {
          width: 100%;
          height: 8px;
          background: #e5e7eb;
          border-radius: 4px;
          overflow: hidden;
          margin-bottom: 0.5rem;
        }

        .progress-fill {
          height: 100%;
          background: linear-gradient(90deg, #3b82f6, #60a5fa);
          transition: width 0.5s ease;
          border-radius: 4px;
        }

        .progress-text {
          font-size: 0.75rem;
          color: #6b7280;
          font-weight: 600;
        }

        .card-fields {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 0.75rem;
          margin-top: 0.75rem;
        }

        .card-field {
          padding: 0.5rem;
          background: #f9fafb;
          border-radius: 6px;
        }

        .card-field-full {
          grid-column: 1 / -1;
        }

        .field-title {
          font-size: 0.75rem;
          font-weight: 600;
          color: #6b7280;
          text-transform: uppercase;
          letter-spacing: 0.025em;
          margin-bottom: 0.25rem;
        }

        .field-value {
          font-size: 0.875rem;
          color: #111827;
          font-weight: 500;
          white-space: pre-line;
        }

        :global(.str-chat__theme-dark) .card-title {
          color: #f9fafb;
        }

        :global(.str-chat__theme-dark) .card-text {
          color: #d1d5db;
        }

        :global(.str-chat__theme-dark) .card-field {
          background: #111827;
        }

        :global(.str-chat__theme-dark) .progress-text {
          color: #9ca3af;
        }

        @media (max-width: 640px) {
          .card-fields {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </BaseCard>
  );
}

// Similar pattern for JobCard, BidsCard, ApprovalCard, CompletionCard
function JobCard({ data, onActionClick, loadingAction }: CardProps) {
  return <IncidentCard data={data} onActionClick={onActionClick} loadingAction={loadingAction} />;
}

function BidsCard({ data, onActionClick, loadingAction }: CardProps) {
  return (
    <BaseCard data={data} onActionClick={onActionClick} loadingAction={loadingAction}>
      <div className="card-header">
        <h3 className="card-title">{data.title}</h3>
      </div>

      <div className="card-body">
        <p className="card-text">{data.text}</p>

        {data.fields && data.fields.length > 0 && (
          <div className="bids-list">
            {data.fields.map((field: CardField, idx: number) => (
              <div key={idx} className="bid-item">
                <div className="bid-contractor">{field.title}</div>
                <div className="bid-details">{field.value}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      <style jsx>{`
        .card-header {
          padding: 1rem 1rem 0.5rem 1rem;
        }

        .card-title {
          font-size: 1rem;
          font-weight: 600;
          color: #111827;
          margin: 0;
        }

        .card-body {
          padding: 0.75rem 1rem;
        }

        .card-text {
          color: #4b5563;
          font-size: 0.875rem;
          line-height: 1.5;
          margin: 0 0 0.75rem 0;
        }

        .bids-list {
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
          margin-top: 0.75rem;
        }

        .bid-item {
          padding: 0.75rem;
          background: #f9fafb;
          border-radius: 8px;
          border: 1px solid #e5e7eb;
          transition: all 0.2s ease;
        }

        .bid-item:hover {
          border-color: #3b82f6;
          box-shadow: 0 2px 4px rgba(59, 130, 246, 0.1);
          transform: translateX(2px);
        }

        .bid-contractor {
          font-size: 0.875rem;
          font-weight: 600;
          color: #111827;
          margin-bottom: 0.25rem;
        }

        .bid-details {
          font-size: 0.8125rem;
          color: #6b7280;
          white-space: pre-line;
        }

        :global(.str-chat__theme-dark) .card-title {
          color: #f9fafb;
        }

        :global(.str-chat__theme-dark) .card-text {
          color: #d1d5db;
        }

        :global(.str-chat__theme-dark) .bid-item {
          background: #111827;
          border-color: #374151;
        }

        :global(.str-chat__theme-dark) .bid-item:hover {
          border-color: #60a5fa;
        }

        :global(.str-chat__theme-dark) .bid-contractor {
          color: #f9fafb;
        }

        :global(.str-chat__theme-dark) .bid-details {
          color: #9ca3af;
        }
      `}</style>
    </BaseCard>
  );
}

function ApprovalCard({ data, onActionClick, loadingAction }: CardProps) {
  return <IncidentCard data={data} onActionClick={onActionClick} loadingAction={loadingAction} />;
}

function CompletionCard({ data, onActionClick, loadingAction }: CardProps) {
  return <IncidentCard data={data} onActionClick={onActionClick} loadingAction={loadingAction} />;
}
