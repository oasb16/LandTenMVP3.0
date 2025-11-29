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
 */
export type Stage =
  | "intro"         // Determine persona, show welcome + options
  | "item_select"   // Show items (appliances, incidents, jobs, etc.)
  | "issue_select"  // Choose what's wrong with the item
  | "diagnosis"     // Multi-turn troubleshooting
  | "resolution";   // Final actions

/**
 * UI Modes - determines which panel is displayed
 * These are the ONLY valid UI modes (Amazon spec)
 */
export type UIMode =
  | "cta_panel"    // Large button menu (What do you need help with?)
  | "gallery"      // Scrollable list of items (orders, maintenance, etc.)
  | "selector"     // List of issue reasons
  | "chat"         // Pure conversational messages (diagnosis)
  | "resolution"   // Final actions user can take
  | "fallback";    // Chat unavailable

/**
 * Intent types - user/system actions (Amazon spec)
 */
export type IntentType =
  // User-initiated intents
  | "user_message"       // Plain chat text
  | "select_cta"         // Selected main option from CTA panel
  | "item_selected"      // Selected item from gallery
  | "reason_selected"    // Selected reason from selector
  | "diagnosis_answer"   // Answer during diagnosis
  | "resolution_action"  // Final action chosen

  // System-initiated intents
  | "ai_init"            // Initialize session
  | "ai_continue"        // Continue flow
  | "ai_escalate"        // Escalate to human
  | "ai_close_session";  // Close session

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
    "cta_panel", "gallery", "selector", "chat", "resolution", "fallback"
  ].includes(mode);
};

export const isValidStage = (stage: unknown): stage is Stage => {
  return typeof stage === "string" && [
    "intro", "item_select", "issue_select", "diagnosis", "resolution"
  ].includes(stage);
};

export const isValidIntentType = (type: unknown): type is IntentType => {
  return typeof type === "string" && [
    "user_message", "select_cta", "item_selected", "reason_selected",
    "diagnosis_answer", "resolution_action", "ai_init", "ai_continue",
    "ai_escalate", "ai_close_session"
  ].includes(type);
};

export const isValidPersona = (persona: unknown): persona is Persona => {
  return typeof persona === "string" &&
    ["tenant", "landlord", "property_manager", "contractor"].includes(persona);
};
