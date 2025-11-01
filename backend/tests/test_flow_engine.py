from app.services.flow_engine import process_transition


def base_context():
    return {
        "flow_state": {"stage": "incident", "question_index": 0, "answers": {}},
        "active_incident": "INC-123",
        "active_intent": "incident.report",
    }


def test_incident_to_discovery_transition_allowed():
    context = base_context()
    result = process_transition(
        user_id="tenant-1",
        channel_id="channel-1",
        persona="tenant",
        intent="incident.report",
        message="There's water everywhere in the kitchen.",
        context=context,
    )
    assert result["next_stage"] == "discovery.response"
    assert result["allowed"] is True


def test_tenant_approval_transition_blocked():
    context = base_context()
    context["flow_state"] = {"stage": "discovery", "question_index": 2, "answers": {}}
    result = process_transition(
        user_id="tenant-1",
        channel_id="channel-1",
        persona="tenant",
        intent="discovery.response",
        message="Please approve this now.",
        context=context,
    )
    assert result["next_stage"] == "approval.decision"
    assert result["allowed"] is False
    assert result["violation_message"]
