"""
Email service for sending checkout links and receipts.

This service handles:
- Sending payment link emails
- Sending payment receipt emails
- HTML email templates
"""

import os
import logging
from typing import Dict, Any, Optional, List
import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Using Resend API for email sending
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
RESEND_API_URL = "https://api.resend.com/emails"


class EmailService:
    """Service for handling email communications."""

    def __init__(self):
        self.api_key = RESEND_API_KEY
        self.from_email = os.getenv("FROM_EMAIL", "hotel@guesto.online")

    def _generate_payment_link_email(self, data: Dict[str, Any]) -> str:
        """Generate HTML for payment link email."""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f5f5f5; margin: 0; padding: 20px;">
    <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
        <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); padding: 32px; text-align: center;">
            <h1 style="color: #d4af37; margin: 0; font-size: 28px;">{data.get('hotel_name', 'Hotel')}</h1>
        </div>

        <div style="padding: 32px;">
            <h2 style="color: #1a1a2e; margin: 0 0 16px 0;">Hello {data.get('guest_name', 'Guest')},</h2>

            <p style="color: #666; font-size: 16px; line-height: 1.6;">
                Please complete your payment using the secure link below.
            </p>

            <div style="background-color: #f8f9fa; border-radius: 8px; padding: 20px; margin: 24px 0; text-align: center;">
                <p style="color: #666; margin: 0 0 8px 0; font-size: 14px;">Amount Due</p>
                <p style="color: #1a1a2e; margin: 0; font-size: 32px; font-weight: bold;">${data.get('amount', 0):.2f}</p>
            </div>

            <a href="{data.get('checkout_url', '#')}"
               style="display: block; background: linear-gradient(135deg, #d4af37 0%, #c9a227 100%); color: #1a1a2e; text-decoration: none; padding: 16px 32px; border-radius: 8px; font-weight: 600; text-align: center; font-size: 16px;">
                Complete Payment
            </a>

            <p style="color: #999; font-size: 12px; margin: 24px 0 0 0; text-align: center;">
                This is a secure payment link. Do not share it with others.
            </p>
        </div>
    </div>
</body>
</html>
        """

    def _generate_receipt_email(self, data: Dict[str, Any]) -> str:
        """Generate HTML for receipt email."""
        additional_charges = data.get('additional_charges', [])
        additional_charges_html = ""

        if additional_charges:
            for charge in additional_charges:
                additional_charges_html += f"""
                <tr>
                    <td style="padding: 8px 0; color: #666; border-bottom: 1px solid #eee;">{charge.get('description', '')}</td>
                    <td style="padding: 8px 0; color: #1a1a2e; text-align: right; border-bottom: 1px solid #eee;">${charge.get('amount', 0):.2f}</td>
                </tr>
                """

        return f"""
<!DOCTYPE html>
<html>
<body style="font-family: sans-serif; background-color: #f5f5f5; padding: 20px;">
    <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden;">
        <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); padding: 32px; text-align: center;">
            <h1 style="color: #d4af37; margin: 0;">{data.get('hotel_name', 'Hotel')}</h1>
            <p style="color: #ffffff; margin: 8px 0 0 0;">Payment Receipt</p>
        </div>

        <div style="padding: 32px;">
            <h2 style="color: #1a1a2e; margin: 0 0 4px 0;">{data.get('guest_name', 'Guest')}</h2>
            <p style="color: #666; margin: 0;">Room {data.get('room_number', 'N/A')}</p>
            <p style="color: #666; margin: 16px 0; font-family: monospace; font-size: 12px;">Transaction: {data.get('transaction_id', 'N/A')}</p>

            <h3 style="color: #1a1a2e; margin: 24px 0 16px 0; border-bottom: 2px solid #d4af37; padding-bottom: 8px;">Charges</h3>

            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; color: #666; border-bottom: 1px solid #eee;">
                        Room Charges ({data.get('nights', 0)} nights)
                    </td>
                    <td style="padding: 8px 0; color: #1a1a2e; text-align: right; border-bottom: 1px solid #eee;">
                        ${data.get('room_charges', 0):.2f}
                    </td>
                </tr>
                {additional_charges_html}
            </table>

            <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); border-radius: 8px; padding: 20px; text-align: center; margin-top: 24px;">
                <p style="color: #d4af37; margin: 0 0 4px 0;">Total Paid</p>
                <p style="color: #ffffff; margin: 0; font-size: 32px; font-weight: bold;">${data.get('amount', 0):.2f}</p>
            </div>

            <p style="color: #28a745; text-align: center; margin: 24px 0 0 0;">✓ Payment Completed Successfully</p>
        </div>
    </div>
</body>
</html>
        """

    async def send_checkout_email(
        self,
        guest_email: str,
        guest_name: str,
        amount: float,
        email_type: str = "payment_link",
        hotel_name: str = "Hotel",
        checkout_url: Optional[str] = None,
        room_number: Optional[str] = None,
        nights: Optional[int] = None,
        check_in_date: Optional[str] = None,
        check_out_date: Optional[str] = None,
        room_charges: Optional[float] = None,
        additional_charges: Optional[List[Dict]] = None,
        transaction_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send checkout email to guest.

        Args:
            guest_email: Guest email address
            guest_name: Guest name
            amount: Payment amount
            email_type: Type of email ('payment_link' or 'receipt')
            hotel_name: Hotel name
            checkout_url: Payment checkout URL
            room_number: Room number
            nights: Number of nights
            check_in_date: Check-in date
            check_out_date: Check-out date
            room_charges: Room charges amount
            additional_charges: List of additional charges
            transaction_id: Transaction ID

        Returns:
            Dict containing success status and email ID
        """
        if not self.api_key:
            logger.warning("RESEND_API_KEY not configured, email will not be sent")
            return {
                "success": False,
                "error": "Email service not configured"
            }

        try:
            email_data = {
                "guest_name": guest_name,
                "amount": amount,
                "hotel_name": hotel_name,
                "checkout_url": checkout_url,
                "room_number": room_number,
                "nights": nights,
                "check_in_date": check_in_date,
                "check_out_date": check_out_date,
                "room_charges": room_charges or 0,
                "additional_charges": additional_charges or [],
                "transaction_id": transaction_id,
            }

            if email_type == "payment_link":
                html_content = self._generate_payment_link_email(email_data)
                subject = f"Payment Link - {hotel_name}"
            else:
                html_content = self._generate_receipt_email(email_data)
                subject = f"Receipt - {hotel_name}"

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    RESEND_API_URL,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "from": self.from_email,
                        "to": [guest_email],
                        "subject": subject,
                        "html": html_content,
                    },
                    timeout=30.0
                )

                if response.status_code != 200:
                    error_data = response.json() if response.text else {}
                    logger.error(f"Email send error: {error_data}")
                    return {
                        "success": False,
                        "error": error_data.get("message", "Failed to send email")
                    }

                result = response.json()

                return {
                    "success": True,
                    "emailId": result.get("id"),
                }

        except httpx.HTTPError as e:
            logger.error(f"HTTP error sending email: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def send_sms(
        self,
        phone_number: str,
        guest_name: str,
        amount: float,
        checkout_url: str,
        hotel_name: str = "Hotel"
    ) -> Dict[str, Any]:
        """
        Send SMS with payment link.

        Note: This is a placeholder. Implement with Twilio or similar service.

        Args:
            phone_number: Guest phone number
            guest_name: Guest name
            amount: Payment amount
            checkout_url: Payment checkout URL
            hotel_name: Hotel name

        Returns:
            Dict containing success status
        """
        # TODO: Implement SMS sending with Twilio
        logger.info(f"SMS would be sent to {phone_number}: {hotel_name} - Pay ${amount:.2f} at {checkout_url}")

        return {
            "success": True,
            "messageId": f"sms_placeholder_{int(datetime.now().timestamp())}",
            "note": "SMS sending not yet implemented. Use Twilio or similar service."
        }


# Singleton instance
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get the singleton email service instance."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service


# For backward compatibility
from datetime import datetime
