"""
API v1 router aggregator
"""
from fastapi import APIRouter
from app.api.routes import chat, documents, conversations, feedback, analytics, auth, users, settings, agent, widget, learning, soft_delete, chatbot_config

api_router = APIRouter()

# Include all route modules
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
api_router.include_router(conversations.router, prefix="/conversations", tags=["Conversations"])
api_router.include_router(feedback.router, prefix="/feedback", tags=["Feedback"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(settings.router, prefix="/settings", tags=["Settings"])
api_router.include_router(agent.router, prefix="/agent", tags=["Agent Metrics"])
api_router.include_router(widget.router, prefix="/widget", tags=["Widget Settings"])
api_router.include_router(learning.router, prefix="/learning", tags=["Learning System"])
api_router.include_router(soft_delete.router, tags=["Soft Delete"])
api_router.include_router(chatbot_config.router, prefix="/chatbot-config", tags=["Chatbot Configuration"])
