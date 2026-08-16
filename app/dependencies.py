from typing import Optional
from fastapi import Request, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import User, Role, AuditLog
from services.auth_headers import resolve_user


def get_current_user_optional(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    return resolve_user(request, db)


def require_login(user: Optional[User] = Depends(get_current_user_optional)) -> User:
    if not user:
        raise HTTPException(status_code=401, detail="Autenticação necessária.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Usuário inativo.")
    return user


def require_editor(user: User = Depends(require_login)) -> User:
    if user.role not in (Role.EDITOR, Role.ADMIN):
        raise HTTPException(status_code=403, detail="Somente editores podem alterar dados.")
    return user


def require_admin(user: User = Depends(require_login)) -> User:
    if user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores.")
    return user


def add_audit(db: Session, user_id: int, action: str, *,
              entity_type: str = None, entity_id: int = None,
              details: dict = None, ip: str = None):
    log = AuditLog(
        user_id=user_id, action=action, entity_type=entity_type,
        entity_id=entity_id, details=details, ip_address=ip,
    )
    db.add(log)
    db.commit()
