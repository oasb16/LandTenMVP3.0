"""
Unit Tests for Intent Classifier - Multi-Layer Intent Classification

Tests all 4 layers of intent classification:
- Layer 1: Raw Intent Detection
- Layer 2: Flow State Override
- Layer 3: Safety Guard
- Layer 4: Short Message Resolver

These tests ensure the intent classifier respects flow state and prevents
the failures described in the original transcript.
"""

import pytest
from backend.app.services.intent_classifier import (
    IntentClassifier,
    FlowStage,
    get_intent_classifier
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def classifier():
    """Get intent classifier instance."""
    return get_intent_classifier()


@pytest.fixture
def idle_context():
    """Context for idle state."""
    return {
        "flow_state": {
            "stage": FlowStage.IDLE.value,
        },
        "active_incident_id": None,
        "active_job_id": None,
        "persona": "tenant"
    }


@pytest.fixture
def discovery_context():
    """Context for discovery state."""
    return {
        "flow_state": {
            "stage": FlowStage.DISCOVERY.value,
            "question_index": 2,
            "last_ai_prompt": "Where exactly is the issue located?",
            "answers": {"q0": "yes", "q1": "kitchen"}
        },
        "active_incident_id": "INC-123",
        "active_job_id": None,
        "persona": "tenant"
    }


@pytest.fixture
def job_ready_context():
    """Context for job-ready state."""
    return {
        "flow_state": {
            "stage": FlowStage.JOB_READY.value,
            "question_index": 4,
            "last_ai_prompt": "Should I create a work order now?",
            "answers": {"q0": "yes", "q1": "kitchen", "q2": "30 min ago", "q3": "no"}
        },
        "active_incident_id": "INC-123",
        "active_job_id": None,
        "persona": "tenant"
    }


@pytest.fixture
def approval_pending_context():
    """Context for approval pending state."""
    return {
        "flow_state": {
            "stage": FlowStage.APPROVAL_PENDING.value,
            "last_ai_prompt": "Would you like to approve this work order?",
        },
        "active_incident_id": "INC-123",
        "active_job_id": "JOB-456",
        "persona": "landlord"
    }


@pytest.fixture
def job_context():
    """Context for active job state."""
    return {
        "flow_state": {
            "stage": FlowStage.JOB.value,
        },
        "active_incident_id": "INC-123",
        "active_job_id": "JOB-456",
        "persona": "tenant"
    }


# ============================================================================
# Layer 2 Tests: Flow State Override
# ============================================================================

class TestFlowStateOverride:
    """Test Layer 2: Flow State Override."""

    def test_discovery_forces_discovery_response(self, classifier, discovery_context):
        """
        TEST: During discovery, all messages should be classified as discovery.response

        This prevents the bug where "yes" triggers generic fallback.
        """
        # Try various messages that might be misclassified
        test_messages = [
            "yes",
            "ok",
            "the kitchen",
            "about 30 minutes ago",
            "I need help",  # Even "help" should be treated as discovery answer
        ]

        for message in test_messages:
            final_intent, metadata = classifier.classify_with_context(
                message=message,
                raw_intent="general.chat",  # Simulate OpenAI misclassification
                context=discovery_context,
                persona="tenant"
            )

            assert final_intent == "discovery.response", (
                f"Message '{message}' during discovery should be 'discovery.response', "
                f"got '{final_intent}'"
            )

            # Check that override was applied
            layers = metadata.get("layers_applied", [])
            layer2 = layers[0]  # Flow state override is first
            assert layer2["applied"] == True
            assert layer2["layer"] == "flow_state_override"

    def test_discovery_blocks_incident_report(self, classifier, discovery_context):
        """TEST: Cannot report new incident during active discovery."""
        final_intent, metadata = classifier.classify_with_context(
            message="There's also a leak in the bathroom",
            raw_intent="incident.report",
            context=discovery_context,
            persona="tenant"
        )

        # Should be overridden to discovery.response
        assert final_intent != "incident.report"
        assert final_intent == "discovery.response"

        # Check override reason
        layers = metadata.get("layers_applied", [])
        layer2 = layers[0]
        assert "blocked" in layer2["override_reason"]

    def test_job_ready_allows_job_request(self, classifier, job_ready_context):
        """TEST: Job-ready stage allows job.request intent."""
        final_intent, metadata = classifier.classify_with_context(
            message="yes, create the job",
            raw_intent="job.request",
            context=job_ready_context,
            persona="tenant"
        )

        assert final_intent == "job.request"

    def test_approval_pending_blocks_other_intents(self, classifier, approval_pending_context):
        """TEST: During approval, only approval.decision is allowed."""
        test_cases = [
            ("incident.report", "new leak"),
            ("job.request", "create another job"),
            ("general.chat", "hello"),
        ]

        for raw_intent, message in test_cases:
            final_intent, metadata = classifier.classify_with_context(
                message=message,
                raw_intent=raw_intent,
                context=approval_pending_context,
                persona="landlord"
            )

            assert final_intent == "approval.decision", (
                f"During approval, '{raw_intent}' should be overridden to 'approval.decision', "
                f"got '{final_intent}'"
            )


# ============================================================================
# Layer 3 Tests: Safety Guard
# ============================================================================

class TestSafetyGuard:
    """Test Layer 3: Safety Guard."""

    def test_prevents_new_incident_when_active(self, classifier, discovery_context):
        """TEST: Cannot create new incident when one is already active."""
        final_intent, metadata = classifier.classify_with_context(
            message="Emergency! Fire in the kitchen!",
            raw_intent="incident.report",
            context=discovery_context,
            persona="tenant"
        )

        # Should be converted to incident.followup
        assert final_intent == "incident.followup"

        # Check safety guard was applied
        layers = metadata.get("layers_applied", [])
        layer3 = layers[1]  # Safety guard is second layer
        assert layer3["applied"] == True
        assert layer3["layer"] == "safety_guard"
        assert "Cannot create new incident" in layer3["override_reason"]

    def test_prevents_new_job_when_active(self, classifier, job_context):
        """TEST: Cannot create new job when one is already active."""
        final_intent, metadata = classifier.classify_with_context(
            message="Create a new job for the bathroom",
            raw_intent="job.request",
            context=job_context,
            persona="tenant"
        )

        # Should be converted to job.inquiry
        assert final_intent == "job.inquiry"

        # Check safety guard was applied
        layers = metadata.get("layers_applied", [])
        layer3 = layers[1]
        assert layer3["applied"] == True
        assert "Cannot create new job" in layer3["override_reason"]

    def test_allows_incident_when_none_active(self, classifier, idle_context):
        """TEST: Can create incident when none is active."""
        final_intent, metadata = classifier.classify_with_context(
            message="There's a leak in my kitchen",
            raw_intent="incident.report",
            context=idle_context,
            persona="tenant"
        )

        # Should remain incident.report
        assert final_intent == "incident.report"

        # Check safety guard did not override
        layers = metadata.get("layers_applied", [])
        layer3 = layers[1]
        assert layer3["applied"] == False


# ============================================================================
# Layer 4 Tests: Short Message Resolver
# ============================================================================

class TestShortMessageResolver:
    """Test Layer 4: Short Message Resolver."""

    def test_yes_during_discovery(self, classifier, discovery_context):
        """
        TEST: "yes" during discovery becomes discovery.response

        This is the main bug fix from the transcript.
        """
        final_intent, metadata = classifier.classify_with_context(
            message="yes",
            raw_intent="general.chat",  # OpenAI might classify as general
            context=discovery_context,
            persona="tenant"
        )

        assert final_intent == "discovery.response"

        # Check that layer 2 or 4 applied the override
        layers = metadata.get("layers_applied", [])
        assert any(layer["applied"] == True for layer in layers)

    def test_yes_during_job_ready(self, classifier, job_ready_context):
        """
        TEST: "yes" during job-ready becomes job.request

        Tests affirmative_override in job-ready stage.
        """
        final_intent, metadata = classifier.classify_with_context(
            message="yes",
            raw_intent="general.chat",
            context=job_ready_context,
            persona="tenant"
        )

        assert final_intent == "job.request"

        # Check short message resolver was involved
        layers = metadata.get("layers_applied", [])
        # Either layer 2 (stage override) or layer 4 (short message) should apply
        assert any(layer["applied"] == True for layer in layers)

    def test_yes_during_approval(self, classifier, approval_pending_context):
        """
        TEST: "yes" during approval becomes approval.decision

        Tests both affirmative_override and stage blocking.
        """
        final_intent, metadata = classifier.classify_with_context(
            message="yes, approve",
            raw_intent="general.chat",
            context=approval_pending_context,
            persona="landlord"
        )

        assert final_intent == "approval.decision"

    def test_no_during_approval(self, classifier, approval_pending_context):
        """
        TEST: "no" during approval becomes approval.decision (rejected)

        Tests negative_override.
        """
        final_intent, metadata = classifier.classify_with_context(
            message="no",
            raw_intent="general.chat",
            context=approval_pending_context,
            persona="landlord"
        )

        assert final_intent == "approval.decision"

        # Check that decision is marked as rejected
        layers = metadata.get("layers_applied", [])
        layer4 = layers[2]  # Short message resolver
        if layer4["applied"]:
            assert "decision" in layer4 and layer4["decision"] == "rejected"

    def test_affirmative_words(self, classifier, job_ready_context):
        """TEST: Various affirmative words are recognized."""
        affirmative_messages = [
            "yes",
            "yeah",
            "yep",
            "yup",
            "sure",
            "okay",
            "ok",
            "go ahead",
            "do it",
            "proceed",
        ]

        for message in affirmative_messages:
            final_intent, metadata = classifier.classify_with_context(
                message=message,
                raw_intent="general.chat",
                context=job_ready_context,
                persona="tenant"
            )

            assert final_intent == "job.request", (
                f"Affirmative message '{message}' should resolve to 'job.request' "
                f"in job-ready stage, got '{final_intent}'"
            )

    def test_long_message_not_resolved(self, classifier, discovery_context):
        """TEST: Long messages are not treated as short messages."""
        final_intent, metadata = classifier.classify_with_context(
            message="I think the leak is coming from under the sink and it started yesterday",
            raw_intent="discovery.response",
            context=discovery_context,
            persona="tenant"
        )

        # Should keep original intent
        assert final_intent == "discovery.response"

        # Check short message resolver did not apply
        layers = metadata.get("layers_applied", [])
        layer4 = layers[2]
        # Layer 4 might not apply, or applies with "Not a short message"
        if layer4["applied"]:
            assert "Not a short message" in layer4["override_reason"]


# ============================================================================
# Integration Tests: Full Pipeline
# ============================================================================

class TestFullPipeline:
    """Test complete intent classification pipeline."""

    def test_transcript_scenario_1_yes_in_discovery(self, classifier):
        """
        TEST: Reproduce transcript failure scenario #1

        User says "yes" during discovery, should NOT trigger fallback.
        """
        context = {
            "flow_state": {
                "stage": "discovery",
                "question_index": 0,
                "last_ai_prompt": "Is the water still flowing right now?",
                "answers": {}
            },
            "active_incident_id": "INC-789",
            "persona": "tenant"
        }

        final_intent, metadata = classifier.classify_with_context(
            message="yes",
            raw_intent="general.chat",  # Simulating OpenAI misclassification
            context=context,
            persona="tenant"
        )

        # ASSERT: Should be discovery.response, NOT general.chat
        assert final_intent == "discovery.response"
        assert metadata["final_intent"] == "discovery.response"
        assert metadata["stage"] == "discovery"

    def test_transcript_scenario_2_approve_in_job_ready(self, classifier):
        """
        TEST: Reproduce transcript failure scenario #2

        User says "Approve this job" in job-ready, should NOT restart flow.
        """
        context = {
            "flow_state": {
                "stage": "job-ready",
                "question_index": 4,
                "last_ai_prompt": "Should I create a work order now?",
            },
            "active_incident_id": "INC-789",
            "persona": "tenant"
        }

        final_intent, metadata = classifier.classify_with_context(
            message="Approve this job",
            raw_intent="general.chat",  # Simulating misclassification
            context=context,
            persona="tenant"
        )

        # ASSERT: Should be job.request, NOT general.chat
        assert final_intent == "job.request"

    def test_transcript_scenario_3_early_discovery_termination(self, classifier):
        """
        TEST: Reproduce transcript failure scenario #3

        Discovery should not end after just 1 question.
        """
        context = {
            "flow_state": {
                "stage": "discovery",
                "question_index": 1,  # Only asked 1 question
                "last_ai_prompt": "Where exactly is the issue located?",
                "answers": {"q0": "yes"}
            },
            "active_incident_id": "INC-789",
            "persona": "tenant"
        }

        final_intent, metadata = classifier.classify_with_context(
            message="in the kitchen",
            raw_intent="discovery.response",
            context=context,
            persona="tenant"
        )

        # ASSERT: Should stay in discovery
        assert final_intent == "discovery.response"
        assert metadata["stage"] == "discovery"

        # NOTE: The actual termination check happens in the webhook handler
        # based on question_index vs total_questions


# ============================================================================
# Edge Cases
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_missing_flow_state(self, classifier, idle_context):
        """TEST: Handle missing flow_state gracefully."""
        context = {
            # No flow_state
            "active_incident_id": None,
            "persona": "tenant"
        }

        final_intent, metadata = classifier.classify_with_context(
            message="yes",
            raw_intent="general.chat",
            context=context,
            persona="tenant"
        )

        # Should default to idle behavior
        assert final_intent in ["general.chat", "unclear"]

    def test_invalid_stage(self, classifier):
        """TEST: Handle invalid stage gracefully."""
        context = {
            "flow_state": {
                "stage": "invalid_stage",  # Invalid stage
            },
            "persona": "tenant"
        }

        # Should not crash
        try:
            final_intent, metadata = classifier.classify_with_context(
                message="yes",
                raw_intent="general.chat",
                context=context,
                persona="tenant"
            )
            # Should fallback to original intent or general.chat
            assert final_intent in ["general.chat", "unclear"]
        except Exception as e:
            pytest.fail(f"Should not crash on invalid stage: {e}")

    def test_empty_message(self, classifier, discovery_context):
        """TEST: Handle empty message gracefully."""
        final_intent, metadata = classifier.classify_with_context(
            message="",
            raw_intent="unclear",
            context=discovery_context,
            persona="tenant"
        )

        # Should handle empty message
        assert final_intent in ["unclear", "discovery.response"]


# ============================================================================
# Performance Tests
# ============================================================================

class TestPerformance:
    """Test performance characteristics."""

    def test_classification_speed(self, classifier, discovery_context):
        """TEST: Classification should be fast (<100ms)."""
        import time

        start = time.time()

        for _ in range(10):
            classifier.classify_with_context(
                message="yes",
                raw_intent="general.chat",
                context=discovery_context,
                persona="tenant"
            )

        duration = time.time() - start
        avg_duration = duration / 10

        # Should be fast (no OpenAI calls in these tests)
        assert avg_duration < 0.1, f"Classification too slow: {avg_duration*1000:.2f}ms"


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
