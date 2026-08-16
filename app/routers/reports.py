from datetime import datetime
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from dependencies import require_login
from models import (
    MonthlyEntry, Rov, Vessel, User, VesselMaturity, META_BY_MATURITY, Maturity,
)
from services.kpi import (
    evolution_by_vessel, fleet_evolution, rollup_by_vessel_year, rollup_by_vessel_month,
    contractor_rollup, target_for, MONTH_LABELS_PT, MONTH_FULL_PT,
)

router = APIRouter(prefix="/reports")
templates = Jinja2Templates(directory="templates")


def _years(db: Session, current: int) -> list[int]:
    ys = {y for (y,) in db.query(MonthlyEntry.year).distinct().all()} | {current}
    return sorted(ys, reverse=True)


@router.get("/evolucao", response_class=HTMLResponse, name="report_evolucao")
def report_evolucao(
    request: Request,
    ano: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
):
    now = datetime.now()
    year = ano or now.year
    series = evolution_by_vessel(db, year)
    fleet = fleet_evolution(db, year)

    vessels = sorted(series.keys())
    return templates.TemplateResponse(
        "reports/evolucao.html",
        {
            "request": request, "current_user": current_user, "active": "reports",
            "year": year, "years": _years(db, now.year),
            "vessels": vessels,
            "series": series,
            "fleet": fleet,
        },
    )


@router.get("/pareto", response_class=HTMLResponse, name="report_pareto")
def report_pareto(
    request: Request,
    ano: int | None = None,
    mes: int | None = None,
    vessel_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
):
    now = datetime.now()
    year = ano or now.year
    month = mes  # None = full year

    q = (
        db.query(
            func.coalesce(func.sum(MonthlyEntry.c1), 0),
            func.coalesce(func.sum(MonthlyEntry.c2), 0),
            func.coalesce(func.sum(MonthlyEntry.c3), 0),
            func.coalesce(func.sum(MonthlyEntry.c4_crm), 0),
            func.coalesce(func.sum(MonthlyEntry.c4_elo), 0),
        )
        .select_from(MonthlyEntry)
        .join(Rov, Rov.id == MonthlyEntry.rov_id)
        .filter(MonthlyEntry.year == year)
    )
    if month:
        q = q.filter(MonthlyEntry.month == month)
    if vessel_id:
        q = q.filter(Rov.vessel_id == vessel_id)

    c1, c2, c3, c4crm, c4elo = [int(x or 0) for x in q.one()]
    buckets = [
        ("C1 · Nome/Função", c1),
        ("C2 · Classificação incoerente", c2),
        ("C3 · Dano potencial", c3),
        ("C4 · CRM", c4crm),
        ("C4 · Elo", c4elo),
    ]
    buckets.sort(key=lambda t: t[1], reverse=True)
    total = sum(v for _, v in buckets) or 1
    cum = 0
    rows = []
    for label, v in buckets:
        cum += v
        rows.append({"label": label, "value": v, "cum_pct": cum / total})

    vessels = db.query(Vessel).order_by(Vessel.name).all()
    return templates.TemplateResponse(
        "reports/pareto.html",
        {
            "request": request, "current_user": current_user, "active": "reports",
            "year": year, "month": month, "vessel_id": vessel_id,
            "years": _years(db, now.year), "vessels": vessels,
            "rows": rows, "total": total,
        },
    )


@router.get("/ranking", response_class=HTMLResponse, name="report_ranking")
def report_ranking(
    request: Request,
    ano: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
):
    now = datetime.now()
    year = ano or now.year
    rows = rollup_by_vessel_year(db, year)

    ranked = []
    for r in rows:
        if r.total_bbs <= 0:
            continue
        target = target_for(db, r.vessel_id, year)
        ranked.append({
            "vessel_name": r.vessel_name,
            "contractor": r.contractor,
            "kpi_pct": r.kpi_pct,
            "total_bbs": r.total_bbs,
            "conforming": r.conforming,
            "target": target,
            "hit": r.kpi_pct is not None and r.kpi_pct >= target,
        })
    ranked.sort(key=lambda x: (x["kpi_pct"] or 0), reverse=True)

    return templates.TemplateResponse(
        "reports/ranking.html",
        {
            "request": request, "current_user": current_user, "active": "reports",
            "year": year, "years": _years(db, now.year), "rows": ranked,
        },
    )


@router.get("/heatmap", response_class=HTMLResponse, name="report_heatmap")
def report_heatmap(
    request: Request,
    ano: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
):
    now = datetime.now()
    year = ano or now.year
    series = evolution_by_vessel(db, year)
    vessels = sorted(series.keys())
    matrix = [[series[v][m] for m in range(12)] for v in vessels]
    return templates.TemplateResponse(
        "reports/heatmap.html",
        {
            "request": request, "current_user": current_user, "active": "reports",
            "year": year, "years": _years(db, now.year),
            "vessels": vessels, "matrix": matrix,
        },
    )


@router.get("/contratante", response_class=HTMLResponse, name="report_contratante")
def report_contratante(
    request: Request,
    ano: int | None = None,
    mes: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
):
    now = datetime.now()
    year = ano or now.year
    rows = contractor_rollup(db, year, mes)
    return templates.TemplateResponse(
        "reports/contratante.html",
        {
            "request": request, "current_user": current_user, "active": "reports",
            "year": year, "month": mes,
            "years": _years(db, now.year), "rows": rows,
        },
    )
