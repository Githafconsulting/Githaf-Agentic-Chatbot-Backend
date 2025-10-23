"""
Analytics service for metrics calculation
"""
from typing import Dict, List, Any
from datetime import datetime, timedelta
from app.core.database import get_supabase_client
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def get_conversation_metrics() -> Dict[str, Any]:
    """
    Get conversation-related metrics

    Returns:
        Dict: Conversation metrics
    """
    try:
        client = get_supabase_client()

        # Total conversations
        total_conv_response = client.table("conversations").select("id", count="exact").execute()
        total_conversations = total_conv_response.count if total_conv_response.count else 0

        # Total messages
        total_msg_response = client.table("messages").select("id", count="exact").execute()
        total_messages = total_msg_response.count if total_msg_response.count else 0

        # Average messages per conversation
        avg_messages = total_messages / total_conversations if total_conversations > 0 else 0

        # Conversations today
        today = datetime.utcnow().date().isoformat()
        today_conv_response = client.table("conversations").select(
            "id", count="exact"
        ).gte("created_at", today).execute()
        conversations_today = today_conv_response.count if today_conv_response.count else 0

        # Calculate average conversation duration
        avg_duration_seconds = 0
        try:
            # Get all conversations with their created_at and last_message_at timestamps
            conversations_response = client.table("conversations").select(
                "created_at, last_message_at"
            ).execute()

            conversations_data = conversations_response.data if conversations_response.data else []

            if conversations_data:
                total_duration_seconds = 0
                valid_conversations = 0

                for conv in conversations_data:
                    created_at = conv.get("created_at")
                    last_message_at = conv.get("last_message_at")

                    if created_at and last_message_at:
                        # Parse timestamps
                        start_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        end_time = datetime.fromisoformat(last_message_at.replace('Z', '+00:00'))

                        # Calculate duration in seconds
                        duration = (end_time - start_time).total_seconds()

                        # Only count conversations with positive duration
                        if duration > 0:
                            total_duration_seconds += duration
                            valid_conversations += 1

                # Calculate average
                if valid_conversations > 0:
                    avg_duration_seconds = total_duration_seconds / valid_conversations

        except Exception as duration_error:
            logger.warning(f"Error calculating conversation duration: {duration_error}")
            avg_duration_seconds = 0

        # Calculate average active chat time (time between consecutive messages)
        avg_active_chat_seconds = 0
        try:
            # Get all conversations
            conversations_response = client.table("conversations").select("id").execute()
            conversation_ids = [conv["id"] for conv in conversations_response.data] if conversations_response.data else []

            if conversation_ids:
                total_active_time = 0
                conversations_with_activity = 0

                for conv_id in conversation_ids:
                    # Get messages for this conversation, ordered by time
                    messages_response = client.table("messages").select(
                        "created_at"
                    ).eq("conversation_id", conv_id).order("created_at", desc=False).execute()

                    messages = messages_response.data if messages_response.data else []

                    # Need at least 2 messages to calculate active time
                    if len(messages) >= 2:
                        conversation_active_time = 0

                        for i in range(1, len(messages)):
                            prev_msg_time = datetime.fromisoformat(messages[i-1]["created_at"].replace('Z', '+00:00'))
                            curr_msg_time = datetime.fromisoformat(messages[i]["created_at"].replace('Z', '+00:00'))

                            # Calculate time gap between consecutive messages
                            gap_seconds = (curr_msg_time - prev_msg_time).total_seconds()

                            # Only count gaps up to 5 minutes (300 seconds) as "active" time
                            # Gaps longer than 5 minutes indicate user left and came back
                            if 0 < gap_seconds <= 300:
                                conversation_active_time += gap_seconds

                        if conversation_active_time > 0:
                            total_active_time += conversation_active_time
                            conversations_with_activity += 1

                # Calculate average active chat time
                if conversations_with_activity > 0:
                    avg_active_chat_seconds = total_active_time / conversations_with_activity

        except Exception as active_time_error:
            logger.warning(f"Error calculating active chat time: {active_time_error}")
            avg_active_chat_seconds = 0

        return {
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "avg_messages_per_conversation": round(avg_messages, 2),
            "conversations_today": conversations_today,
            "avg_conversation_duration_seconds": round(avg_duration_seconds, 2),
            "avg_active_chat_time_seconds": round(avg_active_chat_seconds, 2)
        }

    except Exception as e:
        logger.error(f"Error getting conversation metrics: {e}")
        return {
            "total_conversations": 0,
            "total_messages": 0,
            "avg_messages_per_conversation": 0,
            "conversations_today": 0,
            "avg_conversation_duration_seconds": 0,
            "avg_active_chat_time_seconds": 0
        }


async def get_satisfaction_metrics() -> Dict[str, Any]:
    """
    Get user satisfaction metrics

    Returns:
        Dict: Satisfaction metrics
    """
    try:
        client = get_supabase_client()

        # Total feedback
        total_feedback_response = client.table("feedback").select("*").execute()
        feedback_list = total_feedback_response.data if total_feedback_response.data else []

        total_feedback = len(feedback_list)

        if total_feedback == 0:
            return {
                "avg_rating": 0,
                "total_feedback": 0,
                "positive_feedback": 0,
                "negative_feedback": 0,
                "satisfaction_rate": 0
            }

        # Calculate metrics
        # Rating is 0 (thumbs down) or 1 (thumbs up) in our system
        ratings = [f["rating"] for f in feedback_list]

        # Calculate average satisfaction (0-1 scale)
        avg_satisfaction = sum(ratings) / len(ratings)

        # Count positive (1) and negative (0) feedback
        positive_feedback = len([r for r in ratings if r == 1])
        negative_feedback = len([r for r in ratings if r == 0])

        # Feedback rate: percentage of messages that received feedback
        total_messages_response = client.table("messages").select("id", count="exact").eq("role", "assistant").execute()
        total_assistant_messages = total_messages_response.count if total_messages_response.count else 0
        feedback_rate = (total_feedback / total_assistant_messages) if total_assistant_messages > 0 else 0

        return {
            "avg_satisfaction": round(avg_satisfaction, 2),
            "feedback_rate": round(feedback_rate, 2),
            "total_feedback": total_feedback,
            "positive_feedback": positive_feedback,
            "negative_feedback": negative_feedback
        }

    except Exception as e:
        logger.error(f"Error getting satisfaction metrics: {e}")
        return {
            "avg_satisfaction": 0,
            "feedback_rate": 0,
            "total_feedback": 0,
            "positive_feedback": 0,
            "negative_feedback": 0
        }


async def get_trending_queries(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get trending/common queries grouped by intent

    Args:
        limit: Number of trending intents to return

    Returns:
        List[Dict]: Trending intents with sample queries
    """
    try:
        from app.services.intent_service import classify_intent_hybrid

        client = get_supabase_client()

        # Get all user messages from last 30 days
        thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).isoformat()

        response = client.table("messages").select("content").eq(
            "role", "user"
        ).gte("created_at", thirty_days_ago).execute()

        messages = response.data if response.data else []

        # Group queries by intent
        intent_groups = {}

        for msg in messages:
            content = msg.get("content", "").strip()

            # Skip very short queries or conversational intents
            if len(content) < 3:
                continue

            try:
                # Classify intent (using pattern matching only for speed - no LLM fallback)
                # Note: We suppress verbose logging for batch operations
                import logging
                intent_logger = logging.getLogger("githaf_chatbot.app.services.intent_service")
                original_level = intent_logger.level
                intent_logger.setLevel(logging.WARNING)  # Suppress INFO logs during batch classification

                intent, confidence = await classify_intent_hybrid(content, use_llm_fallback=False)
                intent_str = intent.value

                intent_logger.setLevel(original_level)  # Restore original log level

                # Only track QUESTION intents for trending (skip greetings, thanks, etc.)
                if intent_str not in ["question", "unknown"]:
                    continue

                # Initialize intent group if not exists
                if intent_str not in intent_groups:
                    intent_groups[intent_str] = {
                        "queries": [],
                        "count": 0
                    }

                # Add query to intent group
                intent_groups[intent_str]["queries"].append(content)
                intent_groups[intent_str]["count"] += 1

            except Exception as classify_error:
                logger.debug(f"Failed to classify query: {content[:50]}... Error: {classify_error}")
                continue

        # For QUESTION intent, we need more granular grouping by topic
        # Use semantic similarity or keyword extraction
        if "question" in intent_groups:
            question_queries = intent_groups["question"]["queries"]

            # Group questions by topic using simple keyword matching
            topic_groups = await _group_queries_by_topic(question_queries)

            # Replace flat question group with topic-based groups
            del intent_groups["question"]
            intent_groups.update(topic_groups)

        # Sort by frequency
        sorted_intents = sorted(
            intent_groups.items(),
            key=lambda x: x[1]["count"],
            reverse=True
        )

        # Format results with sample queries
        trending = []
        for intent_name, data in sorted_intents[:limit]:
            # Get top 3 unique sample queries (different phrasings)
            sample_queries = list(set(data["queries"]))[:3]

            # Create readable intent label
            intent_label = intent_name.replace("_", " ").title()

            trending.append({
                "intent": intent_name,
                "query": intent_label,  # Display name for frontend
                "count": data["count"],
                "sample_queries": sample_queries,
                "avg_rating": None  # TODO: Join with feedback if needed
            })

        return trending

    except Exception as e:
        logger.error(f"Error getting trending queries: {e}")
        return []


async def _group_queries_by_topic(queries: List[str]) -> Dict[str, Dict]:
    """
    Group questions by topic using keyword matching

    Args:
        queries: List of question queries

    Returns:
        Dict mapping topic names to query groups
    """
    # Define topic keywords
    topics = {
        "services": ["service", "services", "offer", "provide", "do you do", "specialize", "expertise"],
        "pricing": ["price", "pricing", "cost", "costs", "how much", "expensive", "rate", "rates", "fee", "fees", "payment"],
        "contact": ["contact", "email", "phone", "call", "reach", "address", "location", "office", "where"],
        "hours": ["hours", "open", "available", "availability", "schedule", "when", "time"],
        "process": ["process", "how do", "how does", "work", "steps", "procedure", "workflow"],
        "technology": ["technology", "technologies", "tech", "tools", "framework", "platform", "stack"],
        "support": ["support", "help", "assist", "problem", "issue", "trouble", "fix"],
        "team": ["team", "who", "employees", "staff", "people", "experience", "experts"],
        "projects": ["project", "projects", "portfolio", "work", "clients", "case study", "examples"],
    }

    topic_groups = {}
    unmatched = []

    for query in queries:
        query_lower = query.lower()
        matched = False

        # Try to match to a topic
        for topic_name, keywords in topics.items():
            if any(keyword in query_lower for keyword in keywords):
                if topic_name not in topic_groups:
                    topic_groups[topic_name] = {
                        "queries": [],
                        "count": 0
                    }
                topic_groups[topic_name]["queries"].append(query)
                topic_groups[topic_name]["count"] += 1
                matched = True
                break

        if not matched:
            unmatched.append(query)

    # Add unmatched queries as "general" category if significant
    if len(unmatched) > 0:
        topic_groups["general_questions"] = {
            "queries": unmatched,
            "count": len(unmatched)
        }

    return topic_groups


async def get_knowledge_base_metrics() -> Dict[str, Any]:
    """
    Get knowledge base metrics

    Returns:
        Dict: Knowledge base metrics
    """
    try:
        client = get_supabase_client()

        # Total documents
        docs_response = client.table("documents").select("id", count="exact").execute()
        total_documents = docs_response.count if docs_response.count else 0

        # Total chunks/embeddings
        embeddings_response = client.table("embeddings").select("id", count="exact").execute()
        total_chunks = embeddings_response.count if embeddings_response.count else 0

        # Documents added this month
        this_month = datetime.utcnow().replace(day=1).isoformat()
        month_docs_response = client.table("documents").select(
            "id", count="exact"
        ).gte("created_at", this_month).execute()
        documents_added_this_month = month_docs_response.count if month_docs_response.count else 0

        return {
            "total_documents": total_documents,
            "total_chunks": total_chunks,
            "documents_added_this_month": documents_added_this_month
        }

    except Exception as e:
        logger.error(f"Error getting knowledge base metrics: {e}")
        return {
            "total_documents": 0,
            "total_chunks": 0,
            "documents_added_this_month": 0
        }


async def get_flagged_queries(limit: int = 20) -> List[Dict[str, Any]]:
    """
    Get all feedback (both positive and negative) with queries and responses

    Args:
        limit: Maximum number of feedback entries

    Returns:
        List[Dict]: Feedback entries with user queries and bot responses
    """
    try:
        client = get_supabase_client()

        # Get ALL feedback (both thumbs up and thumbs down)
        # No rating filter - frontend will handle filtering
        feedback_response = client.table("feedback").select(
            "*, messages(*)"
        ).order("created_at", desc=True).limit(limit).execute()

        flagged = []

        if feedback_response.data:
            for item in feedback_response.data:
                # Get the rated message (this is the assistant's response)
                rated_message = item.get("messages", {})
                if not rated_message:
                    continue

                conversation_id = rated_message.get("conversation_id")
                message_id = str(item.get("message_id", ""))

                # The rated message is the assistant's response
                bot_response = rated_message.get("content", "")

                # Find the user query (the message before this assistant response)
                user_query = ""
                if conversation_id:
                    # Get messages from this conversation before the rated message
                    conv_messages_response = client.table("messages").select(
                        "content, role, created_at"
                    ).eq("conversation_id", conversation_id).lt(
                        "created_at", rated_message.get("created_at")
                    ).order("created_at", desc=True).limit(1).execute()

                    if conv_messages_response.data and len(conv_messages_response.data) > 0:
                        last_message = conv_messages_response.data[0]
                        if last_message.get("role") == "user":
                            user_query = last_message.get("content", "")

                flagged.append({
                    "feedback_id": str(item.get("id", "")),  # Actual feedback ID for soft-delete
                    "message_id": message_id,
                    "conversation_id": str(conversation_id) if conversation_id else None,
                    "query": user_query,  # User's question
                    "response": bot_response,  # Bot's answer
                    "rating": item.get("rating"),  # 0 = thumbs down, 1 = thumbs up
                    "comment": item.get("comment"),  # Optional user comment
                    "created_at": item.get("created_at"),
                    "reason": "User feedback"
                })

        logger.info(f"Retrieved {len(flagged)} feedback entries")
        return flagged

    except Exception as e:
        logger.error(f"Error getting flagged queries: {e}")
        return []


async def get_analytics_overview() -> Dict[str, Any]:
    """
    Get complete analytics overview

    Returns:
        Dict: Complete analytics data
    """
    try:
        conversation_metrics = await get_conversation_metrics()
        satisfaction_metrics = await get_satisfaction_metrics()
        trending_queries = await get_trending_queries(limit=10)
        knowledge_base_metrics = await get_knowledge_base_metrics()

        return {
            "conversation_metrics": conversation_metrics,
            "satisfaction_metrics": satisfaction_metrics,
            "trending_queries": trending_queries,
            "knowledge_base_metrics": knowledge_base_metrics,
            "last_updated": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting analytics overview: {e}")
        raise


async def get_daily_stats(start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    Get daily conversation statistics for a date range

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        List[Dict]: Daily statistics
    """
    try:
        # Validate dates
        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date)

        if start_dt > end_dt:
            raise ValueError("Start date must be before or equal to end date")

        client = get_supabase_client()

        # Get conversations in date range
        conversations_response = client.table("conversations").select(
            "id, created_at"
        ).gte("created_at", start_date).lte("created_at", f"{end_date}T23:59:59").execute()

        conversations = conversations_response.data if conversations_response.data else []

        # Get messages in date range
        messages_response = client.table("messages").select(
            "id, created_at, conversation_id"
        ).gte("created_at", start_date).lte("created_at", f"{end_date}T23:59:59").execute()

        messages = messages_response.data if messages_response.data else []

        # Get feedback in date range
        feedback_response = client.table("feedback").select(
            "rating, created_at"
        ).gte("created_at", start_date).lte("created_at", f"{end_date}T23:59:59").execute()

        feedback_list = feedback_response.data if feedback_response.data else []

        # Group by date
        daily_data = {}

        # Initialize all dates in range with zeros
        current_date = start_dt
        while current_date <= end_dt:
            date_str = current_date.strftime("%Y-%m-%d")
            daily_data[date_str] = {
                "date": date_str,
                "conversations": 0,
                "messages": 0,
                "avg_satisfaction": 0,
                "ratings": []
            }
            current_date += timedelta(days=1)

        # Count conversations by date
        for conv in conversations:
            date_str = conv["created_at"][:10]
            if date_str in daily_data:
                daily_data[date_str]["conversations"] += 1

        # Count messages by date
        for msg in messages:
            date_str = msg["created_at"][:10]
            if date_str in daily_data:
                daily_data[date_str]["messages"] += 1

        # Calculate satisfaction by date
        for fb in feedback_list:
            date_str = fb["created_at"][:10]
            if date_str in daily_data:
                daily_data[date_str]["ratings"].append(fb["rating"])

        # Calculate average satisfaction
        for date_str, data in daily_data.items():
            if data["ratings"]:
                data["avg_satisfaction"] = round(sum(data["ratings"]) / len(data["ratings"]), 2)
            del data["ratings"]  # Remove temporary ratings list

        # Convert to sorted list
        daily_stats = sorted(daily_data.values(), key=lambda x: x["date"])

        logger.info(f"Generated daily stats for {len(daily_stats)} days")
        return daily_stats

    except ValueError as e:
        logger.error(f"Date validation error: {e}")
        raise
    except Exception as e:
        logger.error(f"Error getting daily stats: {e}")
        return []


async def get_country_stats(start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
    """
    Get visitor country statistics with real geo-location data

    Args:
        start_date: Optional start date (YYYY-MM-DD)
        end_date: Optional end date (YYYY-MM-DD)

    Returns:
        List[Dict]: Country statistics with visitor counts and percentages
    """
    try:
        client = get_supabase_client()

        # Build query based on date range
        query = client.table("conversations").select("country_code, country_name")

        if start_date:
            query = query.gte("created_at", start_date)
        if end_date:
            query = query.lte("created_at", f"{end_date}T23:59:59")

        response = query.execute()
        conversations = response.data if response.data else []

        if not conversations:
            return []

        # Count conversations by country
        country_counts = {}
        total_visitors = len(conversations)

        for conv in conversations:
            country_code = conv.get("country_code") or "UNKNOWN"
            country_name = conv.get("country_name") or "Unknown"

            key = f"{country_code}|{country_name}"
            country_counts[key] = country_counts.get(key, 0) + 1

        # Build result list with percentages
        country_stats = []
        for key, count in country_counts.items():
            country_code, country_name = key.split("|")
            percentage = (count / total_visitors * 100) if total_visitors > 0 else 0

            country_stats.append({
                "country_code": country_code,
                "country_name": country_name,
                "visitors": count,
                "percentage": round(percentage, 1)
            })

        # Sort by visitor count (descending)
        country_stats.sort(key=lambda x: x["visitors"], reverse=True)

        logger.info(f"Retrieved country stats: {len(country_stats)} countries, {total_visitors} total visitors")
        return country_stats

    except Exception as e:
        logger.error(f"Error getting country stats: {e}")
        return []
