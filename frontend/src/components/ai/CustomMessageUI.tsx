"use client";

import Image from "next/image";
import { motion } from "framer-motion";
import React, { memo, useCallback, useEffect, useMemo, useState } from "react";
import type { Attachment, MessageResponse } from "stream-chat";
import { Sparkles, ChevronDown } from "lucide-react";
import { MessageCards } from "./MessageCards";
import { AIResponseParser } from "./AIResponseParser";

type StreamMessage = MessageResponse;

type CustomMessageUIProps = {
  message: StreamMessage;
  currentUserId?: string;
  onActionClick?: (actionValue: string) => Promise<void> | void;
};

type MetadataPayload = {
  context_type?: string;
  incident_id?: string | null;
  persona?: string;
  flow_state?: { stage?: string | null };
};

const CARD_BORDER: Record<string, string> = {
  incident: "border-red-500",
  discovery: "border-amber-500",
  job: "border-indigo-500",
  approval: "border-emerald-500",
  bids: "border-blue-400",
  completion: "border-emerald-500",
};

const deriveStage = (contextType?: string): string | undefined => {
  if (!contextType) return undefined;
  const lowered = contextType.toLowerCase();
  if (lowered.includes("incident")) return "incident";
  if (lowered.includes("discovery")) return "discovery";
  if (lowered.includes("job")) return "job";
  if (lowered.includes("approval")) return "approval";
  if (lowered.includes("completion")) return "completion";
  if (lowered.includes("policy")) return "policy_violation";
  return lowered;
};

const STAGE_PULSE_DURATION = 2200;

/**
 * Safely detect and parse JSON from message text.
 * Returns parsed data if valid and matches expected structure, null otherwise.
 *
 * Handles multiple JSON structures:
 * 1. { analysis: { summary, next_actions } }
 * 2. { summary, next_actions } (top-level)
 * 3. { reasoning, answer, next_actions }
 */
function tryParseStructuredReasoning(text: string): { analysis?: { summary?: string; next_actions?: Array<{ action: string; details?: string }> } } | null {
  const trimmed = text.trim();

  // Quick check: does it look like JSON?
  if (!trimmed.startsWith("{") && !trimmed.startsWith("[")) {
    return null;
  }

  try {
    const parsed = JSON.parse(trimmed);

    if (!parsed || typeof parsed !== "object") {
      return null;
    }

    // Case 1: Already has analysis field
    if (parsed.analysis) {
      return parsed;
    }

    // Case 2: Top-level summary/next_actions - normalize to expected structure
    if (parsed.summary || parsed.next_actions) {
      return {
        analysis: {
          summary: parsed.summary || parsed.answer || parsed.reply || parsed.reasoning,
          next_actions: parsed.next_actions,
        },
      };
    }

    // Case 3: Has related_to_property_management field (AI reasoning output)
    if (parsed.related_to_property_management !== undefined || parsed.analysis_summary) {
      // Convert AI reasoning structure to display format
      const summary = parsed.analysis_summary || parsed.reasoning || "Analysis completed.";
      const actions = parsed.next_actions || (parsed.recommended_actions ?
        parsed.recommended_actions.map((action: string) => ({ action })) :
        []);

      return {
        analysis: {
          summary,
          next_actions: actions,
        },
      };
    }

    return null;
  } catch {
    return null;
  }
}

export const CustomMessageUI = memo(function CustomMessageUI({
  message,
  currentUserId,
  onActionClick,
}: CustomMessageUIProps) {
  const msg = message;

  const handleActionClick = useCallback(
    async (actionValue: string) => {
      await onActionClick?.(actionValue);
    },
    [onActionClick],
  );

  const attachments = useMemo<Attachment[]>(
    () => (Array.isArray(msg?.attachments) ? (msg.attachments as Attachment[]) : []),
    [msg?.attachments],
  );

  const cardAttachments = useMemo(
    () =>
      attachments.filter((att) =>
        ["incident", "discovery", "job", "bids", "approval", "completion", "custom_actions"].includes(att.type ?? ""),
      ),
    [attachments],
  );

  const messageText = useMemo(() => {
    const raw = msg?.text ?? "";
    if (!raw.startsWith("[AI_TYPE:")) {
      return raw;
    }
    return raw.replace(/^\[AI_TYPE:.*?\]\n/, "");
  }, [msg?.text]);

  const metadata = useMemo<MetadataPayload>(() => {
    const raw = (msg as { metadata?: MetadataPayload })?.metadata ?? {};
    return raw;
  }, [msg]);

  const stage = deriveStage(metadata.context_type || metadata.flow_state?.stage || msg?.type);
  const isPolicyViolation = stage === "policy_violation";
  const [policyHighlight, setPolicyHighlight] = useState(false);
  const [showRawJSON, setShowRawJSON] = useState(false);

  // Try to parse structured reasoning from message text
  const parsedReasoning = useMemo(() => {
    return tryParseStructuredReasoning(messageText);
  }, [messageText]);

  useEffect(() => {
    if (isPolicyViolation) {
      setPolicyHighlight(true);
      const timeout = setTimeout(() => setPolicyHighlight(false), STAGE_PULSE_DURATION);
      return () => clearTimeout(timeout);
    }
    setPolicyHighlight(false);
    return undefined;
  }, [isPolicyViolation, msg?.id]);

  if (!msg || typeof msg !== "object") return null;

  const actorId = msg?.user?.id ?? "";
  const actorName = msg?.user?.name ?? "";
  const messageType = (msg?.type as string | undefined) ?? "regular";

  const isOwnMessage = currentUserId ? actorId === currentUserId : Boolean((msg as { own?: boolean }).own);

  const isAIMessage =
    actorId.startsWith("ai-") ||
    actorName.includes("PropertyHelper") ||
    actorName.includes("PropertyManager") ||
    actorName.includes("JobAssistant") ||
    actorName.includes("LandTen Agent") ||
    messageType === "ai-message";

  const contextType = metadata.context_type;
  const isSystemMessage = msg?.type === "system" && !contextType;
  if (isSystemMessage) {
    return null;
  }

  const containerAlignment = isOwnMessage ? "items-end" : "items-start";
  const bubbleAlignment = isOwnMessage ? "self-end" : "self-start";

  const bubbleClasses = [
    "max-w-[85%] rounded-3xl px-4 py-3 text-sm leading-relaxed shadow-lg transition",
    isAIMessage
      ? "bg-gradient-to-br from-slate-900/80 via-slate-900 to-emerald-900/70 text-emerald-100 border border-emerald-500/30"
      : isOwnMessage
        ? "bg-emerald-500/20 text-emerald-100 border border-emerald-400/30"
        : "bg-slate-800/70 text-slate-100 border border-slate-700/50",
    policyHighlight ? "ring-2 ring-rose-400/70" : "ring-0",
  ].join(" ");

  const primaryCardType = cardAttachments[0]?.type;
  const cardAccent = CARD_BORDER[primaryCardType ?? ""] || "border-slate-700";

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 6 }}
      transition={{ type: "spring", stiffness: 320, damping: 30 }}
      className={`flex w-full flex-col gap-2 ${containerAlignment}`}
      data-message-id={msg?.id}
    >
      {isAIMessage && (
        <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-emerald-300">
          <Sparkles className="h-3 w-3" /> Intelligent assistant
        </div>
      )}

      {messageText && parsedReasoning ? (
        // Structured reasoning detected - render as natural language UI
        <div className="flex w-full max-w-[90%] flex-col gap-2">
          <AIResponseParser
            data={parsedReasoning}
            stage={stage}
            incidentId={metadata.incident_id}
            persona={metadata.persona}
          />

          {/* Show Details toggle */}
          <button
            onClick={() => setShowRawJSON(!showRawJSON)}
            className="flex items-center gap-1 self-start text-xs text-slate-400 hover:text-emerald-300 transition-colors"
          >
            <ChevronDown
              className={`h-3 w-3 transition-transform ${showRawJSON ? "rotate-180" : ""}`}
            />
            {showRawJSON ? "Hide" : "Show"} Details
          </button>

          {showRawJSON && (
            <motion.pre
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="overflow-x-auto rounded-lg bg-slate-950/80 border border-slate-700 p-3 text-xs text-slate-300 font-mono"
            >
              {JSON.stringify(parsedReasoning, null, 2)}
            </motion.pre>
          )}
        </div>
      ) : messageText ? (
        // Regular text message
        <motion.div
          layout
          className={`${bubbleClasses} ${bubbleAlignment}`}
          transition={{ type: "spring", stiffness: 260, damping: 24 }}
        >
          {messageText}
        </motion.div>
      ) : null}

      {contextType && (
        <span className="inline-flex w-fit items-center gap-1 rounded-full bg-slate-900/80 px-2 py-0.5 text-xs text-slate-300">
          Stage: {contextType}
        </span>
      )}

      {cardAttachments.length > 0 && (
        <div className={`w-full max-w-[90%] overflow-hidden rounded-xl border ${cardAccent} bg-slate-900/60`}>
          <MessageCards message={msg as StreamMessage} onActionClick={handleActionClick} />
        </div>
      )}

      {attachments
        .filter((att) =>
          !["incident", "discovery", "job", "bids", "approval", "completion", "custom_actions"].includes(att.type ?? ""),
        )
        .map((att, idx) => {
          if (att.type === "image" && att.image_url) {
            return (
              <div key={`${att.image_url}-${idx}`} className="overflow-hidden rounded-xl border border-slate-800">
                <Image
                  src={att.image_url}
                  alt={att.title || "Attachment"}
                  width={800}
                  height={600}
                  className="h-auto max-h-72 w-full object-cover"
                  sizes="(max-width: 768px) 100vw, 600px"
                />
              </div>
            );
          }
          if (att.type === "file" && att.asset_url) {
            return (
              <a
                key={`${att.asset_url}-${idx}`}
                href={att.asset_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900/70 p-3 text-sm text-slate-200 transition hover:bg-slate-800"
              >
                <span className="text-lg">📎</span>
                <span>{att.title || "File"}</span>
              </a>
            );
          }
          return null;
        })}
    </motion.div>
  );
});
