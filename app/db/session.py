from sqlmodel import create_engine
from app.core.config import settings

# engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI), pool_pre_ping=True)

from sqlalchemy.pool import NullPool
engine = create_engine(
    str(settings.SQLALCHEMY_DATABASE_URI),
    pool_pre_ping=True,
    poolclass=NullPool
)