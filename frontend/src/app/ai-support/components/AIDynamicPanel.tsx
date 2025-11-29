/**
 * AIDynamicPanel
 *
 * Router component that renders the appropriate panel based on UI mode
 * Amazon Spec: cta_panel, gallery, selector, chat, resolution, fallback
 */

"use client";

import { AnimatePresence } from "framer-motion";
import type { UIMode, IntentType, FlowState } from "@/types/ai-support";

import ActionPanel from "../panels/ActionPanel";
import ItemPicker from "../panels/ItemPicker";
import ReasonPicker from "../panels/ReasonPicker";
import ResolutionPanel from "../panels/ResolutionPanel";
import FallbackPanel from "../panels/FallbackPanel";

interface AIDynamicPanelProps {
  uiMode: UIMode;
  payload: Record<string, unknown>;
  sendIntent: (intent: IntentType, payload: Record<string, unknown>) => Promise<void>;
  flowState: FlowState | null;
}

export default function AIDynamicPanel({
  uiMode,
  payload,
  sendIntent,
  flowState,
}: AIDynamicPanelProps) {
  // Helper to safely extract typed payload
  const getPayload = <T,>(defaultValue: T): T => {
    return (payload as T) || defaultValue;
  };

  return (
    <AnimatePresence mode="wait">
      {/* CTA Panel - Stage: intro */}
      {uiMode === "cta_panel" && (
        <ActionPanel
          key="cta"
          options={getPayload({ options: [] }).options}
          onSelect={async (id) => {
            await sendIntent("select_cta", { cta_id: id });
          }}
        />
      )}

      {/* Gallery - Stage: item_select */}
      {uiMode === "gallery" && (
        <ItemPicker
          key="gallery"
          items={getPayload({ items: [] }).items}
          onSelect={async (itemId) => {
            await sendIntent("item_selected", { item_id: itemId });
          }}
        />
      )}

      {/* Selector - Stage: issue_select */}
      {uiMode === "selector" && (
        <ReasonPicker
          key="selector"
          reasons={getPayload({ reasons: [] }).reasons}
          onSelect={async (reason) => {
            await sendIntent("reason_selected", { reason });
          }}
        />
      )}

      {/* Chat - Stage: diagnosis */}
      {uiMode === "chat" && (
        <div
          key="chat"
          className="flex items-center justify-center p-8 text-slate-400 text-sm"
        >
          <div className="text-center">
            <div className="mb-3 text-lg">💬</div>
            <p>Use the chat panel on the left for diagnosis</p>
            {flowState?.selected_reason && (
              <p className="mt-2 text-xs text-slate-500">
                Issue: {flowState.selected_reason}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Resolution - Stage: resolution */}
      {uiMode === "resolution" && (
        <ResolutionPanel
          key="resolution"
          summary={getPayload({ summary: "" }).summary}
          actions={getPayload({ actions: [] }).actions}
          onAction={async (actionId) => {
            await sendIntent("resolution_action", { action_id: actionId });
          }}
        />
      )}

      {/* Fallback - Error state */}
      {uiMode === "fallback" && (
        <FallbackPanel
          key="fallback"
          error={getPayload({ error: "An error occurred" }).error}
        />
      )}
    </AnimatePresence>
  );
}
