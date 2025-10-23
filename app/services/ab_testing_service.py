"""
A/B Testing Service (Phase 3: Self-Improvement Loop)
Compare different RAG strategies and parameters
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from app.core.database import get_supabase_client
from app.utils.logger import get_logger
import random
import hashlib

logger = get_logger(__name__)

# Active A/B tests
ACTIVE_TESTS = {}


class ABTest:
    """A/B test configuration"""

    def __init__(
        self,
        test_id: str,
        name: str,
        variant_a: Dict,
        variant_b: Dict,
        traffic_split: float = 0.5,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ):
        self.test_id = test_id
        self.name = name
        self.variant_a = variant_a
        self.variant_b = variant_b
        self.traffic_split = traffic_split  # % of traffic to variant B
        self.start_date = start_date or datetime.utcnow()
        self.end_date = end_date
        self.active = True

    def assign_variant(self, session_id: str) -> str:
        """
        Assign user to variant based on session_id

        Args:
            session_id: User session identifier

        Returns:
            "A" or "B"
        """
        # Deterministic assignment based on session hash
        hash_val = int(hashlib.md5(session_id.encode()).hexdigest(), 16)
        assignment_value = (hash_val % 100) / 100.0

        if assignment_value < self.traffic_split:
            return "B"
        else:
            return "A"

    def get_variant_params(self, variant: str) -> Dict:
        """Get parameters for assigned variant"""
        if variant == "B":
            return self.variant_b
        else:
            return self.variant_a

    def is_active(self) -> bool:
        """Check if test is currently active"""
        now = datetime.utcnow()

        if not self.active:
            return False

        if self.end_date and now > self.end_date:
            return False

        return True


def create_ab_test(
    test_id: str,
    name: str,
    variant_a: Dict,
    variant_b: Dict,
    traffic_split: float = 0.5,
    duration_days: int = 7
) -> ABTest:
    """
    Create and register new A/B test

    Args:
        test_id: Unique test identifier
        name: Human-readable test name
        variant_a: Control parameters
        variant_b: Treatment parameters
        traffic_split: Percentage to variant B (0.0-1.0)
        duration_days: Test duration in days

    Returns:
        Created ABTest instance
    """
    logger.info(f"Creating A/B test: {name} (ID: {test_id})")

    end_date = datetime.utcnow() + timedelta(days=duration_days)

    test = ABTest(
        test_id=test_id,
        name=name,
        variant_a=variant_a,
        variant_b=variant_b,
        traffic_split=traffic_split,
        end_date=end_date
    )

    ACTIVE_TESTS[test_id] = test

    logger.info(f"A/B test created: {test_id}, ends {end_date.isoformat()}")
    return test


def get_active_test(test_id: str) -> Optional[ABTest]:
    """Get active test by ID"""
    test = ACTIVE_TESTS.get(test_id)
    if test and test.is_active():
        return test
    return None


def assign_to_test(test_id: str, session_id: str) -> Optional[Dict]:
    """
    Assign session to test variant and return parameters

    Args:
        test_id: Test identifier
        session_id: User session ID

    Returns:
        Variant parameters or None if test inactive
    """
    test = get_active_test(test_id)

    if not test:
        return None

    variant = test.assign_variant(session_id)
    params = test.get_variant_params(variant)

    logger.debug(f"Session {session_id[:8]}... assigned to variant {variant} in test {test_id}")

    return {
        "test_id": test_id,
        "variant": variant,
        "params": params
    }


async def get_ab_test_results(test_id: str) -> Dict:
    """
    Calculate A/B test results from feedback data

    Args:
        test_id: Test identifier

    Returns:
        Statistical comparison of variants
    """
    logger.info(f"Calculating results for A/B test: {test_id}")

    test = ACTIVE_TESTS.get(test_id)

    if not test:
        return {
            "error": "Test not found",
            "test_id": test_id
        }

    client = get_supabase_client()

    try:
        # Get feedback within test window
        response = client.table("feedback").select(
            "rating, message_id, created_at"
        ).gte("created_at", test.start_date.isoformat()).execute()

        if test.end_date:
            # Filter by end date (client-side since Supabase filter already applied)
            feedback_data = [
                f for f in response.data or []
                if datetime.fromisoformat(f["created_at"].replace("Z", "+00:00")) <= test.end_date
            ]
        else:
            feedback_data = response.data or []

        if not feedback_data:
            return {
                "test_id": test_id,
                "name": test.name,
                "status": "No data yet",
                "variant_a": {"sample_size": 0, "satisfaction": 0.0},
                "variant_b": {"sample_size": 0, "satisfaction": 0.0}
            }

        # Get session assignments (stored in message metadata)
        message_ids = [f["message_id"] for f in feedback_data]
        messages_response = client.table("messages").select(
            "id, conversation_id"
        ).in_("id", message_ids).execute()

        # Get session IDs from conversations
        conversation_ids = [msg["conversation_id"] for msg in messages_response.data or []]
        conversations_response = client.table("conversations").select(
            "id, session_id"
        ).in_("id", conversation_ids).execute()

        session_map = {conv["id"]: conv["session_id"] for conv in conversations_response.data or []}
        message_session_map = {
            msg["id"]: session_map.get(msg["conversation_id"])
            for msg in messages_response.data or []
        }

        # Separate feedback by variant
        variant_a_ratings = []
        variant_b_ratings = []

        for feedback in feedback_data:
            session_id = message_session_map.get(feedback["message_id"])

            if not session_id:
                continue

            variant = test.assign_variant(session_id)

            if variant == "A":
                variant_a_ratings.append(feedback["rating"])
            else:
                variant_b_ratings.append(feedback["rating"])

        # Calculate metrics
        def calculate_metrics(ratings: List[int]) -> Dict:
            if not ratings:
                return {"sample_size": 0, "satisfaction": 0.0, "feedback_rate": 0.0}

            return {
                "sample_size": len(ratings),
                "satisfaction": sum(ratings) / len(ratings),
                "positive_count": sum(1 for r in ratings if r == 1),
                "negative_count": sum(1 for r in ratings if r == 0)
            }

        metrics_a = calculate_metrics(variant_a_ratings)
        metrics_b = calculate_metrics(variant_b_ratings)

        # Calculate lift
        lift = 0.0
        if metrics_a["satisfaction"] > 0:
            lift = ((metrics_b["satisfaction"] - metrics_a["satisfaction"]) / metrics_a["satisfaction"]) * 100

        # Determine winner
        winner = "Inconclusive"
        if metrics_b["sample_size"] >= 30 and metrics_a["sample_size"] >= 30:
            if metrics_b["satisfaction"] > metrics_a["satisfaction"] * 1.05:  # 5% improvement threshold
                winner = "Variant B"
            elif metrics_a["satisfaction"] > metrics_b["satisfaction"] * 1.05:
                winner = "Variant A"
            else:
                winner = "No significant difference"

        return {
            "test_id": test_id,
            "name": test.name,
            "start_date": test.start_date.isoformat(),
            "end_date": test.end_date.isoformat() if test.end_date else None,
            "variant_a": {
                "name": "Control",
                "params": test.variant_a,
                **metrics_a
            },
            "variant_b": {
                "name": "Treatment",
                "params": test.variant_b,
                **metrics_b
            },
            "lift_percentage": round(lift, 2),
            "winner": winner,
            "recommendation": _generate_recommendation(winner, lift, metrics_a, metrics_b)
        }

    except Exception as e:
        logger.error(f"Error calculating A/B test results: {e}")
        return {
            "error": str(e),
            "test_id": test_id
        }


def _generate_recommendation(winner: str, lift: float, metrics_a: Dict, metrics_b: Dict) -> str:
    """Generate recommendation based on A/B test results"""
    if winner == "Variant B":
        return f"Implement Variant B parameters. Shows {abs(lift):.1f}% improvement over control."
    elif winner == "Variant A":
        return "Keep current parameters (Variant A). Treatment underperformed."
    elif winner == "No significant difference":
        return "Both variants perform similarly. Consider cost/complexity in decision."
    else:
        sample_size = min(metrics_a["sample_size"], metrics_b["sample_size"])
        if sample_size < 30:
            return f"Continue test. Need more data (current: {sample_size}, target: 30+ per variant)."
        else:
            return "Inconclusive results. Consider running test longer or with different parameters."


def stop_ab_test(test_id: str) -> bool:
    """Stop an active A/B test"""
    test = ACTIVE_TESTS.get(test_id)

    if not test:
        logger.warning(f"Test {test_id} not found")
        return False

    test.active = False
    logger.info(f"A/B test {test_id} stopped")
    return True


def list_active_tests() -> List[Dict]:
    """List all active A/B tests"""
    active = []

    for test_id, test in ACTIVE_TESTS.items():
        if test.is_active():
            active.append({
                "test_id": test_id,
                "name": test.name,
                "start_date": test.start_date.isoformat(),
                "end_date": test.end_date.isoformat() if test.end_date else None,
                "traffic_split": test.traffic_split
            })

    return active


# Example: Create default A/B test for threshold comparison
def create_default_threshold_test():
    """Create default test comparing similarity thresholds"""
    create_ab_test(
        test_id="threshold_test_001",
        name="Similarity Threshold Optimization",
        variant_a={"similarity_threshold": 0.5, "top_k": 5},  # Current default
        variant_b={"similarity_threshold": 0.4, "top_k": 7},  # Lower threshold, more results
        traffic_split=0.5,
        duration_days=14
    )

    logger.info("Default A/B test created: Threshold optimization")
