"""
Calendar Tool (Phase 5: Tool Ecosystem)
Check availability and schedule appointments
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from app.services.tools.tools_registry import Tool, ToolCategory
from app.core.database import get_supabase_client
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CalendarTool(Tool):
    """Tool for calendar operations"""

    def __init__(self):
        super().__init__(
            name="calendar",
            description="Check availability and schedule appointments",
            category=ToolCategory.SCHEDULING,
            enabled=True,
            requires_auth=False
        )

    def validate_params(self, params: Dict[str, Any]) -> bool:
        """Validate calendar parameters"""
        action = params.get("action")

        if action not in ["check_availability", "schedule", "list_appointments"]:
            logger.error(f"Invalid action: {action}")
            return False

        if action == "check_availability":
            if "date" not in params:
                logger.error("Missing required field: date")
                return False

        elif action == "schedule":
            required = ["date", "time", "duration_minutes", "description"]
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
                    "enum": ["check_availability", "schedule", "list_appointments"],
                    "description": "Calendar action to perform"
                },
                "date": {
                    "type": "string",
                    "description": "Date in YYYY-MM-DD format"
                },
                "time": {
                    "type": "string",
                    "description": "Time in HH:MM format (for scheduling)"
                },
                "duration_minutes": {
                    "type": "integer",
                    "description": "Duration in minutes (for scheduling)"
                },
                "description": {
                    "type": "string",
                    "description": "Appointment description"
                },
                "attendee_email": {
                    "type": "string",
                    "description": "Attendee email address"
                }
            },
            "required": ["action"]
        }

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute calendar action

        Args:
            params: Calendar action parameters

        Returns:
            Execution result
        """
        action = params["action"]
        logger.info(f"Calendar action: {action}")

        if action == "check_availability":
            return await self._check_availability(params)
        elif action == "schedule":
            return await self._schedule_appointment(params)
        elif action == "list_appointments":
            return await self._list_appointments(params)
        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}"
            }

    async def _check_availability(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check availability for a given date

        Args:
            params: Contains 'date' in YYYY-MM-DD format

        Returns:
            Available time slots
        """
        logger.info(f"Checking availability for {params['date']}")

        try:
            date_str = params["date"]
            # Parse date
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()

            # Business hours: 9 AM - 5 PM
            business_start = 9
            business_end = 17

            # Get existing appointments for this date
            client = get_supabase_client()

            start_datetime = datetime.combine(target_date, datetime.min.time())
            end_datetime = datetime.combine(target_date, datetime.max.time())

            response = client.table("appointments").select("*").gte(
                "start_time", start_datetime.isoformat()
            ).lte(
                "start_time", end_datetime.isoformat()
            ).execute()

            booked_slots = response.data or []

            # Generate available slots (1-hour increments)
            available_slots = []

            for hour in range(business_start, business_end):
                slot_start = datetime.combine(target_date, datetime.min.time()).replace(hour=hour)
                slot_end = slot_start + timedelta(hours=1)

                # Check if slot is available
                is_available = True

                for booking in booked_slots:
                    booking_start = datetime.fromisoformat(booking["start_time"].replace("Z", "+00:00"))
                    booking_end = booking_start + timedelta(minutes=booking["duration_minutes"])

                    # Check for overlap
                    if (slot_start < booking_end and slot_end > booking_start):
                        is_available = False
                        break

                if is_available:
                    available_slots.append({
                        "start": slot_start.strftime("%H:%M"),
                        "end": slot_end.strftime("%H:%M")
                    })

            logger.info(f"Found {len(available_slots)} available slots for {date_str}")

            return {
                "success": True,
                "date": date_str,
                "available_slots": available_slots,
                "total_slots": len(available_slots)
            }

        except ValueError as e:
            logger.error(f"Invalid date format: {e}")
            return {
                "success": False,
                "error": "Invalid date format. Use YYYY-MM-DD."
            }

        except Exception as e:
            logger.error(f"Error checking availability: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _schedule_appointment(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Schedule a new appointment

        Args:
            params: Appointment details

        Returns:
            Scheduling result
        """
        logger.info(f"Scheduling appointment for {params['date']} at {params['time']}")

        try:
            date_str = params["date"]
            time_str = params["time"]
            duration = params["duration_minutes"]
            description = params["description"]
            attendee_email = params.get("attendee_email")

            # Parse datetime
            datetime_str = f"{date_str} {time_str}"
            start_time = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")

            # Create appointment
            client = get_supabase_client()

            appointment_data = {
                "start_time": start_time.isoformat(),
                "duration_minutes": duration,
                "description": description,
                "attendee_email": attendee_email,
                "status": "scheduled"
            }

            response = client.table("appointments").insert(appointment_data).execute()

            if response.data:
                appointment = response.data[0]

                logger.info(f"Appointment scheduled: {appointment['id']}")

                # Send confirmation email if attendee email provided
                if attendee_email:
                    try:
                        from app.services.tools.email_tool import send_notification_email

                        await send_notification_email(
                            recipient=attendee_email,
                            subject="Appointment Confirmation",
                            message=f"""Your appointment has been scheduled:

Date: {date_str}
Time: {time_str}
Duration: {duration} minutes
Description: {description}

If you need to reschedule, please contact us.

Best regards,
Githaf Consulting"""
                        )

                        logger.info(f"Confirmation email sent to {attendee_email}")

                    except Exception as e:
                        logger.warning(f"Failed to send confirmation email: {e}")

                return {
                    "success": True,
                    "message": "Appointment scheduled successfully",
                    "appointment_id": appointment["id"],
                    "start_time": start_time.isoformat(),
                    "duration_minutes": duration
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to create appointment"
                }

        except ValueError as e:
            logger.error(f"Invalid datetime format: {e}")
            return {
                "success": False,
                "error": "Invalid date/time format. Use YYYY-MM-DD for date and HH:MM for time."
            }

        except Exception as e:
            logger.error(f"Error scheduling appointment: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _list_appointments(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        List upcoming appointments

        Args:
            params: Optional filters

        Returns:
            List of appointments
        """
        logger.info("Listing appointments")

        try:
            client = get_supabase_client()

            # Get appointments from today onwards
            now = datetime.utcnow()

            response = client.table("appointments").select("*").gte(
                "start_time", now.isoformat()
            ).order("start_time", desc=False).limit(20).execute()

            appointments = response.data or []

            formatted_appointments = []

            for apt in appointments:
                start_time = datetime.fromisoformat(apt["start_time"].replace("Z", "+00:00"))
                formatted_appointments.append({
                    "id": apt["id"],
                    "date": start_time.strftime("%Y-%m-%d"),
                    "time": start_time.strftime("%H:%M"),
                    "duration_minutes": apt["duration_minutes"],
                    "description": apt.get("description", ""),
                    "attendee_email": apt.get("attendee_email"),
                    "status": apt.get("status", "scheduled")
                })

            logger.info(f"Found {len(formatted_appointments)} upcoming appointments")

            return {
                "success": True,
                "appointments": formatted_appointments,
                "total": len(formatted_appointments)
            }

        except Exception as e:
            logger.error(f"Error listing appointments: {e}")
            return {
                "success": False,
                "error": str(e)
            }
