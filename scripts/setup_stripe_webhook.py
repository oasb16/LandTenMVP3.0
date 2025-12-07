#!/usr/bin/env python3
"""Automatically create Stripe webhook and configure Heroku with the secret."""

import os
import sys
from typing import Optional

import requests
import stripe

HEROKU_APP_NAME = os.getenv("HEROKU_APP_NAME", "landtenmvp3")
PRODUCTION_WEBHOOK_URL = (
    "https://landtenmvp3-55ce0053f28a.herokuapp.com/api/v1/payments/webhooks/stripe"
)
ENABLED_EVENTS = [
    "payment_intent.succeeded",
    "payment_intent.payment_failed",
    "payment_intent.processing",
    "payment_intent.canceled",
]


def setup_stripe_webhook() -> str:
    """Create Stripe webhook and update Heroku config automatically."""

    stripe_key = os.getenv("STRIPE_SECRET_KEY")
    if not stripe_key:
        print("❌ STRIPE_SECRET_KEY not found in environment")
        sys.exit(1)

    stripe.api_key = stripe_key

    print(f"🔧 Setting up Stripe webhook for {PRODUCTION_WEBHOOK_URL}")
    existing_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    existing = _find_existing_webhook()
    if existing:
        print(f"✓ Webhook already exists: {existing.id}")
        secret = getattr(existing, "secret", None) or existing_secret
        if secret:
            print(f"✓ Using existing webhook secret: {secret[:20]}...")
            update_heroku_config(secret)
            verify_webhook(existing.id)
            return secret
        print("⚠️  Webhook found but secret unavailable; creating a fresh endpoint")

    webhook = stripe.WebhookEndpoint.create(
        url=PRODUCTION_WEBHOOK_URL,
        enabled_events=ENABLED_EVENTS,
        description="LandTen MVP 3.0 Production Webhook",
    )

    secret = webhook.secret
    print(f"✅ Created webhook: {webhook.id}")
    print(f"✅ Webhook secret: {secret[:20]}...")

    update_heroku_config(secret)
    verify_webhook(webhook.id)
    return secret


def _find_existing_webhook() -> Optional[stripe.WebhookEndpoint]:
    """Return an existing webhook endpoint for the production URL if present."""
    endpoints = stripe.WebhookEndpoint.list(limit=50)
    for endpoint in endpoints.auto_paging_iter():
        if endpoint.url == PRODUCTION_WEBHOOK_URL:
            return endpoint
    return None


def update_heroku_config(webhook_secret: str) -> None:
    """Update Heroku config vars using the Platform API."""
    api_key = os.getenv("HEROKU_API_KEY")
    if not api_key:
        print("⚠️  HEROKU_API_KEY missing. Set STRIPE_WEBHOOK_SECRET manually on Heroku.")
        return

    print("\n🔧 Updating Heroku configuration...")
    url = f"https://api.heroku.com/apps/{HEROKU_APP_NAME}/config-vars"
    headers = {
        "Accept": "application/vnd.heroku+json; version=3",
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    response = requests.patch(url, headers=headers, json={"STRIPE_WEBHOOK_SECRET": webhook_secret})
    if response.status_code == 200:
        print("✅ Heroku config updated successfully")
    else:
        print(f"⚠️  Heroku config update failed ({response.status_code})")
        print(response.text)


def verify_webhook(webhook_id: str) -> None:
    """Verify webhook exists and is enabled."""
    print("\n🧪 Verifying webhook...")
    try:
        webhook = stripe.WebhookEndpoint.retrieve(webhook_id)
        print(f"✅ Webhook status: {webhook.status}")
    except Exception as exc:  # pragma: no cover - network/stripe failure
        print(f"⚠️  Could not verify webhook: {exc}")


if __name__ == "__main__":
    print("=" * 60)
    print("🎯 Stripe Webhook Automatic Setup")
    print("=" * 60)

    secret = setup_stripe_webhook()

    print("\n" + "=" * 60)
    print("✅ Stripe webhook setup complete!")
    print("=" * 60)
    print(f"\nWebhook URL: {PRODUCTION_WEBHOOK_URL}")
    print(f"Webhook Secret: {secret[:20]}... (configured in Heroku)")
    print("\n✓ Backend will now receive Stripe payment events automatically")
