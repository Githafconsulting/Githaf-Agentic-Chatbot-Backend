"""
Email Tool (Phase 5: Tool Ecosystem)
Send emails via SMTP or email service APIs
"""
from typing import Dict, Any, List, Optional
from app.services.tools.tools_registry import Tool, ToolCategory
from app.utils.logger import get_logger
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

logger = get_logger(__name__)


class EmailTool(Tool):
    """Tool for sending emails"""

    def __init__(self):
        super().__init__(
            name="send_email",
            description="Send email to recipients with subject and body",
            category=ToolCategory.COMMUNICATION,
            enabled=True,  # Enabled by default, but will fail gracefully if not configured
            requires_auth=True
        )

        # SMTP configuration from environment
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.from_email = os.getenv("FROM_EMAIL", self.smtp_user)
        self.from_name = os.getenv("FROM_NAME", "Githaf Consulting Bot")

        # Check if configured
        self.configured = bool(self.smtp_user and self.smtp_password)

        if not self.configured:
            logger.warning("Email tool not configured (missing SMTP_USER or SMTP_PASSWORD)")

    def validate_params(self, params: Dict[str, Any]) -> bool:
        """Validate email parameters"""
        required = ["to", "subject", "body"]

        for field in required:
            if field not in params:
                logger.error(f"Missing required field: {field}")
                return False

        # Validate email format
        to_email = params["to"]
        if isinstance(to_email, str):
            if "@" not in to_email:
                logger.error(f"Invalid email format: {to_email}")
                return False
        elif isinstance(to_email, list):
            for email in to_email:
                if "@" not in email:
                    logger.error(f"Invalid email format: {email}")
                    return False

        return True

    def get_schema(self) -> Dict[str, Any]:
        """Get parameter schema"""
        return {
            "type": "object",
            "properties": {
                "to": {
                    "type": ["string", "array"],
                    "description": "Recipient email address(es)",
                    "items": {"type": "string"}
                },
                "subject": {
                    "type": "string",
                    "description": "Email subject line"
                },
                "body": {
                    "type": "string",
                    "description": "Email body content"
                },
                "cc": {
                    "type": ["string", "array"],
                    "description": "CC email address(es) (optional)",
                    "items": {"type": "string"}
                },
                "html": {
                    "type": "boolean",
                    "description": "Whether body is HTML (default: false)"
                }
            },
            "required": ["to", "subject", "body"]
        }

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send email

        Args:
            params: Email parameters (to, subject, body, cc, html)

        Returns:
            Execution result
        """
        logger.info(f"Sending email to {params['to']}")

        # Check if configured
        if not self.configured:
            logger.error("Email tool not configured")
            return {
                "success": False,
                "error": "Email service not configured. Please set SMTP_USER and SMTP_PASSWORD environment variables."
            }

        try:
            # Extract parameters
            to_emails = params["to"]
            if isinstance(to_emails, str):
                to_emails = [to_emails]

            subject = params["subject"]
            body = params["body"]
            cc_emails = params.get("cc", [])
            if isinstance(cc_emails, str):
                cc_emails = [cc_emails]
            is_html = params.get("html", False)

            # Create message
            msg = MIMEMultipart("alternative")
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = ", ".join(to_emails)
            if cc_emails:
                msg["Cc"] = ", ".join(cc_emails)
            msg["Subject"] = subject

            # Add body
            if is_html:
                msg.attach(MIMEText(body, "html"))
            else:
                msg.attach(MIMEText(body, "plain"))

            # Send via SMTP
            all_recipients = to_emails + cc_emails

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()  # Secure connection
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg, from_addr=self.from_email, to_addrs=all_recipients)

            logger.info(f"Email sent successfully to {len(all_recipients)} recipient(s)")

            return {
                "success": True,
                "message": f"Email sent to {len(all_recipients)} recipient(s)",
                "recipients": to_emails,
                "cc": cc_emails
            }

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
            return {
                "success": False,
                "error": "Email authentication failed. Check SMTP credentials."
            }

        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            return {
                "success": False,
                "error": f"Failed to send email: {str(e)}"
            }

        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Example usage function (for testing)
async def send_notification_email(recipient: str, subject: str, message: str) -> bool:
    """
    Helper function to send notification emails

    Args:
        recipient: Email address
        subject: Email subject
        message: Email body

    Returns:
        True if sent successfully
    """
    tool = EmailTool()

    result = await tool.execute({
        "to": recipient,
        "subject": subject,
        "body": message
    })

    return result.get("success", False)
