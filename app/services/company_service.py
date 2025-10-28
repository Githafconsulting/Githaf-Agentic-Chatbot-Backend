"""
Company service for multi-tenant operations
"""
from typing import List, Optional
from supabase import Client
from app.models.company import Company, CompanyCreate, CompanyUpdate, CompanyStats
from app.core.database import get_supabase_client
import logging

logger = logging.getLogger(__name__)


class CompanyService:
    def __init__(self):
        self.client: Client = get_supabase_client()

    async def create_company(self, company_data: CompanyCreate) -> Company:
        """Create a new company"""
        try:
            response = self.client.table("companies").insert({
                "name": company_data.name,
                "website": company_data.website,
                "logo_url": company_data.logo_url,
                "primary_color": company_data.primary_color,
                "secondary_color": company_data.secondary_color,
                "company_size": company_data.company_size,
                "industry": company_data.industry,
                "plan": company_data.plan
            }).execute()

            if not response.data:
                raise Exception("Failed to create company")

            logger.info(f"Created company: {response.data[0]['id']}")
            return Company(**response.data[0])

        except Exception as e:
            logger.error(f"Error creating company: {str(e)}")
            raise

    async def get_company(self, company_id: str) -> Optional[Company]:
        """Get company by ID"""
        try:
            response = self.client.table("companies").select("*").eq("id", company_id).single().execute()

            if not response.data:
                return None

            return Company(**response.data)

        except Exception as e:
            logger.error(f"Error fetching company: {str(e)}")
            return None

    async def update_company(self, company_id: str, company_data: CompanyUpdate) -> Optional[Company]:
        """Update company settings"""
        try:
            update_data = company_data.dict(exclude_unset=True)

            if not update_data:
                # No fields to update
                return await self.get_company(company_id)

            response = self.client.table("companies").update(update_data).eq("id", company_id).execute()

            if not response.data:
                return None

            logger.info(f"Updated company: {company_id}")
            return Company(**response.data[0])

        except Exception as e:
            logger.error(f"Error updating company: {str(e)}")
            raise

    async def delete_company(self, company_id: str) -> bool:
        """Delete company (soft delete by setting is_active=false)"""
        try:
            response = self.client.table("companies").update({
                "is_active": False
            }).eq("id", company_id).execute()

            if not response.data:
                return False

            logger.info(f"Soft deleted company: {company_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting company: {str(e)}")
            return False

    async def list_companies(self, limit: int = 100, offset: int = 0) -> List[Company]:
        """List all companies (admin only)"""
        try:
            response = self.client.table("companies").select("*").eq("is_active", True).range(offset, offset + limit - 1).execute()

            return [Company(**company) for company in response.data]

        except Exception as e:
            logger.error(f"Error listing companies: {str(e)}")
            return []

    async def get_company_stats(self, company_id: str) -> CompanyStats:
        """Get company statistics"""
        try:
            # Use the SQL function created in migration
            response = self.client.rpc("get_company_stats", {"p_company_id": company_id}).execute()

            if not response.data or len(response.data) == 0:
                return CompanyStats(
                    total_bots=0,
                    total_documents=0,
                    total_conversations=0,
                    total_messages=0,
                    avg_satisfaction=None
                )

            stats = response.data[0]
            return CompanyStats(
                total_bots=stats.get("total_bots", 0),
                total_documents=stats.get("total_documents", 0),
                total_conversations=stats.get("total_conversations", 0),
                total_messages=stats.get("total_messages", 0),
                avg_satisfaction=stats.get("avg_satisfaction")
            )

        except Exception as e:
            logger.error(f"Error fetching company stats: {str(e)}")
            return CompanyStats(
                total_bots=0,
                total_documents=0,
                total_conversations=0,
                total_messages=0,
                avg_satisfaction=None
            )

    async def provision_company_resources(self, company_id: str) -> bool:
        """Provision storage bucket and default resources for new company"""
        try:
            # Create storage bucket for company documents
            bucket_name = f"company-{company_id}-documents"

            try:
                self.client.storage.create_bucket(bucket_name, {
                    "public": False
                })
                logger.info(f"Created storage bucket: {bucket_name}")
            except Exception as bucket_error:
                # Bucket might already exist
                logger.warning(f"Bucket creation warning: {str(bucket_error)}")

            # Set RLS context for this company
            self.client.rpc("set_company_context", {
                "p_company_id": company_id,
                "p_is_super_admin": False
            }).execute()

            return True

        except Exception as e:
            logger.error(f"Error provisioning company resources: {str(e)}")
            return False


# Singleton instance
_company_service = None


def get_company_service() -> CompanyService:
    global _company_service
    if _company_service is None:
        _company_service = CompanyService()
    return _company_service
