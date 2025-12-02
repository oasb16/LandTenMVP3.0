/**
 * AI Support Experience - Type Definitions
 *
 * Complete type system for the Amazon-style guided support flow
 *
 * OFFICIAL SPECIFICATION:
 * - Stages: intro → item_select → issue_select → diagnosis → resolution
 * - UI Modes: cta_panel, gallery, selector, chat, resolution, fallback
 * - Event Protocol: ai_intent (frontend→backend), ai_state (backend→frontend)
 */

// ============================================================================
// AMAZON-STYLE FLOW - CORE TYPES
// ============================================================================

/**
 * User personas - determines vocabulary, actions, and routing
 */
export type Persona = "tenant" | "landlord" | "property_manager" | "contractor";

/**
 * Amazon-style flow stages (backbone of flow)
 * Extended for multi-persona support
 */
export type Stage =
  | "intro"                // Determine persona, show welcome + options
  | "item_select"          // Show items (appliances, incidents, jobs, etc.)
  | "issue_select"         // Choose what's wrong with the item
  | "photo_upload"         // Upload photos of the issue
  | "summary"              // Confirmation summary before diagnosis
  | "diagnosis"            // Multi-turn troubleshooting
  | "resolution"           // Final actions

  // Landlord-specific stages
  | "incident_detail"      // View full incident details
  | "incident_triage"      // Classify and prioritize incident
  | "job_creation"         // Create work order/job
  | "bid_comparison"       // Compare contractor bids
  | "bid_approval"         // Approve selected bid

  // Contractor-specific stages
  | "job_browse"           // Browse available jobs
  | "job_detail"           // View job details
  | "bid_submission"       // Submit bid for job
  | "job_acceptance"       // Accept approved job
  | "job_execution"        // Track job progress
  | "job_completion"       // Mark job complete

  // Shared tracking
  | "status_tracking";     // Track incident/job status

/**
 * UI Modes - determines which panel is displayed
 * Extended for multi-persona flows
 */
export type UIMode =
  | "cta_panel"             // Large button menu (What do you need help with?)
  | "gallery"               // Scrollable list of items (orders, maintenance, etc.)
  | "selector"              // List of issue reasons
  | "photo_uploader"        // Photo upload interface
  | "summary"               // Confirmation summary panel
  | "chat"                  // Pure conversational messages (diagnosis)
  | "resolution"            // Final actions user can take
  | "fallback"              // Chat unavailable

  // Landlord-specific UI modes
  | "incident_detail"       // Full incident details view
  | "triage_panel"          // Incident classification/prioritization
  | "job_form"              // Job creation form
  | "bid_comparison"        // Side-by-side bid comparison
  | "bid_approval"          // Bid approval interface

  // Contractor-specific UI modes
  | "job_gallery"           // Browse available jobs
  | "job_detail"            // Full job details view
  | "bid_form"              // Bid submission form
  | "job_acceptance"        // Job acceptance confirmation
  | "completion_form"       // Job completion form

  // Shared UI modes
  | "status_tracker";       // Status tracking timeline

/**
 * Intent types - user/system actions (Amazon spec)
 * Extended for multi-persona flows
 */
export type IntentType =
  // User-initiated intents (base)
  | "user_message"          // Plain chat text
  | "user_action"           // Action clicked from AI message card
  | "select_cta"            // Selected main option from CTA panel
  | "item_selected"         // Selected item from gallery
  | "reason_selected"       // Selected reason from selector
  | "photos_uploaded"       // Photos uploaded successfully
  | "skip_photos"           // Skip photo upload
  | "confirm_summary"       // Confirmed summary, proceed to diagnosis
  | "edit_summary"          // Edit summary, go back to selection
  | "diagnosis_answer"      // Answer during diagnosis
  | "resolution_action"     // Final action chosen

  // Landlord-initiated intents
  | "select_incident"       // Selected incident to view/triage
  | "classify_incident"     // Classified incident (emergency/routine/etc)
  | "create_job"            // Create job from incident
  | "request_bids"          // Request bids from contractors
  | "select_bid"            // Selected bid to review
  | "approve_bid"           // Approved bid
  | "reject_bid"            // Rejected bid
  | "close_incident"        // Mark incident as resolved

  // Contractor-initiated intents
  | "select_job"            // Selected job to view
  | "submit_bid"            // Submitted bid for job
  | "accept_job"            // Accepted approved job
  | "decline_job"           // Declined job
  | "start_work"            // Started work on job
  | "update_progress"       // Updated job progress
  | "mark_complete"         // Marked job as complete
  | "upload_completion_photos" // Uploaded completion photos

  // System-initiated intents
  | "ai_init"               // Initialize session
  | "ai_continue"           // Continue flow
  | "ai_escalate"           // Escalate to human
  | "ai_close_session";     // Close session

// ============================================================================
// PAYLOAD TYPES
// ============================================================================

/**
 * CTA Panel (Stage: intro, UI Mode: cta_panel)
 */
export interface CTAOption {
  id: string;
  label: string;
  description?: string;
  icon?: string;
}

export interface CTAPanelPayload {
  options: CTAOption[];
}

/**
 * Gallery/Item Picker (Stage: item_select, UI Mode: gallery)
 */
export interface GalleryItem {
  id: string;
  title: string;
  subtitle?: string;
  image?: string;
  metadata?: Record<string, unknown>;
}

export interface GalleryPayload {
  items: GalleryItem[];
}

/**
 * Reason Selector (Stage: issue_select, UI Mode: selector)
 */
export interface ReasonSelectorPayload {
  reasons: string[];  // Simple string array per Amazon spec
  itemId?: string;    // Optional reference to selected item
}

/**
 * Chat/Diagnosis (Stage: diagnosis, UI Mode: chat)
 */
export interface ChatPayload {
  agent_prompt?: string;  // AI's response/question
  reason?: string;        // Issue reason being diagnosed
  summary?: string;       // Current understanding
}

/**
 * Summary (Stage: summary, UI Mode: summary)
 */
export interface SummaryPayload {
  selected_cta: string;
  selected_cta_label: string;
  selected_item_id: string;
  selected_item_title: string;
  selected_reason: string;
  severity?: string;
  urgency?: string;
}

export interface SummaryPanelProps {
  summary: SummaryPayload;
  onConfirm: () => void;
  onEdit: () => void;
}

/**
 * Resolution (Stage: resolution, UI Mode: resolution)
 */
export interface ResolutionAction {
  id: string;
  label: string;
}

export interface ResolutionPayload {
  summary: string;
  actions: ResolutionAction[];
}

/**
 * Fallback (UI Mode: fallback)
 */
export interface FallbackPayload {
  error: string;
}

/**
 * Photo Uploader (Stage: photo_upload, UI Mode: photo_uploader)
 */
export interface PhotoUploaderPayload {
  max_photos?: number;
  required?: boolean;
  existing_photos?: string[];
}

/**
 * Incident Detail (Stage: incident_detail, UI Mode: incident_detail)
 */
export interface IncidentDetailPayload {
  incident: {
    id: string;
    title: string;
    description: string;
    category: string;
    status: string;
    priority?: string;
    reported_by: string;
    reported_at: string;
    photos?: string[];
    location?: string;
  };
  actions: Array<{ id: string; label: string }>;
}

/**
 * Triage Panel (Stage: incident_triage, UI Mode: triage_panel)
 */
export interface TriagePayload {
  incident_id: string;
  incident_summary: string;
  classification_options: Array<{
    id: string;
    label: string;
    description: string;
    priority: "emergency" | "urgent" | "routine" | "low";
  }>;
}

/**
 * Bid Comparison (Stage: bid_comparison, UI Mode: bid_comparison)
 */
export interface BidComparisonPayload {
  job_id: string;
  job_title: string;
  bids: Array<{
    id: string;
    contractor_name: string;
    contractor_rating?: number;
    price: number;
    estimated_duration: string;
    proposed_start_date: string;
    notes?: string;
    materials_included: boolean;
  }>;
}

/**
 * Job Detail (Stage: job_detail, UI Mode: job_detail)
 */
export interface JobDetailPayload {
  job: {
    id: string;
    title: string;
    description: string;
    category: string;
    location: string;
    urgency: string;
    budget_range?: string;
    posted_at: string;
    deadline?: string;
    photos?: string[];
    requirements?: string[];
  };
  can_bid: boolean;
  existing_bid?: {
    id: string;
    price: number;
    status: string;
  };
}

/**
 * Bid Form (Stage: bid_submission, UI Mode: bid_form)
 */
export interface BidFormPayload {
  job_id: string;
  job_title: string;
  suggested_price_range?: { min: number; max: number };
}

/**
 * Status Tracker (UI Mode: status_tracker)
 */
export interface StatusTrackerPayload {
  entity_type: "incident" | "job";
  entity_id: string;
  title: string;
  current_status: string;
  timeline: Array<{
    timestamp: string;
    status: string;
    description: string;
    actor?: string;
  }>;
  next_actions?: Array<{ id: string; label: string }>;
}

/**
 * Acceptance Panel (Stage: job_acceptance, UI Mode: job_acceptance)
 */
export interface AcceptancePanelPayload {
  job_id: string;
  job_title: string;
  approved_bid: {
    price: number;
    estimated_duration: string;
    start_date: string;
  };
  terms: string[];
}

/**
 * Completion Form (Stage: job_completion, UI Mode: completion_form)
 */
export interface CompletionFormPayload {
  job_id: string;
  job_title: string;
  work_summary_required: boolean;
  photos_required: boolean;
}

// ============================================================================
// BACKEND PROTOCOL
// ============================================================================

/**
 * Backend Response (ai_state event)
 */
export interface AIStateEvent {
  type: "ai_state";
  stage: Stage;
  ui_mode: UIMode;
  persona?: Persona;
  payload:
    | CTAPanelPayload
    | GalleryPayload
    | ReasonSelectorPayload
    | ChatPayload
    | ResolutionPayload
    | FallbackPayload
    | Record<string, unknown>;
}

/**
 * Frontend Intent (ai_intent event)
 */
export interface AIIntentEvent {
  type: "ai_intent";
  intent: IntentType;
  payload: Record<string, unknown>;
}

// ============================================================================
// FLOW STATE
// ============================================================================

/**
 * Overall flow state tracking
 */
export interface FlowState {
  session_id: string | null;
  incident_id: string | null;
  persona: Persona;
  current_stage: Stage;
  current_mode: UIMode;
  selected_item: GalleryItem | null;
  selected_reason: string | null;
  chat_channel_id: string | null;
}

// ============================================================================
// COMPONENT PROPS
// ============================================================================

export interface ActionPanelProps {
  options: CTAOption[];
  onSelect: (optionId: string) => void;
}

export interface ItemPickerProps {
  items: GalleryItem[];
  onSelect: (itemId: string) => void;
}

export interface ReasonPickerProps {
  reasons: string[];
  onSelect: (reason: string) => void;
}

export interface ResolutionPanelProps {
  summary: string;
  actions: ResolutionAction[];
  onAction: (actionId: string) => void;
}

export interface FallbackPanelProps {
  error: string;
}

export interface PhotoUploaderProps {
  maxPhotos?: number;
  required?: boolean;
  existingPhotos?: string[];
  onUpload: (photos: File[]) => void;
  onSkip?: () => void;
}

export interface IncidentDetailPanelProps {
  incident: IncidentDetailPayload["incident"];
  actions: Array<{ id: string; label: string }>;
  onAction: (actionId: string) => void;
}

export interface TriagePanelProps {
  incidentId: string;
  incidentSummary: string;
  classificationOptions: TriagePayload["classification_options"];
  onClassify: (classificationId: string) => void;
}

export interface BidComparisonPanelProps {
  jobId: string;
  jobTitle: string;
  bids: BidComparisonPayload["bids"];
  onSelectBid: (bidId: string) => void;
}

export interface JobDetailPanelProps {
  job: JobDetailPayload["job"];
  canBid: boolean;
  existingBid?: JobDetailPayload["existing_bid"];
  onBid: () => void;
  onBack: () => void;
}

export interface BidFormProps {
  jobId: string;
  jobTitle: string;
  suggestedPriceRange?: { min: number; max: number };
  onSubmit: (bidData: { price: number; duration: string; startDate: string; notes: string }) => void;
  onCancel: () => void;
}

export interface StatusTrackerPanelProps {
  entityType: "incident" | "job";
  entityId: string;
  title: string;
  currentStatus: string;
  timeline: StatusTrackerPayload["timeline"];
  nextActions?: Array<{ id: string; label: string }>;
  onAction?: (actionId: string) => void;
  onBack?: () => void | Promise<void>;
}

export interface AcceptancePanelProps {
  jobId: string;
  jobTitle: string;
  approvedBid: AcceptancePanelPayload["approved_bid"];
  terms: string[];
  onAccept: () => void;
  onDecline: () => void;
  onBack?: () => void | Promise<void>;
}

export interface CompletionFormProps {
  jobId: string;
  jobTitle: string;
  workSummaryRequired: boolean;
  photosRequired: boolean;
  onSubmit: (data: { summary: string; photos: File[] }) => void;
  onCancel: () => void;
}

// ============================================================================
// HOOK RETURN TYPES
// ============================================================================

/**
 * Return type for useAISupportFlow hook
 */
export interface AISupportFlowHook {
  // Stream Chat
  channel: any | null;

  // State
  uiMode: UIMode;
  stage: Stage;
  payload: Record<string, unknown>;
  flowState: FlowState | null;

  // Loading states
  loading: boolean;
  initializing: boolean;

  // Error handling
  error: string | null;

  // Actions
  sendIntent: (intent: IntentType, payload: Record<string, unknown>) => Promise<void>;
  resetSession: () => Promise<void>;
}

// ============================================================================
// VALIDATION
// ============================================================================

export const isValidUIMode = (mode: unknown): mode is UIMode => {
  return typeof mode === "string" && [
    "cta_panel", "gallery", "selector", "photo_uploader", "summary", "chat", "resolution", "fallback",
    "incident_detail", "triage_panel", "job_form", "bid_comparison", "bid_approval",
    "job_gallery", "job_detail", "bid_form", "job_acceptance", "completion_form", "status_tracker"
  ].includes(mode);
};

export const isValidStage = (stage: unknown): stage is Stage => {
  return typeof stage === "string" && [
    "intro", "item_select", "issue_select", "photo_upload", "summary", "diagnosis", "resolution",
    "incident_detail", "incident_triage", "job_creation", "bid_comparison", "bid_approval",
    "job_browse", "job_detail", "bid_submission", "job_acceptance", "job_execution", "job_completion",
    "status_tracking"
  ].includes(stage);
};

export const isValidIntentType = (type: unknown): type is IntentType => {
  return typeof type === "string" && [
    "user_message", "select_cta", "item_selected", "reason_selected", "photos_uploaded", "skip_photos",
    "confirm_summary", "edit_summary", "diagnosis_answer", "resolution_action",
    "select_incident", "classify_incident", "create_job", "request_bids", "select_bid", "approve_bid", "reject_bid", "close_incident",
    "select_job", "submit_bid", "accept_job", "decline_job", "start_work", "update_progress", "mark_complete", "upload_completion_photos",
    "ai_init", "ai_continue", "ai_escalate", "ai_close_session"
  ].includes(type);
};

export const isValidPersona = (persona: unknown): persona is Persona => {
  return typeof persona === "string" &&
    ["tenant", "landlord", "property_manager", "contractor"].includes(persona);
};
