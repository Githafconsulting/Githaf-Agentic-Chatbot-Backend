"""
Seed sample conversations with country data for testing analytics
Adds realistic country distribution to existing or new conversations
"""
import sys
import os
import uuid
from datetime import datetime, timedelta
import random

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import get_supabase_client
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Sample country data with realistic distribution
COUNTRY_DATA = [
    ("US", "United States", 0.30),      # 30%
    ("GB", "United Kingdom", 0.15),     # 15%
    ("CA", "Canada", 0.12),             # 12%
    ("DE", "Germany", 0.10),            # 10%
    ("FR", "France", 0.08),             # 8%
    ("AU", "Australia", 0.07),          # 7%
    ("ES", "Spain", 0.05),              # 5%
    ("NL", "Netherlands", 0.05),        # 5%
    ("IT", "Italy", 0.04),              # 4%
    ("SE", "Sweden", 0.04),             # 4%
]


def generate_anonymized_ip(country_code: str) -> str:
    """Generate a realistic anonymized IP address"""
    # Different IP ranges for different regions
    ip_ranges = {
        "US": "192.168.1.0",
        "GB": "172.16.1.0",
        "CA": "192.168.2.0",
        "DE": "10.0.1.0",
        "FR": "10.0.2.0",
        "AU": "192.168.3.0",
        "ES": "172.16.2.0",
        "NL": "10.0.3.0",
        "IT": "172.16.3.0",
        "SE": "10.0.4.0",
    }
    return ip_ranges.get(country_code, "192.168.0.0")


def seed_country_data(num_conversations: int = 50):
    """
    Add country data to conversations

    Args:
        num_conversations: Number of sample conversations to create
    """
    try:
        client = get_supabase_client()

        logger.info(f"Seeding {num_conversations} conversations with country data...")

        # Create weighted country list for random selection
        weighted_countries = []
        for code, name, weight in COUNTRY_DATA:
            count = int(weight * num_conversations)
            weighted_countries.extend([(code, name)] * count)

        # Fill remaining slots
        while len(weighted_countries) < num_conversations:
            weighted_countries.append(random.choice([(code, name) for code, name, _ in COUNTRY_DATA]))

        # Shuffle to randomize order
        random.shuffle(weighted_countries)

        created_count = 0
        updated_count = 0

        # Check if we have existing conversations
        existing_response = client.table("conversations").select("id, session_id, country_code").execute()
        existing_conversations = existing_response.data if existing_response.data else []

        logger.info(f"Found {len(existing_conversations)} existing conversations")

        # Update existing conversations without country data
        for conv in existing_conversations:
            if not conv.get("country_code") and weighted_countries:
                country_code, country_name = weighted_countries.pop()
                ip_address = generate_anonymized_ip(country_code)

                client.table("conversations").update({
                    "ip_address": ip_address,
                    "country_code": country_code,
                    "country_name": country_name
                }).eq("id", conv["id"]).execute()

                updated_count += 1
                logger.info(f"Updated conversation {conv['session_id'][:8]}... with {country_name}")

        # Create new conversations if needed
        for i in range(len(weighted_countries)):
            if weighted_countries:
                country_code, country_name = weighted_countries.pop()
                ip_address = generate_anonymized_ip(country_code)

                # Generate session ID
                session_id = str(uuid.uuid4())

                # Random date within last 30 days
                days_ago = random.randint(0, 30)
                created_at = (datetime.utcnow() - timedelta(days=days_ago)).isoformat()

                conversation_data = {
                    "session_id": session_id,
                    "ip_address": ip_address,
                    "country_code": country_code,
                    "country_name": country_name,
                    "created_at": created_at,
                    "last_message_at": created_at
                }

                client.table("conversations").insert(conversation_data).execute()
                created_count += 1
                logger.info(f"Created conversation from {country_name} ({country_code})")

        logger.info("\n" + "="*80)
        logger.info("SEEDING COMPLETE")
        logger.info("="*80)
        logger.info(f"Updated conversations: {updated_count}")
        logger.info(f"Created conversations: {created_count}")
        logger.info(f"Total conversations with country data: {updated_count + created_count}")
        logger.info("\nCountry distribution:")
        logger.info("-"*80)

        # Show distribution
        all_conversations = client.table("conversations").select("country_code, country_name").execute()
        country_counts = {}
        for conv in all_conversations.data:
            code = conv.get("country_code", "UNKNOWN")
            name = conv.get("country_name", "Unknown")
            key = f"{code}|{name}"
            country_counts[key] = country_counts.get(key, 0) + 1

        for key, count in sorted(country_counts.items(), key=lambda x: x[1], reverse=True):
            code, name = key.split("|")
            logger.info(f"  {code:6s} {name:20s} {count:3d} conversations")

        logger.info("="*80)

    except Exception as e:
        logger.error(f"Seeding failed: {e}")
        raise


if __name__ == "__main__":
    # Default to 50 conversations, or use command line argument
    num_conv = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    seed_country_data(num_conv)
