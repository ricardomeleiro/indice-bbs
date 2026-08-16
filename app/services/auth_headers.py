"""Parse Authentik forward-auth headers and upsert users."""
from datetime import datetime
from typing import Optional
from fastapi import Request
from sqlalchemy.orm import Session

from config import settings
from models import User, Role


def _pick_header(request: Request, name: str) -> Optional[str]:
    val = request.headers.get(name)
    return val.strip() if val else None


def _parse_groups(raw: Optional[str]) -> list[str]:
    if not raw:
        return []
    # Authentik sends comma-separated group names
    return [g.strip() for g in raw.split(",") if g.strip()]


def _role_for(groups: list[str]) -> Role:
    if settings.BBS_ADMIN_GROUP and settings.BBS_ADMIN_GROUP in groups:
        return Role.ADMIN
    if settings.BBS_EDITOR_GROUP and settings.BBS_EDITOR_GROUP in groups:
        return Role.EDITOR
    return Role.VIEWER


def resolve_user(request: Request, db: Session) -> Optional[User]:
    """Return the authenticated User (upserted from Authentik headers)."""
    email = _pick_header(request, settings.AUTHENTIK_HEADER_EMAIL)
    username = _pick_header(request, settings.AUTHENTIK_HEADER_USERNAME)
    name = _pick_header(request, settings.AUTHENTIK_HEADER_NAME)
    groups_raw = _pick_header(request, settings.AUTHENTIK_HEADER_GROUPS)

    if not email and settings.DEV_MODE:
        email = settings.DEV_USER_EMAIL
        username = settings.DEV_USER_EMAIL.split("@")[0]
        name = settings.DEV_USER_NAME
        # dev role forces the configured role even without groups
        dev_role = Role(settings.DEV_USER_ROLE.lower())
        return _upsert(db, email=email, username=username, name=name,
                       groups=[], forced_role=dev_role)

    if not email:
        return None

    groups = _parse_groups(groups_raw)
    return _upsert(db, email=email, username=username or email, name=name or email,
                   groups=groups, forced_role=None)


def _upsert(db: Session, *, email: str, username: str, name: str,
            groups: list[str], forced_role: Optional[Role]) -> User:
    email_norm = email.lower().strip()
    user = db.query(User).filter(User.email == email_norm).first()
    role = forced_role if forced_role is not None else _role_for(groups)
    now = datetime.utcnow()

    if user is None:
        user = User(email=email_norm, username=username, name=name,
                    role=role, authentik_groups=groups, is_active=True,
                    last_login_at=now)
        db.add(user)
    else:
        user.username = username or user.username
        user.name = name or user.name
        user.authentik_groups = groups
        # Only auto-update role from groups if not dev-forced and user is not manually pinned admin
        # (admins keep their role even if groups change — reset via /admin/users if needed)
        if forced_role is None and user.role != Role.ADMIN:
            user.role = role
        elif forced_role is not None:
            user.role = forced_role
        user.last_login_at = now

    db.commit()
    db.refresh(user)
    return user
