import csv
import io
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload

from database import get_db
from dependencies import require_login
from models import MonthlyEntry, Rov, User

router = APIRouter(prefix="/export")


@router.get("/entries.csv", name="export_entries_csv")
def export_entries_csv(
    ano: int | None = None,
    mes: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_login),
):
    q = (
        db.query(MonthlyEntry)
        .options(joinedload(MonthlyEntry.rov).joinedload(Rov.vessel))
    )
    if ano:
        q = q.filter(MonthlyEntry.year == ano)
    if mes:
        q = q.filter(MonthlyEntry.month == mes)
    entries = q.order_by(MonthlyEntry.year, MonthlyEntry.month, MonthlyEntry.rov_id).all()

    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow([
        "Ano", "Mês", "ROV", "Embarcação", "Contratante",
        "Total BBS", "Não conformes", "Conformes", "KPI %",
        "C1", "C2", "C3", "C4-CRM", "C4-Elo",
        "Observações",
    ])
    for e in entries:
        kpi = f"{e.kpi_pct*100:.2f}".replace(".", ",") if e.kpi_pct is not None else ""
        w.writerow([
            e.year, e.month, e.rov.rov_id, e.rov.vessel.name, e.rov.vessel.contractor,
            e.total_bbs, e.non_conforming, e.conforming, kpi,
            e.c1, e.c2, e.c3, e.c4_crm, e.c4_elo,
            e.observations or "",
        ])
    buf.seek(0)
    filename = f"indicebbs_{ano or 'all'}_{mes or 'all'}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
