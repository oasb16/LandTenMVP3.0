"use client";

import { useState } from "react";

interface CardAction {
  name: string;
  text?: string;
  label?: string;
  value: string;
}

interface CardField {
  title: string;
  value: string;
  short?: boolean;
}

interface CardAttachment {
  type: string;
  fallback?: string;
  title?: string;
  text?: string;
  color?: string;
  fields?: CardField[];
  actions?: CardAction[];
  buttons?: CardAction[];
  footer?: string;
  ts?: string;
  metadata?: Record<string, any>;
}

interface ActionCardProps {
  card: CardAttachment;
  onActionClick: (actionValue: string) => void | Promise<void>;
}

export function ActionCard({ card, onActionClick }: ActionCardProps) {
  const [loadingAction, setLoadingAction] = useState<string | null>(null);

  // Get card type and style
  const cardType = card.metadata?.context_type || card.type || "general";

  const getCardStyle = () => {
    if (card.color) {
      return { borderColor: card.color, bgColor: `${card.color}10` };
    }

    switch (cardType) {
      case "incident":
      case "incident_card":
        return { borderColor: "#ef4444", bgColor: "rgba(239, 68, 68, 0.1)" };
      case "discovery":
        return { borderColor: "#3b82f6", bgColor: "rgba(59, 130, 246, 0.1)" };
      case "job":
      case "work_order":
        return { borderColor: "#eab308", bgColor: "rgba(234, 179, 8, 0.1)" };
      case "bids":
        return { borderColor: "#8b5cf6", bgColor: "rgba(139, 92, 246, 0.1)" };
      case "approval":
        return { borderColor: "#10b981", bgColor: "rgba(16, 185, 129, 0.1)" };
      case "completion":
        return { borderColor: "#22c55e", bgColor: "rgba(34, 197, 94, 0.1)" };
      default:
        return { borderColor: "#64748b", bgColor: "rgba(100, 116, 139, 0.1)" };
    }
  };

  const style = getCardStyle();

  // Handle action click
  const handleActionClick = async (action: CardAction) => {
    if (loadingAction) return;

    setLoadingAction(action.value);

    try {
      await onActionClick(action.value);
    } finally {
      setTimeout(() => setLoadingAction(null), 500);
    }
  };

  // Get actions from either actions or buttons array
  const actions = card.actions || card.buttons || [];

  return (
    <div
      className="rounded-lg border-2 overflow-hidden shadow-lg"
      style={{ borderColor: style.borderColor, backgroundColor: style.bgColor }}
    >
      {/* Header */}
      {card.title && (
        <div className="px-4 py-3 border-b" style={{ borderColor: style.borderColor }}>
          <h3 className="font-semibold text-white">{card.title}</h3>
        </div>
      )}

      {/* Body */}
      <div className="px-4 py-3 space-y-3">
        {/* Text */}
        {card.text && <p className="text-sm text-slate-300">{card.text}</p>}

        {/* Fields */}
        {card.fields && card.fields.length > 0 && (
          <div
            className={`grid gap-3 ${
              card.fields.some((f) => f.short) ? "grid-cols-2" : "grid-cols-1"
            }`}
          >
            {card.fields.map((field, idx) => (
              <div key={idx} className={field.short ? "" : "col-span-full"}>
                <div className="text-xs font-medium text-slate-400 mb-1">{field.title}</div>
                <div className="text-sm text-slate-200">{field.value}</div>
              </div>
            ))}
          </div>
        )}

        {/* Actions */}
        {actions.length > 0 && (
          <div className="flex flex-wrap gap-2 pt-2">
            {actions.map((action, idx) => {
              const isLoading = loadingAction === action.value;
              const buttonText = action.text || action.label || action.name;

              return (
                <button
                  key={idx}
                  onClick={() => handleActionClick(action)}
                  disabled={isLoading || !!loadingAction}
                  className="px-4 py-2 rounded text-sm font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                  style={{
                    backgroundColor: style.borderColor,
                    color: "white",
                  }}
                >
                  {isLoading ? "Processing..." : buttonText}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Footer */}
      {(card.footer || card.ts) && (
        <div
          className="px-4 py-2 border-t text-xs text-slate-400"
          style={{ borderColor: style.borderColor }}
        >
          {card.footer && <span>{card.footer}</span>}
          {card.ts && (
            <span className="ml-2">
              {new Date(card.ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
            </span>
          )}
        </div>
      )}

      {/* Metadata Debug (Development Only) */}
      {process.env.NODE_ENV === "development" && card.metadata && (
        <details className="px-4 py-2 text-xs text-slate-500 border-t" style={{ borderColor: style.borderColor }}>
          <summary className="cursor-pointer hover:text-slate-400">Card Metadata</summary>
          <pre className="mt-2 text-[10px] overflow-x-auto">
            {JSON.stringify(card.metadata, null, 2)}
          </pre>
        </details>
      )}
    </div>
  );
}
