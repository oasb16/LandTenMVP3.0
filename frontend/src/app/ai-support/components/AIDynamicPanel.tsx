/**
 * AIDynamicPanel
 *
 * Router component that renders the appropriate panel based on UI mode
 * Extended for multi-persona flows (Phases 1-5)
 */

"use client";

import { AnimatePresence } from "framer-motion";
import type { UIMode, IntentType, FlowState } from "@/types/ai-support";

// Base panels
import ActionPanel from "../panels/ActionPanel";
import ItemPicker from "../panels/ItemPicker";
import ReasonPicker from "../panels/ReasonPicker";
import SummaryPanel from "../panels/SummaryPanel";
import ResolutionPanel from "../panels/ResolutionPanel";
import FallbackPanel from "../panels/FallbackPanel";

// Phase 1: Tenant Photo Upload
import PhotoUploader from "../panels/PhotoUploader";

// Phase 2: Landlord Incident Triage
import IncidentDetailPanel from "../panels/IncidentDetailPanel";
import TriagePanel from "../panels/TriagePanel";

// Phase 3: Landlord Job + Bids
import BidComparisonPanel from "../panels/BidComparisonPanel";

// Phase 4: Contractor Bidding
import JobDetailPanel from "../panels/JobDetailPanel";
import BidForm from "../panels/BidForm";

// Phase 5: Job Execution
import StatusTrackerPanel from "../panels/StatusTrackerPanel";
import AcceptancePanel from "../panels/AcceptancePanel";
import CompletionForm from "../panels/CompletionForm";

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
            const selectedItem = getPayload<any>({ items: [] }).items.find((item: any) => item.id === itemId);
            await sendIntent("item_selected", {
              item_id: itemId,
              item_title: selectedItem?.title || itemId
            });
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

      {/* Summary - Stage: summary */}
      {uiMode === "summary" && (
        <SummaryPanel
          key="summary"
          summary={getPayload<any>({
            selected_cta: "",
            selected_cta_label: "",
            selected_item_id: "",
            selected_item_title: "",
            selected_reason: "",
          })}
          onConfirm={async () => {
            await sendIntent("confirm_summary", {});
          }}
          onEdit={async () => {
            await sendIntent("edit_summary", {});
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

      {/* ===== PHASE 1: TENANT PHOTO UPLOAD ===== */}
      {uiMode === "photo_uploader" && (
        <PhotoUploader
          key="photo_uploader"
          maxPhotos={getPayload<any>({ max_photos: 5 }).max_photos}
          required={getPayload<any>({ required: false }).required}
          existingPhotos={getPayload<any>({ existing_photos: [] }).existing_photos}
          onUpload={async (photos) => {
            await sendIntent("photos_uploaded", { photos: photos.map(f => f.name) });
          }}
          onSkip={async () => {
            await sendIntent("skip_photos", {});
          }}
        />
      )}

      {/* ===== PHASE 2: LANDLORD INCIDENT TRIAGE ===== */}
      {uiMode === "incident_detail" && (
        <IncidentDetailPanel
          key="incident_detail"
          incident={getPayload<any>({ incident: {} }).incident}
          actions={getPayload<any>({ actions: [] }).actions}
          onAction={async (actionId) => {
            await sendIntent("select_incident", { action_id: actionId });
          }}
        />
      )}

      {uiMode === "triage_panel" && (
        <TriagePanel
          key="triage_panel"
          incidentId={getPayload<any>({ incident_id: "" }).incident_id}
          incidentSummary={getPayload<any>({ incident_summary: "" }).incident_summary}
          classificationOptions={getPayload<any>({ classification_options: [] }).classification_options}
          onClassify={async (classificationId) => {
            await sendIntent("classify_incident", { classification_id: classificationId });
          }}
        />
      )}

      {/* ===== PHASE 3: LANDLORD JOB + BIDS ===== */}
      {uiMode === "bid_comparison" && (
        <BidComparisonPanel
          key="bid_comparison"
          jobId={getPayload<any>({ job_id: "" }).job_id}
          jobTitle={getPayload<any>({ job_title: "" }).job_title}
          bids={getPayload<any>({ bids: [] }).bids}
          onSelectBid={async (bidId) => {
            await sendIntent("approve_bid", { bid_id: bidId });
          }}
        />
      )}

      {/* ===== PHASE 4: CONTRACTOR BIDDING ===== */}
      {uiMode === "job_detail" && (
        <JobDetailPanel
          key="job_detail"
          job={getPayload<any>({ job: {} }).job}
          canBid={getPayload<any>({ can_bid: false }).can_bid}
          existingBid={getPayload<any>({ existing_bid: undefined }).existing_bid}
          onBid={async () => {
            await sendIntent("select_job", { job_id: getPayload<any>({ job: { id: "" } }).job.id });
          }}
          onBack={async () => {
            await sendIntent("ai_continue", {});
          }}
        />
      )}

      {uiMode === "bid_form" && (
        <BidForm
          key="bid_form"
          jobId={getPayload<any>({ job_id: "" }).job_id}
          jobTitle={getPayload<any>({ job_title: "" }).job_title}
          suggestedPriceRange={getPayload<any>({ suggested_price_range: undefined }).suggested_price_range}
          onSubmit={async (bidData) => {
            await sendIntent("submit_bid", bidData);
          }}
          onCancel={async () => {
            await sendIntent("ai_continue", {});
          }}
        />
      )}

      {/* ===== PHASE 5: JOB EXECUTION ===== */}
      {uiMode === "status_tracker" && (
        <StatusTrackerPanel
          key="status_tracker"
          entityType={getPayload<any>({ entity_type: "incident" }).entity_type}
          entityId={getPayload<any>({ entity_id: "" }).entity_id}
          title={getPayload<any>({ title: "" }).title}
          currentStatus={getPayload<any>({ current_status: "" }).current_status}
          timeline={getPayload<any>({ timeline: [] }).timeline}
          nextActions={getPayload<any>({ next_actions: undefined }).next_actions}
          onAction={async (actionId) => {
            await sendIntent("resolution_action", { action_id: actionId });
          }}
          onBack={async () => {
            await sendIntent("ai_continue", {});
          }}
        />
      )}

      {uiMode === "job_acceptance" && (
        <AcceptancePanel
          key="job_acceptance"
          jobId={getPayload<any>({ job_id: "" }).job_id}
          jobTitle={getPayload<any>({ job_title: "" }).job_title}
          approvedBid={getPayload<any>({ approved_bid: {} }).approved_bid}
          terms={getPayload<any>({ terms: [] }).terms}
          onAccept={async () => {
            await sendIntent("accept_job", { job_id: getPayload<any>({ job_id: "" }).job_id });
          }}
          onDecline={async () => {
            await sendIntent("decline_job", { job_id: getPayload<any>({ job_id: "" }).job_id });
          }}
          onBack={async () => {
            await sendIntent("ai_continue", {});
          }}
        />
      )}

      {uiMode === "completion_form" && (
        <CompletionForm
          key="completion_form"
          jobId={getPayload<any>({ job_id: "" }).job_id}
          jobTitle={getPayload<any>({ job_title: "" }).job_title}
          workSummaryRequired={getPayload<any>({ work_summary_required: true }).work_summary_required}
          photosRequired={getPayload<any>({ photos_required: true }).photos_required}
          onSubmit={async (data) => {
            await sendIntent("mark_complete", {
              job_id: getPayload<any>({ job_id: "" }).job_id,
              summary: data.summary,
              photos: data.photos.map(f => f.name),
            });
          }}
          onCancel={async () => {
            await sendIntent("ai_continue", {});
          }}
        />
      )}
    </AnimatePresence>
  );
}
