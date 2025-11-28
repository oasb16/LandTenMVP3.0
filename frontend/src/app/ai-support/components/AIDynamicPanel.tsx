/**
 * AIDynamicPanel
 *
 * Router component that renders the appropriate panel based on UI mode
 */

"use client";

import { AnimatePresence } from "framer-motion";
import type { DynamicPanelProps } from "@/types/ai-support";

import ActionPanel from "../panels/ActionPanel";
import ItemPicker from "../panels/ItemPicker";
import ReasonPicker from "../panels/ReasonPicker";
import ResolutionPanel from "../panels/ResolutionPanel";
import DiagnosisPanel from "./DiagnosisPanel";

export default function AIDynamicPanel({
  uiMode,
  payload,
  onAction,
}: DynamicPanelProps) {
  // Helper to safely extract typed payload
  const getPayload = <T,>(defaultValue: T): T => {
    return (payload as T) || defaultValue;
  };

  return (
    <AnimatePresence mode="wait">
      {uiMode === "cta_panel" && (
        <ActionPanel
          key="cta"
          options={getPayload({ options: [] }).options}
          title={getPayload({ title: undefined }).title}
          subtitle={getPayload({ subtitle: undefined }).subtitle}
          onSelect={async (id) => {
            await onAction("user_message", { category: id });
          }}
        />
      )}

      {uiMode === "gallery" && (
        <ItemPicker
          key="gallery"
          items={getPayload({ items: [] }).items}
          title={getPayload({ title: undefined }).title}
          subtitle={getPayload({ subtitle: undefined }).subtitle}
          allowSkip={getPayload({ allow_skip: false }).allow_skip}
          onSelect={async (itemId, itemData) => {
            await onAction("item_selected", { item_id: itemId, item_data: itemData });
          }}
          onSkip={
            getPayload({ allow_skip: false }).allow_skip
              ? async () => {
                  await onAction("user_message", { text: "Skip item selection" });
                }
              : undefined
          }
        />
      )}

      {uiMode === "selector" && (
        <ReasonPicker
          key="selector"
          reasons={getPayload({ reasons: [] }).reasons}
          title={getPayload({ title: undefined }).title}
          subtitle={getPayload({ subtitle: undefined }).subtitle}
          selectedItem={getPayload({ selected_item: undefined }).selected_item}
          onSelect={async (reasonId, reason) => {
            await onAction("reason_selected", {
              reason_id: reasonId,
              reason_label: reason?.label,
            });
          }}
        />
      )}

      {uiMode === "diagnosis" && (
        <DiagnosisPanel
          key="diagnosis"
          data={getPayload({ status: "analyzing" })}
        />
      )}

      {uiMode === "resolution" && (
        <ResolutionPanel
          key="resolution"
          data={getPayload({
            summary: "",
            actions: [],
          })}
          onAction={async (actionId) => {
            await onAction("resolution_action", { action_id: actionId });
          }}
        />
      )}

      {uiMode === "escalation" && (
        <div
          key="escalation"
          className="p-6 border-t bg-gray-50 dark:bg-gray-900"
        >
          <h3 className="font-semibold text-lg mb-3 text-gray-900 dark:text-gray-100">
            Connect with a Human Agent
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
            A member of our support team will be with you shortly.
          </p>
          <textarea
            className="w-full p-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 resize-none"
            rows={4}
            placeholder={
              getPayload({ message_placeholder: "Describe your issue..." })
                .message_placeholder
            }
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                const message = e.currentTarget.value.trim();
                if (message) {
                  onAction("escalate_human", { message });
                  e.currentTarget.value = "";
                }
              }
            }}
          />
          <button
            onClick={() => {
              const textarea = document.querySelector("textarea");
              const message = textarea?.value.trim();
              if (message) {
                onAction("escalate_human", { message });
                if (textarea) textarea.value = "";
              }
            }}
            className="mt-3 w-full p-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
          >
            Send to Agent
          </button>
        </div>
      )}

      {uiMode === "complete" && (
        <div
          key="complete"
          className="p-6 border-t bg-green-50 dark:bg-green-900/20 text-center"
        >
          <div className="w-16 h-16 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg
              className="w-8 h-8 text-green-600 dark:text-green-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={3}
                d="M5 13l4 4L19 7"
              />
            </svg>
          </div>
          <h3 className="font-semibold text-lg text-gray-900 dark:text-gray-100 mb-2">
            All Set!
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Your request has been processed successfully.
          </p>
        </div>
      )}
    </AnimatePresence>
  );
}
