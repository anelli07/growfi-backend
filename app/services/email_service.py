from pathlib import Path
from typing import Any, Dict, List

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from pydantic import BaseModel, EmailStr

from app.core.config import settings


class EmailSchema(BaseModel):
    email: List[EmailStr]
    body: Dict[str, Any]


conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=settings.MAIL_STARTTLS,
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
    MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
    TEMPLATE_FOLDER=Path(__file__).parent.parent / "templates" / "email",
    USE_CREDENTIALS=True,
    SUPPRESS_SEND=settings.MAIL_CONSOLE,
)


async def send_email(
    recipients: List[EmailStr],
    subject: str,
    template_name: str,
    template_body: Dict[str, Any],
):
    message = MessageSchema(
        subject=subject,
        recipients=recipients,
        template_body=template_body,
        subtype=MessageType.html,
    )

    fm = FastMail(conf)
    await fm.send_message(message, template_name=template_name)


async def send_verification_email(
    email_to: EmailStr, full_name: str, verification_token: str
):
    project_name = settings.MAIL_FROM_NAME
    subject = f"{project_name} - Подтверждение аккаунта"

    # This should be your frontend URL
    verification_link = f"http://localhost:3000/verify-email?token={verification_token}"

    template_body = {
        "full_name": full_name,
        "verification_link": verification_link,
        "project_name": project_name,
    }

    await send_email(
        recipients=[email_to],
        subject=subject,
        template_name="verify_email.html",
        template_body=template_body,
    )
