from datetime import datetime
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from database import get_db
from dependencies import require_admin, add_audit
from models import (
    User, Role, Vessel, VesselMaturity, Maturity, MATURITY_LABELS,
    META_BY_MATURITY, AuditLog,
)
from templating import templates

router = APIRouter(prefix="/admin")


def _client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else ""


# --- Vessels ---
@router.get("/vessels", response_class=HTMLResponse, name="admin_vessels")
def admin_vessels(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    vessels = db.query(Vessel).order_by(Vessel.name).all()
    return templates.TemplateResponse(
        "admin/vessels.html",
        {"request": request, "current_user": current_user, "active": "admin",
         "vessels": vessels},
    )


@router.post("/vessels/{vessel_id}", name="admin_vessels_update")
def admin_vessels_update(
    vessel_id: int, request: Request,
    name: str = Form(...), contractor: str = Form(...),
    is_active: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    v = db.query(Vessel).filter(Vessel.id == vessel_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Embarcação não encontrada.")
    v.name = name.strip()
    v.contractor = contractor.strip()
    v.is_active = bool(is_active)
    db.commit()
    add_audit(db, current_user.id, "vessel.update",
              entity_type="Vessel", entity_id=v.id,
              details={"name": v.name, "contractor": v.contractor, "is_active": v.is_active},
              ip=_client_ip(request))
    return RedirectResponse(request.url_for("admin_vessels"), status_code=303)


# --- Maturity ---
@router.get("/maturidade", response_class=HTMLResponse, name="admin_maturity")
def admin_maturity(
    request: Request,
    ano: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    year = ano or datetime.now().year
    vessels = db.query(Vessel).order_by(Vessel.name).all()
    existing = {
        m.vessel_id: m for m in db.query(VesselMaturity).filter(VesselMaturity.year == year).all()
    }
    rows = [
        {"vessel": v, "maturity": (existing[v.id].maturity if v.id in existing else Maturity.INICIAL)}
        for v in vessels
    ]
    return templates.TemplateResponse(
        "admin/maturidade.html",
        {"request": request, "current_user": current_user, "active": "admin",
         "year": year, "rows": rows,
         "maturities": list(Maturity), "MATURITY_LABELS": MATURITY_LABELS,
         "META_BY_MATURITY": {k.value: v for k, v in META_BY_MATURITY.items()}},
    )


@router.post("/maturidade", name="admin_maturity_save")
async def admin_maturity_save(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    form = await request.form()
    year = int(form.get("year"))
    for key, val in form.items():
        if not key.startswith("m_"):
            continue
        vessel_id = int(key[2:])
        maturity = Maturity(val)
        existing = (
            db.query(VesselMaturity)
            .filter(VesselMaturity.vessel_id == vessel_id, VesselMaturity.year == year)
            .first()
        )
        if existing:
            existing.maturity = maturity
        else:
            db.add(VesselMaturity(vessel_id=vessel_id, year=year, maturity=maturity))
    db.commit()
    add_audit(db, current_user.id, "maturity.save",
              entity_type="VesselMaturity", details={"year": year}, ip=_client_ip(request))
    return RedirectResponse(request.url_for("admin_maturity").include_query_params(ano=year),
                            status_code=303)


# --- Users ---
@router.get("/users", response_class=HTMLResponse, name="admin_users")
def admin_users(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    users = db.query(User).order_by(User.name).all()
    return templates.TemplateResponse(
        "admin/users.html",
        {"request": request, "current_user": current_user, "active": "admin",
         "users": users, "roles": list(Role)},
    )


@router.post("/users/{user_id}", name="admin_users_update")
def admin_users_update(
    user_id: int, request: Request,
    role: str = Form(...), is_active: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    u.role = Role(role)
    u.is_active = bool(is_active)
    db.commit()
    add_audit(db, current_user.id, "user.update",
              entity_type="User", entity_id=u.id,
              details={"role": u.role.value, "is_active": u.is_active},
              ip=_client_ip(request))
    return RedirectResponse(request.url_for("admin_users"), status_code=303)


# --- Audit log ---
@router.get("/audit", response_class=HTMLResponse, name="admin_audit")
def admin_audit(
    request: Request,
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    logs = (
        db.query(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .limit(min(max(limit, 10), 1000))
        .all()
    )
    users_by_id = {u.id: u for u in db.query(User).all()}
    return templates.TemplateResponse(
        "admin/audit.html",
        {"request": request, "current_user": current_user, "active": "admin",
         "logs": logs, "users_by_id": users_by_id, "limit": limit},
    )
