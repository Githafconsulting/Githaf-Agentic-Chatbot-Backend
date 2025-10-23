"""
Dialog State Tracking Service
Maintains conversation state to enable context-aware intent detection

This service solves the problem of isolated message processing by tracking
the conversation flow and maintaining state across multiple turns.

Example:
    User: "Hello" → State: GREETING
    User: "I have one more question" → State: AWAITING_QUESTION
    User: "What services do you offer?" → State: ANSWERING
"""
from typing import Dict, Optional, List
from enum import Enum
from app.core.database import get_supabase_client
from app.utils.logger import get_logger
import json

logger = get_logger(__name__)


class DialogState(Enum):
    """
    Conversation states representing the dialog flow

    State Transitions:
    IDLE → GREETING → AWAITING_QUESTION → ANSWERING → FOLLOWUP → CLOSING
    """
    IDLE = "idle"                      # No active conversation
    GREETING = "greeting"              # User initiated with greeting
    AWAITING_QUESTION = "awaiting_q"   # User signaled question intent ("I have a question")
    ANSWERING = "answering"            # Bot provided answer to question
    FOLLOWUP = "followup"              # User asking related/follow-up question
    CLOSING = "closing"                # Conversation ending (farewell)
    HELP = "help"                      # User requested guidance


class ConversationContext:
    """
    Tracks conversation state and metadata for a session

    Attributes:
        session_id: Unique session identifier
        current_state: Current dialog state
        previous_state: Previous dialog state (for state transitions)
        last_intent: Last detected intent
        message_count: Number of messages in conversation
        current_topic: Current topic being discussed (optional)
        metadata: Additional conversation metadata
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.current_state = DialogState.IDLE
        self.previous_state = DialogState.IDLE
        self.last_intent = None
        self.message_count = 0
        self.current_topic = None
        self.metadata = {}

    def to_dict(self) -> Dict:
        """Convert context to dictionary for storage"""
        return {
            "session_id": self.session_id,
            "current_state": self.current_state.value,
            "previous_state": self.previous_state.value,
            "last_intent": self.last_intent,
            "message_count": self.message_count,
            "current_topic": self.current_topic,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ConversationContext":
        """Create context from dictionary"""
        ctx = cls(data["session_id"])
        ctx.current_state = DialogState(data.get("current_state", "idle"))
        ctx.previous_state = DialogState(data.get("previous_state", "idle"))
        ctx.last_intent = data.get("last_intent")
        ctx.message_count = data.get("message_count", 0)
        ctx.current_topic = data.get("current_topic")
        ctx.metadata = data.get("metadata", {})
        return ctx


# In-memory cache for conversation contexts (faster than DB lookup every time)
_context_cache: Dict[str, ConversationContext] = {}


async def get_conversation_context(session_id: str) -> ConversationContext:
    """
    Get or create conversation context for a session

    Args:
        session_id: Session identifier

    Returns:
        ConversationContext object
    """
    # Check cache first (fast path)
    if session_id in _context_cache:
        logger.debug(f"Context cache hit for session {session_id}")
        return _context_cache[session_id]

    # Try to load from database (stored in conversation metadata)
    client = get_supabase_client()

    try:
        response = client.table("conversations").select(
            "metadata"
        ).eq("session_id", session_id).execute()

        if response.data and len(response.data) > 0:
            metadata = response.data[0].get("metadata", {})
            context_data = metadata.get("dialog_context", {})

            if context_data:
                context = ConversationContext.from_dict(context_data)
                _context_cache[session_id] = context
                logger.debug(f"Loaded context from database for session {session_id}")
                return context
    except Exception as e:
        logger.warning(f"Could not load context from database: {e}")

    # Create new context (first message in conversation)
    context = ConversationContext(session_id)
    _context_cache[session_id] = context
    logger.info(f"Created new conversation context for session {session_id}")
    return context


async def update_conversation_state(
    session_id: str,
    new_state: DialogState,
    intent: Optional[str] = None,
    topic: Optional[str] = None
) -> ConversationContext:
    """
    Update conversation state and persist to database

    Args:
        session_id: Session identifier
        new_state: New dialog state
        intent: Detected intent (optional)
        topic: Current topic (optional)

    Returns:
        Updated ConversationContext
    """
    context = await get_conversation_context(session_id)

    # Update state
    context.previous_state = context.current_state
    context.current_state = new_state

    if intent:
        context.last_intent = intent

    if topic:
        context.current_topic = topic

    context.message_count += 1

    # Update cache
    _context_cache[session_id] = context

    # Persist to database (async, non-blocking)
    await save_conversation_context(session_id, context)

    logger.info(f"State transition: {context.previous_state.value} -> {new_state.value} (intent: {intent}, msg: {context.message_count})")

    return context


async def save_conversation_context(session_id: str, context: ConversationContext):
    """
    Save context to database conversation metadata

    Args:
        session_id: Session identifier
        context: ConversationContext to save
    """
    client = get_supabase_client()

    try:
        # Get current conversation
        response = client.table("conversations").select(
            "id, metadata"
        ).eq("session_id", session_id).execute()

        if response.data and len(response.data) > 0:
            conv_id = response.data[0]["id"]
            current_metadata = response.data[0].get("metadata", {})

            # Update metadata with dialog context
            current_metadata["dialog_context"] = context.to_dict()

            # Save back to database
            client.table("conversations").update({
                "metadata": current_metadata
            }).eq("id", conv_id).execute()

            logger.debug(f"Saved context to database for session {session_id}")
    except Exception as e:
        logger.error(f"Error saving conversation context: {e}")


def determine_state_from_intent(
    intent: str,
    query: str,
    current_context: ConversationContext
) -> DialogState:
    """
    Determine next dialog state based on intent and current context

    This is the state machine that governs conversation flow.

    Args:
        intent: Detected intent (GREETING, QUESTION, CHIT_CHAT, etc.)
        query: User's message
        current_context: Current conversation context

    Returns:
        New DialogState
    """
    query_lower = query.lower().strip()

    # STATE MACHINE LOGIC

    # GREETING intent
    if intent == "greeting":
        return DialogState.GREETING

    # FAREWELL intent
    elif intent == "farewell":
        return DialogState.CLOSING

    # HELP intent
    elif intent == "help":
        return DialogState.HELP

    # GRATITUDE intent
    elif intent == "gratitude":
        # If we just answered, stay in answering state
        # Otherwise go to idle
        if current_context.current_state == DialogState.ANSWERING:
            return DialogState.ANSWERING
        return DialogState.IDLE

    # QUESTION intent
    elif intent == "question":
        # Check if it's a follow-up question
        if current_context.current_state in [DialogState.ANSWERING, DialogState.FOLLOWUP]:
            # We just answered a question, this is a follow-up
            return DialogState.FOLLOWUP
        else:
            # First question in conversation
            return DialogState.ANSWERING

    # CHIT_CHAT intent - CONTEXT-DEPENDENT!
    elif intent == "chit_chat":
        # Check for question signals (e.g., "I have a question")
        question_signals = [
            "i have a question", "i have one more question", "i have another question",
            "can i ask", "may i ask", "could i ask",
            "i want to ask", "i'd like to ask", "i would like to ask",
            "another question", "one more question",
            "one more thing", "another thing",
            "also,", "additionally", "also i wanted to",
            "i was wondering", "i wanted to know"
        ]

        if any(signal in query_lower for signal in question_signals):
            # User is signaling they want to ask a question
            logger.info(f"Detected question signal in chit-chat: '{query[:50]}...'")
            return DialogState.AWAITING_QUESTION

        # Check for continuation signals (context-dependent)
        continuation_signals = ["yes", "yeah", "yep", "sure", "okay", "ok", "alright"]

        if query_lower in continuation_signals:
            # If we're waiting for a question, stay in that state
            if current_context.current_state == DialogState.AWAITING_QUESTION:
                return DialogState.AWAITING_QUESTION
            # If we just answered, treat as acknowledgment
            elif current_context.current_state == DialogState.ANSWERING:
                return DialogState.ANSWERING

        # Default: idle chit-chat
        return DialogState.IDLE

    # OUT_OF_SCOPE intent
    elif intent == "out_of_scope":
        return DialogState.IDLE

    # UNCLEAR intent
    elif intent == "unclear":
        # If we're in a conversation flow, stay in current state
        if current_context.current_state in [DialogState.ANSWERING, DialogState.FOLLOWUP]:
            return current_context.current_state
        return DialogState.IDLE

    # Default: maintain current state or go idle
    if current_context.current_state != DialogState.IDLE:
        return current_context.current_state
    return DialogState.IDLE


def get_contextual_response_for_state(state: DialogState, query: str) -> Optional[str]:
    """
    Get appropriate response based on dialog state

    Returns state-specific responses when the state alone determines
    the appropriate answer (without needing RAG).

    Args:
        state: Current dialog state
        query: User's message

    Returns:
        Response string or None if should proceed to RAG/normal intent handling
    """
    if state == DialogState.AWAITING_QUESTION:
        # User signaled question intent, encourage them to ask
        # Examples: "I have a question" → "Of course! What would you like to know?"
        import random
        responses = [
            "Of course! What would you like to know?",
            "Sure! I'm here to help. What's your question?",
            "Absolutely! Go ahead and ask.",
            "I'd be happy to help! What would you like to ask?",
            "Feel free to ask - I'm listening!"
        ]
        return random.choice(responses)

    # For other states, let the normal intent system handle it
    # (greeting, farewell, help, etc. have their own response templates)
    return None


def should_override_intent_with_context(
    current_state: DialogState,
    detected_intent: str,
    query: str
) -> Optional[str]:
    """
    Check if dialog state should override detected intent

    This handles cases where the same message means different things
    in different contexts.

    Args:
        current_state: Current dialog state
        detected_intent: Intent detected by classifier
        query: User's message

    Returns:
        Overridden intent or None if no override needed
    """
    query_lower = query.lower().strip()

    # Case 1: User in AWAITING_QUESTION state
    if current_state == DialogState.AWAITING_QUESTION:
        # They previously said "I have a question"
        # Now ANY message (except greeting/farewell) should be treated as the question

        # Check if it's actually a greeting/farewell (user changed mind)
        if detected_intent in ["greeting", "farewell"]:
            return None  # Don't override, they changed direction

        # Check if it's another question signal (unlikely but possible)
        question_signals = ["i have a question", "can i ask", "i want to ask"]
        if any(signal in query_lower for signal in question_signals):
            return None  # Stay in awaiting_question state

        # Otherwise, treat as QUESTION
        logger.info(f"State override: AWAITING_QUESTION -> treating '{query[:50]}...' as QUESTION")
        return "question"

    # Case 2: User in ANSWERING/FOLLOWUP state with continuation signal
    if current_state in [DialogState.ANSWERING, DialogState.FOLLOWUP]:
        # Check for follow-up signals
        followup_signals = ["also", "additionally", "and", "plus", "furthermore"]
        if any(signal in query_lower[:15] for signal in followup_signals):
            # Likely a follow-up question
            if detected_intent == "chit_chat":
                logger.info(f"State override: In ANSWERING state with 'also/and' -> treating as FOLLOWUP")
                return "question"

    # No override needed
    return None


# Cache cleanup (optional, for long-running servers)
def clear_context_cache():
    """Clear the in-memory context cache (useful for testing or memory management)"""
    global _context_cache
    _context_cache = {}
    logger.info("Cleared conversation context cache")
