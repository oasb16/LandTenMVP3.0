"""
Stream Chat AI Bot Service
Manages AI bot users for different personas (tenant, landlord, contractor)
"""

import os
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

try:
    from stream_chat import StreamChat
    from stream_chat.base.exceptions import StreamAPIException
except ImportError:
    StreamChat = None
    StreamAPIException = Exception

from app.services.ai_service import get_ai_response
from app.services.card_builder import CardBuilder, send_card_message
from app.services.incident_flow import (
    classify_issue,
    diy_suggestions,
    create_incident_record,
    generate_contractor_bids
)
import json
import re


class PropertyAIBot:
    """AI Bot manager for PropertyAI multi-persona system"""

    def __init__(self):
        self.api_key = os.getenv("STREAM_CHAT_API_KEY")
        self.api_secret = os.getenv("STREAM_CHAT_API_SECRET")

        if not self.api_key or not self.api_secret:
            raise ValueError("STREAM_CHAT_API_KEY and STREAM_CHAT_API_SECRET must be set")

        if StreamChat is None:
            raise RuntimeError("stream-chat SDK not installed")

        self.client = StreamChat(api_key=self.api_key, api_secret=self.api_secret)

        # Bot configurations for each persona
        self.bots = {
            "tenant": {
                "id": "ai-tenant-bot",
                "name": "PropertyHelper",
                "role": "admin",
                "description": "AI assistant for tenants - helps troubleshoot issues and report incidents"
            },
            "landlord": {
                "id": "ai-landlord-bot",
                "name": "PropertyManager",
                "role": "admin",
                "description": "AI assistant for landlords - automates property management tasks"
            },
            "contractor": {
                "id": "ai-contractor-bot",
                "name": "JobAssistant",
                "role": "admin",
                "description": "AI assistant for contractors - manages jobs, bids, and payments"
            }
        }

    def create_bot_users(self):
        """Create or update all AI bot users"""
        for persona, config in self.bots.items():
            try:
                self.client.upsert_user({
                    "id": config["id"],
                    "name": config["name"],
                    "role": config["role"],
                    "is_bot": True,
                    "persona": persona,
                    "image": f"https://api.dicebear.com/7.x/bottts/svg?seed={persona}"
                })
                print(f"[stream-bot] Created/updated bot: {config['name']} ({config['id']})")
            except Exception as e:
                print(f"[stream-bot] Error creating bot {config['id']}: {e}")

    def get_bot_id(self, persona: str) -> str:
        """Get bot ID for a persona"""
        return self.bots.get(persona, {}).get("id", "ai-tenant-bot")

    def add_bot_to_channel(self, channel_id: str, persona: str) -> bool:
        """Add appropriate AI bot to a channel"""
        try:
            bot_id = self.get_bot_id(persona)
            channel = self.client.channel("messaging", channel_id)

            # Add bot as member with moderator privileges
            channel.add_members([bot_id], {"is_moderator": True})

            # Send welcome message
            welcome_messages = {
                "tenant": "👋 Hi! I'm PropertyHelper, your AI assistant. I can help you troubleshoot issues, report incidents, and communicate with your landlord. How can I help you today?",
                "landlord": "👋 Hello! I'm PropertyManager, your AI property management assistant. I can help you manage incidents, find contractors, and automate tasks. What would you like to do?",
                "contractor": "👋 Hey! I'm JobAssistant, your AI job helper. I can help you find jobs, manage your schedule, submit bids, and get paid. What can I do for you?"
            }

            self.send_message(
                channel_id=channel_id,
                bot_id=bot_id,
                text=welcome_messages.get(persona, "Hi! How can I help?")
            )

            return True
        except Exception as e:
            print(f"[stream-bot] Error adding bot to channel {channel_id}: {e}")
            return False

    def send_message(
        self,
        channel_id: str,
        bot_id: str,
        text: str,
        attachments: Optional[List[Dict]] = None,
        custom_data: Optional[Dict] = None
    ) -> Optional[Dict]:
        """Send a message from AI bot to channel"""
        try:
            channel = self.client.channel("messaging", channel_id)

            message_data = {
                "text": text,
                "type": "regular"
            }

            if attachments:
                message_data["attachments"] = attachments

            if custom_data:
                message_data.update(custom_data)

            response = channel.send_message(message_data, bot_id)
            return response
        except Exception as e:
            print(f"[stream-bot] Error sending message: {e}")
            return None

    def send_action_buttons(
        self,
        channel_id: str,
        bot_id: str,
        text: str,
        actions: List[Dict[str, Any]]
    ) -> Optional[Dict]:
        """Send a message with action buttons"""
        attachments = [{
            "type": "actions",
            "text": text,
            "actions": [
                {
                    "name": action.get("name", "action"),
                    "text": action.get("text", "Action"),
                    "style": action.get("style", "primary"),
                    "type": "button",
                    "value": action.get("value", "")
                }
                for action in actions
            ]
        }]

        return self.send_message(
            channel_id=channel_id,
            bot_id=bot_id,
            text=text,
            attachments=attachments
        )

    def process_tenant_message(
        self,
        message: str,
        user_id: str,
        channel_id: str,
        context: Optional[Dict] = None
    ) -> str:
        """Process tenant message and generate AI response"""

        system_context = f"""You are PropertyHelper, an AI assistant for tenants in PropertyAI.

Your role:
1. Help troubleshoot property issues
2. Ask clarifying questions about problems
3. Assess severity (Low/Medium/High/Emergency)
4. Suggest DIY fixes when appropriate
5. Recommend when to create incidents for landlord

Be friendly, helpful, and concise. Use emojis sparingly.

Current conversation context: {context if context else 'New conversation'}
"""

        # Use existing AI service with enhanced context
        response = get_ai_response(
            message=message,
            persona="tenant",
            context=system_context
        )

        return response

    def process_landlord_message(
        self,
        message: str,
        user_id: str,
        channel_id: str,
        context: Optional[Dict] = None
    ) -> str:
        """Process landlord message and generate AI response"""

        system_context = f"""You are PropertyManager, an AI assistant for landlords in PropertyAI.

Your role:
1. Help manage property incidents
2. Find and recommend contractors
3. Provide job cost estimates
4. Track property maintenance
5. Automate approval workflows

Be professional, data-driven, and proactive.

Current conversation context: {context if context else 'New conversation'}
"""

        response = get_ai_response(
            message=message,
            persona="landlord",
            context=system_context
        )

        return response

    def process_contractor_message(
        self,
        message: str,
        user_id: str,
        channel_id: str,
        context: Optional[Dict] = None
    ) -> str:
        """Process contractor message and generate AI response"""

        system_context = f"""You are JobAssistant, an AI assistant for contractors in PropertyAI.

Your role:
1. Help contractors find relevant jobs
2. Assist with bid creation
3. Send job reminders
4. Track job completion
5. Help generate receipts and invoices

Be supportive, organized, and motivating.

Current conversation context: {context if context else 'New conversation'}
"""

        response = get_ai_response(
            message=message,
            persona="contractor",
            context=system_context
        )

        return response

    def get_channel_persona(self, channel_id: str) -> Optional[str]:
        """Determine persona from channel metadata"""
        try:
            channel = self.client.channel("messaging", channel_id)
            channel_data = channel.query()

            # Check custom data for persona
            custom_data = channel_data.get("channel", {}).get("custom", {})
            return custom_data.get("persona")
        except Exception as e:
            print(f"[stream-bot] Error getting channel persona: {e}")
            return None

    def handle_message_event(self, event_data: Dict[str, Any]) -> Optional[Dict]:
        """Handle incoming message webhook event"""
        try:
            message = event_data.get("message", {})
            user = event_data.get("user", {})
            channel_id = event_data.get("channel_id")

            # Ignore bot's own messages
            if user.get("is_bot") or user.get("id", "").startswith("ai-"):
                return None

            # Get channel persona
            persona = self.get_channel_persona(channel_id)
            if not persona:
                # Try to infer from user data
                persona = user.get("persona", "tenant")

            bot_id = self.get_bot_id(persona)
            message_text = message.get("text", "")
            user_id = user.get("id")
            user_name = user.get("name", user_id)

            # Check if message is an action trigger
            if message_text.startswith("action:") or "@agent action:" in message_text:
                action_value = message_text.replace("@agent ", "").strip()
                return self.handle_action(action_value, user_id, channel_id, persona)

            # Detect incident in message (for tenant persona)
            if persona == "tenant":
                incident_data = self.detect_incident_in_message(message_text)
                if incident_data:
                    # Send incident detection card
                    self.send_incident_card(
                        channel_id=channel_id,
                        persona=persona,
                        incident_data=incident_data,
                        user_name=user_name
                    )
                    # Also send a conversational response
                    response_text = self.process_tenant_message(
                        message=message_text,
                        user_id=user_id,
                        channel_id=channel_id
                    )
                    return self.send_message(
                        channel_id=channel_id,
                        bot_id=bot_id,
                        text=response_text
                    )

            # Process message based on persona
            if persona == "tenant":
                response_text = self.process_tenant_message(
                    message=message_text,
                    user_id=user_id,
                    channel_id=channel_id
                )
            elif persona == "landlord":
                response_text = self.process_landlord_message(
                    message=message_text,
                    user_id=user_id,
                    channel_id=channel_id
                )
            elif persona == "contractor":
                response_text = self.process_contractor_message(
                    message=message_text,
                    user_id=user_id,
                    channel_id=channel_id
                )
            else:
                response_text = "I'm not sure how to help with that. Could you please clarify?"

            # Send response
            return self.send_message(
                channel_id=channel_id,
                bot_id=bot_id,
                text=response_text
            )

        except Exception as e:
            print(f"[stream-bot] Error handling message event: {e}")
            return None

    def handle_action(
        self,
        action_value: str,
        user_id: str,
        channel_id: str,
        persona: str
    ) -> Optional[Dict]:
        """
        Handle action button clicks from cards

        Action format: "action:action_name:param1:param2"
        """
        try:
            parts = action_value.split(":")
            if len(parts) < 2 or parts[0] != "action":
                return None

            action_name = parts[1]
            params = parts[2:] if len(parts) > 2 else []

            print(f"[stream-bot] Handling action: {action_name} with params: {params}")

            # Route to appropriate handler
            if action_name == "start_discovery":
                return self._handle_start_discovery(channel_id, user_id, persona, params)
            elif action_name == "upload_photos":
                return self._handle_upload_photos(channel_id, user_id, persona, params)
            elif action_name == "create_work_order":
                return self._handle_create_work_order(channel_id, user_id, persona, params)
            elif action_name == "view_bids":
                return self._handle_view_bids(channel_id, user_id, persona, params)
            elif action_name == "approve_contractor":
                return self._handle_approve_contractor(channel_id, user_id, persona, params)
            elif action_name == "approve_job":
                return self._handle_approve_job(channel_id, user_id, persona, params)
            elif action_name == "dismiss":
                return self._handle_dismiss(channel_id, user_id, persona, params)
            else:
                print(f"[stream-bot] Unknown action: {action_name}")
                return None

        except Exception as e:
            print(f"[stream-bot] Error handling action: {e}")
            return None

    def _handle_start_discovery(self, channel_id, user_id, persona, params):
        """Handle start discovery action"""
        incident_id = params[0] if params else f"INC-{int(datetime.now().timestamp())}"
        bot_id = self.get_bot_id(persona)

        # Send discovery message
        self.send_message(
            channel_id=channel_id,
            bot_id=bot_id,
            text="Great! Let's gather some details about the issue. I'll ask you a few questions."
        )

        # Send first discovery question
        self.send_message(
            channel_id=channel_id,
            bot_id=bot_id,
            text="📍 First, can you tell me exactly where the issue is located? (e.g., 'kitchen sink', 'bedroom ceiling')"
        )

        # Send discovery progress card
        discovery_card = CardBuilder.discovery_card(
            incident_id=incident_id,
            questions_asked=0,
            questions_total=4,
            current_question="Where is the issue located?",
            images_uploaded=0
        )

        return send_card_message(
            self.client,
            channel_id,
            bot_id,
            discovery_card
        )

    def _handle_upload_photos(self, channel_id, user_id, persona, params):
        """Handle upload photos action"""
        bot_id = self.get_bot_id(persona)

        self.send_message(
            channel_id=channel_id,
            bot_id=bot_id,
            text="📸 Please upload photos of the issue. You can attach images directly in the chat or use the attachment button."
        )

        return {"status": "prompted_for_photos"}

    def _handle_create_work_order(self, channel_id, user_id, persona, params):
        """Handle create work order action"""
        incident_id = params[0] if params else f"INC-{int(datetime.now().timestamp())}"
        job_id = f"JOB-{int(datetime.now().timestamp())}"
        bot_id = self.get_bot_id(persona)

        # Simulate incident analysis
        category = "plumbing"
        estimated_cost = "$150-200"
        urgency = "routine"

        # Send confirmation message
        self.send_message(
            channel_id=channel_id,
            bot_id=bot_id,
            text="✅ Creating work order for this issue..."
        )

        # Send work order card
        work_order_card = CardBuilder.work_order_card(
            incident_id=incident_id,
            job_id=job_id,
            title="Plumbing Repair",
            category=category,
            estimated_cost=estimated_cost,
            urgency=urgency,
            status="created"
        )

        result = send_card_message(
            self.client,
            channel_id,
            bot_id,
            work_order_card,
            "🔧 Work order has been created! Your landlord will be notified."
        )

        # Notify landlord (simplified - in real system, send to landlord's channel)
        self.send_message(
            channel_id=channel_id,
            bot_id=bot_id,
            text="I've notified your landlord. They should respond within 24 hours."
        )

        return result

    def _handle_view_bids(self, channel_id, user_id, persona, params):
        """Handle view contractor bids action"""
        incident_id = params[0] if params else "INC-unknown"
        job_id = f"JOB-{int(datetime.now().timestamp())}"
        bot_id = self.get_bot_id(persona)

        # Generate contractor bids
        bids = generate_contractor_bids("plumbing")

        # Enhance bids with additional data
        enhanced_bids = []
        for idx, bid in enumerate(bids):
            enhanced_bids.append({
                **bid,
                "rating": 4.8 - (idx * 0.2),
                "distance": f"{2 + idx} miles"
            })

        # Send bids card
        bids_card = CardBuilder.bids_card(
            incident_id=incident_id,
            job_id=job_id,
            bids=enhanced_bids,
            recommended_bid_index=0
        )

        return send_card_message(
            self.client,
            channel_id,
            bot_id,
            bids_card,
            "💼 Here are the qualified contractors in your area:"
        )

    def _handle_approve_contractor(self, channel_id, user_id, persona, params):
        """Handle approve contractor action"""
        if len(params) < 3:
            return None

        job_id = params[0]
        contractor_name = params[1]
        cost = float(params[2]) if params[2] else 0
        incident_id = params[3] if len(params) > 3 else "INC-unknown"

        bot_id = self.get_bot_id(persona)

        # Send approval card
        approval_card = CardBuilder.approval_card(
            incident_id=incident_id,
            job_id=job_id,
            contractor_name=contractor_name,
            cost=cost,
            scheduled_date="Tomorrow, 9:00 AM",
            status="approved"
        )

        result = send_card_message(
            self.client,
            channel_id,
            bot_id,
            approval_card,
            f"✅ {contractor_name} has been hired for this job!"
        )

        # Send follow-up message
        self.send_message(
            channel_id=channel_id,
            bot_id=bot_id,
            text=f"The contractor will arrive tomorrow at 9:00 AM. You'll receive a notification when they're on their way."
        )

        return result

    def _handle_approve_job(self, channel_id, user_id, persona, params):
        """Handle approve job action (landlord approval)"""
        job_id = params[0] if params else "JOB-unknown"
        bot_id = self.get_bot_id(persona)

        self.send_message(
            channel_id=channel_id,
            bot_id=bot_id,
            text="✅ Job approved! Now let's find qualified contractors."
        )

        # Automatically show bids after approval
        return self._handle_view_bids(channel_id, user_id, persona, [])

    def _handle_dismiss(self, channel_id, user_id, persona, params):
        """Handle dismiss incident action"""
        bot_id = self.get_bot_id(persona)

        self.send_message(
            channel_id=channel_id,
            bot_id=bot_id,
            text="Okay, I've dismissed this incident. Let me know if you need help with anything else!"
        )

        return {"status": "dismissed"}

    def detect_incident_in_message(self, message_text: str) -> Optional[Dict[str, Any]]:
        """
        Analyze message to detect if it describes an incident
        Returns incident data if detected, None otherwise
        """
        # Keywords that indicate potential incidents
        incident_keywords = [
            "leak", "broken", "damage", "not working", "broken", "crack",
            "flooding", "water", "electric", "smell", "noise", "stuck"
        ]

        lower_text = message_text.lower()

        # Check if message contains incident keywords
        if any(keyword in lower_text for keyword in incident_keywords):
            # Classify the issue
            category, severity, urgency = classify_issue(message_text)

            return {
                "detected": True,
                "description": message_text,
                "category": category,
                "severity": severity,
                "urgency": urgency,
                "title": message_text[:50] + "..." if len(message_text) > 50 else message_text
            }

        return None

    def send_incident_card(
        self,
        channel_id: str,
        persona: str,
        incident_data: Dict[str, Any],
        user_name: Optional[str] = None
    ) -> Optional[Dict]:
        """Send an incident detection card"""
        incident_id = f"INC-{int(datetime.now().timestamp())}"
        bot_id = self.get_bot_id(persona)

        card = CardBuilder.incident_card(
            incident_id=incident_id,
            title=incident_data.get("title", "Maintenance Issue"),
            description=incident_data.get("description", ""),
            severity=incident_data.get("severity", "medium"),
            tenant_name=user_name,
            status="detected"
        )

        return send_card_message(
            self.client,
            channel_id,
            bot_id,
            card,
            "🔍 I detected a potential maintenance issue. Would you like me to help with this?"
        )


# Singleton instance
_bot_instance: Optional[PropertyAIBot] = None


def get_bot() -> PropertyAIBot:
    """Get or create PropertyAI bot instance"""
    global _bot_instance
    if _bot_instance is None:
        _bot_instance = PropertyAIBot()
        # Initialize bot users on first access
        _bot_instance.create_bot_users()
    return _bot_instance
