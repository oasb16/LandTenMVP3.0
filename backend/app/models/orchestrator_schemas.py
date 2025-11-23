"""
Pydantic v2 schemas for the LLM Orchestrator system.
"""
from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime


# ==================== META-CONTEXT SCHEMAS ====================

class DiscoveryState(BaseModel):
    """Discovery question flow state"""
    question_index: int = 0
    questions: List[str] = Field(default_factory=list)
    answers: Dict[str, str] = Field(default_factory=dict)


class ConversationMessage(BaseModel):
    """Single message in conversation history"""
    role: Literal["user", "assistant"]
    text: str
    timestamp: str


class MetaContext(BaseModel):
    """Complete conversation meta-context for HYBRID MODE"""
    user_id: str
    channel_id: str
    persona: Literal["tenant", "landlord", "contractor"]
    stage: Literal["idle", "detected", "discovery", "diagnosing", "work_order", "scheduling", "approval", "completed"] = "idle"
    active_incident_id: Optional[str] = None
    active_job_id: Optional[str] = None
    discovery: DiscoveryState = Field(default_factory=DiscoveryState)
    last_intent: Optional[str] = None
    last_user_message: Optional[str] = None
    conversation_history: List[ConversationMessage] = Field(default_factory=list)
    entities: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        extra = "allow"


# ==================== ORCHESTRATOR OUTPUT SCHEMAS ====================

class FunctionCall(BaseModel):
    """Function call specification"""
    name: Optional[str] = None
    arguments: Dict[str, Any] = Field(default_factory=dict)


class ContextUpdates(BaseModel):
    """Updates to apply to meta-context"""
    stage: Optional[str] = None
    active_incident_id: Optional[str] = None
    active_job_id: Optional[str] = None
    discovery: Optional[DiscoveryState] = None
    last_intent: Optional[str] = None
    entities: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    next_action: Optional[str] = None

    class Config:
        extra = "allow"


class OrchestratorOutput(BaseModel):
    """Complete LLM orchestrator output"""
    intent: str
    reasoning: str
    context_updates: ContextUpdates = Field(default_factory=ContextUpdates)
    function_call: FunctionCall = Field(default_factory=FunctionCall)
    response_to_user: Optional[str] = None


# ==================== FUNCTION PARAMETER SCHEMAS ====================

class CreateIncidentParams(BaseModel):
    """Parameters for create_incident function"""
    title: str
    description: str
    category: Literal["plumbing", "electrical", "hvac", "appliance", "structural", "other"]
    severity: Literal["low", "medium", "high", "emergency"]
    urgency: Literal["routine", "urgent", "immediate"]
    user_id: Optional[str] = None
    channel_id: Optional[str] = None
    property_id: Optional[str] = None


class UpdateIncidentParams(BaseModel):
    """Parameters for update_incident function"""
    incident_id: str
    status: Optional[Literal["detected", "discovery", "diagnosing", "work_order", "scheduling", "approval", "in_progress", "completed"]] = None
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    severity: Optional[str] = None
    urgency: Optional[str] = None


class GetIncidentParams(BaseModel):
    """Parameters for get_incident function"""
    incident_id: str


class CloseIncidentParams(BaseModel):
    """Parameters for close_incident function"""
    incident_id: str
    resolution_notes: Optional[str] = None


class StartDiscoveryParams(BaseModel):
    """Parameters for start_discovery function"""
    incident_id: str
    questions: Optional[List[str]] = None


class RecordDiscoveryAnswerParams(BaseModel):
    """Parameters for record_discovery_answer function"""
    incident_id: str
    question_index: int
    answer: str


class CompleteDiscoveryParams(BaseModel):
    """Parameters for complete_discovery function"""
    incident_id: str


class GetDiscoveryStatusParams(BaseModel):
    """Parameters for get_discovery_status function"""
    incident_id: str


class CreateWorkOrderParams(BaseModel):
    """Parameters for create_work_order function"""
    incident_id: str
    title: str
    estimated_cost: str
    urgency: Optional[str] = None


class UpdateWorkOrderParams(BaseModel):
    """Parameters for update_work_order function"""
    job_id: str
    status: Optional[Literal["created", "approved", "scheduled", "in_progress", "completed"]] = None
    scheduled_date: Optional[str] = None
    completion_date: Optional[str] = None
    final_cost: Optional[str] = None


class GetWorkOrderParams(BaseModel):
    """Parameters for get_work_order function"""
    job_id: str


class AssignContractorParams(BaseModel):
    """Parameters for assign_contractor function"""
    job_id: str
    contractor_id: str
    contractor_name: Optional[str] = None


class GenerateBidsParams(BaseModel):
    """Parameters for generate_bids function"""
    job_id: str
    category: str


class GetBidsParams(BaseModel):
    """Parameters for get_bids function"""
    job_id: str


class AcceptBidParams(BaseModel):
    """Parameters for accept_bid function"""
    bid_id: str
    job_id: str


class RequestLandlordApprovalParams(BaseModel):
    """Parameters for request_landlord_approval function"""
    job_id: str
    incident_id: str


class ProcessApprovalDecisionParams(BaseModel):
    """Parameters for process_approval_decision function"""
    job_id: str
    decision: Literal["approved", "rejected"]
    reason: Optional[str] = None


class UpdateContextParams(BaseModel):
    """Parameters for update_context function"""
    updates: Dict[str, Any]


class GetUserIncidentsParams(BaseModel):
    """Parameters for get_user_incidents function"""
    user_id: str
    limit: Optional[int] = 10


class GetUserJobsParams(BaseModel):
    """Parameters for get_user_jobs function"""
    user_id: str
    limit: Optional[int] = 10


class GetPropertyInfoParams(BaseModel):
    """Parameters for get_property_info function"""
    property_id: str


# ==================== FUNCTION DEFINITION SCHEMA ====================

class FunctionParameter(BaseModel):
    """JSON Schema for a function parameter"""
    type: str
    description: str
    enum: Optional[List[str]] = None
    items: Optional[Dict[str, Any]] = None
    properties: Optional[Dict[str, Any]] = None
    required: Optional[List[str]] = None


class FunctionDefinition(BaseModel):
    """Complete function definition for LLM tool calling"""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema
    parameter_model: Optional[str] = None  # Pydantic model name


# ==================== FUNCTION RESULT SCHEMAS ====================

class FunctionResult(BaseModel):
    """Result of function execution"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    message: Optional[str] = None


class IncidentResult(BaseModel):
    """Result of incident creation/update"""
    incident_id: str
    status: str
    title: str
    category: str
    severity: str
    urgency: str
    created_at: Optional[str] = None


class JobResult(BaseModel):
    """Result of job creation/update"""
    job_id: str
    incident_id: str
    status: str
    title: str
    estimated_cost: Optional[str] = None
    created_at: Optional[str] = None


class BidResult(BaseModel):
    """Contractor bid information"""
    bid_id: str
    job_id: str
    contractor_id: str
    contractor_name: str
    quote: str
    eta: str
    rating: Optional[str] = None
    status: str


# ==================== LLM REQUEST/RESPONSE SCHEMAS ====================

class LLMMessage(BaseModel):
    """Message for LLM API"""
    role: Literal["system", "user", "assistant", "function"]
    content: str
    name: Optional[str] = None


class LLMTool(BaseModel):
    """Tool definition for LLM API"""
    type: Literal["function"] = "function"
    function: FunctionDefinition


class OrchestratorRequest(BaseModel):
    """Complete request to orchestrator"""
    user_message: str
    meta_context: MetaContext
    available_functions: List[FunctionDefinition]
    function_result: Optional[FunctionResult] = None  # For multi-turn calls
