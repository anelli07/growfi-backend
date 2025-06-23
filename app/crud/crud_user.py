# from typing import Any, Dict, Optional, Union
from typing import Optional
import uuid

from sqlmodel import Session
from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.crud.base import CRUDBase


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    def get_by_email(self, db: Session, *, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()

    def get_by_google_id(self, db: Session, *, google_id: str) -> Optional[User]:
        return db.query(User).filter(User.google_id == google_id).first()

    def create(self, db: Session, *, obj_in: UserCreate) -> User:
        verification_token = uuid.uuid4().hex
        db_obj = User(
            email=obj_in.email,
            hashed_password=get_password_hash(obj_in.password),
            full_name=obj_in.full_name,
            email_verification_token=verification_token,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def create_with_google(
        self, db: Session, *, full_name: Optional[str], email: str, google_id: str
    ) -> User:
        db_obj = User(
            full_name=full_name,
            email=email,
            google_id=google_id,
            is_email_verified=True,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: User, obj_in: UserUpdate) -> User:
        update_data = obj_in.dict(exclude_unset=True)
        return super().update(db, db_obj=db_obj, obj_in=update_data)

    def authenticate(self, db: Session, *, email: str, password: str) -> Optional[User]:
        user = self.get_by_email(db, email=email)
        if not user:
            return None
        if not user.hashed_password:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    def is_active(self, user: User) -> bool:
        return user.is_active

    def get_by_verification_token(self, db: Session, *, token: str) -> Optional[User]:
        return db.query(User).filter(User.email_verification_token == token).first()

    def mark_as_verified(self, db: Session, *, user: User) -> User:
        user.is_email_verified = True
        user.email_verification_token = None
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


user = CRUDUser(User)
