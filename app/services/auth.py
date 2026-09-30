"""User authentication and resolution service."""
from datetime import datetime
from typing import Optional
from fastapi import Request
from sqlalchemy.orm import Session

from config import settings
from models import User, Role


def resolve_user(request: Request, db: Session) -> Optional[User]:
    """Return the active system user, creating or updating if necessary."""
    email = (settings.DEFAULT_USER_EMAIL or "admin@c-innovation.com.br").lower().strip()
    username = email.split("@")[0]
    name = settings.DEFAULT_USER_NAME or "Administrador"
    role_str = (settings.DEFAULT_USER_ROLE or "admin").lower().strip()
    try:
        default_role = Role(role_str)
    except ValueError:
        default_role = Role.ADMIN

    now = datetime.utcnow()
    user = db.query(User).filter(User.email == email).first()

    if user is None:
        user = User(
            email=email,
            username=username,
            name=name,
            role=default_role,
            is_active=True,
            last_login_at=now,
        )
        db.add(user)
    else:
        user.name = name or user.name
        user.last_login_at = now

    db.commit()
    db.refresh(user)
    return user
