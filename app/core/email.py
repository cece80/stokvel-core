import boto3
from botocore.exceptions import ClientError
from typing import Optional
from app.config import get_settings
import asyncio

__all__ = ["send_otp_email"]


async def send_otp_email(to_email: str, otp_code: str, purpose: str) -> None:
    """
    Send an OTP email via AWS SES.
    Args:
        to_email: Recipient email address
        otp_code: OTP code to send
        purpose: Purpose of OTP ("register", "login", "forgot_password")
    Raises:
        Exception if sending fails
    """
    settings = get_settings()
    aws_access_key = settings.AWS_ACCESS_KEY_ID
    aws_secret_key = settings.AWS_SECRET_ACCESS_KEY
    aws_region = settings.AWS_REGION
    sender = settings.EMAIL_FROM

    subject_map = {
        "register": "Your Registration OTP",
        "login": "Your Login OTP",
        "forgot_password": "Your Password Reset OTP",
    }
    subject = subject_map.get(purpose, "Your OTP Code")

    html_body = _otp_email_html_template(otp_code, purpose)
    text_body = f"Your OTP code is: {otp_code}\n\nThis code is valid for 10 minutes."

    ses_client = boto3.client(
        "ses",
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
        region_name=aws_region,
    )

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        _send_email_sync,
        ses_client,
        sender,
        to_email,
        subject,
        html_body,
        text_body,
    )


def _send_email_sync(
    ses_client,
    sender: str,
    recipient: str,
    subject: str,
    html_body: str,
    text_body: str,
) -> None:
    """
    Synchronous helper to send email via SES.
    """
    try:
        ses_client.send_email(
            Source=sender,
            Destination={"ToAddresses": [recipient]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {
                    "Html": {"Data": html_body, "Charset": "UTF-8"},
                    "Text": {"Data": text_body, "Charset": "UTF-8"},
                },
            },
        )
    except ClientError as e:
        raise Exception(f"Failed to send OTP email: {e.response['Error']['Message']}")


def _otp_email_html_template(otp_code: str, purpose: str) -> str:
    """
    Generate HTML email template for OTP delivery.
    Args:
        otp_code: OTP code
        purpose: Purpose string
    Returns:
        HTML string
    """
    purpose_map = {
        "register": "Registration",
        "login": "Login",
        "forgot_password": "Password Reset",
    }
    pretty_purpose = purpose_map.get(purpose, "Authentication")
    return f"""
    <html>
      <body style=\"font-family: Arial, sans-serif;\">
        <h2>{pretty_purpose} OTP</h2>
        <p>Your one-time password (OTP) is:</p>
        <div style=\"font-size: 2em; font-weight: bold; margin: 16px 0;\">{otp_code}</div>
        <p>This code is valid for 10 minutes. If you did not request this, please ignore this email.</p>
        <hr />
        <small>This is an automated message. Please do not reply.</small>
      </body>
    </html>
    """
