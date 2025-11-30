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
from datetime import datetime, timezone
from ..services.stream_bot import get_bot
from ..services.dynamo_service import IncidentDB, JobDB, PropertyDB
from ..services.ai_diagnosis_agent import get_diagnosis_agent
from ..services.ai_support_analytics import get_analytics_tracker

logger = logging.getLogger(__name__)


class SessionState:
    """
    Maintains state for an AI Support session.
    Tracks selected items, reasons, and context across flow stages.
    """
    def __init__(self, session_id: str, user_id: str, channel_id: str, persona: str):
        self.session_id = session_id
        self.user_id = user_id
        self.channel_id = channel_id
        self.persona = persona
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.updated_at = self.created_at

        # Flow tracking
        self.current_stage: str = "intro"
        self.current_mode: str = "cta_panel"

        # User selections
        self.selected_cta: Optional[str] = None
        self.selected_item_id: Optional[str] = None
        self.selected_item_title: Optional[str] = None
        self.selected_reason: Optional[str] = None

        # Diagnosis context
        self.diagnosis_messages: List[str] = []

        # Metadata
        self.metadata: Dict[str, Any] = {}

    def update_stage(self, stage: str, mode: str):
        """Update current stage and mode."""
        self.current_stage = stage
        self.current_mode = mode
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize state to dictionary."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "channel_id": self.channel_id,
            "persona": self.persona,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "current_stage": self.current_stage,
            "current_mode": self.current_mode,
            "selected_cta": self.selected_cta,
            "selected_item_id": self.selected_item_id,
            "selected_item_title": self.selected_item_title,
            "selected_reason": self.selected_reason,
            "diagnosis_messages": self.diagnosis_messages,
            "metadata": self.metadata
        }


class SessionStateManager:
    """
    In-memory session state manager.

    In production, this would be backed by DynamoDB or Redis for persistence.
    For now, uses in-memory dict keyed by channel_id.
    """
    def __init__(self):
        self._sessions: Dict[str, SessionState] = {}

    def get_or_create(self, channel_id: str, user_id: str, persona: str) -> SessionState:
        """Get existing session or create new one."""
        if channel_id not in self._sessions:
            session_id = f"sess-{channel_id}-{int(datetime.now().timestamp())}"
            self._sessions[channel_id] = SessionState(
                session_id=session_id,
                user_id=user_id,
                channel_id=channel_id,
                persona=persona
            )
            logger.info(f"Created new session: {session_id}")

        return self._sessions[channel_id]

    def get(self, channel_id: str) -> Optional[SessionState]:
        """Get session by channel ID."""
        return self._sessions.get(channel_id)

    def clear(self, channel_id: str):
        """Clear session state."""
        if channel_id in self._sessions:
            del self._sessions[channel_id]
            logger.info(f"Cleared session for channel: {channel_id}")


# Global session manager instance
_session_manager = SessionStateManager()


class AISupportOrchestrator:
    """
    Orchestrates Amazon-style guided support flow.
    Routes user intents through state machine and generates UI responses.
    """

    def __init__(self):
        self.bot = get_bot()
        self.session_manager = _session_manager
        self.diagnosis_agent = get_diagnosis_agent()
        self.analytics = get_analytics_tracker()

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
        elif intent == "confirm_summary":
            return await self._handle_confirm_summary(payload, channel_id, user_id, persona)
        elif intent == "edit_summary":
            return await self._handle_edit_summary(payload, channel_id, user_id, persona)
        elif intent == "diagnosis_answer":
            return await self._handle_diagnosis_answer(payload, channel_id, user_id, persona)
        elif intent == "ai_escalate":
            return await self._handle_escalation(payload, channel_id, user_id, persona)
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

        # Track session start
        self.analytics.track_event(
            event_type="session_start",
            channel_id=channel_id,
            user_id=user_id,
            persona=persona
        )

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

        # Track CTA selection and stage transition
        self.analytics.track_event(
            event_type="cta_selected",
            channel_id=channel_id,
            user_id=user_id,
            persona=persona,
            cta_id=cta_id
        )
        self.analytics.track_event(
            event_type="stage_transition",
            channel_id=channel_id,
            user_id=user_id,
            persona=persona,
            from_stage="intro",
            to_stage="item_select"
        )

        # Get or create session and update state
        session = self.session_manager.get_or_create(channel_id, user_id, persona)
        session.selected_cta = cta_id
        session.update_stage("item_select", "gallery")

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

        # Track item selection and stage transition
        self.analytics.track_event(
            event_type="item_selected",
            channel_id=channel_id,
            user_id=user_id,
            persona=persona,
            item_id=item_id
        )
        self.analytics.track_event(
            event_type="stage_transition",
            channel_id=channel_id,
            user_id=user_id,
            persona=persona,
            from_stage="item_select",
            to_stage="issue_select"
        )

        # Update session state
        session = self.session_manager.get_or_create(channel_id, user_id, persona)
        session.selected_item_id = item_id

        # Extract item title from payload if provided
        item_title = payload.get("item_title")
        if item_title:
            session.selected_item_title = item_title
        else:
            # Fallback: use item_id as title if not provided
            session.selected_item_title = item_id

        session.update_stage("issue_select", "selector")

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
        Handle reason selection - show summary confirmation.
        Stage: issue_select → summary, UI Mode: selector → summary
        """
        reason = payload.get("reason")
        logger.info(f"[AI Support] Reason selected: {reason}")

        # Track reason selection and transitions
        self.analytics.track_event(
            event_type="reason_selected",
            channel_id=channel_id,
            user_id=user_id,
            persona=persona,
            reason=reason
        )
        self.analytics.track_event(
            event_type="stage_transition",
            channel_id=channel_id,
            user_id=user_id,
            persona=persona,
            from_stage="issue_select",
            to_stage="summary"
        )

        # Update session state
        session = self.session_manager.get_or_create(channel_id, user_id, persona)
        session.selected_reason = reason
        session.update_stage("summary", "summary")

        # Build summary payload with all user selections
        summary_payload = {
            "selected_cta": session.selected_cta or "unknown",
            "selected_cta_label": self._get_cta_label(session.selected_cta, persona),
            "selected_item_id": session.selected_item_id or "unknown",
            "selected_item_title": session.selected_item_title or "Unknown Item",
            "selected_reason": reason,
            "severity": "medium",
            "urgency": "routine",
        }

        return {
            "stage": "summary",
            "ui_mode": "summary",
            "persona": persona,
            "payload": summary_payload
        }

    async def _handle_confirm_summary(
        self,
        payload: Dict[str, Any],
        channel_id: str,
        user_id: str,
        persona: str
    ) -> Dict[str, Any]:
        """
        Handle summary confirmation - transition to diagnosis.
        Stage: summary → diagnosis, UI Mode: summary → chat
        """
        logger.info(f"[AI Support] Summary confirmed for {channel_id}")

        # Track confirmation and transitions
        self.analytics.track_event(
            event_type="summary_confirmed",
            channel_id=channel_id,
            user_id=user_id,
            persona=persona
        )
        self.analytics.track_event(
            event_type="stage_transition",
            channel_id=channel_id,
            user_id=user_id,
            persona=persona,
            from_stage="summary",
            to_stage="diagnosis"
        )
        self.analytics.track_event(
            event_type="diagnosis_started",
            channel_id=channel_id,
            user_id=user_id,
            persona=persona
        )

        # Get session for context
        session = self.session_manager.get_or_create(channel_id, user_id, persona)
        session.update_stage("diagnosis", "chat")

        # Build session context for diagnosis agent
        session_context = {
            "selected_cta": session.selected_cta,
            "selected_item_id": session.selected_item_id,
            "selected_reason": session.selected_reason
        }

        # Start AI diagnosis conversation
        initial_message = self.diagnosis_agent.start_diagnosis(
            channel_id=channel_id,
            persona=persona,
            session_context=session_context
        )

        # Send initial diagnosis message from AI agent
        bot_id = self.bot.get_bot_id(persona)
        self.bot.send_message(
            channel_id=channel_id,
            bot_id=bot_id,
            text=initial_message,
            internal_type="ai-message"
        )

        # Follow up with first diagnostic question
        first_question = "When did this issue first start? Is it constant or intermittent?"
        self.bot.send_message(
            channel_id=channel_id,
            bot_id=bot_id,
            text=first_question,
            internal_type="ai-message"
        )

        return {
            "stage": "diagnosis",
            "ui_mode": "chat",
            "persona": persona,
            "payload": {
                "agent_prompt": first_question,
                "reason": session.selected_reason
            }
        }

    async def _handle_edit_summary(
        self,
        payload: Dict[str, Any],
        channel_id: str,
        user_id: str,
        persona: str
    ) -> Dict[str, Any]:
        """
        Handle edit summary - go back to issue selection.
        Stage: summary → issue_select, UI Mode: summary → selector
        """
        logger.info(f"[AI Support] User wants to edit summary for {channel_id}")

        # Track edit action
        self.analytics.track_event(
            event_type="summary_edited",
            channel_id=channel_id,
            user_id=user_id,
            persona=persona
        )

        # Get session
        session = self.session_manager.get_or_create(channel_id, user_id, persona)

        # Go back to issue selection
        session.update_stage("issue_select", "selector")

        # Get reasons again
        reasons = self._get_issue_reasons(persona, session.selected_item_id or "")

        return {
            "stage": "issue_select",
            "ui_mode": "selector",
            "persona": persona,
            "payload": {
                "reasons": reasons,
                "itemId": session.selected_item_id
            }
        }

    async def _handle_escalation(
        self,
        payload: Dict[str, Any],
        channel_id: str,
        user_id: str,
        persona: str
    ) -> Dict[str, Any]:
        """
        Handle AI → Human escalation request.
        User wants to speak to a human agent.
        """
        from datetime import datetime, timezone

        reason = payload.get("reason", "user_requested")
        logger.info(f"[AI Support] Escalation requested: {reason} for {channel_id}")

        # Track escalation
        self.analytics.track_event(
            event_type="escalation_requested",
            channel_id=channel_id,
            user_id=user_id,
            persona=persona,
            reason=reason
        )

        # Get session
        session = self.session_manager.get_or_create(channel_id, user_id, persona)

        # Send notification to AI agent
        bot_id = self.bot.get_bot_id(persona)
        self.bot.send_message(
            channel_id=channel_id,
            bot_id=bot_id,
            text="I understand you'd like to speak with a human agent. Let me connect you...",
            internal_type="ai-message"
        )

        # Send handoff message
        self.bot.send_message(
            channel_id=channel_id,
            bot_id=bot_id,
            text=(
                "🤝 **Connecting you to a human agent**\n\n"
                "A support specialist will join this conversation shortly. "
                "In the meantime, feel free to provide any additional details about your issue.\n\n"
                "**Your context:**\n"
                f"• Category: {session.selected_cta}\n"
                f"• Item: {session.selected_item_title or session.selected_item_id}\n"
                f"• Issue: {session.selected_reason}\n\n"
                "Average wait time: 2-5 minutes"
            ),
            internal_type="ai-message"
        )

        # Mark session as escalated
        session.metadata["escalated"] = True
        session.metadata["escalation_reason"] = reason
        session.metadata["escalated_at"] = datetime.now(timezone.utc).isoformat()

        return {
            "stage": "diagnosis",
            "ui_mode": "chat",
            "persona": persona,
            "payload": {
                "escalated": True,
                "agent_prompt": "A human agent will join shortly. Feel free to provide more details."
            }
        }

    def _get_cta_label(self, cta_id: str, persona: str) -> str:
        """Get human-readable label for CTA ID."""
        cta_map = {
            "maintenance": "Report Maintenance Issue",
            "billing": "Billing Question",
            "amenities": "Amenities & Services",
            "incidents": "Review Incidents",
            "contractors": "Manage Contractors",
            "properties": "Property Overview",
            "jobs": "Available Jobs",
            "my_jobs": "My Active Jobs",
            "payments": "Payments & Invoices",
        }
        return cta_map.get(cta_id, cta_id.title())

    async def _handle_diagnosis_answer(
        self,
        payload: Dict[str, Any],
        channel_id: str,
        user_id: str,
        persona: str
    ) -> Dict[str, Any]:
        """
        Handle diagnosis chat answer - use LLM to continue conversation or move to resolution.
        Stage: diagnosis (stay or → resolution), UI Mode: chat (or → resolution)
        """
        answer = payload.get("answer")
        logger.info(f"[AI Support] Diagnosis answer: {answer}")

        # Get session for context
        session = self.session_manager.get_or_create(channel_id, user_id, persona)

        # Store user message in session
        session.diagnosis_messages.append(answer)

        # Build session context for LLM
        session_context = {
            "selected_cta": session.selected_cta,
            "selected_item_id": session.selected_item_id,
            "selected_reason": session.selected_reason
        }

        # Get AI response
        ai_response, is_complete = await self.diagnosis_agent.send_message(
            channel_id=channel_id,
            user_message=answer,
            persona=persona,
            session_context=session_context
        )

        # Send AI response back to user
        bot_id = self.bot.get_bot_id(persona)
        self.bot.send_message(
            channel_id=channel_id,
            bot_id=bot_id,
            text=ai_response,
            internal_type="ai-message"
        )

        # If diagnosis is complete, transition to resolution
        if is_complete:
            logger.info(f"[AI Support] Diagnosis complete for {channel_id}, moving to resolution")

            # Track diagnosis completion
            self.analytics.track_event(
                event_type="diagnosis_completed",
                channel_id=channel_id,
                user_id=user_id,
                persona=persona,
                num_messages=len(session.diagnosis_messages)
            )

            # Store diagnosis summary in session
            session.metadata["diagnosis_summary"] = ai_response

            # Clear diagnosis conversation
            self.diagnosis_agent.clear_conversation(channel_id)

            # Transition to resolution
            return await self._transition_to_resolution(
                channel_id=channel_id,
                user_id=user_id,
                persona=persona,
                context={"diagnosis_summary": ai_response}
            )

        # Otherwise, stay in diagnosis stage
        return {
            "stage": "diagnosis",
            "ui_mode": "chat",
            "persona": persona,
            "payload": {
                "agent_prompt": ai_response,
                "continue": True
            }
        }

    async def _handle_resolution_action(
        self,
        payload: Dict[str, Any],
        channel_id: str,
        user_id: str,
        persona: str
    ) -> Dict[str, Any]:
        """
        Handle resolution action - execute actual business logic.
        Stage: resolution → complete or back to intro
        """
        action_id = payload.get("action_id")
        logger.info(f"[AI Support] Resolution action: {action_id}, persona: {persona}")

        # Track action taken
        self.analytics.track_event(
            event_type="action_taken",
            channel_id=channel_id,
            user_id=user_id,
            persona=persona,
            action_id=action_id
        )

        bot_id = self.bot.get_bot_id(persona)

        # Execute action based on ID
        try:
            # TENANT ACTIONS
            if action_id == "create_incident":
                success = await self._create_incident_from_session(
                    user_id=user_id,
                    channel_id=channel_id,
                    payload=payload
                )

                if success:
                    self.bot.send_message(
                        channel_id=channel_id,
                        bot_id=bot_id,
                        text="✅ Maintenance request submitted successfully! Your landlord has been notified and will respond soon. You'll receive updates in this chat.",
                        internal_type="ai-message"
                    )
                else:
                    self.bot.send_message(
                        channel_id=channel_id,
                        bot_id=bot_id,
                        text="⚠️ There was an issue submitting your request. Please try again or contact support.",
                        internal_type="ai-message"
                    )

            elif action_id == "try_diy":
                # Show DIY troubleshooting tips
                self.bot.send_message(
                    channel_id=channel_id,
                    bot_id=bot_id,
                    text="🔧 Here are some DIY troubleshooting steps you can try:\n\n1. Check if the issue is isolated to one fixture\n2. Look for visible leaks or damage\n3. Try turning it off and on again\n4. Check circuit breakers if electrical\n\nIf these don't help, I can still submit a maintenance request for you.",
                    internal_type="ai-message"
                )

            elif action_id == "contact_emergency":
                self.bot.send_message(
                    channel_id=channel_id,
                    bot_id=bot_id,
                    text="🚨 **Emergency Support**\n\nFor immediate emergencies (water leaks, gas leaks, no heat in winter, etc.):\n📞 Emergency Hotline: 1-800-EMERGENCY\n\nAvailable 24/7 for urgent maintenance issues.",
                    internal_type="ai-message"
                )

            # LANDLORD ACTIONS
            elif action_id == "approve_work":
                success = await self._approve_work_order(
                    user_id=user_id,
                    channel_id=channel_id,
                    payload=payload
                )

                if success:
                    self.bot.send_message(
                        channel_id=channel_id,
                        bot_id=bot_id,
                        text="✅ Work order approved! I'll now find qualified contractors in your area.",
                        internal_type="ai-message"
                    )
                else:
                    self.bot.send_message(
                        channel_id=channel_id,
                        bot_id=bot_id,
                        text="⚠️ Could not approve work order. Please try again.",
                        internal_type="ai-message"
                    )

            elif action_id == "find_contractor":
                self.bot.send_message(
                    channel_id=channel_id,
                    bot_id=bot_id,
                    text="👷 Searching for qualified contractors in your area...\n\nI'm looking for contractors with:\n✓ Relevant experience\n✓ Good ratings\n✓ Availability this week\n\nYou'll see bids shortly.",
                    internal_type="ai-message"
                )

            elif action_id == "request_more_info":
                self.bot.send_message(
                    channel_id=channel_id,
                    bot_id=bot_id,
                    text="📸 I've requested additional photos and details from the tenant. They'll be notified to provide more information.",
                    internal_type="ai-message"
                )

            # CONTRACTOR ACTIONS
            elif action_id == "submit_bid":
                self.bot.send_message(
                    channel_id=channel_id,
                    bot_id=bot_id,
                    text="💼 Great! Please provide:\n\n1. Your estimated cost\n2. When you can start\n3. How long it will take\n\nReply in the chat and I'll submit your bid.",
                    internal_type="ai-message"
                )

            elif action_id == "view_details":
                self.bot.send_message(
                    channel_id=channel_id,
                    bot_id=bot_id,
                    text="📋 **Job Details**\n\nCategory: Plumbing\nPriority: Medium\nLocation: Property #123\n\nDescription: Kitchen sink clogged, water draining slowly.\n\nPhotos and additional details are available in the job portal.",
                    internal_type="ai-message"
                )

            # GENERIC ACTIONS
            elif action_id == "done":
                self.bot.send_message(
                    channel_id=channel_id,
                    bot_id=bot_id,
                    text="✅ Great! I'm glad I could help. Feel free to come back anytime you need assistance.",
                    internal_type="ai-message"
                )

            else:
                logger.warning(f"Unhandled action: {action_id}")
                self.bot.send_message(
                    channel_id=channel_id,
                    bot_id=bot_id,
                    text="✅ Action noted. Is there anything else I can help you with?",
                    internal_type="ai-message"
                )

        except Exception as e:
            logger.error(f"Error executing action {action_id}: {e}", exc_info=True)
            self.bot.send_message(
                channel_id=channel_id,
                bot_id=bot_id,
                text="❌ Sorry, something went wrong processing your request. Please try again.",
                internal_type="ai-message"
            )

        # Track session completion
        self.analytics.track_event(
            event_type="session_completed",
            channel_id=channel_id,
            user_id=user_id,
            persona=persona,
            final_action=action_id
        )

        # Clear session state
        self.session_manager.clear(channel_id)

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

    async def _create_incident_from_session(
        self,
        user_id: str,
        channel_id: str,
        payload: Dict[str, Any]
    ) -> bool:
        """
        Create an incident record from the AI Support session.
        Uses session state to populate incident details with user selections.
        """
        try:
            import time

            # Get session state to populate incident
            session = self.session_manager.get(channel_id)

            # Generate incident ID
            incident_id = f"INC-AI-{int(time.time())}"

            # Build title from session selections
            title_parts = []
            if session and session.selected_reason:
                title_parts.append(session.selected_reason)
            if session and session.selected_item_title:
                title_parts.append(f"({session.selected_item_title})")

            title = " - ".join(title_parts) if title_parts else "Maintenance Issue (AI Support)"

            # Build description from session context
            description_parts = ["Issue reported via AI Support chat."]
            if session:
                if session.selected_cta:
                    description_parts.append(f"\nCategory: {session.selected_cta}")
                if session.selected_item_id:
                    description_parts.append(f"Item: {session.selected_item_id}")
                if session.selected_reason:
                    description_parts.append(f"Issue: {session.selected_reason}")

                # Include AI diagnosis summary if available
                if "diagnosis_summary" in session.metadata:
                    description_parts.append(f"\n**AI Diagnosis:**\n{session.metadata['diagnosis_summary']}")
                elif session.diagnosis_messages:
                    description_parts.append(f"\nUser provided {len(session.diagnosis_messages)} additional details in chat.")

            description = "\n".join(description_parts)

            # Infer category from selections
            category = "general"
            if session and session.selected_item_id:
                item_lower = session.selected_item_id.lower()
                if "kitchen" in item_lower or "sink" in item_lower or "dishwasher" in item_lower:
                    category = "plumbing"
                elif "bathroom" in item_lower or "toilet" in item_lower or "shower" in item_lower:
                    category = "plumbing"
                elif "hvac" in item_lower or "heating" in item_lower or "cooling" in item_lower:
                    category = "hvac"
                elif "electric" in item_lower:
                    category = "electrical"

            # Build incident data
            incident_data = {
                "incident_id": incident_id,
                "user_id": user_id,
                "tenant_id": user_id,
                "property_id": "unknown",  # Would come from user profile
                "title": title,
                "description": description,
                "category": category,
                "severity": payload.get("severity", "medium"),
                "urgency": payload.get("urgency", "routine"),
                "status": "detected",
                "channel_id": channel_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "metadata": {
                    "source": "ai_support",
                    "session_id": session.session_id if session else None,
                    "session_channel": channel_id,
                    "selected_cta": session.selected_cta if session else None,
                    "selected_item": session.selected_item_id if session else None,
                    "selected_reason": session.selected_reason if session else None
                }
            }

            # Create incident in DynamoDB
            IncidentDB.create_incident(incident_data)

            logger.info(f"Created incident {incident_id} from AI Support session with context: {title}")
            return True

        except Exception as e:
            logger.error(f"Error creating incident from session: {e}", exc_info=True)
            return False

    async def _approve_work_order(
        self,
        user_id: str,
        channel_id: str,
        payload: Dict[str, Any]
    ) -> bool:
        """
        Approve work order and create job record.
        """
        try:
            import time

            # Generate job ID
            job_id = f"JOB-AI-{int(time.time())}"

            # Get incident ID from payload (if provided)
            incident_id = payload.get("incident_id", "unknown")

            # Create job record
            job_data = {
                "job_id": job_id,
                "incident_id": incident_id,
                "property_id": "unknown",  # Would come from incident
                "landlord_id": user_id,
                "title": "Approved Maintenance Work",
                "category": "general",
                "estimated_cost": "$150-250",
                "urgency": "routine",
                "status": "approved",
                "channel_id": channel_id
            }

            JobDB.create_job(job_data)

            logger.info(f"Created job {job_id} from work order approval")
            return True

        except Exception as e:
            logger.error(f"Error approving work order: {e}", exc_info=True)
            return False

    async def _transition_to_resolution(
        self,
        channel_id: str,
        user_id: str,
        persona: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Transition to resolution stage with persona-specific action options.
        Uses diagnosis summary from LLM if available.
        """
        # Track resolution shown and stage transition
        self.analytics.track_event(
            event_type="resolution_shown",
            channel_id=channel_id,
            user_id=user_id,
            persona=persona
        )
        self.analytics.track_event(
            event_type="stage_transition",
            channel_id=channel_id,
            user_id=user_id,
            persona=persona,
            from_stage="diagnosis",
            to_stage="resolution"
        )

        # Get diagnosis summary from context or session
        diagnosis_summary = None
        if context and "diagnosis_summary" in context:
            diagnosis_summary = context["diagnosis_summary"]
        else:
            # Try to get from session metadata
            session = self.session_manager.get(channel_id)
            if session and "diagnosis_summary" in session.metadata:
                diagnosis_summary = session.metadata["diagnosis_summary"]

        # Persona-specific actions and summaries
        if persona == "tenant":
            # Use LLM summary if available, otherwise default
            if diagnosis_summary:
                summary = f"**Diagnosis Summary:** {diagnosis_summary}\n\nI can help you proceed with the next steps."
            else:
                summary = "Based on your description, I can help you create a maintenance request for your landlord to review."

            actions = [
                {"id": "create_incident", "label": "📋 Submit Maintenance Request"},
                {"id": "try_diy", "label": "🔧 View DIY Troubleshooting Tips"},
                {"id": "contact_emergency", "label": "🚨 Report Emergency (24/7)"},
                {"id": "done", "label": "✅ Issue Resolved"}
            ]

        elif persona == "landlord":
            if diagnosis_summary:
                summary = f"**Issue Analysis:** {diagnosis_summary}\n\nRecommended actions:"
            else:
                summary = "I can help you take action on this incident or find a contractor."

            actions = [
                {"id": "approve_work", "label": "✅ Approve Work Order"},
                {"id": "find_contractor", "label": "👷 Find Contractor"},
                {"id": "request_more_info", "label": "📸 Request More Details"},
                {"id": "close_incident", "label": "✓ Mark as Resolved"}
            ]

        elif persona == "contractor":
            if diagnosis_summary:
                summary = f"**Job Details:** {diagnosis_summary}\n\nYour options:"
            else:
                summary = "You can bid on this job or update your availability."

            actions = [
                {"id": "submit_bid", "label": "💼 Submit Bid"},
                {"id": "view_details", "label": "📋 View Full Job Details"},
                {"id": "decline", "label": "❌ Not Interested"}
            ]

        elif persona == "property_manager":
            if diagnosis_summary:
                summary = f"**Assessment:** {diagnosis_summary}\n\nManagement options:"
            else:
                summary = "Here are your options for managing this request."

            actions = [
                {"id": "assign_contractor", "label": "👷 Assign to Contractor"},
                {"id": "escalate", "label": "🚨 Escalate to Landlord"},
                {"id": "schedule_inspection", "label": "📅 Schedule Inspection"},
                {"id": "resolve", "label": "✅ Mark as Resolved"}
            ]

        else:
            # Default fallback
            summary = diagnosis_summary or "Based on our conversation, here are the recommended next steps."
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
