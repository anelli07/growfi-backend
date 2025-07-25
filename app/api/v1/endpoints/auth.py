from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from sqlmodel import Session
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from pydantic import BaseModel, EmailStr
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import text

from app import crud, schemas
from app.api import deps
from app.core import security
from app.core.config import settings
from app.schemas.token import GoogleToken, AppleToken
from app.services.email_service import send_verification_code_email, send_password_reset_email
from app.models.category import CategoryType
from app.schemas.wallet import WalletCreate
from app.schemas.category import CategoryCreate
from app.schemas.transaction import IncomeCreate, ExpenseCreate
from app.schemas.user import PasswordResetRequest, PasswordResetConfirm

router = APIRouter()


@router.post("/register", response_model=schemas.User)
async def register_user(
    *,
    db: Session = Depends(deps.get_db),
    user_in: schemas.UserCreate,
) -> Any:
    """
    Create new user and send verification code.
    """
    user = crud.user.get_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists in the system.",
        )
    user = crud.user.create(db, obj_in=user_in)

    # ДЕФОЛТНЫЕ КОШЕЛЬКИ
    wallet1 = crud.crud_wallet.create_with_user(db, WalletCreate(name="Карта", balance=0, icon_name="card", color_hex="#4F8A8B", currency="KZT"), user.id)
    wallet2 = crud.crud_wallet.create_with_user(db, WalletCreate(name="Наличные", balance=0, icon_name="cash", color_hex="#F9B208", currency="KZT"), user.id)

    # ДЕФОЛТНЫЕ КАТЕГОРИИ
    cat_income1 = crud.category.create_with_user(db, obj_in=CategoryCreate(name="Зарплата", type=CategoryType.INCOME), user=user)
    cat_expense1 = crud.category.create_with_user(db, obj_in=CategoryCreate(name="Еда", type=CategoryType.EXPENSE), user=user)
    cat_expense2 = crud.category.create_with_user(db, obj_in=CategoryCreate(name="Транспорт", type=CategoryType.EXPENSE), user=user)
    cat_expense3 = crud.category.create_with_user(db, obj_in=CategoryCreate(name="Продукты", type=CategoryType.EXPENSE), user=user)
    cat_expense4 = crud.category.create_with_user(db, obj_in=CategoryCreate(name="Развлечения", type=CategoryType.EXPENSE), user=user)
    cat_expense5 = crud.category.create_with_user(db, obj_in=CategoryCreate(name="Здоровье", type=CategoryType.EXPENSE), user=user)
    cat_expense6 = crud.category.create_with_user(db, obj_in=CategoryCreate(name="Связь", type=CategoryType.EXPENSE), user=user)
    cat_expense7 = crud.category.create_with_user(db, obj_in=CategoryCreate(name="Путешествия", type=CategoryType.EXPENSE), user=user)
    cat_expense8 = crud.category.create_with_user(db, obj_in=CategoryCreate(name="Одежда", type=CategoryType.EXPENSE), user=user)
    cat_expense9 = crud.category.create_with_user(db, obj_in=CategoryCreate(name="Красота", type=CategoryType.EXPENSE), user=user)
    


    # ДЕФОЛТНЫЕ ДОХОДЫ
    crud.income.create_with_user(db, obj_in=IncomeCreate(
        name="Зарплата",
        icon="dollarsign.circle.fill",
        color="#00FF00",
        amount=0,
        transaction_date=date.today(),
        category_id=cat_income1.id
    ), user=user)

    # ДЕФОЛТНЫЕ РАСХОДЫ
    expense_templates = [
        ("Еда", "cart.fill", "#FF0000", cat_expense1.id),
        ("Транспорт", "car.fill", "#00FF00", cat_expense2.id),
        ("Продукты", "cart.fill", "#00FF00", cat_expense3.id),
        ("Развлечения", "gamecontroller.fill", "#00FF00", cat_expense4.id),
        ("Здоровье", "cross.case.fill", "#00FF00", cat_expense5.id),
        ("Связь", "phone.fill", "#00FF00", cat_expense6.id),
        ("Путешествия", "airplane", "#00FF00", cat_expense7.id),
        ("Одежда", "tshirt.fill", "#00FF00", cat_expense8.id),
        ("Красота", "scissors", "#00FF00", cat_expense9.id),
    ]
    for name, icon, color, category_id in expense_templates:
        crud.expense.create_with_user(db, obj_in=ExpenseCreate(
            name=name,
            icon=icon,
            color=color,
            amount=0,
            transaction_date=date.today(),
            category_id=category_id,
            wallet_id=wallet1.id
        ), user=user)

    await send_verification_code_email(
        email_to=user.email,
        full_name=user.full_name or user.email,
        code=user.email_verification_code,
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
    elif not user.is_email_verified:
        raise HTTPException(status_code=400, detail="Email не подтверждён")

    access_token = security.create_access_token(user.id)
    refresh_token = security.create_refresh_token(user.id)
    user.refresh_token = refresh_token
    db.add(user)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


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
        # ДЕФОЛТНЫЕ КОШЕЛЬКИ
        wallet1 = crud.crud_wallet.create_with_user(db, WalletCreate(name="Карта", balance=0, icon_name="card", color_hex="#4F8A8B", currency="KZT"), user.id)
        wallet2 = crud.crud_wallet.create_with_user(db, WalletCreate(name="Наличные", balance=0, icon_name="cash", color_hex="#F9B208", currency="KZT"), user.id)
        # ДЕФОЛТНЫЕ КАТЕГОРИИ
        cat_income1 = crud.category.create_with_user(db, obj_in=CategoryCreate(name="Зарплата", type=CategoryType.INCOME), user=user)
        cat_expense1 = crud.category.create_with_user(db, obj_in=CategoryCreate(name="Еда", type=CategoryType.EXPENSE), user=user)
        cat_expense2 = crud.category.create_with_user(db, obj_in=CategoryCreate(name="Транспорт", type=CategoryType.EXPENSE), user=user)
        cat_expense3 = crud.category.create_with_user(db, obj_in=CategoryCreate(name="Продукты", type=CategoryType.EXPENSE), user=user)
        cat_expense4 = crud.category.create_with_user(db, obj_in=CategoryCreate(name="Развлечения", type=CategoryType.EXPENSE), user=user)
        cat_expense5 = crud.category.create_with_user(db, obj_in=CategoryCreate(name="Здоровье", type=CategoryType.EXPENSE), user=user)
        cat_expense6 = crud.category.create_with_user(db, obj_in=CategoryCreate(name="Связь", type=CategoryType.EXPENSE), user=user)
        cat_expense7 = crud.category.create_with_user(db, obj_in=CategoryCreate(name="Путешествия", type=CategoryType.EXPENSE), user=user)
        cat_expense8 = crud.category.create_with_user(db, obj_in=CategoryCreate(name="Одежда", type=CategoryType.EXPENSE), user=user)
        cat_expense9 = crud.category.create_with_user(db, obj_in=CategoryCreate(name="Красота", type=CategoryType.EXPENSE), user=user)
        # ДЕФОЛТНЫЕ ДОХОДЫ
        crud.income.create_with_user(db, obj_in=IncomeCreate(
            name="Зарплата",
            icon="dollarsign.circle.fill",
            color="#00FF00",
            amount=0,
            transaction_date=date.today(),
            category_id=cat_income1.id
        ), user=user)
        # ДЕФОЛТНЫЕ РАСХОДЫ
        expense_templates = [
            ("Еда", "cart.fill", "#FF0000", cat_expense1.id),
            ("Транспорт", "car.fill", "#00FF00", cat_expense2.id),
            ("Продукты", "cart.fill", "#00FF00", cat_expense3.id),
            ("Развлечения", "gamecontroller.fill", "#00FF00", cat_expense4.id),
            ("Здоровье", "cross.case.fill", "#00FF00", cat_expense5.id),
            ("Связь", "phone.fill", "#00FF00", cat_expense6.id),
            ("Путешествия", "airplane", "#00FF00", cat_expense7.id),
            ("Одежда", "tshirt.fill", "#00FF00", cat_expense8.id),
            ("Красота", "scissors", "#00FF00", cat_expense9.id),
        ]
        for name, icon, color, category_id in expense_templates:
            crud.expense.create_with_user(db, obj_in=ExpenseCreate(
                name=name,
                icon=icon,
                color=color,
                amount=0,
                transaction_date=date.today(),
                category_id=category_id,
                wallet_id=wallet1.id
            ), user=user)
    refresh_token = security.create_refresh_token(user.id)
    user.refresh_token = refresh_token
    db.add(user)
    db.commit()
    return {
        "access_token": security.create_access_token(user.id),
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/apple", response_model=schemas.Token)
def auth_apple(
    *, db: Session = Depends(deps.get_db), apple_token: AppleToken
) -> Any:
    """
    Authenticate with Apple.
    """
    try:
        import jwt
        from jwt.exceptions import InvalidTokenError

        token_data = jwt.decode(apple_token.token, options={"verify_signature": False})

        apple_id = token_data.get("sub")
        email = token_data.get("email")
        # full_name из токена не используем, только из body
        full_name = apple_token.full_name or token_data.get("name")

        if not apple_id:
            raise HTTPException(
                status_code=403, detail="Invalid Apple token: missing sub"
            )
        print(f"Apple login: apple_id={apple_id}, email={email}, full_name={full_name}")

    except (InvalidTokenError, Exception) as e:
        raise HTTPException(
            status_code=403, detail=f"Could not validate Apple credentials: {str(e)}"
        )

    user = crud.user.get_by_apple_id(db, apple_id=apple_id)
    if not user:
        # Если email есть — создаём нового пользователя
        if email:
            user = crud.user.create_with_apple(
                db, full_name=full_name, email=email, apple_id=apple_id
            )
            # ... (создание кошельков, категорий и т.д. как раньше)
            wallet1 = crud.crud_wallet.create_with_user(db, WalletCreate(name="Карта", balance=0, icon_name="card", color_hex="#4F8A8B", currency="KZT"), user.id)
            wallet2 = crud.crud_wallet.create_with_user(db, WalletCreate(name="Наличные", balance=0, icon_name="cash", color_hex="#F9B208", currency="KZT"), user.id)
            cat_income1 = crud.category.create_with_user(db, obj_in=CategoryCreate(name="Зарплата", type=CategoryType.INCOME), user=user)
            cat_expense1 = crud.category.create_with_user(db, obj_in=CategoryCreate(name="Еда", type=CategoryType.EXPENSE), user=user)
            cat_expense2 = crud.category.create_with_user(db, obj_in=CategoryCreate(name="Транспорт", type=CategoryType.EXPENSE), user=user)
            cat_expense3 = crud.category.create_with_user(db, obj_in=CategoryCreate(name="Продукты", type=CategoryType.EXPENSE), user=user)
            cat_expense4 = crud.category.create_with_user(db, obj_in=CategoryCreate(name="Развлечения", type=CategoryType.EXPENSE), user=user)
            cat_expense5 = crud.category.create_with_user(db, obj_in=CategoryCreate(name="Здоровье", type=CategoryType.EXPENSE), user=user)
            cat_expense6 = crud.category.create_with_user(db, obj_in=CategoryCreate(name="Связь", type=CategoryType.EXPENSE), user=user)
            cat_expense7 = crud.category.create_with_user(db, obj_in=CategoryCreate(name="Путешествия", type=CategoryType.EXPENSE), user=user)
            cat_expense8 = crud.category.create_with_user(db, obj_in=CategoryCreate(name="Одежда", type=CategoryType.EXPENSE), user=user)
            cat_expense9 = crud.category.create_with_user(db, obj_in=CategoryCreate(name="Красота", type=CategoryType.EXPENSE), user=user)
            crud.income.create_with_user(db, obj_in=IncomeCreate(
                name="Зарплата",
                icon="dollarsign.circle.fill",
                color="#00FF00",
                amount=0,
                transaction_date=date.today(),
                category_id=cat_income1.id
            ), user=user)
            expense_templates = [
                ("Еда", "cart.fill", "#FF0000", cat_expense1.id),
                ("Транспорт", "car.fill", "#00FF00", cat_expense2.id),
                ("Продукты", "cart.fill", "#00FF00", cat_expense3.id),
                ("Развлечения", "gamecontroller.fill", "#00FF00", cat_expense4.id),
                ("Здоровье", "cross.case.fill", "#00FF00", cat_expense5.id),
                ("Связь", "phone.fill", "#00FF00", cat_expense6.id),
                ("Путешествия", "airplane", "#00FF00", cat_expense7.id),
                ("Одежда", "tshirt.fill", "#00FF00", cat_expense8.id),
                ("Красота", "scissors", "#00FF00", cat_expense9.id),
            ]
            for name, icon, color, category_id in expense_templates:
                crud.expense.create_with_user(db, obj_in=ExpenseCreate(
                    name=name,
                    icon=icon,
                    color=color,
                    amount=0,
                    transaction_date=date.today(),
                    category_id=category_id,
                    wallet_id=wallet1.id
                ), user=user)
    refresh_token = security.create_refresh_token(user.id)
    user.refresh_token = refresh_token
    db.add(user)
    db.commit()
    return {
        "access_token": security.create_access_token(user.id),
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


class EmailCodeVerifyRequest(BaseModel):
    email: EmailStr
    code: str


@router.post("/verify-code")
def verify_code(
    data: EmailCodeVerifyRequest,
    db: Session = Depends(deps.get_db),
) -> Any:
    """
    Verify user's email by code.
    """
    ok = crud.user.verify_email_code(db, email=data.email, code=data.code)
    if not ok:
        raise HTTPException(status_code=400, detail="Неверный или истёкший код")
    return {"message": "Email подтверждён"}


class ResendCodeRequest(BaseModel):
    email: EmailStr


@router.post("/resend-code")
async def resend_code(
    data: ResendCodeRequest,
    db: Session = Depends(deps.get_db),
) -> Any:
    user = crud.user.get_by_email(db, email=data.email)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    code = crud.user.resend_verification_code(db, email=data.email)
    await send_verification_code_email(
        email_to=user.email,
        full_name=user.full_name or user.email,
        code=code,
    )
    return {"message": "Код отправлен повторно"}


class TokenRefreshRequest(BaseModel):
    refresh_token: str

@router.post("/refresh", response_model=schemas.Token)
def refresh_token(
    *,
    db: Session = Depends(deps.get_db),
    data: TokenRefreshRequest
) -> Any:
    """
    Обновить access_token по refresh_token
    """
    user = db.query(crud.user.model).filter_by(refresh_token=data.refresh_token).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return {
        "access_token": security.create_access_token(user.id),
        "refresh_token": user.refresh_token,
        "token_type": "bearer",
    }

class LogoutRequest(BaseModel):
    refresh_token: str

@router.post("/logout")
def logout(
    *,
    db: Session = Depends(deps.get_db),
    data: LogoutRequest
) -> Any:
    """
    Logout пользователя (инвалидировать refresh_token)
    """
    user = db.query(crud.user.model).filter_by(refresh_token=data.refresh_token).first()
    if not user:
        return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "Already logged out"})
    user.refresh_token = None
    db.add(user)
    db.commit()
    return {"message": "Logged out"}

@router.post("/reset-password-request")
async def reset_password_request(
    data: PasswordResetRequest,
    db: Session = Depends(deps.get_db),
):
    user = crud.user.get_by_email(db, email=data.email)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь с таким email не найден")
    token = crud.user.generate_reset_password_token(db, email=data.email)
    await send_password_reset_email(
        email_to=user.email,
        full_name=user.full_name or user.email,
        token=token,
    )
    return {"message": "Письмо для сброса пароля отправлено"}

@router.post("/reset-password")
def reset_password(
    data: PasswordResetConfirm,
    db: Session = Depends(deps.get_db),
):
    ok = crud.user.reset_password(db, token=data.token, new_password=data.new_password)
    if not ok:
        raise HTTPException(status_code=400, detail="Неверный или истёкший токен")
    return {"message": "Пароль успешно сброшен"}

class DeleteAccountRequest(BaseModel):
    refresh_token: str
    apple_id: Optional[str] = None
    google_id: Optional[str] = None

@router.post("/delete-account")
def delete_account(
    *, db: Session = Depends(deps.get_db), data: DeleteAccountRequest
) -> Any:
    """
    Удалить аккаунт пользователя и все связанные данные (каскадно)
    """
    print(f"[DELETE_ACCOUNT] Received request with data: {data}")
    print(f"[DELETE_ACCOUNT] refresh_token: {data.refresh_token[:20]}...")
    print(f"[DELETE_ACCOUNT] apple_id: {data.apple_id}")
    print(f"[DELETE_ACCOUNT] google_id: {data.google_id}")
    
    user = db.query(crud.user.model).filter_by(refresh_token=data.refresh_token).first()
    print(f"[DELETE_ACCOUNT] Found user by refresh_token: {user.id if user else None}")
    
    if not user and data.apple_id:
        user = db.query(crud.user.model).filter_by(apple_id=data.apple_id).first()
        print(f"[DELETE_ACCOUNT] Found user by apple_id: {user.id if user else None}")
    
    if not user and data.google_id:
        user = db.query(crud.user.model).filter_by(google_id=data.google_id).first()
        print(f"[DELETE_ACCOUNT] Found user by google_id: {user.id if user else None}")
    
    if not user:
        print(f"[DELETE_ACCOUNT] No user found with any method")
        raise HTTPException(status_code=401, detail="Invalid refresh token, apple_id, or google_id")
    
    user_id = user.id
    print(f"[DELETE_ACCOUNT] Deleting user ID: {user_id}")
    
    # Принудительно удаляем все данные пользователя через SQL
    try:
        # Удаляем транзакции
        db.execute(text('DELETE FROM expense WHERE user_id = :user_id'), {'user_id': user_id})
        db.execute(text('DELETE FROM income WHERE user_id = :user_id'), {'user_id': user_id})
        
        # Удаляем цели
        db.execute(text('DELETE FROM goal WHERE user_id = :user_id'), {'user_id': user_id})
        
        # Удаляем кошельки
        db.execute(text('DELETE FROM wallet WHERE user_id = :user_id'), {'user_id': user_id})
        
        # Удаляем категории
        db.execute(text('DELETE FROM category WHERE user_id = :user_id'), {'user_id': user_id})
        
        # Удаляем пользователя
        db.execute(text('DELETE FROM "user" WHERE id = :user_id'), {'user_id': user_id})
        
        # Удаляем orphaned данные
        db.execute(text('DELETE FROM expense WHERE user_id NOT IN (SELECT id FROM "user") OR wallet_id IS NULL OR category_id IS NULL'))
        db.execute(text('DELETE FROM income WHERE user_id NOT IN (SELECT id FROM "user") OR wallet_id IS NULL OR category_id IS NULL'))
        
        db.commit()
        print(f"[DELETE_ACCOUNT] Successfully deleted user {user_id} and all related data")
        
    except Exception as e:
        db.rollback()
        print(f"[DELETE_ACCOUNT] Error deleting user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete account: {str(e)}")
    
    return {"message": "Account and all related data deleted"}
