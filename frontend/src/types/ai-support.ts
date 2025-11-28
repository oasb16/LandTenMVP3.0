/**
 * AI Support Experience - Type Definitions
 *
 * Complete type system for the Amazon-style guided support flow
 */

// ============================================================================
// CORE TYPES
// ============================================================================

/**
 * User persona types
 */
export type Persona = "tenant" | "landlord" | "contractor";

/**
 * UI Mode - determines which panel is currently displayed
 */
export type UIMode =
  | "idle"           // No active panel
  | "cta_panel"      // Initial "How can we help?" panel
  | "gallery"        // Item picker (properties, units, etc.)
  | "selector"       // Reason picker (issue selection)
  | "diagnosis"      // AI is analyzing the issue
  | "resolution"     // Final resolution options
  | "escalation"     // Human escalation form
  | "complete";      // Session complete

/**
 * Intent types - user actions that trigger backend processing
 */
export type IntentType =
  | "user_message"       // Free-form text message
  | "item_selected"      // User selected an item from gallery
  | "reason_selected"    // User selected a reason/issue
  | "resolution_action"  // User chose a resolution action
  | "escalate_human"     // User requested human support
  | "session_init";      // Session initialization

// ============================================================================
// PAYLOAD TYPES
// ============================================================================

/**
 * CTA Panel Options
 */
export interface CTAOption {
  id: string;
  label: string;
  description?: string;
  icon?: string;
  persona_specific?: boolean;
}

export interface CTAPanelPayload {
  title?: string;
  subtitle?: string;
  options: CTAOption[];
}

/**
 * Gallery/Item Picker
 */
export interface GalleryItem {
  id: string;
  title: string;
  subtitle?: string;
  description?: string;
  image?: string;
  metadata?: Record<string, unknown>;
}

export interface GalleryPayload {
  title?: string;
  subtitle?: string;
  items: GalleryItem[];
  allow_skip?: boolean;
}

/**
 * Reason Selector
 */
export interface ReasonOption {
  id: string;
  label: string;
  description?: string;
  severity?: "low" | "medium" | "high" | "urgent";
}

export interface ReasonSelectorPayload {
  title?: string;
  subtitle?: string;
  reasons: ReasonOption[];
  selected_item?: GalleryItem;
}

/**
 * Diagnosis State
 */
export interface DiagnosisPayload {
  status: "analyzing" | "complete" | "error";
  message?: string;
  progress?: number;
}

/**
 * Resolution Panel
 */
export interface ResolutionAction {
  id: string;
  label: string;
  description?: string;
  type: "primary" | "secondary" | "danger";
  icon?: string;
  requires_confirmation?: boolean;
}

export interface ResolutionPayload {
  summary: string;
  diagnosis?: string;
  severity?: "low" | "medium" | "high" | "urgent";
  actions: ResolutionAction[];
  estimated_time?: string;
  estimated_cost?: string;
}

/**
 * Escalation Form
 */
export interface EscalationPayload {
  reason?: string;
  context?: Record<string, unknown>;
  message_placeholder?: string;
}

// ============================================================================
// EVENT PAYLOADS (Frontend → Backend)
// ============================================================================

/**
 * Intent payload structures
 */
export interface UserMessageIntent {
  intent: "user_message";
  payload: {
    text: string;
    metadata?: Record<string, unknown>;
  };
}

export interface ItemSelectedIntent {
  intent: "item_selected";
  payload: {
    item_id: string;
    item_data?: GalleryItem;
  };
}

export interface ReasonSelectedIntent {
  intent: "reason_selected";
  payload: {
    reason_id: string;
    reason_label?: string;
  };
}

export interface ResolutionActionIntent {
  intent: "resolution_action";
  payload: {
    action_id: string;
    confirmation?: boolean;
    metadata?: Record<string, unknown>;
  };
}

export interface EscalateHumanIntent {
  intent: "escalate_human";
  payload: {
    message: string;
    context?: Record<string, unknown>;
  };
}

export interface SessionInitIntent {
  intent: "session_init";
  payload: {
    persona: Persona;
    mode: "guided";
  };
}

/**
 * Union type for all intents
 */
export type AIIntent =
  | UserMessageIntent
  | ItemSelectedIntent
  | ReasonSelectedIntent
  | ResolutionActionIntent
  | EscalateHumanIntent
  | SessionInitIntent;

// ============================================================================
// STATE EVENTS (Backend → Frontend)
// ============================================================================

/**
 * UI State event structure
 */
export interface AIStateEvent {
  type: "ai_state";
  ui_mode: UIMode;
  payload:
    | CTAPanelPayload
    | GalleryPayload
    | ReasonSelectorPayload
    | DiagnosisPayload
    | ResolutionPayload
    | EscalationPayload
    | Record<string, unknown>;
  metadata?: {
    session_id?: string;
    incident_id?: string;
    timestamp?: string;
  };
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
  current_mode: UIMode;
  selected_item: GalleryItem | null;
  selected_reason: ReasonOption | null;
  resolution_data: ResolutionPayload | null;
  chat_channel_id: string | null;
}

// ============================================================================
// API TYPES
// ============================================================================

/**
 * API Request/Response types
 */
export interface InitSessionRequest {
  user_id: string;
  persona: Persona;
  mode: "guided";
}

export interface InitSessionResponse {
  success: boolean;
  session_id: string;
  channel_id: string;
  initial_state?: AIStateEvent;
  error?: string;
}

export interface SendIntentRequest {
  channel_id: string;
  session_id: string;
  intent: AIIntent;
}

export interface SendIntentResponse {
  success: boolean;
  acknowledged: boolean;
  error?: string;
}

// ============================================================================
// STREAM CHAT CUSTOM EVENTS
// ============================================================================

/**
 * Custom Stream Chat event types
 */
export interface StreamAIStateEvent {
  type: "ai_state";
  ui_mode: UIMode;
  payload: Record<string, unknown>;
  user_id?: string;
  created_at?: string;
}

export interface StreamAIIntentEvent {
  type: "ai_intent";
  intent: IntentType;
  payload: Record<string, unknown>;
  user_id?: string;
  created_at?: string;
}

// ============================================================================
// COMPONENT PROPS
// ============================================================================

/**
 * Props for dynamic panel components
 */
export interface DynamicPanelProps {
  uiMode: UIMode;
  payload: Record<string, unknown>;
  onAction: (intent: IntentType, payload: Record<string, unknown>) => Promise<void>;
}

export interface ActionPanelProps {
  options: CTAOption[];
  title?: string;
  subtitle?: string;
  onSelect: (optionId: string) => void;
}

export interface ItemPickerProps {
  items: GalleryItem[];
  title?: string;
  subtitle?: string;
  allowSkip?: boolean;
  onSelect: (itemId: string, itemData?: GalleryItem) => void;
  onSkip?: () => void;
}

export interface ReasonPickerProps {
  reasons: ReasonOption[];
  title?: string;
  subtitle?: string;
  selectedItem?: GalleryItem;
  onSelect: (reasonId: string, reason?: ReasonOption) => void;
}

export interface ResolutionPanelProps {
  data: ResolutionPayload;
  onAction: (actionId: string, metadata?: Record<string, unknown>) => void;
}

// ============================================================================
// HOOK RETURN TYPES
// ============================================================================

/**
 * Return type for useAISupportFlow hook
 */
export interface AISupportFlowHook {
  // Stream Chat
  channel: any | null; // Channel from stream-chat

  // State
  uiMode: UIMode;
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
// VALIDATION SCHEMAS
// ============================================================================

/**
 * Type guards for runtime validation
 */
export const isValidUIMode = (mode: unknown): mode is UIMode => {
  return typeof mode === "string" && [
    "idle", "cta_panel", "gallery", "selector",
    "diagnosis", "resolution", "escalation", "complete"
  ].includes(mode);
};

export const isValidIntentType = (type: unknown): type is IntentType => {
  return typeof type === "string" && [
    "user_message", "item_selected", "reason_selected",
    "resolution_action", "escalate_human", "session_init"
  ].includes(type);
};

export const isValidPersona = (persona: unknown): persona is Persona => {
  return typeof persona === "string" &&
    ["tenant", "landlord", "contractor"].includes(persona);
};
