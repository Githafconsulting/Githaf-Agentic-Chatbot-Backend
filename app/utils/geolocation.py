"""
IP Geolocation utility
Uses ip-api.com free API for IP to country resolution
"""
import httpx
from typing import Dict, Optional
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def get_country_from_ip(ip_address: str) -> Dict[str, Optional[str]]:
    """
    Get country information from IP address using ip-api.com

    Args:
        ip_address: IPv4 or IPv6 address

    Returns:
        Dict with country_code and country_name, or None values if failed
    """
    # Handle localhost/private IPs
    if ip_address in ['127.0.0.1', 'localhost', '::1'] or ip_address.startswith('192.168.') or ip_address.startswith('10.'):
        return {
            "country_code": "US",  # Default to US for local development
            "country_name": "United States"
        }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # ip-api.com free tier: 45 requests/minute
            response = await client.get(
                f"http://ip-api.com/json/{ip_address}",
                params={"fields": "status,message,countryCode,country"}
            )

            if response.status_code == 200:
                data = response.json()

                if data.get("status") == "success":
                    return {
                        "country_code": data.get("countryCode"),
                        "country_name": data.get("country")
                    }
                else:
                    logger.warning(f"IP geolocation failed: {data.get('message')}")

    except Exception as e:
        logger.error(f"Error resolving IP {ip_address}: {e}")

    # Return None values if resolution failed
    return {
        "country_code": None,
        "country_name": None
    }


def anonymize_ip(ip_address: str) -> str:
    """
    Anonymize IP address for GDPR compliance by removing last octet

    Args:
        ip_address: Original IP address

    Returns:
        Anonymized IP address (e.g., 192.168.1.0 instead of 192.168.1.100)
    """
    try:
        if ':' in ip_address:  # IPv6
            parts = ip_address.split(':')
            # Zero out last 2 groups
            return ':'.join(parts[:-2] + ['0', '0'])
        else:  # IPv4
            parts = ip_address.split('.')
            # Zero out last octet
            return '.'.join(parts[:3] + ['0'])
    except Exception as e:
        logger.error(f"Error anonymizing IP: {e}")
        return "0.0.0.0"
