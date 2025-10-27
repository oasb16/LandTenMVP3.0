"use client";

import React from 'react';
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

interface BaseCardData {
  type: string;
  title: string;
  text: string;
  color?: string;
  fields?: CardField[];
  footer?: string;
  ts?: string;
  image_url?: string;
  thumb_url?: string;
  actions?: CardAction[];
}

interface MessageCardsProps {
  message: StreamMessage;
  onActionClick: (actionValue: string) => void;
}

export function MessageCards({ message, onActionClick }: MessageCardsProps) {
  const attachments = message.attachments || [];

  if (attachments.length === 0) {
    return null;
  }

  return (
    <div className="message-cards-container">
      {attachments.map((attachment: any, index: number) => {
        const cardType = attachment.type;

        switch (cardType) {
          case 'incident':
            return <IncidentCard key={index} data={attachment} onActionClick={onActionClick} />;
          case 'discovery':
            return <DiscoveryCard key={index} data={attachment} onActionClick={onActionClick} />;
          case 'job':
            return <JobCard key={index} data={attachment} onActionClick={onActionClick} />;
          case 'bids':
            return <BidsCard key={index} data={attachment} onActionClick={onActionClick} />;
          case 'approval':
            return <ApprovalCard key={index} data={attachment} onActionClick={onActionClick} />;
          case 'completion':
            return <CompletionCard key={index} data={attachment} onActionClick={onActionClick} />;
          default:
            return null;
        }
      })}
    </div>
  );
}

function IncidentCard({ data, onActionClick }: { data: any; onActionClick: (value: string) => void }) {
  return (
    <div className="card incident-card" style={{ borderLeftColor: data.color || '#6b7280' }}>
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

      {data.actions && data.actions.length > 0 && (
        <div className="card-actions">
          {data.actions.map((action: CardAction, idx: number) => (
            <button
              key={idx}
              onClick={() => onActionClick(action.value)}
              className={`card-button card-button-${action.style || 'default'}`}
            >
              {action.text}
            </button>
          ))}
        </div>
      )}

      {data.footer && (
        <div className="card-footer">
          {data.footer}
        </div>
      )}
    </div>
  );
}

function DiscoveryCard({ data, onActionClick }: { data: any; onActionClick: (value: string) => void }) {
  const discoveryData = data.discovery_data || {};
  const progress = discoveryData.progress || 0;

  return (
    <div className="card discovery-card" style={{ borderLeftColor: data.color || '#3b82f6' }}>
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

        {data.text && (
          <p className="card-text">{data.text}</p>
        )}

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

      {data.actions && data.actions.length > 0 && (
        <div className="card-actions">
          {data.actions.map((action: CardAction, idx: number) => (
            <button
              key={idx}
              onClick={() => onActionClick(action.value)}
              className={`card-button card-button-${action.style || 'default'}`}
            >
              {action.text}
            </button>
          ))}
        </div>
      )}

      {data.footer && (
        <div className="card-footer">
          {data.footer}
        </div>
      )}
    </div>
  );
}

function JobCard({ data, onActionClick }: { data: any; onActionClick: (value: string) => void }) {
  return (
    <div className="card job-card" style={{ borderLeftColor: data.color || '#8b5cf6' }}>
      <div className="card-header">
        <h3 className="card-title">{data.title}</h3>
      </div>

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

      {data.actions && data.actions.length > 0 && (
        <div className="card-actions">
          {data.actions.map((action: CardAction, idx: number) => (
            <button
              key={idx}
              onClick={() => onActionClick(action.value)}
              className={`card-button card-button-${action.style || 'default'}`}
            >
              {action.text}
            </button>
          ))}
        </div>
      )}

      {data.footer && (
        <div className="card-footer">
          {data.footer}
        </div>
      )}
    </div>
  );
}

function BidsCard({ data, onActionClick }: { data: any; onActionClick: (value: string) => void }) {
  return (
    <div className="card bids-card" style={{ borderLeftColor: data.color || '#059669' }}>
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

      {data.actions && data.actions.length > 0 && (
        <div className="card-actions card-actions-vertical">
          {data.actions.map((action: CardAction, idx: number) => (
            <button
              key={idx}
              onClick={() => onActionClick(action.value)}
              className={`card-button card-button-${action.style || 'default'} card-button-full`}
            >
              {action.text}
            </button>
          ))}
        </div>
      )}

      {data.footer && (
        <div className="card-footer">
          {data.footer}
        </div>
      )}
    </div>
  );
}

function ApprovalCard({ data, onActionClick }: { data: any; onActionClick: (value: string) => void }) {
  return (
    <div className="card approval-card" style={{ borderLeftColor: data.color || '#f59e0b' }}>
      <div className="card-header">
        <h3 className="card-title">{data.title}</h3>
      </div>

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

      {data.actions && data.actions.length > 0 && (
        <div className="card-actions">
          {data.actions.map((action: CardAction, idx: number) => (
            <button
              key={idx}
              onClick={() => onActionClick(action.value)}
              className={`card-button card-button-${action.style || 'default'}`}
            >
              {action.text}
            </button>
          ))}
        </div>
      )}

      {data.footer && (
        <div className="card-footer">
          {data.footer}
        </div>
      )}
    </div>
  );
}

function CompletionCard({ data, onActionClick }: { data: any; onActionClick: (value: string) => void }) {
  return (
    <div className="card completion-card" style={{ borderLeftColor: data.color || '#10b981' }}>
      <div className="card-header">
        <h3 className="card-title">{data.title}</h3>
      </div>

      {data.image_url && (
        <div className="card-image">
          <img src={data.image_url} alt="Completion" />
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

      {data.actions && data.actions.length > 0 && (
        <div className="card-actions">
          {data.actions.map((action: CardAction, idx: number) => (
            <button
              key={idx}
              onClick={() => onActionClick(action.value)}
              className={`card-button card-button-${action.style || 'default'}`}
            >
              {action.text}
            </button>
          ))}
        </div>
      )}

      {data.footer && (
        <div className="card-footer">
          {data.footer}
        </div>
      )}
    </div>
  );
}
