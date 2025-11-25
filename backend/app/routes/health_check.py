"""
Health Check Endpoint - System diagnostics and monitoring.
Provides comprehensive health status for Phase Omega components.
"""
import logging
from typing import Dict, Any
from fastapi import APIRouter, Response
from datetime import datetime

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health")
async def health_check():
    """
    Basic health check - returns 200 if service is up.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "LandTen MVP 3.0 - Phase Omega",
    }


@router.get("/health/detailed")
async def detailed_health_check():
    """
    Detailed health check - checks all system components.

    Returns:
        Dict with health status of each component
    """
    health_status = {
        "overall": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {},
    }

    # Check Dynamic Tools Runtime
    try:
        from ..dynamic_tools.tool_runtime import get_dynamic_tool_runtime

        runtime = get_dynamic_tool_runtime()
        tools = runtime.list_tools()

        health_status["components"]["dynamic_tools"] = {
            "status": "healthy",
            "tool_count": len(tools),
        }
    except Exception as e:
        logger.error(f"Dynamic tools health check failed: {e}")
        health_status["components"]["dynamic_tools"] = {
            "status": "unhealthy",
            "error": str(e),
        }
        health_status["overall"] = "degraded"

    # Check Skills Recorder
    try:
        from ..services.auto_evolving_skills import get_skills_recorder

        recorder = get_skills_recorder()
        skill_count = len(recorder.generated_skills)

        health_status["components"]["skills_recorder"] = {
            "status": "healthy",
            "generated_skills": skill_count,
        }
    except Exception as e:
        logger.error(f"Skills recorder health check failed: {e}")
        health_status["components"]["skills_recorder"] = {
            "status": "unhealthy",
            "error": str(e),
        }
        health_status["overall"] = "degraded"

    # Check DynamoDB Connection
    try:
        from ..services.dynamo_service import get_dynamo_service

        dynamo = get_dynamo_service()
        table = dynamo._get_table()

        # Simple check - table exists
        table_name = table.name

        health_status["components"]["dynamodb"] = {
            "status": "healthy",
            "table_name": table_name,
        }
    except Exception as e:
        logger.error(f"DynamoDB health check failed: {e}")
        health_status["components"]["dynamodb"] = {
            "status": "unhealthy",
            "error": str(e),
        }
        health_status["overall"] = "degraded"

    # Check Orchestrator
    try:
        from ..services.orchestrator import get_orchestrator

        orchestrator = get_orchestrator()

        health_status["components"]["orchestrator"] = {
            "status": "healthy",
            "model": orchestrator.model,
        }
    except Exception as e:
        logger.error(f"Orchestrator health check failed: {e}")
        health_status["components"]["orchestrator"] = {
            "status": "unhealthy",
            "error": str(e),
        }
        health_status["overall"] = "degraded"

    return health_status


@router.get("/health/metrics")
async def get_metrics():
    """
    Get system metrics if resilience module is available.

    Returns:
        Dict with all collected metrics
    """
    try:
        from ..services.resilience import get_metrics_collector

        metrics = get_metrics_collector()
        return {
            "status": "success",
            "metrics": metrics.get_summary(),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except ImportError:
        return {
            "status": "unavailable",
            "message": "Resilience module not available",
        }
    except Exception as e:
        logger.error(f"Error fetching metrics: {e}")
        return {
            "status": "error",
            "error": str(e),
        }


@router.get("/health/skills")
async def get_skills_health():
    """
    Get health status of all auto-evolved skills.

    Returns:
        Performance report for all skills
    """
    try:
        from ..services.auto_evolving_skills import get_skill_evolution_engine

        engine = get_skill_evolution_engine()
        report = engine.get_skill_performance_report()

        return {
            "status": "success",
            "report": report,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error fetching skill health: {e}")
        return {
            "status": "error",
            "error": str(e),
        }


@router.post("/health/skills/prune")
async def prune_skills(dry_run: bool = True):
    """
    Prune unused skills from the system.

    Args:
        dry_run: If True, only report what would be pruned without actually pruning

    Returns:
        Pruning report
    """
    try:
        from ..services.auto_evolving_skills import get_skill_evolution_engine

        engine = get_skill_evolution_engine()
        result = engine.prune_unused_skills(dry_run=dry_run)

        return {
            "status": "success",
            "result": result,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error pruning skills: {e}")
        return {
            "status": "error",
            "error": str(e),
        }


@router.get("/health/skills/{skill_name}/optimize")
async def optimize_skill(skill_name: str):
    """
    Get optimization suggestions for a specific skill.

    Args:
        skill_name: Name of the skill to analyze

    Returns:
        Optimization suggestions
    """
    try:
        from ..services.auto_evolving_skills import get_skill_evolution_engine

        engine = get_skill_evolution_engine()
        result = engine.optimize_skill(skill_name)

        return {
            "status": "success",
            "optimization": result,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error optimizing skill: {e}")
        return {
            "status": "error",
            "error": str(e),
        }


@router.get("/health/topic-graphs/{user_id}")
async def get_user_topic_graph_stats(user_id: str):
    """
    Get statistics for a user's topic graph.

    Args:
        user_id: User ID to check

    Returns:
        Topic graph statistics
    """
    try:
        from ..services.incident_topic_graph import get_incident_graph

        graph = get_incident_graph(user_id)

        return {
            "status": "success",
            "stats": {
                "user_id": user_id,
                "total_nodes": len(graph.nodes),
                "total_edges": len(graph.edges),
                "active_incidents": len(graph.active_incidents),
                "categories": list(graph.category_index.keys()),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error fetching topic graph stats: {e}")
        return {
            "status": "error",
            "error": str(e),
        }
