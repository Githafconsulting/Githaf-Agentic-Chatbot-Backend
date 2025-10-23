"""
Agent Metrics API Endpoints
Phase 6: Metrics & Observability
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Dict, Any
from app.services.metrics_service import (
    get_full_dashboard,
    get_metrics_summary,
    get_latency_breakdown,
    get_quality_metrics,
    get_usage_metrics,
    get_agentic_maturity_score
)
from app.core.dependencies import get_current_user
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/metrics", response_model=Dict[str, Any])
async def get_agent_metrics(
    days: int = Query(default=7, ge=1, le=90, description="Number of days to aggregate metrics"),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get comprehensive agent performance metrics

    **Authentication Required:** Admin users only

    **Query Parameters:**
    - days: Number of days to aggregate (1-90, default: 7)

    **Returns:**
    - latency_metrics: Response time breakdown
    - quality_metrics: Validation confidence and success rates
    - usage_metrics: Query volume and distribution
    - agentic_maturity: Overall agentic capability score
    - timestamp: When metrics were generated
    """
    try:
        logger.info(f"Fetching agent metrics for last {days} days")

        dashboard = await get_full_dashboard(days=days)

        logger.info(f"Successfully retrieved agent metrics (agentic_maturity: {dashboard.get('agentic_maturity', {}).get('overall_score', 0):.2f}/10)")

        return dashboard

    except Exception as e:
        logger.error(f"Error fetching agent metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve agent metrics: {str(e)}"
        )


@router.get("/metrics/summary", response_model=Dict[str, Any])
async def get_agent_metrics_summary(
    days: int = Query(default=7, ge=1, le=90),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get quick summary of agent performance

    **Authentication Required:** Admin users only

    **Returns:**
    - Aggregated counts and averages
    - Most recent metrics
    """
    try:
        summary = await get_metrics_summary(days=days)
        return summary

    except Exception as e:
        logger.error(f"Error fetching metrics summary: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve metrics summary: {str(e)}"
        )


@router.get("/metrics/latency", response_model=Dict[str, Any])
async def get_agent_latency_metrics(
    days: int = Query(default=7, ge=1, le=90),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get detailed latency breakdown

    **Authentication Required:** Admin users only

    **Returns:**
    - Average latency per operation (intent, embedding, search, LLM, validation)
    - Total average latency
    - P50, P95, P99 percentiles
    """
    try:
        latency = await get_latency_breakdown(days=days)
        return latency

    except Exception as e:
        logger.error(f"Error fetching latency metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve latency metrics: {str(e)}"
        )


@router.get("/metrics/quality", response_model=Dict[str, Any])
async def get_agent_quality_metrics(
    days: int = Query(default=7, ge=1, le=90),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get quality metrics (validation results)

    **Authentication Required:** Admin users only

    **Returns:**
    - Validation pass rate
    - Average confidence scores
    - Retry statistics
    """
    try:
        quality = await get_quality_metrics(days=days)
        return quality

    except Exception as e:
        logger.error(f"Error fetching quality metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve quality metrics: {str(e)}"
        )


@router.get("/metrics/usage", response_model=Dict[str, Any])
async def get_agent_usage_metrics(
    days: int = Query(default=7, ge=1, le=90),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get usage metrics (query volume)

    **Authentication Required:** Admin users only

    **Returns:**
    - Total query count
    - Queries by intent
    - Query trends over time
    """
    try:
        usage = await get_usage_metrics(days=days)
        return usage

    except Exception as e:
        logger.error(f"Error fetching usage metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve usage metrics: {str(e)}"
        )


@router.get("/metrics/maturity", response_model=Dict[str, Any])
async def get_agent_maturity_score(
    days: int = Query(default=7, ge=1, le=90),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get agentic maturity score (1-10 scale)

    **Authentication Required:** Admin users only

    **Scoring Components:**
    - Perception: Intent classification accuracy
    - Memory: Semantic memory utilization
    - Reasoning: LLM response quality
    - Planning: Multi-step task success
    - Execution: Action completion rate
    - Observation: Validation coverage
    - Self-Improvement: Learning iteration count

    **Returns:**
    - overall_score: Weighted average (1-10)
    - component_scores: Individual capability scores
    - interpretation: Text description of maturity level
    """
    try:
        maturity = await get_agentic_maturity_score(days=days)
        return maturity

    except Exception as e:
        logger.error(f"Error fetching agentic maturity score: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve agentic maturity score: {str(e)}"
        )
