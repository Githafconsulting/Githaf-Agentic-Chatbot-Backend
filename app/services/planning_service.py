"""
Planning Service (Phase 2: Planning Layer)
Decomposes complex queries into executable action plans using LLM
"""
from typing import Dict, List, Optional
from app.models.action import Action, ActionPlan, ActionResult, ActionType
from app.services.llm_service import generate_response
from app.services.intent_service import Intent
from app.utils.prompts import PLANNING_PROMPT
from app.utils.logger import get_logger
import json
import time

logger = get_logger(__name__)


async def needs_planning(query: str, intent: Intent) -> bool:
    """
    Determine if query requires multi-step planning

    Args:
        query: User query
        intent: Detected intent

    Returns:
        True if planning needed
    """
    # Always plan for unknown/complex intents
    if intent == Intent.UNKNOWN:
        logger.debug(f"Planning needed: Unknown intent")
        return True

    # Check for multi-step indicators
    multi_step_keywords = [
        "first", "then", "after that", "also", "and then",
        "once you", "next", "finally", "followed by",
        "send me", "draft", "schedule", "book", "create",
        "first.*then", "both.*and", "as well as"
    ]

    query_lower = query.lower()
    has_multi_step = any(keyword in query_lower for keyword in multi_step_keywords)

    if has_multi_step:
        logger.debug(f"Planning needed: Multi-step keywords detected")
        return True

    # Check for multiple question marks or "and" separators
    question_count = query.count("?")
    and_count = query_lower.count(" and ")

    if question_count > 1 or and_count >= 2:
        logger.debug(f"Planning needed: Multiple questions/actions ({question_count} questions, {and_count} 'and's)")
        return True

    return False


async def create_plan(query: str, intent: Intent, context: Dict = None) -> ActionPlan:
    """
    Generate action plan for complex query using LLM

    Args:
        query: User query
        intent: Detected intent
        context: Additional context (conversation history, user data, etc.)

    Returns:
        ActionPlan with sequence of actions
    """
    logger.info(f"Creating plan for query: {query[:100]}...")

    # Build planning prompt
    context_text = ""
    if context:
        context_text = f"\nContext: {json.dumps(context, indent=2)}"

    prompt = PLANNING_PROMPT.format(
        query=query,
        intent=intent.value,
        context=context_text
    )

    # Get LLM to generate plan
    plan_text = await generate_response(prompt, max_tokens=500, temperature=0.3)

    # Parse plan from LLM response
    plan = parse_plan_response(plan_text, query)

    logger.info(f"Generated plan with {len(plan.actions)} actions")
    for i, action in enumerate(plan.actions, 1):
        logger.debug(f"  Step {i}: {action.type.value} - {action.description}")

    return plan


def parse_plan_response(text: str, query: str) -> ActionPlan:
    """
    Parse LLM planning response into ActionPlan

    Expected format:
    GOAL: what the plan achieves
    COMPLEXITY: simple|moderate|complex

    STEP 1: ACTION_TYPE
    Description: what this step does
    Params: {"key": "value"}

    STEP 2: ACTION_TYPE
    ...
    """
    lines = text.strip().split("\n")

    goal = "Fulfill user request"
    complexity = "moderate"
    actions = []

    current_action = None

    for line in lines:
        line = line.strip()

        if line.startswith("GOAL:"):
            goal = line.split(":", 1)[1].strip()

        elif line.startswith("COMPLEXITY:"):
            complexity = line.split(":", 1)[1].strip().lower()

        elif line.startswith("STEP"):
            # Save previous action
            if current_action:
                actions.append(current_action)

            # Parse action type from line
            action_type_str = line.split(":", 1)[1].strip() if ":" in line else "SEARCH_KNOWLEDGE"

            # Map string to ActionType
            action_type = map_action_type(action_type_str)

            current_action = Action(
                type=action_type,
                params={},
                description=""
            )

        elif line.startswith("Description:") and current_action:
            current_action.description = line.split(":", 1)[1].strip()

        elif line.startswith("Params:") and current_action:
            try:
                params_str = line.split(":", 1)[1].strip()
                current_action.params = json.loads(params_str)
            except:
                pass

    # Add last action
    if current_action:
        actions.append(current_action)

    # Fallback if no actions parsed
    if not actions:
        logger.warning("No actions parsed from LLM response, using fallback")
        actions = [Action(
            type=ActionType.SEARCH_KNOWLEDGE,
            params={"query": query},
            description="Search knowledge base for answer"
        )]

    return ActionPlan(
        query=query,
        goal=goal,
        actions=actions,
        estimated_steps=len(actions),
        complexity=complexity
    )


def map_action_type(action_str: str) -> ActionType:
    """Map LLM output string to ActionType enum"""
    action_str = action_str.upper().replace(" ", "_")

    mapping = {
        "SEARCH": ActionType.SEARCH_KNOWLEDGE,
        "SEARCH_KNOWLEDGE": ActionType.SEARCH_KNOWLEDGE,
        "SEARCH_KNOWLEDGE_BASE": ActionType.SEARCH_KNOWLEDGE,
        "GET_CONTACT": ActionType.GET_CONTACT_INFO,
        "GET_CONTACT_INFO": ActionType.GET_CONTACT_INFO,
        "VALIDATE": ActionType.VALIDATE_DATA,
        "VALIDATE_DATA": ActionType.VALIDATE_DATA,
        "FORMAT": ActionType.FORMAT_RESPONSE,
        "FORMAT_RESPONSE": ActionType.FORMAT_RESPONSE,
        "SEND_EMAIL": ActionType.SEND_EMAIL,
        "EMAIL": ActionType.SEND_EMAIL,
        "ASK": ActionType.ASK_CLARIFICATION,
        "CLARIFY": ActionType.ASK_CLARIFICATION,
        "ASK_CLARIFICATION": ActionType.ASK_CLARIFICATION,
    }

    return mapping.get(action_str, ActionType.SEARCH_KNOWLEDGE)


async def execute_plan(plan: ActionPlan, session_id: Optional[str] = None) -> Dict:
    """
    Execute action plan step by step

    Args:
        plan: ActionPlan to execute
        session_id: Session ID for context

    Returns:
        Aggregated results from all actions
    """
    logger.info(f"Executing plan: {plan.goal}")

    results = []
    context = {}  # Shared context between actions

    for i, action in enumerate(plan.actions, 1):
        logger.info(f"Executing step {i}/{len(plan.actions)}: {action.type.value}")

        # Execute action
        result = await execute_action(action, context, session_id)
        results.append(result)

        # Update shared context with result
        if result.success and result.data:
            context[action.type.value] = result.data

        # Stop if action failed and it's critical
        if not result.success and not action.optional:
            logger.error(f"Action {action.type.value} failed: {result.error}")
            break

    # Aggregate results into final response
    final_response = await aggregate_results(plan, results)

    return {
        "response": final_response,
        "plan": plan.dict(),
        "results": [r.dict() for r in results],
        "success": all(r.success for r in results)
    }


async def execute_action(
    action: Action,
    context: Dict,
    session_id: Optional[str]
) -> ActionResult:
    """
    Execute single action

    Args:
        action: Action to execute
        context: Shared context from previous actions
        session_id: Session ID

    Returns:
        ActionResult with outcome
    """
    start_time = time.time()

    try:
        if action.type == ActionType.SEARCH_KNOWLEDGE:
            # RAG search
            from app.services.rag_service import get_rag_response

            query = action.params.get("query", "")
            response = await get_rag_response(query, session_id, max_retries=1)  # Limit retries in plans

            return ActionResult(
                action_type=action.type,
                success=response.get("context_found", False),
                data=response,
                execution_time=time.time() - start_time
            )

        elif action.type == ActionType.GET_CONTACT_INFO:
            # Extract contact info from knowledge base
            from app.services.rag_service import get_rag_response

            contact_type = action.params.get("type", "email")
            query = f"what is your {contact_type}?"
            response = await get_rag_response(query, session_id, max_retries=1)

            return ActionResult(
                action_type=action.type,
                success=response.get("context_found", False),
                data={"contact_info": response.get("response", "")},
                execution_time=time.time() - start_time
            )

        elif action.type == ActionType.FORMAT_RESPONSE:
            # Format aggregated data into response
            template = action.params.get("template", "{data}")
            data = action.params.get("data", context)

            # Simple formatting (replace placeholders)
            formatted = template
            for key, value in data.items():
                formatted = formatted.replace(f"{{{key}}}", str(value))

            return ActionResult(
                action_type=action.type,
                success=True,
                data={"formatted": formatted},
                execution_time=time.time() - start_time
            )

        elif action.type == ActionType.ASK_CLARIFICATION:
            # Generate clarification question
            question = action.params.get("question", "Could you provide more details?")

            return ActionResult(
                action_type=action.type,
                success=True,
                data={"clarification": question},
                execution_time=time.time() - start_time
            )

        # Phase 5: Tool Ecosystem - External tool integrations
        elif action.type == ActionType.SEND_EMAIL:
            # Send email via email tool
            try:
                from app.services.tools import get_tool_registry

                registry = get_tool_registry()
                result = await registry.execute_tool("send_email", action.params)

                return ActionResult(
                    action_type=action.type,
                    success=result.get("success", False),
                    data=result,
                    error=result.get("error"),
                    execution_time=time.time() - start_time
                )

            except Exception as e:
                logger.error(f"Error executing email tool: {e}")
                return ActionResult(
                    action_type=action.type,
                    success=False,
                    error=str(e),
                    execution_time=time.time() - start_time
                )

        elif action.type == ActionType.CHECK_CALENDAR:
            # Calendar operations (check availability, schedule)
            try:
                from app.services.tools import get_tool_registry

                registry = get_tool_registry()
                result = await registry.execute_tool("calendar", action.params)

                return ActionResult(
                    action_type=action.type,
                    success=result.get("success", False),
                    data=result,
                    error=result.get("error"),
                    execution_time=time.time() - start_time
                )

            except Exception as e:
                logger.error(f"Error executing calendar tool: {e}")
                return ActionResult(
                    action_type=action.type,
                    success=False,
                    error=str(e),
                    execution_time=time.time() - start_time
                )

        elif action.type == ActionType.QUERY_CRM:
            # CRM operations (get contact, search, log interaction)
            try:
                from app.services.tools import get_tool_registry

                registry = get_tool_registry()
                result = await registry.execute_tool("crm", action.params)

                return ActionResult(
                    action_type=action.type,
                    success=result.get("success", False),
                    data=result,
                    error=result.get("error"),
                    execution_time=time.time() - start_time
                )

            except Exception as e:
                logger.error(f"Error executing CRM tool: {e}")
                return ActionResult(
                    action_type=action.type,
                    success=False,
                    error=str(e),
                    execution_time=time.time() - start_time
                )

        elif action.type == ActionType.CALL_API:
            # Generic API call (web search or custom API)
            try:
                from app.services.tools import get_tool_registry

                # Determine which tool to use based on params
                tool_name = action.params.get("tool", "web_search")

                registry = get_tool_registry()
                result = await registry.execute_tool(tool_name, action.params)

                return ActionResult(
                    action_type=action.type,
                    success=result.get("success", False),
                    data=result,
                    error=result.get("error"),
                    execution_time=time.time() - start_time
                )

            except Exception as e:
                logger.error(f"Error executing API call: {e}")
                return ActionResult(
                    action_type=action.type,
                    success=False,
                    error=str(e),
                    execution_time=time.time() - start_time
                )

        else:
            # Action not implemented yet
            return ActionResult(
                action_type=action.type,
                success=False,
                error=f"Action type {action.type.value} not implemented yet",
                execution_time=time.time() - start_time
            )

    except Exception as e:
        logger.error(f"Error executing action {action.type.value}: {e}")
        return ActionResult(
            action_type=action.type,
            success=False,
            error=str(e),
            execution_time=time.time() - start_time
        )


async def aggregate_results(plan: ActionPlan, results: List[ActionResult]) -> str:
    """
    Aggregate action results into final user-facing response

    Args:
        plan: Original action plan
        results: Results from each action

    Returns:
        Final response text
    """
    # Extract data from successful actions
    data_parts = []

    for result in results:
        if result.success and result.data:
            if result.action_type == ActionType.SEARCH_KNOWLEDGE:
                data_parts.append(result.data.get("response", ""))

            elif result.action_type == ActionType.GET_CONTACT_INFO:
                data_parts.append(result.data.get("contact_info", ""))

            elif result.action_type == ActionType.FORMAT_RESPONSE:
                data_parts.append(result.data.get("formatted", ""))

            elif result.action_type == ActionType.ASK_CLARIFICATION:
                data_parts.append(result.data.get("clarification", ""))

            # Phase 5: Tool Ecosystem results
            elif result.action_type == ActionType.SEND_EMAIL:
                message = result.data.get("message", "Email sent successfully")
                data_parts.append(message)

            elif result.action_type == ActionType.CHECK_CALENDAR:
                # Format calendar results
                if "available_slots" in result.data:
                    slots = result.data["available_slots"]
                    data_parts.append(f"Found {len(slots)} available time slots on {result.data.get('date', 'the requested date')}")
                elif "appointment_id" in result.data:
                    data_parts.append(f"Appointment scheduled successfully")
                elif "appointments" in result.data:
                    apts = result.data["appointments"]
                    data_parts.append(f"Found {len(apts)} upcoming appointments")

            elif result.action_type == ActionType.QUERY_CRM:
                # Format CRM results
                if "contact" in result.data:
                    contact = result.data["contact"]
                    data_parts.append(f"Contact found: {contact.get('name', contact.get('email', 'Unknown'))}")
                elif "contacts" in result.data:
                    contacts = result.data["contacts"]
                    data_parts.append(f"Found {len(contacts)} contacts")

            elif result.action_type == ActionType.CALL_API:
                # Format web search or API results
                if "results" in result.data:
                    results_count = len(result.data["results"])
                    data_parts.append(f"Found {results_count} results from {result.data.get('provider', 'web search')}")

    # Combine parts
    if data_parts:
        return "\n\n".join(data_parts)
    else:
        return "I'm sorry, I wasn't able to complete that request. Could you rephrase or provide more details?"
