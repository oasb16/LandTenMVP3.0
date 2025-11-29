"""
AI Support Orchestrator - Amazon-Style Guided Flow

State Machine: intro → item_select → issue_select → diagnosis → resolution
UI Modes: cta_panel, gallery, selector, chat, resolution, fallback

Event Protocol:
- Frontend sends: ai_intent (user actions)
- Backend sends: ai_state (UI updates)
"""
import logging
from typing import Dict, Any, Optional, List
from ..services.stream_bot import get_bot
from ..services.dynamo_service import IncidentDB, JobDB, PropertyDB

logger = logging.getLogger(__name__)


class AISupportOrchestrator:
    """
    Orchestrates Amazon-style guided support flow.
    Routes user intents through state machine and generates UI responses.
    """

    def __init__(self):
        self.bot = get_bot()

    async def handle_intent(
        self,
        intent: str,
        payload: Dict[str, Any],
        channel_id: str,
        user_id: str,
        persona: str
    ) -> Dict[str, Any]:
        """
        Main intent router - handles all ai_intent events from frontend.

        Args:
            intent: IntentType from frontend
            payload: Intent-specific data
            channel_id: Stream channel ID
            user_id: User ID
            persona: User persona (tenant, landlord, etc.)

        Returns:
            Dict with stage, ui_mode, and payload for ai_state event
        """
        logger.info(f"[AI Support] Handling intent: {intent}, persona: {persona}")

        # Route to appropriate handler
        if intent == "ai_init":
            return await self._handle_init(payload, channel_id, user_id, persona)
        elif intent == "select_cta":
            return await self._handle_cta_selection(payload, channel_id, user_id, persona)
        elif intent == "item_selected":
            return await self._handle_item_selection(payload, channel_id, user_id, persona)
        elif intent == "reason_selected":
            return await self._handle_reason_selection(payload, channel_id, user_id, persona)
        elif intent == "diagnosis_answer":
            return await self._handle_diagnosis_answer(payload, channel_id, user_id, persona)
        elif intent == "resolution_action":
            return await self._handle_resolution_action(payload, channel_id, user_id, persona)
        else:
            logger.warning(f"Unknown intent: {intent}")
            return self._fallback_state(f"Unknown intent: {intent}")

    async def _handle_init(
        self,
        payload: Dict[str, Any],
        channel_id: str,
        user_id: str,
        persona: str
    ) -> Dict[str, Any]:
        """
        Initialize session - show CTA panel with persona-specific options.
        Stage: intro → UI Mode: cta_panel
        """
        logger.info(f"[AI Support] Initializing session for persona: {persona}")

        # Persona-specific CTA options
        cta_options = self._get_cta_options(persona)

        return {
            "stage": "intro",
            "ui_mode": "cta_panel",
            "persona": persona,
            "payload": {
                "options": cta_options
            }
        }

    async def _handle_cta_selection(
        self,
        payload: Dict[str, Any],
        channel_id: str,
        user_id: str,
        persona: str
    ) -> Dict[str, Any]:
        """
        Handle CTA selection - move to item selection.
        Stage: intro → item_select, UI Mode: cta_panel → gallery
        """
        cta_id = payload.get("cta_id")
        logger.info(f"[AI Support] CTA selected: {cta_id}")

        # Get items based on persona and CTA selection
        items = await self._get_items(persona, cta_id, user_id)

        return {
            "stage": "item_select",
            "ui_mode": "gallery",
            "persona": persona,
            "payload": {
                "items": items
            }
        }

    async def _handle_item_selection(
        self,
        payload: Dict[str, Any],
        channel_id: str,
        user_id: str,
        persona: str
    ) -> Dict[str, Any]:
        """
        Handle item selection - show issue reasons.
        Stage: item_select → issue_select, UI Mode: gallery → selector
        """
        item_id = payload.get("item_id")
        logger.info(f"[AI Support] Item selected: {item_id}")

        # Get reasons based on persona and item
        reasons = self._get_issue_reasons(persona, item_id)

        return {
            "stage": "issue_select",
            "ui_mode": "selector",
            "persona": persona,
            "payload": {
                "reasons": reasons,
                "itemId": item_id
            }
        }

    async def _handle_reason_selection(
        self,
        payload: Dict[str, Any],
        channel_id: str,
        user_id: str,
        persona: str
    ) -> Dict[str, Any]:
        """
        Handle reason selection - start diagnosis chat.
        Stage: issue_select → diagnosis, UI Mode: selector → chat
        """
        reason = payload.get("reason")
        logger.info(f"[AI Support] Reason selected: {reason}")

        # Send initial diagnosis message
        bot_id = self.bot.get_bot_id(persona)
        self.bot.send_message(
            channel_id=channel_id,
            bot_id=bot_id,
            text=f"I understand you're having an issue with: {reason}. Let me ask you a few questions to help diagnose the problem.",
            internal_type="ai-message"
        )

        return {
            "stage": "diagnosis",
            "ui_mode": "chat",
            "persona": persona,
            "payload": {
                "agent_prompt": "Please describe the issue in more detail.",
                "reason": reason
            }
        }

    async def _handle_diagnosis_answer(
        self,
        payload: Dict[str, Any],
        channel_id: str,
        user_id: str,
        persona: str
    ) -> Dict[str, Any]:
        """
        Handle diagnosis chat answer - continue chat or move to resolution.
        Stage: diagnosis (stay), UI Mode: chat
        """
        answer = payload.get("answer")
        logger.info(f"[AI Support] Diagnosis answer: {answer}")

        # For now, after a few exchanges, move to resolution
        # In production, this would use LLM to determine when diagnosis is complete

        # Simplified logic: after any answer, show resolution
        return await self._transition_to_resolution(channel_id, user_id, persona)

    async def _handle_resolution_action(
        self,
        payload: Dict[str, Any],
        channel_id: str,
        user_id: str,
        persona: str
    ) -> Dict[str, Any]:
        """
        Handle resolution action - complete flow.
        Stage: resolution → complete
        """
        action_id = payload.get("action_id")
        logger.info(f"[AI Support] Resolution action: {action_id}")

        # Send completion message
        bot_id = self.bot.get_bot_id(persona)
        self.bot.send_message(
            channel_id=channel_id,
            bot_id=bot_id,
            text="✅ Your request has been processed. Is there anything else I can help you with?",
            internal_type="ai-message"
        )

        # Return to intro stage
        cta_options = self._get_cta_options(persona)
        return {
            "stage": "intro",
            "ui_mode": "cta_panel",
            "persona": persona,
            "payload": {
                "options": cta_options
            }
        }

    async def _transition_to_resolution(
        self,
        channel_id: str,
        user_id: str,
        persona: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Transition to resolution stage with persona-specific action options.
        Provides contextually relevant actions based on user role.
        """
        # Persona-specific summaries and actions
        if persona == "tenant":
            summary = "Based on your description, I can help you create a maintenance request for your landlord to review."
            actions = [
                {"id": "create_incident", "label": "📋 Submit Maintenance Request"},
                {"id": "try_diy", "label": "🔧 View DIY Troubleshooting Tips"},
                {"id": "contact_emergency", "label": "🚨 Report Emergency (24/7)"},
                {"id": "done", "label": "✅ Issue Resolved"}
            ]

        elif persona == "landlord":
            summary = "I can help you take action on this incident or find a contractor."
            actions = [
                {"id": "approve_work", "label": "✅ Approve Work Order"},
                {"id": "find_contractor", "label": "👷 Find Contractor"},
                {"id": "request_more_info", "label": "📸 Request More Details"},
                {"id": "close_incident", "label": "✓ Mark as Resolved"}
            ]

        elif persona == "contractor":
            summary = "You can bid on this job or update your availability."
            actions = [
                {"id": "submit_bid", "label": "💼 Submit Bid"},
                {"id": "view_details", "label": "📋 View Full Job Details"},
                {"id": "decline", "label": "❌ Not Interested"}
            ]

        elif persona == "property_manager":
            summary = "Here are your options for managing this request."
            actions = [
                {"id": "assign_contractor", "label": "👷 Assign to Contractor"},
                {"id": "escalate", "label": "🚨 Escalate to Landlord"},
                {"id": "schedule_inspection", "label": "📅 Schedule Inspection"},
                {"id": "resolve", "label": "✅ Mark as Resolved"}
            ]

        else:
            # Default fallback
            summary = "Based on our conversation, here are the recommended next steps."
            actions = [
                {"id": "create_ticket", "label": "Create Support Ticket"},
                {"id": "contact_support", "label": "Contact Human Support"},
                {"id": "done", "label": "I'm All Set"}
            ]

        return {
            "stage": "resolution",
            "ui_mode": "resolution",
            "persona": persona,
            "payload": {
                "summary": summary,
                "actions": actions
            }
        }

    def _get_cta_options(self, persona: str) -> List[Dict[str, str]]:
        """Get CTA panel options based on persona."""
        persona_options = {
            "tenant": [
                {
                    "id": "maintenance",
                    "label": "Report Maintenance Issue",
                    "description": "Water leaks, broken appliances, etc.",
                    "icon": "🔧"
                },
                {
                    "id": "billing",
                    "label": "Billing Question",
                    "description": "Rent payments, deposits, fees",
                    "icon": "💰"
                },
                {
                    "id": "amenities",
                    "label": "Amenities & Services",
                    "description": "Pool, gym, parking, mail",
                    "icon": "🏊"
                }
            ],
            "landlord": [
                {
                    "id": "incidents",
                    "label": "Review Incidents",
                    "description": "Active maintenance requests",
                    "icon": "📋"
                },
                {
                    "id": "contractors",
                    "label": "Manage Contractors",
                    "description": "Find and hire contractors",
                    "icon": "👷"
                },
                {
                    "id": "properties",
                    "label": "Property Overview",
                    "description": "Units, finances, reports",
                    "icon": "🏢"
                }
            ],
            "property_manager": [
                {
                    "id": "operations",
                    "label": "Daily Operations",
                    "description": "Tasks, inspections, tours",
                    "icon": "📅"
                },
                {
                    "id": "incidents",
                    "label": "Manage Incidents",
                    "description": "Triage and assign work",
                    "icon": "🚨"
                },
                {
                    "id": "tenants",
                    "label": "Tenant Services",
                    "description": "Inquiries and requests",
                    "icon": "👥"
                }
            ],
            "contractor": [
                {
                    "id": "jobs",
                    "label": "Available Jobs",
                    "description": "Browse and bid on work",
                    "icon": "💼"
                },
                {
                    "id": "my_jobs",
                    "label": "My Active Jobs",
                    "description": "Scheduled and in-progress",
                    "icon": "🛠️"
                },
                {
                    "id": "payments",
                    "label": "Payments & Invoices",
                    "description": "Track earnings",
                    "icon": "💵"
                }
            ]
        }

        return persona_options.get(persona, persona_options["tenant"])

    async def _get_items(
        self,
        persona: str,
        cta_id: str,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get items for gallery based on persona and CTA selection.
        Fetches real data from DynamoDB when available, falls back to defaults.
        """
        try:
            # TENANT: Maintenance issues - show recent incidents
            if persona == "tenant" and cta_id == "maintenance":
                try:
                    incidents = IncidentDB.list_incidents_by_tenant(user_id)
                    if incidents and len(incidents) > 0:
                        # Show recent incidents for context
                        return [
                            {
                                "id": inc.get("incident_id"),
                                "title": inc.get("title", "Untitled Issue"),
                                "subtitle": f"Status: {inc.get('status', 'unknown')} • {inc.get('category', 'general')}",
                            }
                            for inc in incidents[:5]  # Limit to 5 most recent
                        ]
                except Exception as e:
                    logger.error(f"Error fetching tenant incidents: {e}")

                # Fallback: Common appliances/areas
                return [
                    {
                        "id": "new_issue",
                        "title": "Report New Issue",
                        "subtitle": "Start a new maintenance request",
                    },
                    {
                        "id": "kitchen",
                        "title": "Kitchen Appliances",
                        "subtitle": "Sink, dishwasher, refrigerator",
                    },
                    {
                        "id": "bathroom",
                        "title": "Bathroom",
                        "subtitle": "Toilet, shower, plumbing",
                    },
                    {
                        "id": "hvac",
                        "title": "HVAC System",
                        "subtitle": "Heating and cooling",
                    }
                ]

            # LANDLORD: Review incidents
            elif persona == "landlord" and cta_id == "incidents":
                try:
                    # Fetch all tenant incidents for properties owned by landlord
                    # Note: In production, filter by property_id linked to landlord
                    incidents = IncidentDB.list_incidents_by_tenant(user_id)
                    if incidents and len(incidents) > 0:
                        return [
                            {
                                "id": inc.get("incident_id"),
                                "title": f"{inc.get('category', 'Issue').title()} - {inc.get('property_id', 'Unknown')}",
                                "subtitle": f"{inc.get('severity', 'medium')} • {inc.get('status', 'pending')}",
                            }
                            for inc in incidents[:10]
                        ]
                except Exception as e:
                    logger.error(f"Error fetching landlord incidents: {e}")

                # Fallback
                return [
                    {
                        "id": "no_incidents",
                        "title": "No Active Incidents",
                        "subtitle": "All maintenance up to date",
                    }
                ]

            # CONTRACTOR: Available jobs
            elif persona == "contractor" and cta_id == "jobs":
                try:
                    # Fetch available jobs (status = "created" or "open")
                    # Note: Would need a query_jobs_by_status method
                    return [
                        {
                            "id": "browse_jobs",
                            "title": "Browse Available Jobs",
                            "subtitle": "See all open maintenance requests",
                        }
                    ]
                except Exception as e:
                    logger.error(f"Error fetching contractor jobs: {e}")

                return []

            # CONTRACTOR: My active jobs
            elif persona == "contractor" and cta_id == "my_jobs":
                # Fetch contractor's assigned jobs
                return [
                    {
                        "id": "active_jobs",
                        "title": "Your Active Jobs",
                        "subtitle": "View scheduled work",
                    }
                ]

            # Default: Empty list
            else:
                logger.warning(f"No items handler for persona={persona}, cta_id={cta_id}")
                return []

        except Exception as e:
            logger.error(f"Error in _get_items: {e}", exc_info=True)
            return []

    def _get_issue_reasons(self, persona: str, item_id: str) -> List[str]:
        """
        Get context-aware issue reason strings for selector.
        Returns different reasons based on the item selected.
        """
        # Item-specific issue reasons
        reason_map = {
            # Kitchen appliances
            "kitchen": [
                "Sink is clogged or draining slowly",
                "Faucet is leaking",
                "Dishwasher not working",
                "Garbage disposal issue",
                "Other kitchen issue"
            ],
            "kitchen_sink": [
                "Clogged or slow drainage",
                "Leaking faucet",
                "No hot water",
                "Broken handle or fixture",
                "Other sink issue"
            ],
            "dishwasher": [
                "Won't start or turn on",
                "Not draining properly",
                "Leaking water",
                "Not cleaning dishes properly",
                "Making loud noises"
            ],

            # Bathroom
            "bathroom": [
                "Toilet not flushing properly",
                "Shower or bathtub issue",
                "Sink leaking or clogged",
                "No hot water",
                "Other bathroom issue"
            ],

            # HVAC
            "hvac": [
                "No heating",
                "No cooling/AC not working",
                "Strange noises or smells",
                "Thermostat not responding",
                "Air quality concerns"
            ],

            # Default for existing incidents
            "incident": [
                "Need status update",
                "Issue is worse",
                "Issue is resolved",
                "Have additional information",
                "Want to speak to someone"
            ],

            # New issue
            "new_issue": [
                "Plumbing problem",
                "Electrical issue",
                "Appliance not working",
                "Structural damage",
                "Other maintenance need"
            ]
        }

        # Check if item_id matches any of our mappings
        for key in reason_map:
            if key in item_id.lower():
                return reason_map[key]

        # Default generic reasons
        return [
            "Not working properly",
            "Making unusual noises or smells",
            "Leaking or damaged",
            "Safety concern",
            "Other issue"
        ]

    def _fallback_state(self, error: str) -> Dict[str, Any]:
        """Return fallback error state."""
        return {
            "stage": "intro",
            "ui_mode": "fallback",
            "payload": {
                "error": error
            }
        }


# Singleton instance
_orchestrator_instance: Optional[AISupportOrchestrator] = None


def get_ai_support_orchestrator() -> AISupportOrchestrator:
    """Get or create AI Support orchestrator instance."""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = AISupportOrchestrator()
    return _orchestrator_instance
