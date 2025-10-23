"""
SSE Event Broadcasting Service
Manages real-time widget update notifications across all connected clients
"""

import asyncio
from typing import Set, Dict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Global list of connected client queues
_connected_clients: Set[asyncio.Queue] = set()


async def broadcast_event(event_type: str, data: dict):
    """
    Broadcast an event to all connected SSE clients.

    Args:
        event_type: Type of event (e.g., "settings_updated")
        data: Event payload (will be JSON serialized)
    """
    if not _connected_clients:
        logger.debug(f"No active SSE connections to broadcast '{event_type}'")
        return

    # Prepare message
    message = {
        "type": event_type,
        "data": data,
        "timestamp": datetime.utcnow().isoformat()
    }

    # Send to all connected clients
    dead_queues = set()
    success_count = 0

    for queue in _connected_clients:
        try:
            # Non-blocking put (don't wait if queue is full)
            queue.put_nowait(message)
            success_count += 1
        except asyncio.QueueFull:
            logger.warning("Client queue full, marking for removal")
            dead_queues.add(queue)
        except Exception as e:
            logger.error(f"Error broadcasting to client: {e}")
            dead_queues.add(queue)

    # Remove dead connections
    for queue in dead_queues:
        _connected_clients.discard(queue)

    logger.info(f"Broadcasted '{event_type}' to {success_count}/{len(_connected_clients)} clients")


def get_connection_count() -> int:
    """Get the number of active SSE connections."""
    return len(_connected_clients)


async def add_client() -> asyncio.Queue:
    """Add a new SSE client and return its queue."""
    queue = asyncio.Queue(maxsize=10)
    _connected_clients.add(queue)
    logger.info(f"SSE client connected. Total: {len(_connected_clients)}")
    return queue


async def remove_client(queue: asyncio.Queue):
    """Remove an SSE client."""
    _connected_clients.discard(queue)
    logger.info(f"SSE client disconnected. Remaining: {len(_connected_clients)}")
