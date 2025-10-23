"""
Action Framework for Planning (Phase 2: Planning Layer)
Defines executable actions and plans for multi-step task decomposition
"""
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class ActionType(str, Enum):
    """Types of actions the agent can execute"""
    SEARCH_KNOWLEDGE = "search_knowledge"      # RAG search
    GET_CONTACT_INFO = "get_contact_info"      # Extract contact details
    VALIDATE_DATA = "validate_data"            # Check data format
    FORMAT_RESPONSE = "format_response"        # Structure response
    CALL_API = "call_api"                      # External API call (future)
    SEND_EMAIL = "send_email"                  # Email action (future)
    CHECK_CALENDAR = "check_calendar"          # Calendar lookup (future)
    QUERY_CRM = "query_crm"                    # CRM integration (future)
    ASK_CLARIFICATION = "ask_clarification"    # Request more info from user


class Action(BaseModel):
    """Single executable action"""
    type: ActionType
    params: Dict[str, Any] = Field(default_factory=dict)
    description: str = ""
    depends_on: Optional[str] = None  # ID of action this depends on
    parallel_group: Optional[int] = None  # Actions with same group run in parallel
    optional: bool = False  # If True, plan continues even if this action fails


class ActionPlan(BaseModel):
    """Sequence of actions to fulfill user request"""
    query: str
    goal: str
    actions: List[Action]
    estimated_steps: int
    complexity: str = "simple"  # simple, moderate, complex


class ActionResult(BaseModel):
    """Result of executing an action"""
    action_type: ActionType
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    execution_time: float = 0.0
