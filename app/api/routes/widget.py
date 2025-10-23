"""
Widget Settings API Endpoints
Includes SSE real-time update broadcasting
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from typing import Dict
import asyncio
import json
import hashlib
from datetime import datetime

from app.services.widget_service import get_widget_settings, update_widget_settings, reset_widget_settings
from app.services.sse_broadcaster import broadcast_event, get_connection_count, add_client, remove_client
from app.models.widget import WidgetSettings, WidgetSettingsUpdate
from app.core.dependencies import get_current_user
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


def generate_version_hash(settings: dict) -> str:
    """
    Generate a hash of settings to detect changes.
    Only changes when actual settings content changes.
    """
    settings_str = json.dumps(settings, sort_keys=True)
    return hashlib.sha256(settings_str.encode()).hexdigest()[:16]


@router.get("/", response_model=Dict)
async def get_settings() -> Dict:
    """
    Get current widget settings with version hash

    **Public endpoint** - No authentication required
    **Returns:** Widget customization settings with version hash for change detection
    """
    try:
        settings = await get_widget_settings()
        version_hash = generate_version_hash(settings)

        return {
            "settings": settings,
            "version": version_hash,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching widget settings: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve widget settings: {str(e)}"
        )


@router.put("/", response_model=Dict)
async def update_settings(
    settings: WidgetSettingsUpdate,
    current_user = Depends(get_current_user)
) -> Dict:
    """
    Update widget settings and broadcast to all connected embeds

    **Authentication Required:** Admin users only

    **Request Body:** Partial or full widget settings update

    **Returns:** Updated widget settings with version hash

    **Side Effects:** Broadcasts "settings_updated" event to all connected SSE clients
    """
    try:
        logger.info(f"Updating widget settings by user {current_user['email']}")

        # Update settings in database
        updated_settings = await update_widget_settings(settings)

        # Generate version hash
        version_hash = generate_version_hash(updated_settings)

        # Get list of updated field names for notification
        updated_fields = [
            field for field, value in settings.model_dump(exclude_unset=True).items()
            if value is not None
        ]

        # **KEY: Broadcast update event to all connected embeds**
        await broadcast_event(
            event_type="settings_updated",
            data={
                "version": version_hash,
                "updated_fields": updated_fields,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

        logger.info(f"Settings updated and broadcast to {get_connection_count()} clients")

        return {
            "settings": updated_settings,
            "version": version_hash,
            "message": f"Settings updated and broadcast to {get_connection_count()} active embeds"
        }

    except Exception as e:
        logger.error(f"Error updating widget settings: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update widget settings: {str(e)}"
        )


@router.post("/reset", response_model=Dict)
async def reset_settings(
    current_user = Depends(get_current_user)
) -> Dict:
    """
    Reset widget settings to defaults and broadcast to all connected embeds

    **Authentication Required:** Admin users only

    **Returns:** Default widget settings with version hash
    """
    try:
        logger.info(f"Resetting widget settings by user {current_user['email']}")
        default_settings = await reset_widget_settings()

        # Generate version hash
        version_hash = generate_version_hash(default_settings)

        # Broadcast reset event
        await broadcast_event(
            event_type="settings_updated",
            data={
                "version": version_hash,
                "updated_fields": ["all"],
                "timestamp": datetime.utcnow().isoformat()
            }
        )

        logger.info(f"Settings reset and broadcast to {get_connection_count()} clients")

        return {
            "settings": default_settings,
            "version": version_hash,
            "message": f"Settings reset and broadcast to {get_connection_count()} active embeds"
        }

    except Exception as e:
        logger.error(f"Error resetting widget settings: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset widget settings: {str(e)}"
        )


# ========== SSE Event Stream Endpoint ==========

async def event_stream_generator(request: Request):
    """
    Persistent SSE stream generator for widget updates.
    Yields properly formatted SSE messages and keeps connection alive indefinitely.
    """
    # Register this client
    queue = await add_client()

    try:
        # Send initial connection confirmation
        logger.info("Sending initial connection event")
        yield f"event: connected\ndata: {json.dumps({'message': 'SSE connection established', 'timestamp': datetime.utcnow().isoformat()})}\n\n"

        # Keep connection open and stream events
        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                logger.info("Client disconnected detected")
                break

            try:
                # Wait for events with timeout (non-blocking with timeout allows disconnect detection)
                message = await asyncio.wait_for(queue.get(), timeout=15.0)

                # Format as proper SSE event: "event: type\ndata: json\n\n"
                event_type = message["type"]
                event_data = json.dumps(message["data"])

                logger.info(f"Sending SSE event: {event_type}")
                yield f"event: {event_type}\ndata: {event_data}\n\n"

            except asyncio.TimeoutError:
                # No events in 15 seconds - send keepalive ping
                logger.debug("Sending keepalive ping")
                yield f"event: ping\ndata: {json.dumps({'timestamp': datetime.utcnow().isoformat()})}\n\n"

            # Small delay to prevent tight loop
            await asyncio.sleep(0.01)

    except asyncio.CancelledError:
        logger.info("SSE stream cancelled")
    except Exception as e:
        logger.error(f"Error in SSE stream: {e}", exc_info=True)
    finally:
        # Always clean up the client connection
        await remove_client(queue)
        logger.info("SSE client cleaned up")


@router.get("/events")
async def widget_events_stream(request: Request):
    """
    SSE endpoint for real-time widget updates.

    **Public endpoint** - No authentication required (widgets connect from third-party sites)

    **Usage:**
    ```javascript
    const eventSource = new EventSource('/api/v1/widget/events');
    eventSource.addEventListener('settings_updated', (e) => {
        const data = JSON.parse(e.data);
        // Handle update
    });
    ```

    **Events:**
    - `connected`: Initial connection confirmation
    - `settings_updated`: Widget settings have been updated (includes version hash)
    - `ping`: Keepalive message every 15 seconds
    """
    return StreamingResponse(
        event_stream_generator(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )
