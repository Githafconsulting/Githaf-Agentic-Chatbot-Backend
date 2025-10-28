"""
Company CRUD API routes for multi-tenant management
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from app.models.company import (
    CompanyCreate,
    CompanyUpdate,
    Company,
    CompanyWithStats,
    CompanyStats
)
from app.services.company_service import CompanyService
from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter()


@router.post("/", response_model=Company, status_code=status.HTTP_201_CREATED)
async def create_company(
    company_data: CompanyCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Create a new company (during signup or by admin)

    - **name**: Company name (2-100 characters)
    - **website**: Optional company website URL
    - **logo_url**: Optional logo URL
    - **primary_color**: Hex color (default: #1e40af)
    - **secondary_color**: Hex color (default: #0ea5e9)
    - **company_size**: Optional size category
    - **industry**: Optional industry
    - **plan**: free/pro/enterprise (default: free)
    """
    try:
        service = CompanyService()
        company = await service.create_company(company_data)

        # Provision company resources (storage bucket, RLS context)
        await service.provision_company_resources(company.id)

        return company
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create company: {str(e)}"
        )


@router.get("/{company_id}", response_model=Company)
async def get_company(
    company_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get company by ID

    - **company_id**: UUID of the company

    Returns company details including plan limits
    """
    # TODO: Verify user belongs to this company or is super admin
    service = CompanyService()
    company = await service.get_company(company_id)

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company {company_id} not found"
        )

    return company


@router.put("/{company_id}", response_model=Company)
async def update_company(
    company_id: str,
    company_data: CompanyUpdate,
    current_user: User = Depends(get_current_user)
):
    """
    Update company settings

    - **company_id**: UUID of the company
    - **company_data**: Fields to update (all optional)

    Allows updating:
    - Company name, website, logo
    - Brand colors (primary, secondary)
    - Company size, industry

    Note: Plan and limits can only be changed by super admin
    """
    # TODO: Verify user is company admin/owner
    service = CompanyService()
    company = await service.update_company(company_id, company_data)

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company {company_id} not found"
        )

    return company


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company(
    company_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Soft delete a company

    - **company_id**: UUID of the company

    Sets is_active=false instead of hard delete
    Cascades to all company resources (chatbots, documents, etc.)

    IMPORTANT: This action cannot be undone by users (admin recovery only)
    """
    # TODO: Verify user is company owner or super admin
    service = CompanyService()
    success = await service.delete_company(company_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company {company_id} not found"
        )

    return None


@router.get("/{company_id}/stats", response_model=CompanyStats)
async def get_company_stats(
    company_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get company statistics

    - **company_id**: UUID of the company

    Returns:
    - Total chatbots
    - Total documents
    - Total conversations
    - Total messages
    - Average satisfaction score
    """
    # TODO: Verify user belongs to this company
    service = CompanyService()

    # Verify company exists
    company = await service.get_company(company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company {company_id} not found"
        )

    stats = await service.get_company_stats(company_id)
    return stats


@router.get("/", response_model=List[Company])
async def list_companies(
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_user)
):
    """
    List all companies (admin only)

    - **limit**: Max number of results (default: 100)
    - **offset**: Pagination offset (default: 0)

    Super admin can see all companies
    Regular users can only see their own company
    """
    # TODO: Implement authorization check
    # if not current_user.is_super_admin:
    #     # Return only user's company
    #     service = CompanyService()
    #     company = await service.get_company(current_user.company_id)
    #     return [company] if company else []

    service = CompanyService()
    companies = await service.list_companies(limit=limit, offset=offset)
    return companies


@router.get("/{company_id}/with-stats", response_model=CompanyWithStats)
async def get_company_with_stats(
    company_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get company details with statistics in a single call

    - **company_id**: UUID of the company

    Combines company info + stats for dashboard display
    Optimized to reduce API calls
    """
    # TODO: Verify user belongs to this company
    service = CompanyService()

    # Get company
    company = await service.get_company(company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company {company_id} not found"
        )

    # Get stats
    stats = await service.get_company_stats(company_id)

    # Combine
    company_with_stats = CompanyWithStats(
        **company.dict(),
        stats=stats
    )

    return company_with_stats
