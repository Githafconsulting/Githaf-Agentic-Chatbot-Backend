"""
Learning Service
Analyzes user feedback and generates knowledge base improvements
"""
from typing import List, Dict, Optional, Any
from uuid import UUID
from datetime import datetime, timedelta
from app.core.database import get_supabase_client
from app.services.llm_service import generate_response
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def get_feedback_insights(start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Analyze feedback to identify knowledge gaps and patterns

    Args:
        start_date: Optional start date (ISO format YYYY-MM-DD)
        end_date: Optional end date (ISO format YYYY-MM-DD)

    Returns:
        Dict with feedback patterns and insights
    """
    try:
        client = get_supabase_client()

        # Default to last 30 days if no dates provided
        if not start_date:
            thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).isoformat()
        else:
            thirty_days_ago = start_date

        if not end_date:
            end_date = datetime.utcnow().isoformat()

        # Query feedback with date range
        response = client.table("feedback").select("id, message_id, rating, comment, created_at").eq(
            "rating", 0).gte("created_at", thirty_days_ago).lte("created_at", end_date).execute()

        negative_feedback = response.data if response.data else []

        # Get feedback IDs already used in VALID drafts (pending or successfully published)
        # Exclude feedback from:
        # 1. Pending drafts (still under review)
        # 2. Successfully published drafts (published_document_id is set)
        # DO NOT exclude feedback from broken drafts (approved but failed to publish)
        used_feedback_response = client.table("draft_documents").select(
            "source_feedback_ids, status, published_document_id"
        ).execute()

        used_feedback_ids = set()
        if used_feedback_response.data:
            for draft in used_feedback_response.data:
                # Only exclude feedback from valid drafts
                is_pending = draft.get("status") == "pending"
                is_published = draft.get("published_document_id") is not None

                if (is_pending or is_published) and draft.get("source_feedback_ids"):
                    used_feedback_ids.update(draft["source_feedback_ids"])

        # Filter out feedback already used in valid drafts
        negative_feedback = [f for f in negative_feedback if str(f["id"]) not in used_feedback_ids]

        message_ids = [f["message_id"] for f in negative_feedback if f.get("message_id")]

        messages = []
        if message_ids:
            msg_response = client.table("messages").select(
                "id, content, role, conversation_id, created_at").in_("id", message_ids).execute()
            messages = msg_response.data if msg_response.data else []

        message_lookup = {msg["id"]: msg for msg in messages}

        feedback_with_context = []
        for fb in negative_feedback:
            if fb.get("message_id") in message_lookup:
                msg = message_lookup[fb["message_id"]]
                user_msg_response = client.table("messages").select("content").eq(
                    "conversation_id", msg["conversation_id"]).eq("role", "user").lt(
                    "created_at", msg.get("created_at", datetime.utcnow().isoformat())).order(
                    "created_at", desc=True).limit(1).execute()

                user_query = ""
                if user_msg_response.data and len(user_msg_response.data) > 0:
                    user_query = user_msg_response.data[0].get("content", "")

                feedback_with_context.append({
                    "feedback_id": fb["id"],
                    "query": user_query,
                    "response": msg.get("content", ""),
                    "comment": fb.get("comment"),
                    "created_at": fb.get("created_at")
                })

        patterns = {}
        for item in feedback_with_context:
            if not item.get("comment"):
                continue

            comment_lower = item["comment"].lower()
            query_lower = item["query"].lower() if item.get("query") else ""

            pattern_key = None
            if any(w in comment_lower or w in query_lower for w in ["price", "pricing", "cost", "fee", "payment"]):
                pattern_key = "pricing_questions"
            elif any(w in comment_lower or w in query_lower for w in ["technical", "tech", "support", "bug", "error"]):
                pattern_key = "technical_support"
            elif any(w in comment_lower or w in query_lower for w in ["contact", "email", "phone", "reach"]):
                pattern_key = "contact_information"
            elif any(w in comment_lower for w in ["inaccurate", "wrong", "incorrect", "false"]):
                pattern_key = "inaccurate_information"
            elif any(w in comment_lower for w in ["incomplete", "missing", "not enough", "vague"]):
                pattern_key = "incomplete_information"
            else:
                pattern_key = "other_issues"

            if pattern_key not in patterns:
                patterns[pattern_key] = {
                    "pattern": pattern_key.replace("_", " ").title(),
                    "count": 0,
                    "samples": [],
                    "feedback_ids": []
                }

            patterns[pattern_key]["count"] += 1
            patterns[pattern_key]["feedback_ids"].append(item["feedback_id"])

            if len(patterns[pattern_key]["samples"]) < 3:
                patterns[pattern_key]["samples"].append({
                    "query": item["query"],
                    "comment": item["comment"],
                    "created_at": item["created_at"]
                })

        sorted_patterns = sorted(patterns.values(), key=lambda x: x["count"], reverse=True)

        for pattern in sorted_patterns:
            if pattern["count"] >= 10:
                pattern["priority"] = "critical"
            elif pattern["count"] >= 5:
                pattern["priority"] = "high"
            elif pattern["count"] >= 2:
                pattern["priority"] = "medium"
            else:
                pattern["priority"] = "low"

        return {
            "total_negative_feedback": len(negative_feedback),
            "feedback_with_comments": len(feedback_with_context),
            "patterns_identified": len(sorted_patterns),
            "patterns": sorted_patterns[:5],
            "period_days": 30
        }

    except Exception as e:
        logger.error(f"Error analyzing feedback insights: {e}")
        return {
            "total_negative_feedback": 0,
            "feedback_with_comments": 0,
            "patterns_identified": 0,
            "patterns": [],
            "error": str(e)
        }


async def generate_draft_from_feedback(
    feedback_ids: List[UUID],
    query_pattern: Optional[str] = None,
    category: Optional[str] = None,
    additional_context: Optional[str] = None
) -> Dict[str, Any]:
    """Generate draft document from feedback using LLM"""
    try:
        client = get_supabase_client()
        feedback_data = []

        for feedback_id in feedback_ids:
            fb_response = client.table("feedback").select(
                "id, message_id, rating, comment, created_at").eq("id", str(feedback_id)).execute()

            if fb_response.data and len(fb_response.data) > 0:
                fb = fb_response.data[0]
                msg_response = client.table("messages").select(
                    "id, content, role, conversation_id, created_at").eq("id", fb["message_id"]).execute()

                if msg_response.data and len(msg_response.data) > 0:
                    msg = msg_response.data[0]
                    user_msg_response = client.table("messages").select("content").eq(
                        "conversation_id", msg["conversation_id"]).eq("role", "user").lt(
                        "created_at", msg.get("created_at", datetime.utcnow().isoformat())).order(
                        "created_at", desc=True).limit(1).execute()

                    user_query = ""
                    if user_msg_response.data and len(user_msg_response.data) > 0:
                        user_query = user_msg_response.data[0].get("content", "")

                    feedback_data.append({
                        "query": user_query,
                        "response": msg.get("content", ""),
                        "comment": fb.get("comment"),
                        "rating": fb.get("rating")
                    })

        if not feedback_data:
            return {"success": False, "message": "No feedback data found"}

        prompt = """You are improving a chatbot knowledge base for Githaf Consulting.

Based on user feedback below, create a comprehensive knowledge base document.

FEEDBACK ANALYSIS:
"""
        for i, item in enumerate(feedback_data, 1):
            prompt += f"\nFeedback #{i}:\nUser Query: {item['query']}\nBot Response: {item['response']}\nUser Feedback: {item['comment']}\n"

        if query_pattern:
            prompt += f"\n\nPATTERN: {query_pattern}\n"
        if additional_context:
            prompt += f"\nCONTEXT: {additional_context}\n"

        prompt += "\n\nCreate a document:\n\n## [Title]\n\n### Overview\n[Introduction]\n\n### Key Information\n[Main content]\n\n### Details\n[Additional details]\n\nGenerate now:"

        generated_content = await generate_response(
            prompt=prompt,
            system_message="You are a technical writer creating knowledge base documents for Githaf Consulting. Create clear, accurate, and helpful documentation based on user feedback.",
            temperature=0.7,
            max_tokens=1000
        )

        lines = generated_content.strip().split("\n")
        title = query_pattern or "Improved Response"
        for line in lines:
            if line.startswith("## "):
                title = line.replace("## ", "").strip()
                break

        draft_data = {
            "title": title[:500],
            "content": generated_content,
            "category": category or "user_feedback",
            "source_type": "feedback_generated",
            "source_feedback_ids": [str(fid) for fid in feedback_ids],
            "query_pattern": query_pattern,
            "generated_by_llm": True,
            "llm_model": "llama-3.1-8b-instant",
            "generation_prompt": prompt[:1000],
            "confidence_score": 0.7,
            "status": "pending",
            "feedback_count": len(feedback_ids),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

        insert_response = client.table("draft_documents").insert(draft_data).execute()

        if insert_response.data and len(insert_response.data) > 0:
            draft = insert_response.data[0]
            logger.info(f"Generated draft: {draft['id']}")
            return {"success": True, "message": "Draft generated", "draft_id": draft["id"], "draft": draft}
        else:
            return {"success": False, "message": "Failed to save draft"}

    except Exception as e:
        logger.error(f"Error generating draft: {e}")
        return {"success": False, "message": f"Error: {str(e)}"}


async def get_pending_drafts(limit: int = 20, offset: int = 0) -> Dict[str, Any]:
    """Get all pending draft documents"""
    try:
        client = get_supabase_client()

        response = client.table("draft_documents").select("*").eq(
            "status", "pending").order("created_at", desc=True).range(offset, offset + limit - 1).execute()

        drafts = response.data if response.data else []
        count_response = client.table("draft_documents").select("id", count="exact").eq("status", "pending").execute()
        total = count_response.count if hasattr(count_response, 'count') else len(drafts)

        return {"drafts": drafts, "total": total, "limit": limit, "offset": offset}

    except Exception as e:
        logger.error(f"Error fetching drafts: {e}")
        return {"drafts": [], "total": 0, "error": str(e)}


async def approve_draft(draft_id: UUID, reviewed_by: UUID, review_notes: Optional[str] = None, auto_publish: bool = True) -> Dict[str, Any]:
    """
    Approve draft and optionally auto-publish to knowledge base

    Args:
        draft_id: UUID of draft to approve
        reviewed_by: UUID of admin who approved
        review_notes: Optional review notes
        auto_publish: If True, automatically publishes draft to knowledge base (default: True)

    Returns:
        Dict with approval results and publication status
    """
    try:
        client = get_supabase_client()

        # Update draft status
        update_data = {
            "status": "approved",
            "reviewed_by": str(reviewed_by),
            "reviewed_at": datetime.utcnow().isoformat(),
            "review_notes": review_notes,
            "updated_at": datetime.utcnow().isoformat()
        }

        response = client.table("draft_documents").update(update_data).eq("id", str(draft_id)).execute()

        if not response.data or len(response.data) == 0:
            return {"success": False, "message": "Draft not found"}

        draft = response.data[0]
        result = {
            "success": True,
            "message": "Draft approved",
            "draft": draft,
            "published": False
        }

        # Auto-publish to knowledge base if enabled
        if auto_publish:
            logger.info(f"📚 Auto-publishing approved draft {draft_id} to knowledge base")
            publish_result = await publish_draft_to_knowledge_base(draft)

            if publish_result.get("success"):
                result["published"] = True
                result["document_id"] = publish_result.get("document_id")
                result["message"] = "Draft approved and published to knowledge base"
                logger.info(f"✅ Draft {draft_id} successfully published as document {publish_result.get('document_id')}")
            else:
                result["publish_error"] = publish_result.get("message")
                result["message"] = "Draft approved but publication failed. Admin can retry manually."
                logger.warning(f"⚠️ Draft {draft_id} approved but publication failed: {publish_result.get('message')}")

        return result

    except Exception as e:
        logger.error(f"Error approving draft: {e}")
        return {"success": False, "message": str(e)}


async def publish_draft_to_knowledge_base(draft: Dict[str, Any]) -> Dict[str, Any]:
    """
    Publish approved draft to knowledge base

    Creates a document from draft content and generates embeddings

    Args:
        draft: Draft document dict from database

    Returns:
        Dict with publication results
    """
    try:
        from app.services.embedding_service import get_embedding
        from app.utils.text_processor import chunk_text

        client = get_supabase_client()

        # Create document from draft
        document_data = {
            "title": draft["title"],
            "file_type": "txt",  # Fixed: was "text", should be "txt" to match constraint
            "file_size": len(draft["content"]),
            "source_type": "draft_published",
            "source_url": None,
            "category": draft.get("category", "learned_content"),
            "summary": draft["content"][:500] + "..." if len(draft["content"]) > 500 else draft["content"],
            "chunk_count": 0,  # Will update after embedding
            "metadata": {
                "source": "learning_system",
                "draft_id": str(draft["id"]),
                "query_pattern": draft.get("query_pattern"),
                "feedback_count": draft.get("feedback_count"),
                "llm_model": draft.get("llm_model"),
                "confidence_score": draft.get("confidence_score")
            },
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

        # Insert document
        doc_response = client.table("documents").insert(document_data).execute()

        if not doc_response.data or len(doc_response.data) == 0:
            return {"success": False, "message": "Failed to create document"}

        document = doc_response.data[0]
        document_id = document["id"]

        # Chunk and embed content
        chunks = chunk_text(draft["content"], chunk_size=500, chunk_overlap=50)
        embeddings_inserted = 0

        for chunk in chunks:
            try:
                # Generate embedding
                embedding = await get_embedding(chunk)

                # Insert embedding
                embedding_data = {
                    "document_id": document_id,
                    "chunk_text": chunk,  # Fixed: was "content", should be "chunk_text"
                    "embedding": embedding,
                    "created_at": datetime.utcnow().isoformat()
                }

                client.table("embeddings").insert(embedding_data).execute()
                embeddings_inserted += 1

            except Exception as e:
                logger.warning(f"Failed to embed chunk: {e}")

        # Update document chunk count
        client.table("documents").update({
            "chunk_count": embeddings_inserted,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", document_id).execute()

        # Update draft with published document ID
        client.table("draft_documents").update({
            "published_document_id": document_id,
            "published_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", str(draft["id"])).execute()

        logger.info(f"📚 Published draft {draft['id']} as document {document_id} with {embeddings_inserted} embeddings")

        return {
            "success": True,
            "message": f"Draft published with {embeddings_inserted} chunks",
            "document_id": document_id,
            "chunk_count": embeddings_inserted
        }

    except Exception as e:
        logger.error(f"Error publishing draft to knowledge base: {e}")
        return {"success": False, "message": str(e)}


async def reject_draft(draft_id: UUID, reviewed_by: UUID, review_notes: Optional[str] = None) -> Dict[str, Any]:
    """Reject draft"""
    try:
        client = get_supabase_client()

        update_data = {
            "status": "rejected",
            "reviewed_by": str(reviewed_by),
            "reviewed_at": datetime.utcnow().isoformat(),
            "review_notes": review_notes or "Rejected by admin",
            "updated_at": datetime.utcnow().isoformat()
        }

        response = client.table("draft_documents").update(update_data).eq("id", str(draft_id)).execute()

        if response.data and len(response.data) > 0:
            return {"success": True, "message": "Draft rejected", "draft": response.data[0]}
        else:
            return {"success": False, "message": "Draft not found"}

    except Exception as e:
        logger.error(f"Error rejecting draft: {e}")
        return {"success": False, "message": str(e)}


async def realtime_learning_check() -> Dict[str, Any]:
    """
    Real-time learning check triggered after negative feedback

    Lighter and faster than weekly job:
    - Analyzes last 7 days (vs 30 days)
    - Lower threshold: generates drafts for patterns with 3+ occurrences (vs 10+)
    - Runs in background to avoid blocking user responses

    Returns:
        Dict with learning check results
    """
    try:
        logger.info("🔄 Starting real-time learning check")

        # Analyze recent feedback (last 7 days only)
        seven_days_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
        insights = await get_feedback_insights(start_date=seven_days_ago)

        results = {
            "success": True,
            "mode": "realtime",
            "timestamp": datetime.utcnow().isoformat(),
            "total_negative_feedback": insights.get("total_negative_feedback", 0),
            "patterns_identified": insights.get("patterns_identified", 0),
            "drafts_generated": 0,
            "patterns_processed": []
        }

        # Process patterns with lower threshold for real-time mode
        patterns = insights.get("patterns", [])
        for pattern in patterns:
            # Real-time mode: generate drafts for patterns with 3+ occurrences
            if pattern["count"] >= 3:
                logger.info(f"🎯 Real-time draft generation for pattern: {pattern['pattern']} ({pattern['count']} occurrences)")

                draft_result = await generate_draft_from_feedback(
                    feedback_ids=[UUID(fid) for fid in pattern["feedback_ids"]],
                    query_pattern=pattern["pattern"],
                    category="realtime_generated",
                    additional_context=f"Auto-generated from real-time learning ({pattern['count']} occurrences in last 7 days)"
                )

                if draft_result.get("success"):
                    results["drafts_generated"] += 1
                    results["patterns_processed"].append({
                        "pattern": pattern["pattern"],
                        "count": pattern["count"],
                        "draft_id": draft_result.get("draft_id"),
                        "status": "draft_created"
                    })
                else:
                    results["patterns_processed"].append({
                        "pattern": pattern["pattern"],
                        "count": pattern["count"],
                        "status": "failed",
                        "error": draft_result.get("message")
                    })

        logger.info(f"✅ Real-time learning check completed: {results['drafts_generated']} drafts generated")
        return results

    except Exception as e:
        logger.error(f"❌ Error in real-time learning check: {e}")
        return {
            "success": False,
            "mode": "realtime",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


async def weekly_learning_job() -> Dict[str, Any]:
    """
    Weekly background job to analyze feedback and generate draft documents

    This job runs every Sunday at 2 AM and:
    1. Analyzes feedback patterns from the past week
    2. Identifies high-priority patterns (5+ occurrences)
    3. Auto-generates draft documents for critical patterns (10+ occurrences)

    Returns:
        Dict with job execution results
    """
    try:
        logger.info("Starting weekly learning job")

        # Get feedback insights
        insights = await get_feedback_insights()

        results = {
            "success": True,
            "timestamp": datetime.utcnow().isoformat(),
            "total_negative_feedback": insights.get("total_negative_feedback", 0),
            "patterns_identified": insights.get("patterns_identified", 0),
            "drafts_generated": 0,
            "patterns_processed": []
        }

        # Process high-priority patterns
        patterns = insights.get("patterns", [])
        for pattern in patterns:
            # Only auto-generate for critical patterns (10+ occurrences)
            if pattern["count"] >= 10 and pattern.get("priority") == "critical":
                logger.info(f"Auto-generating draft for critical pattern: {pattern['pattern']}")

                draft_result = await generate_draft_from_feedback(
                    feedback_ids=[UUID(fid) for fid in pattern["feedback_ids"]],
                    query_pattern=pattern["pattern"],
                    category="auto_generated",
                    additional_context=f"Auto-generated from weekly learning job ({pattern['count']} occurrences)"
                )

                if draft_result.get("success"):
                    results["drafts_generated"] += 1
                    results["patterns_processed"].append({
                        "pattern": pattern["pattern"],
                        "count": pattern["count"],
                        "draft_id": draft_result.get("draft_id"),
                        "status": "draft_created"
                    })
                else:
                    results["patterns_processed"].append({
                        "pattern": pattern["pattern"],
                        "count": pattern["count"],
                        "status": "failed",
                        "error": draft_result.get("message")
                    })

        logger.info(f"Weekly learning job completed: {results['drafts_generated']} drafts generated")
        return results

    except Exception as e:
        logger.error(f"Error in weekly learning job: {e}")
        return {
            "success": False,
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }