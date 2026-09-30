from datetime import datetime
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from database import get_db
from dependencies import require_login
from models import User, MonthlyEntry, Vessel
from services.kpi import (
    rollup_by_vessel_month, maturity_for, target_for, MONTH_FULL_PT,
)
from models import META_BY_MATURITY
from templating import templates

router = APIRouter()


def _available_years(db: Session, current_year: int) -> list[int]:
    years = [y for (y,) in db.query(MonthlyEntry.year).distinct().all()]
    if current_year not in years:
        years.append(current_year)
    return sorted(years, reverse=True)


@router.get("/dashboard", response_class=HTMLResponse, name="dashboard_view")
def dashboard_view(
    request: Request,
    ano: int | None = None,
    mes: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
):
    now = datetime.now()
    year = ano or now.year
    month = mes or now.month

    rollups = rollup_by_vessel_month(db, year, month)

    # attach maturity + target per vessel
    rows = []
    total_bbs = total_nc = 0
    hit_target = tracked = 0
    for r in rollups:
        target = target_for(db, r.vessel_id, year)
        maturity = maturity_for(db, r.vessel_id, year)
        kpi = r.kpi_pct
        status = None
        if kpi is not None:
            status = "yes" if kpi >= target else "no"
            tracked += 1
            if kpi >= target:
                hit_target += 1
        rows.append({
            "vessel_id": r.vessel_id,
            "vessel_name": r.vessel_name,
            "contractor": r.contractor,
            "total_bbs": r.total_bbs,
            "conforming": r.conforming,
            "non_conforming": r.non_conforming,
            "kpi_pct": kpi,
            "non_conforming_pct": r.non_conforming_pct,
            "target": target,
            "maturity": maturity,
            "status": status,
        })
        total_bbs += r.total_bbs
        total_nc += r.non_conforming

    total_conf = max(total_bbs - total_nc, 0)
    fleet_kpi = (total_conf / total_bbs) if total_bbs > 0 else None

    years = _available_years(db, now.year)

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "current_user": current_user,
            "active": "dashboard",
            "year": year, "month": month,
            "month_label": MONTH_FULL_PT[month - 1],
            "years": years,
            "rows": rows,
            "total_bbs": total_bbs,
            "total_conforming": total_conf,
            "total_non_conforming": total_nc,
            "fleet_kpi": fleet_kpi,
            "hit_target": hit_target,
            "tracked": tracked,
            "meta_map": {k.value: v for k, v in META_BY_MATURITY.items()},
        },
    )
