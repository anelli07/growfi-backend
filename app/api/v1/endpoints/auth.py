from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from app import crud, schemas
from app.api import deps
from app.core import security
from app.core.config import settings
from app.schemas.token import GoogleToken
from app.services.email_service import send_verification_email

router = APIRouter()


@router.post("/register", response_model=schemas.User)
async def register_user(
    *,
    db: Session = Depends(deps.get_db),
    user_in: schemas.UserCreate,
) -> Any:
    """
    Create new user and send verification email.
    """
    user = crud.user.get_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists in the system.",
        )
    user = crud.user.create(db, obj_in=user_in)
    await send_verification_email(
        email_to=user.email,
        full_name=user.full_name,
        verification_token=user.email_verification_token,
    )
    return user


@router.post("/login", response_model=schemas.Token)
def login(
    db: Session = Depends(deps.get_db), form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    Get an access token for a user.
    """
    user = crud.user.authenticate(
        db, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    return {
        "access_token": security.create_access_token(user.id),
        "refresh_token": security.create_refresh_token(user.id),
        "token_type": "bearer",
    }


@router.get("/verify-email", response_model=schemas.User)
def verify_email(
    token: str,
    db: Session = Depends(deps.get_db),
) -> Any:
    """
    Verify user's email address.
    """
    user = crud.user.get_by_verification_token(db, token=token)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="Invalid or expired verification token.",
        )
    user = crud.user.mark_as_verified(db, user=user)
    return user


@router.post("/google", response_model=schemas.Token)
def auth_google(
    *, db: Session = Depends(deps.get_db), google_token: GoogleToken
) -> Any:
    """
    Authenticate with Google.
    """
    try:
        id_info = id_token.verify_oauth2_token(
            google_token.token, google_requests.Request(), settings.GOOGLE_CLIENT_ID
        )
        email = id_info["email"]
        google_id = id_info["sub"]
        full_name = id_info.get("name")
    except ValueError:
        raise HTTPException(
            status_code=403, detail="Could not validate Google credentials"
        )

    user = crud.user.get_by_google_id(db, google_id=google_id)
    if not user:
        user = crud.user.get_by_email(db, email=email)
        if user:
            raise HTTPException(
                status_code=400,
                detail="A user with this email already exists. Please log in with your password to link your Google account.",
            )
        user = crud.user.create_with_google(
            db, full_name=full_name, email=email, google_id=google_id
        )

    return {
        "access_token": security.create_access_token(user.id),
        "refresh_token": security.create_refresh_token(user.id),
        "token_type": "bearer",
    }
