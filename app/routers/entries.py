from datetime import datetime
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from database import get_db
from dependencies import require_login, require_editor, add_audit
from models import MonthlyEntry, Rov, Vessel, User
from services.kpi import MONTH_FULL_PT

router = APIRouter(prefix="/entries")
templates = Jinja2Templates(directory="templates")


def _client_ip(request: Request) -> str:
    return request.headers.get("x-forwarded-for", request.client.host if request.client else "") \
        .split(",")[0].strip()


@router.get("", response_class=HTMLResponse, name="entries_list")
def entries_list(
    request: Request,
    ano: int | None = None,
    mes: int | None = None,
    rov_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
):
    now = datetime.now()
    year = ano or now.year
    month = mes  # None = all months
    rov_pk = rov_id

    q = (
        db.query(MonthlyEntry)
        .options(joinedload(MonthlyEntry.rov).joinedload(Rov.vessel))
        .filter(MonthlyEntry.year == year)
    )
    if month:
        q = q.filter(MonthlyEntry.month == month)
    if rov_pk:
        q = q.filter(MonthlyEntry.rov_id == rov_pk)
    entries = q.order_by(MonthlyEntry.month, MonthlyEntry.rov_id).all()

    rovs = db.query(Rov).options(joinedload(Rov.vessel)).order_by(Rov.rov_id).all()
    years = sorted({y for (y,) in db.query(MonthlyEntry.year).distinct().all()} | {now.year}, reverse=True)

    return templates.TemplateResponse(
        "entries/list.html",
        {
            "request": request, "current_user": current_user, "active": "entries",
            "entries": entries, "rovs": rovs, "years": years,
            "year": year, "month": month, "rov_id": rov_pk,
        },
    )


@router.get("/new", response_class=HTMLResponse, name="entries_new")
def entries_new(
    request: Request,
    ano: int | None = None,
    mes: int | None = None,
    rov_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    now = datetime.now()
    rovs = db.query(Rov).options(joinedload(Rov.vessel)).order_by(Rov.rov_id).all()
    return templates.TemplateResponse(
        "entries/form.html",
        {
            "request": request, "current_user": current_user, "active": "entries",
            "entry": None, "rovs": rovs,
            "default_year": ano or now.year,
            "default_month": mes or now.month,
            "default_rov_id": rov_id,
        },
    )


@router.post("", name="entries_create")
def entries_create(
    request: Request,
    year: int = Form(...),
    month: int = Form(...),
    rov_id: int = Form(...),
    total_bbs: int = Form(0),
    non_conforming: int = Form(0),
    c1: int = Form(0), c2: int = Form(0), c3: int = Form(0),
    c4_crm: int = Form(0), c4_elo: int = Form(0),
    observations: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    _validate_payload(month, total_bbs, non_conforming)

    rov = db.query(Rov).filter(Rov.id == rov_id).first()
    if not rov:
        raise HTTPException(status_code=400, detail="ROV inválido.")

    existing = (
        db.query(MonthlyEntry)
        .filter(MonthlyEntry.year == year,
                MonthlyEntry.month == month,
                MonthlyEntry.rov_id == rov_id)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Já existe lançamento para {rov.rov_id} em {month:02d}/{year}. Edite-o em vez de criar novo.",
        )

    entry = MonthlyEntry(
        year=year, month=month, rov_id=rov_id,
        total_bbs=total_bbs, non_conforming=non_conforming,
        c1=c1, c2=c2, c3=c3, c4_crm=c4_crm, c4_elo=c4_elo,
        observations=observations.strip() or None,
        created_by_id=current_user.id, updated_by_id=current_user.id,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    add_audit(db, current_user.id, "entry.create",
              entity_type="MonthlyEntry", entity_id=entry.id,
              details={"rov": rov.rov_id, "year": year, "month": month,
                       "total_bbs": total_bbs, "non_conforming": non_conforming},
              ip=_client_ip(request))

    return RedirectResponse(
        request.url_for("entries_list").include_query_params(ano=year, mes=month),
        status_code=303,
    )


@router.get("/{entry_id}/edit", response_class=HTMLResponse, name="entries_edit")
def entries_edit(
    entry_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    entry = (
        db.query(MonthlyEntry)
        .options(joinedload(MonthlyEntry.rov).joinedload(Rov.vessel))
        .filter(MonthlyEntry.id == entry_id)
        .first()
    )
    if not entry:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado.")

    rovs = db.query(Rov).options(joinedload(Rov.vessel)).order_by(Rov.rov_id).all()
    return templates.TemplateResponse(
        "entries/form.html",
        {
            "request": request, "current_user": current_user, "active": "entries",
            "entry": entry, "rovs": rovs,
            "default_year": entry.year, "default_month": entry.month,
            "default_rov_id": entry.rov_id,
        },
    )


@router.post("/{entry_id}", name="entries_update")
def entries_update(
    entry_id: int,
    request: Request,
    year: int = Form(...),
    month: int = Form(...),
    rov_id: int = Form(...),
    total_bbs: int = Form(0),
    non_conforming: int = Form(0),
    c1: int = Form(0), c2: int = Form(0), c3: int = Form(0),
    c4_crm: int = Form(0), c4_elo: int = Form(0),
    observations: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    entry = db.query(MonthlyEntry).filter(MonthlyEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado.")
    _validate_payload(month, total_bbs, non_conforming)

    # If (year, month, rov) changed, ensure no clash
    if (entry.year, entry.month, entry.rov_id) != (year, month, rov_id):
        clash = (
            db.query(MonthlyEntry)
            .filter(MonthlyEntry.year == year, MonthlyEntry.month == month,
                    MonthlyEntry.rov_id == rov_id, MonthlyEntry.id != entry_id)
            .first()
        )
        if clash:
            raise HTTPException(status_code=400, detail="Já existe outro lançamento para este ROV/mês.")

    entry.year = year
    entry.month = month
    entry.rov_id = rov_id
    entry.total_bbs = total_bbs
    entry.non_conforming = non_conforming
    entry.c1, entry.c2, entry.c3 = c1, c2, c3
    entry.c4_crm, entry.c4_elo = c4_crm, c4_elo
    entry.observations = observations.strip() or None
    entry.updated_by_id = current_user.id
    db.commit()

    add_audit(db, current_user.id, "entry.update",
              entity_type="MonthlyEntry", entity_id=entry.id,
              details={"year": year, "month": month, "rov_id": rov_id,
                       "total_bbs": total_bbs, "non_conforming": non_conforming},
              ip=_client_ip(request))

    return RedirectResponse(
        request.url_for("entries_list").include_query_params(ano=year, mes=month),
        status_code=303,
    )


@router.post("/{entry_id}/delete", name="entries_delete")
def entries_delete(
    entry_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    entry = db.query(MonthlyEntry).filter(MonthlyEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado.")
    year, month = entry.year, entry.month
    db.delete(entry)
    db.commit()

    add_audit(db, current_user.id, "entry.delete",
              entity_type="MonthlyEntry", entity_id=entry_id,
              details={"year": year, "month": month}, ip=_client_ip(request))

    return RedirectResponse(
        request.url_for("entries_list").include_query_params(ano=year, mes=month),
        status_code=303,
    )


def _validate_payload(month: int, total_bbs: int, non_conforming: int):
    if not (1 <= month <= 12):
        raise HTTPException(status_code=400, detail="Mês deve estar entre 1 e 12.")
    if total_bbs < 0 or non_conforming < 0:
        raise HTTPException(status_code=400, detail="Valores não podem ser negativos.")
    if non_conforming > total_bbs:
        raise HTTPException(
            status_code=400,
            detail="Não conformes não pode ser maior que Total BBS.",
        )
