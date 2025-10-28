"""
Chatbot service for multi-tenant bot management
"""
from typing import List, Optional
from supabase import Client
from app.models.chatbot import Chatbot, ChatbotCreate, ChatbotUpdate, ChatbotDeploy, ChatbotStats, ChatbotWithEmbedCode
from app.core.database import get_supabase_client
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class ChatbotService:
    def __init__(self):
        self.client: Client = get_supabase_client()

    async def create_chatbot(self, chatbot_data: ChatbotCreate, company_id: str) -> Chatbot:
        """Create a new chatbot for a company"""
        try:
            response = self.client.table("chatbots").insert({
                "company_id": company_id,
                "name": chatbot_data.name,
                "description": chatbot_data.description,
                "greeting_message": chatbot_data.greeting_message,
                "primary_color": chatbot_data.primary_color,
                "secondary_color": chatbot_data.secondary_color,
                "logo_url": chatbot_data.logo_url,
                "model_preset": chatbot_data.model_preset,
                "temperature": chatbot_data.temperature,
                "max_tokens": chatbot_data.max_tokens,
                "top_k": chatbot_data.top_k,
                "similarity_threshold": chatbot_data.similarity_threshold,
                "allowed_domains": chatbot_data.allowed_domains,
                "rate_limit_per_ip": chatbot_data.rate_limit_per_ip
            }).execute()

            if not response.data:
                raise Exception("Failed to create chatbot")

            logger.info(f"Created chatbot: {response.data[0]['id']} for company: {company_id}")
            return Chatbot(**response.data[0])

        except Exception as e:
            logger.error(f"Error creating chatbot: {str(e)}")
            raise

    async def get_chatbot(self, chatbot_id: str, company_id: Optional[str] = None) -> Optional[Chatbot]:
        """Get chatbot by ID (with optional company_id verification)"""
        try:
            query = self.client.table("chatbots").select("*").eq("id", chatbot_id)

            if company_id:
                query = query.eq("company_id", company_id)

            response = query.single().execute()

            if not response.data:
                return None

            return Chatbot(**response.data)

        except Exception as e:
            logger.error(f"Error fetching chatbot: {str(e)}")
            return None

    async def get_chatbot_with_embed_code(self, chatbot_id: str, company_id: str) -> Optional[ChatbotWithEmbedCode]:
        """Get chatbot with generated embed code"""
        chatbot = await self.get_chatbot(chatbot_id, company_id)

        if not chatbot:
            return None

        # Generate embed code
        embed_code = self._generate_embed_code(chatbot)

        return ChatbotWithEmbedCode(**chatbot.dict(), embed_code=embed_code)

    def _generate_embed_code(self, chatbot: Chatbot) -> str:
        """Generate JavaScript embed code for chatbot"""
        api_url = settings.API_BASE_URL or "http://localhost:8000"

        embed_code = f"""<!-- Githaforge Chatbot -->
<script>
  (function() {{
    const config = {{
      chatbotId: "{chatbot.id}",
      apiUrl: "{api_url}",
      primaryColor: "{chatbot.primary_color or '#1e40af'}",
      secondaryColor: "{chatbot.secondary_color or '#0ea5e9'}",
      greeting: "{chatbot.greeting_message}",
      logoUrl: "{chatbot.logo_url or ''}",
      position: "bottom-right"
    }};

    const script = document.createElement('script');
    script.src = "{api_url}/static/chatbot-widget.js";
    script.async = true;
    script.onload = function() {{
      window.GithaforgeChat.init(config);
    }};
    document.head.appendChild(script);
  }})();
</script>
"""
        return embed_code

    async def update_chatbot(self, chatbot_id: str, chatbot_data: ChatbotUpdate, company_id: str) -> Optional[Chatbot]:
        """Update chatbot settings"""
        try:
            update_data = chatbot_data.dict(exclude_unset=True)

            if not update_data:
                return await self.get_chatbot(chatbot_id, company_id)

            response = self.client.table("chatbots").update(update_data).eq("id", chatbot_id).eq("company_id", company_id).execute()

            if not response.data:
                return None

            logger.info(f"Updated chatbot: {chatbot_id}")
            return Chatbot(**response.data[0])

        except Exception as e:
            logger.error(f"Error updating chatbot: {str(e)}")
            raise

    async def deploy_chatbot(self, chatbot_id: str, deploy_data: ChatbotDeploy, company_id: str) -> Optional[Chatbot]:
        """Deploy or pause a chatbot"""
        try:
            response = self.client.table("chatbots").update({
                "deploy_status": deploy_data.deploy_status
            }).eq("id", chatbot_id).eq("company_id", company_id).execute()

            if not response.data:
                return None

            logger.info(f"Changed chatbot {chatbot_id} status to: {deploy_data.deploy_status}")
            return Chatbot(**response.data[0])

        except Exception as e:
            logger.error(f"Error deploying chatbot: {str(e)}")
            raise

    async def delete_chatbot(self, chatbot_id: str, company_id: str) -> bool:
        """Delete chatbot (soft delete by setting is_active=false)"""
        try:
            response = self.client.table("chatbots").update({
                "is_active": False,
                "deploy_status": "paused"
            }).eq("id", chatbot_id).eq("company_id", company_id).execute()

            if not response.data:
                return False

            logger.info(f"Soft deleted chatbot: {chatbot_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting chatbot: {str(e)}")
            return False

    async def list_company_chatbots(self, company_id: str, limit: int = 100, offset: int = 0) -> List[Chatbot]:
        """List all chatbots for a company"""
        try:
            response = self.client.table("chatbots").select("*").eq("company_id", company_id).eq("is_active", True).order("created_at", desc=True).range(offset, offset + limit - 1).execute()

            return [Chatbot(**bot) for bot in response.data]

        except Exception as e:
            logger.error(f"Error listing chatbots: {str(e)}")
            return []

    async def get_chatbot_stats(self, chatbot_id: str, company_id: str) -> ChatbotStats:
        """Get detailed chatbot statistics"""
        try:
            # Get basic stats from chatbot record
            chatbot = await self.get_chatbot(chatbot_id, company_id)

            if not chatbot:
                raise Exception("Chatbot not found")

            # Get trending queries for this bot
            trending_response = self.client.table("messages").select("content").eq("role", "user").limit(100).execute()

            top_queries = []
            # TODO: Implement proper query frequency analysis

            # Get daily stats
            daily_stats = []
            # TODO: Implement daily aggregation

            # Calculate metrics
            satisfaction_rate = (chatbot.avg_satisfaction * 100) if chatbot.avg_satisfaction else None

            # Get feedback count
            feedback_response = self.client.table("feedback").select("id", count="exact").execute()
            response_rate = (feedback_response.count / chatbot.total_messages * 100) if chatbot.total_messages > 0 else None

            return ChatbotStats(
                total_conversations=chatbot.total_conversations,
                total_messages=chatbot.total_messages,
                avg_satisfaction=chatbot.avg_satisfaction,
                avg_response_time=None,  # TODO: Implement
                satisfaction_rate=satisfaction_rate,
                response_rate=response_rate,
                top_queries=top_queries,
                daily_stats=daily_stats
            )

        except Exception as e:
            logger.error(f"Error fetching chatbot stats: {str(e)}")
            raise


# Singleton instance
_chatbot_service = None


def get_chatbot_service() -> ChatbotService:
    global _chatbot_service
    if _chatbot_service is None:
        _chatbot_service = ChatbotService()
    return _chatbot_service
