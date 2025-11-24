"""
Comprehensive Regression Test Suite for LandTen V3 Orchestrator
Tests all critical bugs fixed in the orchestrator system repair.

Run with: pytest backend/tests/test_orchestrator_regression.py -v
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from app.services.orchestrator import LLMOrchestrator
from app.functions.function_registry import create_incident, record_discovery_answer, create_work_order
from app.models.orchestrator_schemas import MetaContext, DiscoveryState, FunctionResult


# ==================== GARBAGE INPUT TESTS ====================

class TestGarbageInputDetection:
    """Test enhanced garbage input detection"""

    @pytest.fixture
    def orchestrator(self):
        return LLMOrchestrator()

    def test_garbage_random_keyboard_mashing(self, orchestrator):
        """Test 1: Random keyboard mashing should be detected as garbage"""
        assert orchestrator._is_garbage_input("asdafd") == True
        assert orchestrator._is_garbage_input("hjkhjk") == True
        assert orchestrator._is_garbage_input("qwerty") == True

    def test_garbage_repeated_words(self, orchestrator):
        """Test 2: Repeated words should be detected as garbage"""
        assert orchestrator._is_garbage_input("why why why why") == True
        assert orchestrator._is_garbage_input("what what what") == True
        assert orchestrator._is_garbage_input("ok ok ok ok ok") == True

    def test_garbage_punctuation_only(self, orchestrator):
        """Test 3: Punctuation-only input should be garbage"""
        assert orchestrator._is_garbage_input("...") == True
        assert orchestrator._is_garbage_input("???") == True
        assert orchestrator._is_garbage_input(".,;") == True
        assert orchestrator._is_garbage_input("!!!!") == True

    def test_garbage_short_nonsense(self, orchestrator):
        """Test 4: Short nonsense should be garbage"""
        assert orchestrator._is_garbage_input("k") == False  # Greeting, not garbage
        assert orchestrator._is_garbage_input("hi") == False  # Greeting
        assert orchestrator._is_garbage_input("ab") == True  # Too short, not greeting

    def test_valid_maintenance_input_not_garbage(self, orchestrator):
        """Test 5: Valid maintenance messages should NOT be garbage"""
        assert orchestrator._is_garbage_input("my sink is leaking") == False
        assert orchestrator._is_garbage_input("garage door broken") == False
        assert orchestrator._is_garbage_input("AC not working") == False
        assert orchestrator._is_garbage_input("there's a leak") == False

    def test_greeting_not_garbage(self, orchestrator):
        """Test 6: Greetings should not be garbage (but also not create incidents)"""
        assert orchestrator._is_garbage_input("hello") == False
        assert orchestrator._is_garbage_input("thanks") == False
        assert orchestrator._is_garbage_input("ok") == False


# ==================== MULTI-INCIDENT TESTS ====================

class TestMultiIncidentHandling:
    """Test handling of multiple incidents and category switching"""

    @pytest.mark.asyncio
    async def test_different_categories_allowed(self):
        """Test 7: Different categories should be allowed as separate incidents"""
        # Mock DynamoDB to return sink incident
        mock_dynamo = Mock()
        mock_dynamo.list_incidents_by_tenant.return_value = [
            {
                "incident_id": "inc_sink123",
                "status": "discovery",
                "category": "plumbing",
                "title": "Sink leak",
                "description": "Kitchen sink is leaking"
            }
        ]
        mock_dynamo.create_incident = Mock()

        with patch("app.functions.function_registry.get_dynamo_service", return_value=mock_dynamo), \
             patch("app.functions.function_registry.get_bot"), \
             patch("app.functions.function_registry.should_ask_discovery_questions", return_value=False):

            # Try to create garage incident (different category)
            result = await create_incident(
                title="Garage door broken",
                description="Garage door won't open",
                category="structural",
                severity="medium",
                urgency="urgent",
                user_id="user123",
                channel_id="channel123"
            )

            assert result.success == True
            assert "incident_id" in result.data

    @pytest.mark.asyncio
    async def test_same_category_similar_blocked(self):
        """Test 8: Same category + similar title should be blocked"""
        mock_dynamo = Mock()
        mock_dynamo.list_incidents_by_tenant.return_value = [
            {
                "incident_id": "inc_sink123",
                "status": "discovery",
                "category": "plumbing",
                "title": "Sink leaking in kitchen",
                "description": "Water dripping from sink"
            }
        ]

        with patch("app.functions.function_registry.get_dynamo_service", return_value=mock_dynamo):

            # Try to create very similar incident
            result = await create_incident(
                title="Kitchen sink leak",
                description="Sink is leaking water",
                category="plumbing",
                severity="medium",
                urgency="urgent",
                user_id="user123",
                channel_id="channel123"
            )

            assert result.success == False
            assert result.error == "duplicate_incident"

    @pytest.mark.asyncio
    async def test_completed_incident_allows_recurrence(self):
        """Test 9: Completed incidents should allow recurrence"""
        mock_dynamo = Mock()
        mock_dynamo.list_incidents_by_tenant.return_value = [
            {
                "incident_id": "inc_old_garage",
                "status": "completed",  # 🔥 Completed status
                "category": "structural",
                "title": "Garage door stuck",
                "description": "Garage door won't open"
            }
        ]
        mock_dynamo.create_incident = Mock()

        with patch("app.functions.function_registry.get_dynamo_service", return_value=mock_dynamo), \
             patch("app.functions.function_registry.get_bot"), \
             patch("app.functions.function_registry.should_ask_discovery_questions", return_value=False):

            # Try to create same incident again (recurrence)
            result = await create_incident(
                title="Garage door stuck again",
                description="Garage door is stuck",
                category="structural",
                severity="medium",
                urgency="urgent",
                user_id="user123",
                channel_id="channel123"
            )

            assert result.success == True  # Should allow recurrence
            assert "incident_id" in result.data


# ==================== DISCOVERY FLOW TESTS ====================

class TestDiscoveryFlow:
    """Test complete discovery Q1-Q5 flow and transitions"""

    @pytest.mark.asyncio
    async def test_discovery_completion_triggers_transition(self):
        """Test 10: Completing Q5 should transition to discovery_complete"""
        mock_dynamo = Mock()
        mock_dynamo.get_incident.return_value = {
            "incident_id": "inc_test",
            "user_id": "user123",
            "category": "plumbing",
            "severity": "medium",
            "description": "Leak",
            "discovery_answers": {
                "q0": "Yes",
                "q1": "Kitchen",
                "q2": "Today",
                "q3": "No"
            }
        }
        mock_dynamo.update_incident_status = Mock(return_value=True)

        with patch("app.functions.function_registry.get_dynamo_service", return_value=mock_dynamo), \
             patch("app.functions.function_registry.get_bot"):

            # Record final answer (Q5)
            result = await record_discovery_answer(
                incident_id="inc_test",
                question_index=4,  # Last question (0-indexed)
                answer="It's flooding",
                channel_id="channel123",
                user_id="user123",
                total_questions=5
            )

            assert result.success == True
            assert result.data["discovery_complete"] == True
            assert result.data["next_stage"] == "diagnosing"

            # Verify status was updated to 'discovery_complete'
            mock_dynamo.update_incident_status.assert_any_call(
                incident_id="inc_test",
                status="discovery_complete",
                user_id="user123"
            )

    @pytest.mark.asyncio
    async def test_discovery_q1_to_q2_progression(self):
        """Test 11: Answering Q1 should trigger Q2"""
        mock_dynamo = Mock()
        mock_dynamo.get_incident.return_value = {
            "incident_id": "inc_test",
            "user_id": "user123",
            "category": "electrical",
            "severity": "high",
            "description": "Outlet sparking",
            "discovery_answers": {}
        }
        mock_dynamo.update_incident_status = Mock(return_value=True)

        with patch("app.functions.function_registry.get_dynamo_service", return_value=mock_dynamo), \
             patch("app.functions.function_registry.get_bot"):

            # Answer Q1
            result = await record_discovery_answer(
                incident_id="inc_test",
                question_index=0,
                answer="Yes, it's happening now",
                channel_id="channel123",
                user_id="user123",
                total_questions=5
            )

            assert result.success == True
            assert result.data["discovery_complete"] == False
            assert result.data["next_question_index"] == 1


# ==================== WORK ORDER TESTS ====================

class TestWorkOrderCreation:
    """Test work order creation flow"""

    @pytest.mark.asyncio
    async def test_work_order_creation_success(self):
        """Test 12: Work order creation should succeed with valid incident"""
        mock_dynamo = Mock()
        mock_dynamo.get_incident.return_value = {
            "incident_id": "inc_test",
            "user_id": "user123",
            "status": "discovery_complete",  # Valid state for work order
            "category": "plumbing",
            "urgency": "urgent",
            "property_id": "prop123",
            "landlord_id": "landlord456"
        }
        mock_dynamo.create_job = Mock()
        mock_dynamo.update_incident_status = Mock()

        with patch("app.functions.function_registry.get_dynamo_service", return_value=mock_dynamo), \
             patch("app.functions.function_registry.get_bot"):

            result = await create_work_order(
                incident_id="inc_test",
                title="Fix sink leak",
                estimated_cost="150.00",
                user_id="user123",
                channel_id="channel123",
                urgency="urgent"
            )

            assert result.success == True
            assert "job_id" in result.data
            assert result.data["incident_id"] == "inc_test"
            mock_dynamo.create_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_work_order_fails_for_completed_incident(self):
        """Test 13: Work order creation should fail for completed incidents"""
        mock_dynamo = Mock()
        mock_dynamo.get_incident.return_value = {
            "incident_id": "inc_closed",
            "status": "completed",  # Incident is closed
            "category": "plumbing"
        }

        with patch("app.functions.function_registry.get_dynamo_service", return_value=mock_dynamo):

            result = await create_work_order(
                incident_id="inc_closed",
                title="Fix leak",
                estimated_cost="100.00",
                user_id="user123",
                channel_id="channel123"
            )

            assert result.success == False
            assert result.error == "Incident is closed"

    @pytest.mark.asyncio
    async def test_work_order_fails_for_missing_incident(self):
        """Test 14: Work order should fail gracefully if incident not found"""
        mock_dynamo = Mock()
        mock_dynamo.get_incident.return_value = None  # Incident doesn't exist

        with patch("app.functions.function_registry.get_dynamo_service", return_value=mock_dynamo):

            result = await create_work_order(
                incident_id="inc_nonexistent",
                title="Fix something",
                estimated_cost="100.00",
                user_id="user123",
                channel_id="channel123"
            )

            assert result.success == False
            assert result.error == "Incident not found"
            assert "not found" in result.message.lower()


# ==================== CATEGORY SWITCHING TESTS ====================

class TestCategorySwitching:
    """Test switching between different incident categories"""

    @pytest.mark.asyncio
    async def test_leak_to_ac_to_garage_switching(self):
        """Test 15: Leak → AC → Garage category switching"""
        # This would be an integration test with full orchestrator
        # For now, we test the duplicate detection logic

        scenarios = [
            # Scenario 1: Plumbing incident active
            {
                "existing": {"category": "plumbing", "status": "discovery", "title": "Sink leak"},
                "new": {"category": "hvac", "title": "AC not cooling"},
                "should_allow": True  # Different category
            },
            # Scenario 2: HVAC incident active
            {
                "existing": {"category": "hvac", "status": "work_order", "title": "AC broken"},
                "new": {"category": "structural", "title": "Garage door stuck"},
                "should_allow": True  # Different category
            },
            # Scenario 3: Same category
            {
                "existing": {"category": "structural", "status": "discovery", "title": "Garage door stuck"},
                "new": {"category": "structural", "title": "Garage door broken"},
                "should_allow": False  # Same category + similar
            }
        ]

        for scenario in scenarios:
            mock_dynamo = Mock()
            mock_dynamo.list_incidents_by_tenant.return_value = [
                {
                    "incident_id": "inc_existing",
                    **scenario["existing"],
                    "description": "Existing issue"
                }
            ]
            mock_dynamo.create_incident = Mock()

            with patch("app.functions.function_registry.get_dynamo_service", return_value=mock_dynamo), \
                 patch("app.functions.function_registry.get_bot"), \
                 patch("app.functions.function_registry.should_ask_discovery_questions", return_value=False):

                result = await create_incident(
                    title=scenario["new"]["title"],
                    description="New issue",
                    category=scenario["new"]["category"],
                    severity="medium",
                    urgency="urgent",
                    user_id="user123",
                    channel_id="channel123"
                )

                if scenario["should_allow"]:
                    assert result.success == True, f"Should allow: {scenario}"
                else:
                    assert result.success == False, f"Should block: {scenario}"


# ==================== STAGE ENUM TESTS ====================

class TestStageEnumValidation:
    """Test that all stages are valid in Pydantic schemas"""

    def test_stage_enum_includes_discovery_complete(self):
        """Test 16: Ensure 'discovery_complete' is valid stage"""
        context = MetaContext(
            user_id="user123",
            channel_id="channel123",
            persona="tenant",
            stage="discovery_complete"  # Should not raise validation error
        )
        assert context.stage == "discovery_complete"

    def test_stage_enum_includes_diagnosing(self):
        """Test 17: Ensure 'diagnosing' is valid stage"""
        context = MetaContext(
            user_id="user123",
            channel_id="channel123",
            persona="tenant",
            stage="diagnosing"  # Should not raise validation error
        )
        assert context.stage == "diagnosing"

    def test_all_stages_valid(self):
        """Test 18: All expected stages should be valid"""
        valid_stages = [
            "idle", "detected", "discovery", "discovery_complete",
            "diagnosing", "work_order", "scheduling", "approval",
            "in_progress", "completed"
        ]

        for stage in valid_stages:
            context = MetaContext(
                user_id="user123",
                channel_id="channel123",
                persona="tenant",
                stage=stage
            )
            assert context.stage == stage


# ==================== DUPLICATE BEHAVIOR TESTS ====================

class TestDuplicateBehavior:
    """Test duplicate incident detection and recurrence"""

    @pytest.mark.asyncio
    async def test_create_incident_then_recurrence_after_close(self):
        """Test 19: Create → Close → Recurrence should work"""
        mock_dynamo = Mock()

        # First call: No existing incidents
        mock_dynamo.list_incidents_by_tenant.return_value = []
        mock_dynamo.create_incident = Mock()

        with patch("app.functions.function_registry.get_dynamo_service", return_value=mock_dynamo), \
             patch("app.functions.function_registry.get_bot"), \
             patch("app.functions.function_registry.should_ask_discovery_questions", return_value=False):

            # Create initial incident
            result1 = await create_incident(
                title="Sink leak",
                description="Water dripping",
                category="plumbing",
                severity="medium",
                urgency="urgent",
                user_id="user123",
                channel_id="channel123"
            )
            assert result1.success == True

        # Second call: Incident is completed
        mock_dynamo.list_incidents_by_tenant.return_value = [
            {
                "incident_id": "inc_old",
                "status": "completed",  # Closed
                "category": "plumbing",
                "title": "Sink leak",
                "description": "Water dripping"
            }
        ]

        with patch("app.functions.function_registry.get_dynamo_service", return_value=mock_dynamo), \
             patch("app.functions.function_registry.get_bot"), \
             patch("app.functions.function_registry.should_ask_discovery_questions", return_value=False):

            # Create recurrence
            result2 = await create_incident(
                title="Sink leak again",
                description="Water still dripping",
                category="plumbing",
                severity="medium",
                urgency="urgent",
                user_id="user123",
                channel_id="channel123"
            )
            assert result2.success == True  # Recurrence allowed

    @pytest.mark.asyncio
    async def test_fingerprint_cache_clears_after_ttl(self):
        """Test 20: Fingerprint cache should clear after TTL"""
        import time
        from app.functions.function_registry import _recent_incidents, _clean_expired_fingerprints, _FINGERPRINT_TTL_SECONDS

        # Manually add fingerprint with old timestamp
        user_id = "user_ttl_test"
        old_timestamp = time.time() - (_FINGERPRINT_TTL_SECONDS + 10)  # 10 seconds past TTL
        _recent_incidents[user_id]["old_fingerprint"] = old_timestamp

        # Add recent fingerprint
        recent_timestamp = time.time()
        _recent_incidents[user_id]["recent_fingerprint"] = recent_timestamp

        # Clean expired
        _clean_expired_fingerprints(user_id)

        # Old fingerprint should be removed
        assert "old_fingerprint" not in _recent_incidents[user_id]
        # Recent fingerprint should remain
        assert "recent_fingerprint" in _recent_incidents[user_id]


# ==================== SUMMARY ====================

def test_summary():
    """Test 0: Summary of test coverage"""
    print("\n" + "="*60)
    print("REGRESSION TEST SUITE SUMMARY")
    print("="*60)
    print("\n✅ Garbage Input Tests (6 tests)")
    print("   - Random keyboard mashing (asdafd)")
    print("   - Repeated words (why why why)")
    print("   - Punctuation only (..., ???)")
    print("   - Short nonsense")
    print("   - Valid maintenance input")
    print("   - Greetings")
    print("\n✅ Multi-Incident Tests (3 tests)")
    print("   - Different categories allowed")
    print("   - Same category + similar blocked")
    print("   - Completed incident allows recurrence")
    print("\n✅ Discovery Flow Tests (2 tests)")
    print("   - Q5 completion triggers discovery_complete")
    print("   - Q1→Q2 progression")
    print("\n✅ Work Order Tests (3 tests)")
    print("   - Creation succeeds with valid incident")
    print("   - Fails for completed incident")
    print("   - Fails gracefully for missing incident")
    print("\n✅ Category Switching Tests (1 test)")
    print("   - Leak → AC → Garage switching")
    print("\n✅ Stage Enum Tests (3 tests)")
    print("   - discovery_complete valid")
    print("   - diagnosing valid")
    print("   - All stages valid")
    print("\n✅ Duplicate Behavior Tests (2 tests)")
    print("   - Create → Close → Recurrence")
    print("   - Fingerprint cache TTL")
    print("\n" + "="*60)
    print(f"TOTAL: 20 comprehensive regression tests")
    print("="*60 + "\n")


if __name__ == "__main__":
    test_summary()
    print("\nRun tests with: pytest backend/tests/test_orchestrator_regression.py -v")
