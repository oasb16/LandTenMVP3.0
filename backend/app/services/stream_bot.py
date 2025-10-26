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
                "type": "ai-message"
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
