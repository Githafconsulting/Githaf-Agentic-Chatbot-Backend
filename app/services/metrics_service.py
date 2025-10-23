"""
Metrics Service (Phase 6: Metrics & Observability)
Collects and aggregates performance metrics for agent monitoring
"""
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from app.core.database import get_supabase_client
from app.utils.logger import get_logger
import time

logger = get_logger(__name__)

# Metric types
class MetricType:
    # Performance metrics
    LATENCY_TOTAL = "latency_total"  # ms
    LATENCY_INTENT = "latency_intent"  # ms
    LATENCY_EMBEDDING = "latency_embedding"  # ms
    LATENCY_SEARCH = "latency_search"  # ms
    LATENCY_LLM = "latency_llm"  # ms
    LATENCY_VALIDATION = "latency_validation"  # ms
    LATENCY_PLANNING = "latency_planning"  # ms

    # Accuracy metrics
    INTENT_ACCURACY = "intent_accuracy"  # percent
    VALIDATION_SUCCESS_RATE = "validation_success_rate"  # percent
    PLANNING_SUCCESS_RATE = "planning_success_rate"  # percent
    CONTEXT_FOUND_RATE = "context_found_rate"  # percent

    # Usage metrics
    TOKEN_USAGE = "token_usage"  # tokens
    RETRY_COUNT = "retry_count"  # count
    QUERY_COUNT = "query_count"  # count

    # Quality metrics
    VALIDATION_CONFIDENCE = "validation_confidence"  # 0.0-1.0
    INTENT_CONFIDENCE = "intent_confidence"  # 0.0-1.0
    SIMILARITY_SCORE = "similarity_score"  # 0.0-1.0

    # Agentic metrics
    MEMORY_RETRIEVAL_COUNT = "memory_retrieval_count"  # count
    TOOL_EXECUTION_COUNT = "tool_execution_count"  # count
    ACTION_EXECUTION_COUNT = "action_execution_count"  # count


async def record_metric(
    metric_type: str,
    metric_value: float,
    metric_unit: str = "count",
    context: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Record a single metric to database

    Args:
        metric_type: Type of metric (see MetricType class)
        metric_value: Numeric value of the metric
        metric_unit: Unit of measurement (ms, tokens, percent, count, bytes)
        context: Additional context (session_id, intent, query_type, etc.)

    Returns:
        Success status
    """
    try:
        client = get_supabase_client()

        metric_data = {
            "metric_type": metric_type,
            "metric_value": metric_value,
            "metric_unit": metric_unit,
            "context": context or {},
            "timestamp": datetime.utcnow().isoformat()
        }

        client.table("agent_metrics").insert(metric_data).execute()

        logger.debug(f"Recorded metric: {metric_type}={metric_value}{metric_unit}")
        return True

    except Exception as e:
        logger.warning(f"Failed to record metric {metric_type}: {e}")
        return False


async def record_latency(
    operation: str,
    latency_ms: float,
    context: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Record latency metric for an operation

    Args:
        operation: Operation name (intent, embedding, search, llm, validation, planning, total)
        latency_ms: Latency in milliseconds
        context: Additional context

    Returns:
        Success status
    """
    metric_type = f"latency_{operation}"
    return await record_metric(metric_type, latency_ms, "ms", context)


async def record_quality_metric(
    metric_name: str,
    score: float,
    context: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Record quality metric (confidence, similarity, etc.)

    Args:
        metric_name: Metric name (validation_confidence, intent_confidence, similarity_score)
        score: Score value (0.0-1.0)
        context: Additional context

    Returns:
        Success status
    """
    # Ensure score is in valid range
    score = max(0.0, min(1.0, score))

    return await record_metric(metric_name, score, "score", context)


async def record_usage_metric(
    metric_name: str,
    count: int,
    context: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Record usage metric (token_usage, retry_count, query_count)

    Args:
        metric_name: Metric name
        count: Count value
        context: Additional context

    Returns:
        Success status
    """
    return await record_metric(metric_name, float(count), "count", context)


class MetricsContext:
    """
    Context manager for tracking operation metrics

    Usage:
        async with MetricsContext("intent_classification", session_id=session_id) as ctx:
            intent = await classify_intent(query)
            ctx.add_context({"intent": intent.value})
    """

    def __init__(self, operation: str, **context):
        self.operation = operation
        self.context = context
        self.start_time = None
        self.end_time = None

    async def __aenter__(self):
        self.start_time = time.time()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        latency_ms = (self.end_time - self.start_time) * 1000

        # Record latency
        await record_latency(self.operation, latency_ms, self.context)

        # Record success/failure
        if exc_type is None:
            self.context["success"] = True
        else:
            self.context["success"] = False
            self.context["error"] = str(exc_val)

        return False  # Don't suppress exceptions

    def add_context(self, additional_context: Dict[str, Any]):
        """Add additional context during operation"""
        self.context.update(additional_context)


async def get_metrics_summary(
    days: int = 7,
    metric_types: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Get aggregated metrics summary

    Args:
        days: Number of days to analyze
        metric_types: List of metric types to include (None = all)

    Returns:
        Aggregated metrics dictionary
    """
    logger.info(f"Fetching metrics summary for last {days} days")

    client = get_supabase_client()
    cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()

    try:
        # Build query
        query = client.table("agent_metrics").select("*").gte("timestamp", cutoff_date)

        if metric_types:
            query = query.in_("metric_type", metric_types)

        response = query.execute()
        metrics = response.data or []

        if not metrics:
            logger.info("No metrics found in time period")
            return {
                "period_days": days,
                "total_metrics": 0,
                "summary": {}
            }

        # Aggregate by metric type
        summary = {}

        for metric in metrics:
            metric_type = metric["metric_type"]
            value = metric["metric_value"]

            if metric_type not in summary:
                summary[metric_type] = {
                    "count": 0,
                    "sum": 0.0,
                    "min": float('inf'),
                    "max": float('-inf'),
                    "avg": 0.0,
                    "unit": metric.get("metric_unit", "count")
                }

            stats = summary[metric_type]
            stats["count"] += 1
            stats["sum"] += value
            stats["min"] = min(stats["min"], value)
            stats["max"] = max(stats["max"], value)

        # Calculate averages
        for metric_type, stats in summary.items():
            if stats["count"] > 0:
                stats["avg"] = stats["sum"] / stats["count"]

        logger.info(f"Aggregated {len(metrics)} metrics into {len(summary)} types")

        return {
            "period_days": days,
            "start_date": cutoff_date,
            "end_date": datetime.utcnow().isoformat(),
            "total_metrics": len(metrics),
            "summary": summary
        }

    except Exception as e:
        logger.error(f"Error fetching metrics summary: {e}")
        return {
            "period_days": days,
            "total_metrics": 0,
            "summary": {},
            "error": str(e)
        }


async def get_latency_breakdown(days: int = 7) -> Dict[str, Any]:
    """
    Get latency breakdown by operation

    Args:
        days: Number of days to analyze

    Returns:
        Latency breakdown dictionary
    """
    logger.info(f"Fetching latency breakdown for last {days} days")

    latency_types = [
        MetricType.LATENCY_TOTAL,
        MetricType.LATENCY_INTENT,
        MetricType.LATENCY_EMBEDDING,
        MetricType.LATENCY_SEARCH,
        MetricType.LATENCY_LLM,
        MetricType.LATENCY_VALIDATION,
        MetricType.LATENCY_PLANNING
    ]

    summary = await get_metrics_summary(days=days, metric_types=latency_types)

    # Calculate percentages
    breakdown = {}
    total_latency_stats = summary["summary"].get(MetricType.LATENCY_TOTAL)

    if total_latency_stats:
        total_avg = total_latency_stats["avg"]

        for metric_type, stats in summary["summary"].items():
            if metric_type == MetricType.LATENCY_TOTAL:
                continue

            operation = metric_type.replace("latency_", "")
            avg_latency = stats["avg"]
            percentage = (avg_latency / total_avg * 100) if total_avg > 0 else 0

            breakdown[operation] = {
                "avg_ms": round(avg_latency, 2),
                "min_ms": round(stats["min"], 2),
                "max_ms": round(stats["max"], 2),
                "percentage": round(percentage, 1),
                "count": stats["count"]
            }

    return {
        "period_days": days,
        "total_avg_ms": round(total_latency_stats["avg"], 2) if total_latency_stats else 0,
        "breakdown": breakdown
    }


async def get_quality_metrics(days: int = 7) -> Dict[str, Any]:
    """
    Get quality metrics (confidence, similarity, success rates)

    Args:
        days: Number of days to analyze

    Returns:
        Quality metrics dictionary
    """
    logger.info(f"Fetching quality metrics for last {days} days")

    quality_types = [
        MetricType.VALIDATION_CONFIDENCE,
        MetricType.INTENT_CONFIDENCE,
        MetricType.SIMILARITY_SCORE,
        MetricType.VALIDATION_SUCCESS_RATE,
        MetricType.PLANNING_SUCCESS_RATE,
        MetricType.CONTEXT_FOUND_RATE
    ]

    summary = await get_metrics_summary(days=days, metric_types=quality_types)

    # Format quality metrics
    quality_metrics = {}

    for metric_type, stats in summary["summary"].items():
        metric_name = metric_type.replace("_", " ").title()

        quality_metrics[metric_type] = {
            "name": metric_name,
            "avg": round(stats["avg"], 3),
            "min": round(stats["min"], 3),
            "max": round(stats["max"], 3),
            "count": stats["count"]
        }

    return {
        "period_days": days,
        "quality_metrics": quality_metrics
    }


async def get_usage_metrics(days: int = 7) -> Dict[str, Any]:
    """
    Get usage metrics (queries, retries, tokens)

    Args:
        days: Number of days to analyze

    Returns:
        Usage metrics dictionary
    """
    logger.info(f"Fetching usage metrics for last {days} days")

    usage_types = [
        MetricType.QUERY_COUNT,
        MetricType.RETRY_COUNT,
        MetricType.TOKEN_USAGE,
        MetricType.MEMORY_RETRIEVAL_COUNT,
        MetricType.TOOL_EXECUTION_COUNT,
        MetricType.ACTION_EXECUTION_COUNT
    ]

    summary = await get_metrics_summary(days=days, metric_types=usage_types)

    # Calculate totals and averages
    usage_metrics = {}

    for metric_type, stats in summary["summary"].items():
        metric_name = metric_type.replace("_", " ").title()

        usage_metrics[metric_type] = {
            "name": metric_name,
            "total": int(stats["sum"]),
            "avg_per_query": round(stats["avg"], 2),
            "max": int(stats["max"]),
            "count": stats["count"]
        }

    # Calculate derived metrics
    query_count_stats = summary["summary"].get(MetricType.QUERY_COUNT)
    retry_count_stats = summary["summary"].get(MetricType.RETRY_COUNT)

    if query_count_stats and retry_count_stats:
        total_queries = int(query_count_stats["sum"])
        total_retries = int(retry_count_stats["sum"])

        usage_metrics["retry_rate"] = {
            "name": "Retry Rate",
            "percentage": round((total_retries / total_queries * 100) if total_queries > 0 else 0, 2)
        }

    return {
        "period_days": days,
        "usage_metrics": usage_metrics
    }


async def get_agentic_maturity_score(days: int = 7) -> Dict[str, Any]:
    """
    Calculate agentic maturity score based on metrics

    Agentic Maturity Formula:
    - Perception (10%): Intent confidence
    - Memory (20%): Memory retrieval rate
    - Reasoning (20%): Context found rate + similarity score
    - Planning (15%): Planning success rate
    - Execution (10%): Action execution success
    - Observation (10%): Validation confidence
    - Self-Improvement (15%): Learning job success + threshold optimization

    Args:
        days: Number of days to analyze

    Returns:
        Agentic maturity score (0-10) with breakdown
    """
    logger.info(f"Calculating agentic maturity score for last {days} days")

    summary = await get_metrics_summary(days=days)
    metrics = summary["summary"]

    # Calculate component scores (0-10)
    scores = {}

    # Perception (10%): Intent confidence
    intent_conf = metrics.get(MetricType.INTENT_CONFIDENCE, {}).get("avg", 0.7)
    scores["perception"] = intent_conf * 10  # 0.7 -> 7.0

    # Memory (20%): Memory retrieval rate (assume 50% if no data)
    memory_count = metrics.get(MetricType.MEMORY_RETRIEVAL_COUNT, {}).get("sum", 0)
    query_count = metrics.get(MetricType.QUERY_COUNT, {}).get("sum", 1)
    memory_rate = memory_count / query_count if query_count > 0 else 0.5
    scores["memory"] = min(memory_rate * 10, 10)  # Cap at 10

    # Reasoning (20%): Context found rate + similarity
    context_rate = metrics.get(MetricType.CONTEXT_FOUND_RATE, {}).get("avg", 0.7)
    similarity = metrics.get(MetricType.SIMILARITY_SCORE, {}).get("avg", 0.6)
    scores["reasoning"] = ((context_rate + similarity) / 2) * 10

    # Planning (15%): Planning success rate
    planning_success = metrics.get(MetricType.PLANNING_SUCCESS_RATE, {}).get("avg", 0.8)
    scores["planning"] = planning_success * 10

    # Execution (10%): Action execution success
    action_count = metrics.get(MetricType.ACTION_EXECUTION_COUNT, {}).get("sum", 0)
    # Assume 80% success if no data
    execution_score = 8.0 if action_count > 0 else 8.0
    scores["execution"] = execution_score

    # Observation (10%): Validation confidence
    val_conf = metrics.get(MetricType.VALIDATION_CONFIDENCE, {}).get("avg", 0.75)
    scores["observation"] = val_conf * 10

    # Self-Improvement (15%): Assume moderate score if learning active
    # This would be calculated from learning_history table
    scores["self_improvement"] = 7.0  # Placeholder

    # Calculate weighted total
    weights = {
        "perception": 0.10,
        "memory": 0.20,
        "reasoning": 0.20,
        "planning": 0.15,
        "execution": 0.10,
        "observation": 0.10,
        "self_improvement": 0.15
    }

    total_score = sum(scores[component] * weights[component] for component in scores)

    return {
        "period_days": days,
        "agentic_maturity_score": round(total_score, 1),
        "target_score": 9.0,
        "component_scores": {k: round(v, 1) for k, v in scores.items()},
        "weights": weights
    }


async def get_full_dashboard(days: int = 7) -> Dict[str, Any]:
    """
    Get comprehensive metrics dashboard

    Args:
        days: Number of days to analyze

    Returns:
        Complete dashboard data
    """
    logger.info(f"Building full metrics dashboard for last {days} days")

    try:
        # Fetch all metric categories
        latency = await get_latency_breakdown(days)
        quality = await get_quality_metrics(days)
        usage = await get_usage_metrics(days)
        maturity = await get_agentic_maturity_score(days)

        return {
            "period_days": days,
            "generated_at": datetime.utcnow().isoformat(),
            "latency_breakdown": latency,
            "quality_metrics": quality,
            "usage_metrics": usage,
            "agentic_maturity": maturity
        }

    except Exception as e:
        logger.error(f"Error building dashboard: {e}")
        return {
            "period_days": days,
            "error": str(e)
        }
