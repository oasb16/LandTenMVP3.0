"""
Flow Engine V2 - Graph-Based Declarative Flow Orchestrator

This is the next-generation flow engine that uses JSON-based flow configurations
to create adaptive, intelligent conversation flows.

Features:
- JSON-based flow definitions
- Graph-based state transitions
- Flow recovery and replay
- Async follow-through
- Persona-aware routing
- Condition-based branching
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum

from ..services.policy_validator import validate_action, PolicyValidationResult

logger = logging.getLogger(__name__)


class NodeType(str, Enum):
    """Types of flow nodes."""
    START = "start"
    DECISION = "decision"
    INFORMATION = "information"
    INFORMATION_GATHERING = "information_gathering"
    ACTION = "action"
    WAITING = "waiting"
    TRACKING = "tracking"
    TERMINAL = "terminal"


class FlowEngine:
    """
    Graph-based flow orchestrator that reads declarative flow configurations
    and executes them intelligently.
    """

    def __init__(self):
        """Initialize the flow engine with all available flows."""
        self.flows: Dict[str, Dict[str, Any]] = {}
        self.flow_dir = Path(__file__).parent.parent / "config" / "flows"
        self._load_flows()

    def _load_flows(self) -> None:
        """Load all flow configurations from the flows directory."""
        if not self.flow_dir.exists():
            logger.warning(f"[flow-engine-v2] Flow directory not found: {self.flow_dir}")
            self._load_default_flows()
            return

        for flow_file in self.flow_dir.glob("*.json"):
            try:
                with open(flow_file, 'r') as f:
                    flow_config = json.load(f)
                    flow_id = flow_config.get("flow_id")
                    if flow_id:
                        self.flows[flow_id] = flow_config
                        logger.info(f"[flow-engine-v2] Loaded flow: {flow_id} ({flow_config.get('name')})")
                    else:
                        logger.warning(f"[flow-engine-v2] Flow file {flow_file} missing flow_id")
            except Exception as e:
                logger.error(f"[flow-engine-v2] Failed to load flow {flow_file}: {e}")

        if not self.flows:
            logger.warning("[flow-engine-v2] No flows loaded, using defaults")
            self._load_default_flows()

    def _load_default_flows(self) -> None:
        """Load minimal default flows as fallback."""
        self.flows = {
            "maintenance": {
                "flow_id": "maintenance",
                "name": "Maintenance Flow",
                "nodes": {
                    "idle": {"type": "start", "next_nodes": ["incident.report"]},
                    "incident.report": {"type": "decision", "next_nodes": ["discovery.response"]},
                    "discovery.response": {"type": "information_gathering", "next_nodes": ["job.request"]},
                    "job.request": {"type": "action", "next_nodes": ["approval.decision"]},
                    "approval.decision": {"type": "decision", "next_nodes": ["completion.confirmation"]},
                    "completion.confirmation": {"type": "terminal", "next_nodes": ["idle"]},
                }
            }
        }

    def get_flow(self, flow_id: str) -> Optional[Dict[str, Any]]:
        """Get a flow configuration by ID."""
        return self.flows.get(flow_id)

    def get_node(self, flow_id: str, node_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific node from a flow."""
        flow = self.get_flow(flow_id)
        if not flow:
            return None
        return flow.get("nodes", {}).get(node_id)

    def determine_next_node(
        self,
        flow_id: str,
        current_node_id: str,
        context: Dict[str, Any],
        intent: str,
        message: str,
        persona: str
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Determine the next node in the flow based on current state and conditions.

        Returns:
            Tuple of (next_node_id, metadata)
        """
        current_node = self.get_node(flow_id, current_node_id)
        if not current_node:
            logger.warning(f"[flow-engine-v2] Node not found: {flow_id}.{current_node_id}")
            return "idle", {"reason": "node_not_found"}

        node_type = current_node.get("type")
        next_nodes = current_node.get("next_nodes", [])

        # If node has conditions, evaluate them
        conditions = current_node.get("conditions", {})
        if conditions:
            next_node_id = self._evaluate_conditions(conditions, context, message, intent)
            if next_node_id and next_node_id in next_nodes:
                return next_node_id, {"reason": "condition_matched", "condition": next_node_id}

        # Check for intent-based routing
        next_node_id = self._route_by_intent(intent, next_nodes, current_node)
        if next_node_id:
            return next_node_id, {"reason": "intent_routing", "intent": intent}

        # Default to first next node
        if next_nodes:
            return next_nodes[0], {"reason": "default_transition"}

        # No next node - stay in current node or go to idle
        return current_node_id if node_type != NodeType.TERMINAL.value else "idle", {"reason": "terminal_or_stay"}

    def _evaluate_conditions(
        self,
        conditions: Dict[str, str],
        context: Dict[str, Any],
        message: str,
        intent: str
    ) -> Optional[str]:
        """
        Evaluate flow conditions to determine next node.

        Conditions can check:
        - Message content keywords
        - Context values
        - Intent types
        - Entity presence
        """
        message_lower = message.lower()
        entities = context.get("entities", {})
        flow_state = context.get("flow_state", {})

        for condition_key, next_node in conditions.items():
            # Check for emergency
            if condition_key == "emergency":
                if any(word in message_lower for word in ["emergency", "urgent", "immediately", "asap"]):
                    return next_node
                if entities.get("severity") == "emergency" or entities.get("urgency") == "immediate":
                    return next_node

            # Check for photos/attachments
            elif condition_key == "has_photos":
                if context.get("has_attachments") or "photo" in message_lower or "picture" in message_lower:
                    return next_node

            # Check for DIY capability
            elif condition_key == "can_diy":
                severity = entities.get("severity", "medium")
                if severity in ["low", "routine"] and not any(word in message_lower for word in ["professional", "contractor"]):
                    return next_node

            # Check for approval requirement
            elif condition_key == "needs_approval":
                cost_estimate = entities.get("cost_estimate", 0)
                if cost_estimate > 500 or entities.get("severity") in ["high", "emergency"]:
                    return next_node

            # Check approval status
            elif condition_key == "approved":
                if "approve" in message_lower or context.get("approval_status") == "approved":
                    return next_node

            elif condition_key == "rejected":
                if "reject" in message_lower or "deny" in message_lower or context.get("approval_status") == "rejected":
                    return next_node

            # Default condition
            elif condition_key == "default":
                continue  # Skip default, handle it last

        # Return default if exists
        return conditions.get("default")

    def _route_by_intent(
        self,
        intent: str,
        available_nodes: List[str],
        current_node: Dict[str, Any]
    ) -> Optional[str]:
        """Route to next node based on detected intent."""
        # Map intents to node patterns
        intent_patterns = {
            "incident.report": ["incident.report", "discovery"],
            "discovery.response": ["discovery", "job.request"],
            "discovery.continue": ["discovery"],
            "job.request": ["job.request", "job"],
            "bids.request": ["bids"],
            "approval.decision": ["approval", "contractor.assigned", "job.rejected"],
            "completion": ["completion"],
            "help": ["help"],
            "greeting": ["greeting"],
            "feedback": ["feedback"],
        }

        patterns = intent_patterns.get(intent, [])
        for node_id in available_nodes:
            for pattern in patterns:
                if pattern in node_id:
                    return node_id

        return None

    def process_transition(
        self,
        flow_id: str,
        current_node_id: str,
        user_id: str,
        channel_id: str,
        persona: str,
        intent: str,
        message: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Process a flow transition with policy validation.

        Returns:
            Dictionary containing:
            {
                "next_node": str,
                "flow_id": str,
                "allowed": bool,
                "violation_message": str | None,
                "metadata": dict,
                "actions": list,
                "card_type": str | None,
                "persona_tone": str | None
            }
        """
        next_node_id, transition_metadata = self.determine_next_node(
            flow_id, current_node_id, context, intent, message, persona
        )

        next_node = self.get_node(flow_id, next_node_id)
        if not next_node:
            return {
                "next_node": "idle",
                "flow_id": flow_id,
                "allowed": True,
                "violation_message": None,
                "metadata": {"error": "node_not_found"},
                "actions": [],
                "card_type": None,
                "persona_tone": None
            }

        # Check policy permissions
        action_name = self._get_action_name(next_node_id)
        validation: PolicyValidationResult = validate_action(persona, action_name, context)

        # Get persona-specific actions and tone
        persona_actions = next_node.get("persona_actions", {}).get(persona, [])
        persona_tones = next_node.get("persona_tone", {})
        persona_tone = persona_tones.get(persona) if isinstance(persona_tones, dict) else None

        logger.info(
            "[flow-engine-v2] Transition: %s.%s → %s | allowed=%s | reason=%s",
            flow_id,
            current_node_id,
            next_node_id,
            validation.allowed,
            transition_metadata.get("reason")
        )

        return {
            "next_node": next_node_id,
            "flow_id": flow_id,
            "allowed": validation.allowed,
            "violation_message": validation.message,
            "metadata": transition_metadata,
            "actions": persona_actions,
            "card_type": next_node.get("card_template"),
            "persona_tone": persona_tone,
            "node_type": next_node.get("type"),
            "required_entities": next_node.get("required_entities", []),
        }

    def _get_action_name(self, node_id: str) -> str:
        """Extract action name from node ID for policy validation."""
        # Map node IDs to policy actions
        action_map = {
            "approval.decision": "approve_job",
            "job.request": "create_job",
            "job.emergency_dispatch": "create_job",
            "bids.request": "view_bids",
            "contractor.assigned": "assign_contractor",
        }
        return action_map.get(node_id, node_id)

    def recover_flow(
        self,
        flow_id: str,
        recent_intents: List[str],
        context: Dict[str, Any]
    ) -> str:
        """
        Recover flow state by replaying recent intents.

        Args:
            flow_id: The flow to recover
            recent_intents: Last 3-5 intents from conversation
            context: Current context

        Returns:
            Best guess at current node ID
        """
        if not recent_intents:
            return "idle"

        # Start from idle and replay
        current_node = "idle"
        for intent in recent_intents:
            flow = self.get_flow(flow_id)
            if not flow:
                break

            node = self.get_node(flow_id, current_node)
            if not node:
                break

            next_nodes = node.get("next_nodes", [])
            next_node = self._route_by_intent(intent, next_nodes, node)
            if next_node:
                current_node = next_node

        logger.info(f"[flow-engine-v2] Flow recovery: {flow_id} → {current_node}")
        return current_node

    def get_available_actions(
        self,
        flow_id: str,
        node_id: str,
        persona: str
    ) -> List[str]:
        """Get available actions for a persona at a specific node."""
        node = self.get_node(flow_id, node_id)
        if not node:
            return []

        persona_actions = node.get("persona_actions", {})
        return persona_actions.get(persona, [])

    def get_required_entities(self, flow_id: str, node_id: str) -> List[str]:
        """Get required entities for a node."""
        node = self.get_node(flow_id, node_id)
        if not node:
            return []
        return node.get("required_entities", [])

    def supports_proactive_prompting(self, flow_id: str) -> bool:
        """Check if a flow supports proactive prompting."""
        flow = self.get_flow(flow_id)
        if not flow:
            return False
        return flow.get("metadata", {}).get("supports_proactive_prompting", False)


# Singleton instance
_flow_engine_v2: Optional[FlowEngine] = None


def get_flow_engine() -> FlowEngine:
    """Get or create the singleton FlowEngine instance."""
    global _flow_engine_v2
    if _flow_engine_v2 is None:
        _flow_engine_v2 = FlowEngine()
    return _flow_engine_v2
