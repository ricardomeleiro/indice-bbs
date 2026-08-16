import enum
from sqlalchemy import Column, Integer, String, Boolean, Enum, DateTime, JSON
from sqlalchemy.sql import func
from database import Base


class Role(str, enum.Enum):
    VIEWER = "viewer"
    EDITOR = "editor"
    ADMIN = "admin"


ROLE_LABELS = {
    Role.VIEWER: "Visualizador",
    Role.EDITOR: "Editor",
    Role.ADMIN: "Administrador",
}


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(200), unique=True, index=True, nullable=False)
    username = Column(String(200))
    name = Column(String(200), nullable=False)
    role = Column(Enum(Role), default=Role.VIEWER, nullable=False)
    authentik_groups = Column(JSON, default=list)
    is_active = Column(Boolean, default=True)
    last_login_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
