"""
Stream Chat Card Builder Service
Creates interactive message cards for incident management workflow
"""

from typing import List, Dict, Any, Optional
from datetime import datetime


class CardBuilder:
    """Build interactive message cards for Stream Chat"""

    @staticmethod
    def incident_card(
        incident_id: str,
        title: str,
        description: str,
        severity: str,
        images: Optional[List[str]] = None,
        tenant_name: Optional[str] = None,
        property_address: Optional[str] = None,
        status: str = "detected"
    ) -> Dict[str, Any]:
        """
        Create an incident detection card

        Status can be: detected, discovery, work_order, bids, approved, completed
        """

        severity_colors = {
            "low": "#10b981",      # green
            "medium": "#f59e0b",   # amber
            "high": "#ef4444",     # red
            "emergency": "#dc2626" # dark red
        }

        severity_emoji = {
            "low": "🔵",
            "medium": "🟡",
            "high": "🔴",
            "emergency": "🚨"
        }

        actions = []

        # Actions based on status
        if status == "detected":
            actions = [
                {
                    "name": "start_discovery",
                    "text": "Start Discovery",
                    "style": "primary",
                    "type": "button",
                    "value": f"action:start_discovery:{incident_id}"
                },
                {
                    "name": "dismiss",
                    "text": "Dismiss",
                    "style": "default",
                    "type": "button",
                    "value": f"action:dismiss:{incident_id}"
                }
            ]
        elif status == "discovery":
            actions = [
                {
                    "name": "upload_photos",
                    "text": "📸 Upload Photos",
                    "style": "primary",
                    "type": "button",
                    "value": f"action:upload_photos:{incident_id}"
                },
                {
                    "name": "create_work_order",
                    "text": "Create Work Order",
                    "style": "primary",
                    "type": "button",
                    "value": f"action:create_work_order:{incident_id}"
                }
            ]
        elif status == "work_order":
            actions = [
                {
                    "name": "view_bids",
                    "text": "View Contractor Bids",
                    "style": "primary",
                    "type": "button",
                    "value": f"action:view_bids:{incident_id}"
                }
            ]

        # Build card structure
        card = {
            "type": "incident",
            "title": title,
            "title_link": f"#incident-{incident_id}",
            "text": description,
            "color": severity_colors.get(severity.lower(), "#6b7280"),
            "fields": [
                {
                    "title": "Severity",
                    "value": f"{severity_emoji.get(severity.lower(), '⚪')} {severity.upper()}",
                    "short": True
                },
                {
                    "title": "Status",
                    "value": status.replace("_", " ").title(),
                    "short": True
                }
            ],
            "footer": f"Incident {incident_id}",
            "footer_icon": "https://api.dicebear.com/7.x/shapes/svg?seed=incident",
            "ts": datetime.now().isoformat(),
            "actions": actions,
            "incident_id": incident_id,
            "incident_data": {
                "id": incident_id,
                "severity": severity,
                "status": status,
                "title": title,
                "description": description
            }
        }

        # Add tenant info if provided
        if tenant_name:
            card["fields"].append({
                "title": "Reported By",
                "value": tenant_name,
                "short": True
            })

        # Add property if provided
        if property_address:
            card["fields"].append({
                "title": "Property",
                "value": property_address,
                "short": True
            })

        # Add images if provided
        if images:
            card["image_url"] = images[0]  # First image as main
            card["thumb_url"] = images[0]
            if len(images) > 1:
                card["fields"].append({
                    "title": "Images",
                    "value": f"{len(images)} photos attached",
                    "short": False
                })

        return card

    @staticmethod
    def discovery_card(
        incident_id: str,
        questions_asked: int,
        questions_total: int,
        current_question: Optional[str] = None,
        answers: Optional[Dict[str, str]] = None,
        images_uploaded: int = 0
    ) -> Dict[str, Any]:
        """Create a discovery progress card"""

        progress = (questions_asked / questions_total) * 100 if questions_total > 0 else 0

        card = {
            "type": "discovery",
            "title": "🔍 Issue Discovery in Progress",
            "text": current_question or "Gathering information about the issue...",
            "color": "#3b82f6",  # blue
            "fields": [
                {
                    "title": "Progress",
                    "value": f"{questions_asked}/{questions_total} questions answered",
                    "short": True
                },
                {
                    "title": "Photos",
                    "value": f"{images_uploaded} uploaded",
                    "short": True
                }
            ],
            "footer": f"Incident {incident_id} • Discovery",
            "ts": datetime.now().isoformat(),
            "incident_id": incident_id,
            "discovery_data": {
                "progress": progress,
                "questions_asked": questions_asked,
                "questions_total": questions_total,
                "answers": answers or {},
                "images_uploaded": images_uploaded
            }
        }

        # Add progress bar visualization
        filled = int(progress / 10)
        empty = 10 - filled
        progress_bar = "█" * filled + "░" * empty
        card["fields"].insert(0, {
            "title": "Discovery Progress",
            "value": f"{progress_bar} {int(progress)}%",
            "short": False
        })

        return card

    @staticmethod
    def work_order_card(
        incident_id: str,
        job_id: str,
        title: str,
        category: str,
        estimated_cost: str,
        urgency: str,
        status: str = "created",
        property: Optional[str] = None,
        scheduled_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a work order card"""

        urgency_emoji = {
            "routine": "📅",
            "urgent": "⚡",
            "immediate": "🚨",
            "emergency": "🆘"
        }

        status_emoji = {
            "created": "📝",
            "approved": "✅",
            "scheduled": "📅",
            "in_progress": "🔧",
            "completed": "✔️"
        }

        actions = []
        if status == "created":
            actions = [
                {
                    "name": "approve_job",
                    "text": "✅ Approve Job",
                    "style": "primary",
                    "type": "button",
                    "value": f"action:approve_job:{job_id}"
                },
                {
                    "name": "request_bids",
                    "text": "View Contractor Bids",
                    "style": "default",
                    "type": "button",
                    "value": f"action:view_bids:{incident_id}"
                }
            ]

        card = {
            "type": "job",
            "title": f"🔧 Work Order: {title}",
            "text": f"A work order has been created for this {category} issue.",
            "color": "#8b5cf6",  # purple
            "fields": [
                {
                    "title": "Category",
                    "value": category.title(),
                    "short": True
                },
                {
                    "title": "Status",
                    "value": f"{status_emoji.get(status, '📋')} {status.replace('_', ' ').title()}",
                    "short": True
                },
                {
                    "title": "Estimated Cost",
                    "value": estimated_cost,
                    "short": True
                },
                {
                    "title": "Urgency",
                    "value": f"{urgency_emoji.get(urgency, '📋')} {urgency.title()}",
                    "short": True
                }
            ],
            "footer": f"Job {job_id} • Incident {incident_id}",
            "ts": datetime.now().isoformat(),
            "actions": actions,
            "job_data": {
                "job_id": job_id,
                "incident_id": incident_id,
                "status": status,
                "category": category,
                "estimated_cost": estimated_cost,
                "urgency": urgency
            }
        }

        if property:
            card["fields"].insert(0, {
                "title": "Property",
                "value": property,
                "short": False
            })

        if scheduled_date:
            card["fields"].append({
                "title": "Scheduled",
                "value": scheduled_date,
                "short": False
            })

        return card

    @staticmethod
    def bids_card(
        incident_id: str,
        job_id: str,
        bids: List[Dict[str, Any]],
        recommended_bid_index: int = 0
    ) -> Dict[str, Any]:
        """Create a contractor bids comparison card"""

        if not bids:
            return {
                "type": "bids",
                "title": "No Bids Available",
                "text": "No contractors have submitted bids yet.",
                "color": "#6b7280"
            }

        # Sort bids by quote (price)
        sorted_bids = sorted(bids, key=lambda b: b.get("quote", 999999))

        fields = []
        actions = []

        for idx, bid in enumerate(sorted_bids[:3]):  # Top 3 bids
            contractor_name = bid.get("name", f"Contractor {idx+1}")
            quote = bid.get("quote", 0)
            eta = bid.get("eta", "Not specified")
            rating = bid.get("rating", 0)
            distance = bid.get("distance", "")

            # Star rating
            stars = "⭐" * int(rating) if rating else "No rating"

            # Recommendation badge
            badge = "🏆 RECOMMENDED" if idx == recommended_bid_index else ""

            field_value = f"${quote} • {eta}\n{stars}"
            if distance:
                field_value += f" • {distance}"
            if badge:
                field_value = f"{badge}\n{field_value}"

            fields.append({
                "title": contractor_name,
                "value": field_value,
                "short": False
            })

            # Add approve button for each contractor
            actions.append({
                "name": f"approve_contractor_{idx}",
                "text": f"Hire {contractor_name}",
                "style": "primary" if idx == recommended_bid_index else "default",
                "type": "button",
                "value": f"action:approve_contractor:{job_id}:{contractor_name}:{quote}"
            })

        card = {
            "type": "bids",
            "title": "💼 Contractor Bids",
            "text": f"Found {len(bids)} qualified contractors. Review and select one to proceed.",
            "color": "#059669",  # emerald
            "fields": fields,
            "footer": f"Job {job_id} • Incident {incident_id}",
            "ts": datetime.now().isoformat(),
            "actions": actions,
            "bids_data": {
                "job_id": job_id,
                "incident_id": incident_id,
                "bids": bids,
                "recommended_index": recommended_bid_index
            }
        }

        return card

    @staticmethod
    def approval_card(
        incident_id: str,
        job_id: str,
        contractor_name: str,
        cost: float,
        scheduled_date: str,
        status: str = "pending"
    ) -> Dict[str, Any]:
        """Create an approval request card"""

        actions = []
        if status == "pending":
            actions = [
                {
                    "name": "approve",
                    "text": "✅ Approve",
                    "style": "primary",
                    "type": "button",
                    "value": f"action:approve_final:{job_id}"
                },
                {
                    "name": "reject",
                    "text": "❌ Reject",
                    "style": "danger",
                    "type": "button",
                    "value": f"action:reject:{job_id}"
                }
            ]

        status_color = {
            "pending": "#f59e0b",  # amber
            "approved": "#10b981",  # green
            "rejected": "#ef4444"   # red
        }

        status_emoji = {
            "pending": "⏳",
            "approved": "✅",
            "rejected": "❌"
        }

        card = {
            "type": "approval",
            "title": f"{status_emoji.get(status, '📋')} Approval {status.title()}",
            "text": f"Contractor {contractor_name} is ready to start work.",
            "color": status_color.get(status, "#6b7280"),
            "fields": [
                {
                    "title": "Contractor",
                    "value": contractor_name,
                    "short": True
                },
                {
                    "title": "Total Cost",
                    "value": f"${cost}",
                    "short": True
                },
                {
                    "title": "Scheduled Date",
                    "value": scheduled_date,
                    "short": False
                }
            ],
            "footer": f"Job {job_id} • Incident {incident_id}",
            "ts": datetime.now().isoformat(),
            "actions": actions,
            "approval_data": {
                "job_id": job_id,
                "incident_id": incident_id,
                "contractor": contractor_name,
                "cost": cost,
                "status": status
            }
        }

        return card

    @staticmethod
    def completion_card(
        incident_id: str,
        job_id: str,
        contractor_name: str,
        cost: float,
        completion_date: str,
        before_photos: Optional[List[str]] = None,
        after_photos: Optional[List[str]] = None,
        tenant_satisfied: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Create a job completion card"""

        fields = [
            {
                "title": "Contractor",
                "value": contractor_name,
                "short": True
            },
            {
                "title": "Final Cost",
                "value": f"${cost}",
                "short": True
            },
            {
                "title": "Completed On",
                "value": completion_date,
                "short": False
            }
        ]

        if before_photos:
            fields.append({
                "title": "Before Photos",
                "value": f"{len(before_photos)} photos",
                "short": True
            })

        if after_photos:
            fields.append({
                "title": "After Photos",
                "value": f"{len(after_photos)} photos",
                "short": True
            })

        if tenant_satisfied is not None:
            fields.append({
                "title": "Tenant Feedback",
                "value": "✅ Satisfied" if tenant_satisfied else "⚠️ Needs Review",
                "short": False
            })

        actions = [
            {
                "name": "rate_contractor",
                "text": "⭐ Rate Contractor",
                "style": "primary",
                "type": "button",
                "value": f"action:rate_contractor:{job_id}"
            }
        ]

        card = {
            "type": "completion",
            "title": "✅ Job Completed",
            "text": f"The work has been completed by {contractor_name}.",
            "color": "#10b981",  # green
            "fields": fields,
            "footer": f"Job {job_id} • Incident {incident_id}",
            "ts": datetime.now().isoformat(),
            "actions": actions,
            "completion_data": {
                "job_id": job_id,
                "incident_id": incident_id,
                "contractor": contractor_name,
                "cost": cost,
                "before_photos": before_photos or [],
                "after_photos": after_photos or []
            }
        }

        # Add first after photo as thumbnail if available
        if after_photos and len(after_photos) > 0:
            card["image_url"] = after_photos[0]
            card["thumb_url"] = after_photos[0]

        return card


def send_card_message(
    client,
    channel_id: str,
    bot_id: str,
    card_data: Dict[str, Any],
    message_text: Optional[str] = None
) -> Optional[Dict]:
    """
    Send a message with an interactive card attachment

    Args:
        client: StreamChat client
        channel_id: Channel ID
        bot_id: Bot user ID
        card_data: Card structure from CardBuilder
        message_text: Optional text to show above card
    """
    try:
        channel = client.channel("messaging", channel_id)

        message = {
            "text": message_text or card_data.get("text", ""),
            "attachments": [card_data],
            "type": "card"
        }

        response = channel.send_message(message, bot_id)
        return response
    except Exception as e:
        print(f"[card-builder] Error sending card: {e}")
        return None
