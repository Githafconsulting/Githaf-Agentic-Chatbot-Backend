"""
Meta-Planner Service (Phase 2.5: Reflexive Planning)
Adaptive re-planning when action execution fails
Detects failures and generates alternative strategies using LLM
"""
from typing import Dict, List, Optional, Tuple
from app.models.action import Action, ActionPlan, ActionResult, ActionType
from app.services.llm_service import generate_response
from app.services.planning_service import parse_plan_response
from app.utils.logger import get_logger
import json

logger = get_logger(__name__)

# Maximum replanning attempts to prevent infinite loops
MAX_REPLAN_ATTEMPTS = 2


async def should_replan(
    plan: ActionPlan,
    results: List[ActionResult],
    current_step: int
) -> Tuple[bool, str]:
    """
    Determine if replanning is needed based on execution results

    Args:
        plan: Original action plan
        results: Results from executed actions
        current_step: Current step index in plan

    Returns:
        (should_replan: bool, reason: str)
    """
    # Check if any critical actions failed
    failed_actions = [r for r in results if not r.success]

    if not failed_actions:
        logger.debug("No failed actions, replanning not needed")
        return False, ""

    # Get corresponding actions from plan
    failed_critical = []
    for result in failed_actions:
        # Find the action in plan that matches this result
        for i, action in enumerate(plan.actions):
            if i < len(results) and results[i].action_type == action.type:
                if not action.optional:
                    failed_critical.append((action, result))

    if not failed_critical:
        logger.debug("Only optional actions failed, continuing with current plan")
        return False, ""

    # Build failure reason
    failure_reasons = []
    for action, result in failed_critical:
        reason = f"{action.type.value}: {result.error or 'unknown error'}"
        failure_reasons.append(reason)

    reason = "; ".join(failure_reasons)
    logger.info(f"Replanning needed: {len(failed_critical)} critical actions failed")

    return True, reason


async def generate_alternative_plan(
    original_plan: ActionPlan,
    failed_results: List[ActionResult],
    failure_context: str,
    replan_attempt: int = 0
) -> Optional[ActionPlan]:
    """
    Generate alternative action plan using LLM

    Args:
        original_plan: The original action plan that failed
        failed_results: Results from failed actions
        failure_context: Description of what failed and why
        replan_attempt: Number of previous replan attempts

    Returns:
        Alternative ActionPlan or None if replanning not possible
    """
    logger.info(f"Generating alternative plan (attempt {replan_attempt + 1}/{MAX_REPLAN_ATTEMPTS})")

    # Prevent infinite replanning loops
    if replan_attempt >= MAX_REPLAN_ATTEMPTS:
        logger.warning("Max replan attempts reached, giving up")
        return None

    # Build context for LLM
    original_actions_text = "\n".join([
        f"  - {action.type.value}: {action.description}"
        for action in original_plan.actions
    ])

    failed_actions_text = "\n".join([
        f"  - {result.action_type.value}: {result.error or 'failed'}"
        for result in failed_results if not result.success
    ])

    successful_actions = [r for r in failed_results if r.success]
    successful_text = "\n".join([
        f"  - {result.action_type.value}: succeeded"
        for result in successful_actions
    ]) if successful_actions else "  (none)"

    # Create replanning prompt
    replan_prompt = f"""You are an adaptive AI planner. An action plan has failed and you need to generate an alternative approach.

**Original Goal:**
{original_plan.goal}

**Original Plan:**
{original_actions_text}

**What Succeeded:**
{successful_text}

**What Failed:**
{failed_actions_text}

**Failure Context:**
{failure_context}

**Previous Replan Attempts:**
{replan_attempt}

**Your Task:**
Generate an ALTERNATIVE action plan that:
1. Avoids the failed actions
2. Uses different approaches or fallback strategies
3. Achieves the same goal
4. Does NOT repeat the same failure

**Available Fallback Strategies:**
- If SEARCH_KNOWLEDGE failed → Try GET_CONTACT_INFO or ASK_CLARIFICATION
- If GET_CONTACT_INFO failed → Try SEARCH_KNOWLEDGE with different query
- If SEND_EMAIL failed → Try FORMAT_RESPONSE with instructions for manual sending
- If CHECK_CALENDAR failed → Use ASK_CLARIFICATION to get user input
- If CALL_API failed → Use SEARCH_KNOWLEDGE for cached/offline data

**Output Format:**
GOAL: [revised goal or same goal]
COMPLEXITY: simple|moderate|complex

STEP 1: ACTION_TYPE
Description: what this step does
Params: {{"key": "value"}}

STEP 2: ACTION_TYPE
Description: what this step does
Params: {{"key": "value"}}

Alternative plan:"""

    try:
        # Get LLM to generate alternative plan
        plan_text = await generate_response(replan_prompt, max_tokens=600, temperature=0.5)

        # Parse alternative plan
        alternative_plan = parse_plan_response(plan_text, original_plan.query)

        # Validate alternative plan is different
        if is_identical_plan(original_plan, alternative_plan):
            logger.warning("LLM generated identical plan, forcing fallback strategy")
            alternative_plan = generate_fallback_plan(original_plan, failed_results)

        # Mark as replanned
        alternative_plan.metadata = {
            "replanned": True,
            "replan_attempt": replan_attempt + 1,
            "original_plan_id": original_plan.metadata.get("id"),
            "failure_reason": failure_context
        }

        logger.info(f"Generated alternative plan with {len(alternative_plan.actions)} actions")
        return alternative_plan

    except Exception as e:
        logger.error(f"Error generating alternative plan: {e}")
        return None


def is_identical_plan(plan1: ActionPlan, plan2: ActionPlan) -> bool:
    """Check if two plans are identical (same action types in same order)"""
    if len(plan1.actions) != len(plan2.actions):
        return False

    for a1, a2 in zip(plan1.actions, plan2.actions):
        if a1.type != a2.type:
            return False

    return True


def generate_fallback_plan(
    original_plan: ActionPlan,
    failed_results: List[ActionResult]
) -> ActionPlan:
    """
    Generate a simple fallback plan when LLM fails to replan

    Strategy: Replace failed actions with clarification requests

    Args:
        original_plan: Original plan that failed
        failed_results: Failed action results

    Returns:
        Fallback ActionPlan
    """
    logger.info("Generating fallback plan with clarification strategy")

    fallback_actions = []

    for i, action in enumerate(original_plan.actions):
        if i < len(failed_results) and not failed_results[i].success:
            # Replace failed action with clarification request
            fallback_actions.append(Action(
                type=ActionType.ASK_CLARIFICATION,
                params={
                    "question": f"I encountered an issue completing this step: {action.description}. Could you provide more information or try rephrasing your request?"
                },
                description="Ask user for clarification due to execution failure"
            ))
        else:
            # Keep successful actions
            fallback_actions.append(action)

    return ActionPlan(
        query=original_plan.query,
        goal=f"Request clarification for: {original_plan.goal}",
        actions=fallback_actions,
        estimated_steps=len(fallback_actions),
        complexity="simple"
    )


async def execute_with_replanning(
    plan: ActionPlan,
    session_id: Optional[str] = None,
    max_replans: int = MAX_REPLAN_ATTEMPTS
) -> Dict:
    """
    Execute action plan with automatic replanning on failure

    Args:
        plan: Initial action plan
        session_id: Session ID for context
        max_replans: Maximum number of replanning attempts

    Returns:
        Execution results with replanning history
    """
    from app.services.planning_service import execute_plan

    logger.info(f"Executing plan with replanning capability (max {max_replans} replans)")

    current_plan = plan
    replan_history = []
    replan_count = 0

    while replan_count <= max_replans:
        # Execute current plan
        logger.info(f"Executing plan (attempt {replan_count + 1})")
        result = await execute_plan(current_plan, session_id)

        # Check if replanning is needed
        should_replan_flag, failure_reason = await should_replan(
            current_plan,
            [ActionResult(**r) for r in result["results"]],
            len(result["results"])
        )

        if not should_replan_flag:
            # Success! Return results
            logger.info("Plan executed successfully, no replanning needed")
            result["replanning_history"] = replan_history
            result["total_replan_attempts"] = replan_count
            return result

        # Replanning needed
        logger.warning(f"Plan execution failed: {failure_reason}")

        # Record replan attempt
        replan_history.append({
            "attempt": replan_count + 1,
            "failed_plan": current_plan.dict(),
            "failure_reason": failure_reason,
            "failed_actions": [
                r for r in result["results"]
                if not r["success"]
            ]
        })

        # Generate alternative plan
        failed_results = [ActionResult(**r) for r in result["results"] if not r["success"]]
        alternative_plan = await generate_alternative_plan(
            current_plan,
            failed_results,
            failure_reason,
            replan_count
        )

        if not alternative_plan:
            # Replanning failed, return with error
            logger.error("Unable to generate alternative plan, execution failed")
            result["success"] = False
            result["error"] = "Replanning failed after exhausting all attempts"
            result["replanning_history"] = replan_history
            result["total_replan_attempts"] = replan_count
            return result

        # Use alternative plan for next attempt
        current_plan = alternative_plan
        replan_count += 1

        logger.info(f"Generated alternative plan, retrying execution (attempt {replan_count + 1})")

    # Max replans reached
    logger.error(f"Max replan attempts ({max_replans}) reached, execution failed")

    return {
        "success": False,
        "error": f"Max replan attempts ({max_replans}) reached without success",
        "replanning_history": replan_history,
        "total_replan_attempts": replan_count,
        "final_plan": current_plan.dict()
    }


async def detect_planning_loop(replan_history: List[Dict]) -> bool:
    """
    Detect if replanning is stuck in a loop

    Args:
        replan_history: History of replanning attempts

    Returns:
        True if loop detected
    """
    if len(replan_history) < 2:
        return False

    # Check if last two plans are identical
    last_plan = replan_history[-1]["failed_plan"]
    prev_plan = replan_history[-2]["failed_plan"]

    # Compare action types
    last_actions = [a["type"] for a in last_plan["actions"]]
    prev_actions = [a["type"] for a in prev_plan["actions"]]

    if last_actions == prev_actions:
        logger.warning("Planning loop detected: identical action sequences")
        return True

    return False


async def suggest_manual_intervention(
    plan: ActionPlan,
    failure_reason: str
) -> str:
    """
    Generate suggestion for manual intervention when replanning fails

    Args:
        plan: Failed action plan
        failure_reason: Why the plan failed

    Returns:
        Human-readable suggestion message
    """
    suggestion_prompt = f"""You are a helpful AI assistant. An automated task has failed and manual intervention may be needed.

**Task Goal:**
{plan.goal}

**What Failed:**
{failure_reason}

**Your Task:**
Generate a concise, actionable message for the user explaining:
1. What the system tried to do
2. Why it failed
3. What the user should do next (manual steps)

Keep it under 3 sentences, friendly and professional.

Message:"""

    try:
        suggestion = await generate_response(suggestion_prompt, max_tokens=150, temperature=0.7)
        return suggestion.strip()
    except Exception as e:
        logger.error(f"Error generating manual intervention suggestion: {e}")
        return f"I encountered issues completing your request ({failure_reason}). Please try rephrasing your question or contact support for assistance."
