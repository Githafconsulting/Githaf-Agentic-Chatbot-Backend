"""
CRM Tool (Phase 5: Tool Ecosystem)
Customer Relationship Management integration
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from app.services.tools.tools_registry import Tool, ToolCategory
from app.core.database import get_supabase_client
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CRMTool(Tool):
    """Tool for CRM operations"""

    def __init__(self):
        super().__init__(
            name="crm",
            description="Manage customer data and interactions",
            category=ToolCategory.DATA,
            enabled=True,
            requires_auth=False
        )

    def validate_params(self, params: Dict[str, Any]) -> bool:
        """Validate CRM parameters"""
        action = params.get("action")

        if action not in ["create_contact", "update_contact", "get_contact", "search_contacts", "log_interaction"]:
            logger.error(f"Invalid action: {action}")
            return False

        if action == "create_contact":
            if "email" not in params:
                logger.error("Missing required field: email")
                return False

        elif action in ["update_contact", "get_contact"]:
            if "contact_id" not in params and "email" not in params:
                logger.error("Missing required field: contact_id or email")
                return False

        elif action == "log_interaction":
            required = ["contact_id", "interaction_type", "notes"]
            for field in required:
                if field not in params:
                    logger.error(f"Missing required field: {field}")
                    return False

        return True

    def get_schema(self) -> Dict[str, Any]:
        """Get parameter schema"""
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["create_contact", "update_contact", "get_contact", "search_contacts", "log_interaction"],
                    "description": "CRM action to perform"
                },
                "contact_id": {
                    "type": "string",
                    "description": "Contact ID"
                },
                "email": {
                    "type": "string",
                    "description": "Contact email"
                },
                "name": {
                    "type": "string",
                    "description": "Contact full name"
                },
                "company": {
                    "type": "string",
                    "description": "Company name"
                },
                "phone": {
                    "type": "string",
                    "description": "Phone number"
                },
                "industry": {
                    "type": "string",
                    "description": "Industry sector"
                },
                "tags": {
                    "type": "array",
                    "description": "Contact tags",
                    "items": {"type": "string"}
                },
                "interaction_type": {
                    "type": "string",
                    "enum": ["call", "email", "meeting", "chat", "other"],
                    "description": "Type of interaction"
                },
                "notes": {
                    "type": "string",
                    "description": "Interaction notes"
                },
                "search_query": {
                    "type": "string",
                    "description": "Search query for contacts"
                }
            },
            "required": ["action"]
        }

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute CRM action

        Args:
            params: CRM action parameters

        Returns:
            Execution result
        """
        action = params["action"]
        logger.info(f"CRM action: {action}")

        if action == "create_contact":
            return await self._create_contact(params)
        elif action == "update_contact":
            return await self._update_contact(params)
        elif action == "get_contact":
            return await self._get_contact(params)
        elif action == "search_contacts":
            return await self._search_contacts(params)
        elif action == "log_interaction":
            return await self._log_interaction(params)
        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}"
            }

    async def _create_contact(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create new contact"""
        logger.info(f"Creating contact: {params.get('email')}")

        try:
            client = get_supabase_client()

            # Check if contact already exists
            existing = client.table("crm_contacts").select("id").eq(
                "email", params["email"]
            ).execute()

            if existing.data:
                return {
                    "success": False,
                    "error": "Contact with this email already exists",
                    "contact_id": existing.data[0]["id"]
                }

            # Create contact
            contact_data = {
                "email": params["email"],
                "name": params.get("name"),
                "company": params.get("company"),
                "phone": params.get("phone"),
                "industry": params.get("industry"),
                "tags": params.get("tags", []),
                "metadata": {
                    "source": "chatbot",
                    "created_via": "crm_tool"
                }
            }

            response = client.table("crm_contacts").insert(contact_data).execute()

            if response.data:
                contact = response.data[0]
                logger.info(f"Contact created: {contact['id']}")

                return {
                    "success": True,
                    "message": "Contact created successfully",
                    "contact_id": contact["id"],
                    "contact": contact
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to create contact"
                }

        except Exception as e:
            logger.error(f"Error creating contact: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _update_contact(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing contact"""
        logger.info(f"Updating contact: {params.get('contact_id') or params.get('email')}")

        try:
            client = get_supabase_client()

            # Find contact
            if "contact_id" in params:
                query = client.table("crm_contacts").select("*").eq("id", params["contact_id"])
            else:
                query = client.table("crm_contacts").select("*").eq("email", params["email"])

            existing = query.execute()

            if not existing.data:
                return {
                    "success": False,
                    "error": "Contact not found"
                }

            contact_id = existing.data[0]["id"]

            # Update contact
            update_data = {}
            for field in ["name", "company", "phone", "industry", "tags"]:
                if field in params:
                    update_data[field] = params[field]

            if update_data:
                update_data["updated_at"] = datetime.utcnow().isoformat()

                response = client.table("crm_contacts").update(update_data).eq(
                    "id", contact_id
                ).execute()

                if response.data:
                    logger.info(f"Contact updated: {contact_id}")

                    return {
                        "success": True,
                        "message": "Contact updated successfully",
                        "contact_id": contact_id,
                        "contact": response.data[0]
                    }

            return {
                "success": False,
                "error": "No fields to update"
            }

        except Exception as e:
            logger.error(f"Error updating contact: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _get_contact(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get contact by ID or email"""
        logger.info(f"Getting contact: {params.get('contact_id') or params.get('email')}")

        try:
            client = get_supabase_client()

            if "contact_id" in params:
                query = client.table("crm_contacts").select("*").eq("id", params["contact_id"])
            else:
                query = client.table("crm_contacts").select("*").eq("email", params["email"])

            response = query.execute()

            if response.data:
                contact = response.data[0]

                return {
                    "success": True,
                    "contact": contact
                }
            else:
                return {
                    "success": False,
                    "error": "Contact not found"
                }

        except Exception as e:
            logger.error(f"Error getting contact: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _search_contacts(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search contacts"""
        search_query = params.get("search_query", "")
        logger.info(f"Searching contacts: {search_query}")

        try:
            client = get_supabase_client()

            if search_query:
                # Search by name, company, or email
                response = client.table("crm_contacts").select("*").or_(
                    f"name.ilike.%{search_query}%,company.ilike.%{search_query}%,email.ilike.%{search_query}%"
                ).limit(20).execute()
            else:
                # List all contacts
                response = client.table("crm_contacts").select("*").order(
                    "created_at", desc=True
                ).limit(20).execute()

            contacts = response.data or []

            logger.info(f"Found {len(contacts)} contacts")

            return {
                "success": True,
                "contacts": contacts,
                "total": len(contacts)
            }

        except Exception as e:
            logger.error(f"Error searching contacts: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _log_interaction(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Log customer interaction"""
        logger.info(f"Logging interaction for contact: {params['contact_id']}")

        try:
            client = get_supabase_client()

            interaction_data = {
                "contact_id": params["contact_id"],
                "interaction_type": params["interaction_type"],
                "notes": params["notes"],
                "occurred_at": datetime.utcnow().isoformat()
            }

            response = client.table("crm_interactions").insert(interaction_data).execute()

            if response.data:
                interaction = response.data[0]
                logger.info(f"Interaction logged: {interaction['id']}")

                return {
                    "success": True,
                    "message": "Interaction logged successfully",
                    "interaction_id": interaction["id"]
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to log interaction"
                }

        except Exception as e:
            logger.error(f"Error logging interaction: {e}")
            return {
                "success": False,
                "error": str(e)
            }
