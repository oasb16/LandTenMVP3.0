from app.services.ai_reasoning import AIReasoning, Intent


def test_post_process_reasoning_water_leak_fallback():
    reasoning = AIReasoning()
    result = reasoning.post_process_reasoning("there's water everywhere", {}, "tenant")

    assert result["intent"] == Intent.INCIDENT_REPORT.value
    assert result["summary"] == "Severe water leak detected."
    assert "incident" in result["reply"].lower()
    assert result["entities"]["category"] == "plumbing"
    assert result["entities"]["severity"] == "high"
