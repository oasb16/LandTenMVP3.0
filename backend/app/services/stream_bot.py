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
from app.services.dynamo_service import (
    IncidentDB,
    JobDB,
    BidDB,
    UserDB,
    PropertyDB
)
from app.services.context_manager import get_context_manager
import json
import re

def is_ai_trojan_message(text: str) -> bool:
    return bool(re.match(r"^\[AI_TYPE:.*?\]", text or ""))

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
        self.context_manager = get_context_manager()

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
                text=welcome_messages.get(persona, "Hi! How can I help?"),
                internal_type="ai-message"
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
        attachments: Optional[List[Dict[str, Any]]] = None,
        custom_data: Optional[Dict[str, Any]] = None,
        internal_type: str = "ai-message",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict]:
        """Send a message from an AI bot to a channel with natural formatting."""
        try:
            channel = self.client.channel("messaging", channel_id)

            payload: Dict[str, Any] = {
                "text": text,
                "type": "regular",
                "ai_type": internal_type,
            }

            if attachments:
                payload["attachments"] = attachments
            if custom_data:
                payload.update(custom_data)
            if metadata:
                payload["metadata"] = metadata

            print(f"[stream-bot] send_message -> {channel_id} [{bot_id}] :: {text}")
            response = channel.send_message(payload, user_id=bot_id)
            return response
        except Exception as e:  # pragma: no cover - network path
            print(f"[stream-bot] Error sending message: {e}")
            return None

    def send_ai_message(
        self,
        channel_id: str,
        persona: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict]:
        """Convenience wrapper for conversational replies."""
        bot_id = self.get_bot_id(persona)
        return self.send_message(
            channel_id=channel_id,
            bot_id=bot_id,
            text=text,
            internal_type="ai-message",
            metadata=metadata,
        )

    def send_action_buttons(
        self,
        channel_id: str,
        bot_id: str,
        text: str,
        actions: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict]:
        """Send a structured message with action buttons."""
        attachment = {
            "type": "custom_card",
            "fallback": text,
            "text": text,
            "buttons": actions,
        }

        return self.send_message(
            channel_id=channel_id,
            bot_id=bot_id,
            text=text,
            attachments=[attachment],
            metadata=metadata,
            internal_type="ai-message",
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
            message_type = message.get("type", "not_mentioned")
            
            if is_ai_trojan_message(message_text):
                print("[stream-bot] Skipping AI Trojan message echo loop")
                return None

            print(f"[stream-bot] Handling message from {user_name} ({user_id}) in channel {channel_id} as persona {persona}: {message_text} with type {message_type}")
            # Check if message is an action trigger
            if message_text.startswith("action:") or "@agent action:" in message_text:
                action_value = message_text.replace("@agent ", "").strip()
                return self.handle_action(action_value, user_id, channel_id, persona)

            # Detect incident in message (for tenant persona)
            if persona == "tenant":
                incident_data = self.detect_incident_in_message(message_text)
                if incident_data:
                    # Send incident detection card
                    incident_payload = {**incident_data, "user_id": user_id, "tenant_name": user_name}
                    self.send_incident_card(
                        channel_id=channel_id,
                        persona=persona,
                        incident_data=incident_payload,
                    )
                    print("[stream-bot] Incident detected and card sent.")
                    # Also send a conversational response
                    response_text = self.process_tenant_message(
                        message=message_text,
                        user_id=user_id,
                        channel_id=channel_id
                    )
                    print("\n\n\n\n\n[stream-bot] Sending conversational response after incident detection.\n\n\n\n\n\n\n\n")
                    return self.send_ai_message(
                        channel_id=channel_id,
                        persona=persona,
                        text=response_text,
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
                text=response_text,
                internal_type="ai-message"
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
        print(f"[stream-bot] ========== ACTION RECEIVED ==========")
        print(f"[stream-bot] Raw action value: {action_value}")
        print(f"[stream-bot] User: {user_id}, Channel: {channel_id}, Persona: {persona}")

        try:
            parts = action_value.split(":")
            if len(parts) < 2 or parts[0] != "action":
                print(f"[stream-bot] Invalid action format: {action_value}")
                return None

            action_name = parts[1]
            params = parts[2:] if len(parts) > 2 else []

            print(f"[stream-bot] → Routing to handler: {action_name} with params: {params}")

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
        print(f"[PropertyAIBot] Starting discovery for incident {incident_id}")

        # Send discovery message
        self.send_message(
            channel_id=channel_id,
            bot_id=bot_id,
            text="Great! Let's gather some details about the issue. I'll ask you a few questions.",
            internal_type="ai-message"
        )

        # Send first discovery question
        self.send_message(
            channel_id=channel_id,
            bot_id=bot_id,
            text="📍 First, can you tell me exactly where the issue is located? (e.g., 'kitchen sink', 'bedroom ceiling')",
            internal_type="ai-message"
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
            text="📸 Please upload photos of the issue. You can attach images directly in the chat or use the attachment button.",
            internal_type="ai-message"
        )

        return {"status": "prompted_for_photos"}

    def _handle_create_work_order(self, channel_id, user_id, persona, params):
        """Handle create work order action - WITH DYNAMODB PERSISTENCE"""
        incident_id = params[0] if params else f"INC-{int(datetime.now().timestamp())}"
        job_id = f"JOB-{int(datetime.now().timestamp())}"
        bot_id = self.get_bot_id(persona)

        print(f"[PropertyAIBot] Creating work order - incident: {incident_id}, job: {job_id}")

        # Get incident data if available
        incident_data = IncidentDB.get_incident(incident_id) if incident_id else None

        # Determine category, cost, urgency from incident or use defaults
        category = incident_data.get("category", "plumbing") if incident_data else "plumbing"
        severity = incident_data.get("severity", "medium") if incident_data else "medium"
        urgency = incident_data.get("urgency", "routine") if incident_data else "routine"

        # Map severity to estimated cost
        cost_map = {
            "low": "$100-150",
            "medium": "$150-200",
            "high": "$200-350",
            "emergency": "$350-500"
        }
        estimated_cost = cost_map.get(severity, "$150-200")

        # Persist job to DynamoDB
        try:
            job_record = JobDB.create_job({
                "job_id": job_id,
                "incident_id": incident_id,
                "property_id": incident_data.get("property_id", "unknown") if incident_data else "unknown",
                "landlord_id": user_id,  # Assuming user creating job is landlord
                "title": incident_data.get("title", "Maintenance Repair") if incident_data else "Plumbing Repair",
                "category": category,
                "estimated_cost": estimated_cost,
                "urgency": urgency,
                "status": "created",
                "channel_id": channel_id
            })
            print(f"[PropertyAIBot] Job persisted to DynamoDB: {job_id}")

            # Update incident status to work_order
            if incident_id:
                IncidentDB.update_incident_status(incident_id, "work_order", job_id=job_id)
                print(f"[PropertyAIBot] Updated incident {incident_id} status to work_order")

        except Exception as e:
            print(f"[PropertyAIBot] ERROR persisting job to DynamoDB: {e}")
            # Continue anyway - don't block UI

        # Send confirmation message
        self.send_message(
            channel_id=channel_id,
            bot_id=bot_id,
            text="✅ Creating work order for this issue...",
            internal_type="ai-message"
        )

        # Send work order card
        work_order_card = CardBuilder.work_order_card(
            incident_id=incident_id,
            job_id=job_id,
            title=incident_data.get("title", "Maintenance Repair") if incident_data else "Plumbing Repair",
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
            text="I've notified your landlord. They should respond within 24 hours.",
            internal_type="ai-message"
        )

        return result

    def _handle_view_bids(self, channel_id, user_id, persona, params):
        """Handle view contractor bids action - WITH DYNAMODB PERSISTENCE"""
        incident_id = params[0] if params else "INC-unknown"
        job_id = params[1] if len(params) > 1 else f"JOB-{int(datetime.now().timestamp())}"
        bot_id = self.get_bot_id(persona)

        print(f"[PropertyAIBot] Viewing bids for job: {job_id}")

        # Generate contractor bids
        bids = generate_contractor_bids("plumbing")

        # Enhance bids with additional data and persist each to DynamoDB
        enhanced_bids = []
        for idx, bid in enumerate(bids):
            bid_id = f"BID-{int(datetime.now().timestamp())}-{idx}"
            contractor_name = bid.get("name", f"Contractor {idx+1}")
            quote = bid.get("quote", 150 + (idx * 25))
            eta = bid.get("eta", "Tomorrow")
            rating = 4.8 - (idx * 0.2)
            distance = f"{2 + idx} miles"

            enhanced_bid = {
                **bid,
                "bid_id": bid_id,
                "rating": rating,
                "distance": distance
            }
            enhanced_bids.append(enhanced_bid)

            # Persist bid to DynamoDB
            try:
                BidDB.create_bid({
                    "bid_id": bid_id,
                    "job_id": job_id,
                    "contractor_id": f"contractor-{idx}",
                    "contractor_name": contractor_name,
                    "quote": quote,
                    "eta": eta,
                    "rating": rating,
                    "distance": distance,
                    "status": "pending"
                })
                print(f"[PropertyAIBot] Bid persisted to DynamoDB: {bid_id} from {contractor_name}")
            except Exception as e:
                print(f"[PropertyAIBot] ERROR persisting bid to DynamoDB: {e}")
                # Continue anyway - don't block UI

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
        """Handle approve contractor action - WITH DYNAMODB PERSISTENCE"""
        if len(params) < 3:
            return None

        job_id = params[0]
        contractor_name = params[1]
        cost = float(params[2]) if params[2] else 0
        incident_id = params[3] if len(params) > 3 else "INC-unknown"

        bot_id = self.get_bot_id(persona)

        print(f"[PropertyAIBot] Approving contractor {contractor_name} for job: {job_id}")

        # Update job in DynamoDB with contractor assignment
        try:
            JobDB.update_job(
                job_id=job_id,
                contractor_id=contractor_name,
                final_cost=f"${cost}",
                status="approved",
                scheduled_date="Tomorrow, 9:00 AM"
            )
            print(f"[PropertyAIBot] Job {job_id} updated with contractor {contractor_name}")

            # Update incident status to "scheduled" if we have incident_id
            if incident_id and incident_id != "INC-unknown":
                IncidentDB.update_incident_status(incident_id, "scheduled")
                print(f"[PropertyAIBot] Updated incident {incident_id} status to scheduled")

        except Exception as e:
            print(f"[PropertyAIBot] ERROR updating job in DynamoDB: {e}")
            # Continue anyway - don't block UI

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
            text=f"The contractor will arrive tomorrow at 9:00 AM. You'll receive a notification when they're on their way.",
            internal_type="ai-message"
        )

        return result

    def _handle_approve_job(self, channel_id, user_id, persona, params):
        """Handle approve job action (landlord approval)"""
        job_id = params[0] if params else "JOB-unknown"
        bot_id = self.get_bot_id(persona)

        self.send_message(
            channel_id=channel_id,
            bot_id=bot_id,
            text="✅ Job approved! Now let's find qualified contractors.",
            internal_type="ai-message"
        )

        # Automatically show bids after approval
        return self._handle_view_bids(channel_id, user_id, persona, [])

    def _handle_dismiss(self, channel_id, user_id, persona, params):
        """Handle dismiss incident action"""
        bot_id = self.get_bot_id(persona)

        self.send_message(
            channel_id=channel_id,
            bot_id=bot_id,
            text="Okay, I've dismissed this incident. Let me know if you need help with anything else!",
            internal_type="ai-message"
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
    ) -> Dict[str, Any]:
        """
        Create an incident record and send a structured card.

        Returns:
            Dict with incident_id and card_response for downstream use
        """
        incident_id = incident_data.get("incident_id") or f"INC-{int(datetime.now().timestamp())}"
        bot_id = self.get_bot_id(persona)
        user_id = incident_data.get("user_id")

        print(f"[stream-bot] 📋 Creating incident card {incident_id} for channel {channel_id}")

        # Persist incident to DynamoDB (best effort)
        persistence_success = False
        try:
            IncidentDB.create_incident(
                {
                    "incident_id": incident_id,
                    "user_id": user_id or "unknown",
                    "tenant_id": incident_data.get("tenant_id", user_id or "unknown"),
                    "property_id": incident_data.get("property_id", "unknown"),
                    "title": incident_data.get("title", "Maintenance Issue"),
                    "description": incident_data.get("description", ""),
                    "category": incident_data.get("category", "plumbing"),
                    "severity": incident_data.get("severity", "medium"),
                    "urgency": incident_data.get("urgency", "routine"),
                    "status": "detected",
                    "channel_id": channel_id,
                    "metadata": incident_data.get("metadata", {}),
                }
            )
            persistence_success = True
            print(f"[stream-bot] ✅ Incident {incident_id} persisted to DynamoDB")
        except Exception as exc:  # pragma: no cover - external service
            print(f"[stream-bot] ❌ Incident persistence failed: {exc}")

        card = CardBuilder.incident_card(
            incident_id=incident_id,
            title=incident_data.get("title", "Maintenance Issue"),
            description=incident_data.get("description", ""),
            severity=incident_data.get("severity", "high"),
            tenant_name=incident_data.get("tenant_name"),
            status="detected",
        )

        response = send_card_message(
            self.client,
            channel_id,
            bot_id,
            card,
            message_text="🔍 I detected a potential maintenance issue. Let's get this logged.",
            metadata={"context_type": "incident", "incident_id": incident_id},
        )

        # Update context manager with incident state
        if user_id:
            try:
                self.context_manager.set_active_incident(user_id, channel_id, incident_id)
                self.context_manager.advance_flow_state(
                    user_id,
                    channel_id,
                    "incident",
                    {"incident_id": incident_id, "question_index": 0},
                )
                print(f"[stream-bot] ✅ Context updated with incident {incident_id}")
            except Exception as exc:
                print(f"[stream-bot] ❌ Context update failed: {exc}")

        # Always return incident_id for downstream use
        return {
            "incident_id": incident_id,
            "card_response": response,
            "persisted": persistence_success,
        }


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
