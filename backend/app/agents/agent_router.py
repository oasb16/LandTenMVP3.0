"""
Agent Router - Routes requests to appropriate specialized agents.
Determines which agent should handle each message based on context and intent.
"""
import logging
from typing import Dict, Any, Optional
from enum import Enum

from .tenant_agent import TenantAgent
from .diagnosis_agent import DiagnosisAgent
from .contractor_agent import ContractorAgent

logger = logging.getLogger(__name__)


class AgentType(Enum):
    """Available agent types"""
    TENANT = "tenant"
    DIAGNOSIS = "diagnosis"
    CONTRACTOR = "contractor"


class AgentRouter:
    """
    Routes messages to appropriate specialized agents.

    Routing logic:
    - General conversation → TenantAgent
    - Discovery complete, need diagnosis → DiagnosisAgent
    - Diagnosis complete, need work order → ContractorAgent
    - Status updates, follow-ups → TenantAgent
    """

    def __init__(self):
        self.agents = {
            AgentType.TENANT: TenantAgent(),
            AgentType.DIAGNOSIS: DiagnosisAgent(),
            AgentType.CONTRACTOR: ContractorAgent(),
        }

    async def route(
        self,
        message: str,
        context: Dict[str, Any],
        agent_type: Optional[AgentType] = None,
    ) -> Dict[str, Any]:
        """
        Route message to appropriate agent.

        Args:
            message: User message
            context: Context dict (stage, incident_id, etc.)
            agent_type: Optional explicit agent selection

        Returns:
            Agent response dict
        """
        # If agent explicitly specified, use it
        if agent_type:
            logger.info(f"📍 Explicit routing to: {agent_type.value}")
            agent = self.agents[agent_type]
            return await agent.process(message, context)

        # Auto-route based on context
        selected_agent_type = self._select_agent(context)
        logger.info(f"🔀 Auto-routing to: {selected_agent_type.value}")

        agent = self.agents[selected_agent_type]
        return await agent.process(message, context)

    def _select_agent(self, context: Dict[str, Any]) -> AgentType:
        """
        Select appropriate agent based on context.

        Routing rules:
        1. discovery_complete stage → DiagnosisAgent
        2. diagnosing stage + need work order → ContractorAgent
        3. work_order stage → ContractorAgent
        4. All other cases → TenantAgent (default)
        """
        stage = context.get("stage", "idle")

        # Discovery complete → Diagnosis needed
        if stage == "discovery_complete":
            return AgentType.DIAGNOSIS

        # Diagnosing stage complete → Work order needed
        if stage == "diagnosing":
            # Check if diagnosis is complete
            diagnosis_complete = context.get("metadata", {}).get("diagnosis_complete", False)
            if diagnosis_complete:
                return AgentType.CONTRACTOR
            else:
                return AgentType.DIAGNOSIS

        # Work order stage → Contractor coordination
        if stage in ["work_order", "scheduling", "approval"]:
            return AgentType.CONTRACTOR

        # Default → Tenant agent for conversation
        return AgentType.TENANT

    async def process_with_tenant_agent(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Shortcut to process with TenantAgent"""
        return await self.agents[AgentType.TENANT].process(message, context)

    async def process_with_diagnosis_agent(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Shortcut to process with DiagnosisAgent"""
        return await self.agents[AgentType.DIAGNOSIS].process(message, context)

    async def process_with_contractor_agent(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Shortcut to process with ContractorAgent"""
        return await self.agents[AgentType.CONTRACTOR].process(message, context)


# Singleton instance
_agent_router = None


def get_agent_router() -> AgentRouter:
    """Get singleton instance of AgentRouter"""
    global _agent_router
    if _agent_router is None:
        _agent_router = AgentRouter()
    return _agent_router
