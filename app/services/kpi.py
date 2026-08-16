"""KPI aggregations — vessel-level rollups from monthly ROV entries."""
from dataclasses import dataclass
from typing import Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from models import (
    MonthlyEntry, Rov, Vessel, VesselMaturity, Maturity, META_BY_MATURITY,
)


MONTH_LABELS_PT = [
    "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
    "Jul", "Ago", "Set", "Out", "Nov", "Dez",
]

MONTH_FULL_PT = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]


@dataclass
class VesselMonthlyRollup:
    vessel_id: int
    vessel_name: str
    contractor: str
    year: int
    month: int
    total_bbs: int
    non_conforming: int
    c1: int
    c2: int
    c3: int
    c4_crm: int
    c4_elo: int
    entries_count: int

    @property
    def conforming(self) -> int:
        return max(self.total_bbs - self.non_conforming, 0)

    @property
    def kpi_pct(self) -> Optional[float]:
        if self.total_bbs <= 0:
            return None
        return self.conforming / self.total_bbs

    @property
    def non_conforming_pct(self) -> Optional[float]:
        if self.total_bbs <= 0:
            return None
        return self.non_conforming / self.total_bbs


def rollup_by_vessel_month(db: Session, year: int, month: int) -> list[VesselMonthlyRollup]:
    """One row per active vessel for the given (year, month)."""
    q = (
        db.query(
            Vessel.id.label("vessel_id"),
            Vessel.name.label("vessel_name"),
            Vessel.contractor.label("contractor"),
            func.coalesce(func.sum(MonthlyEntry.total_bbs), 0).label("total_bbs"),
            func.coalesce(func.sum(MonthlyEntry.non_conforming), 0).label("non_conforming"),
            func.coalesce(func.sum(MonthlyEntry.c1), 0).label("c1"),
            func.coalesce(func.sum(MonthlyEntry.c2), 0).label("c2"),
            func.coalesce(func.sum(MonthlyEntry.c3), 0).label("c3"),
            func.coalesce(func.sum(MonthlyEntry.c4_crm), 0).label("c4_crm"),
            func.coalesce(func.sum(MonthlyEntry.c4_elo), 0).label("c4_elo"),
            func.count(MonthlyEntry.id).label("entries_count"),
        )
        .select_from(Vessel)
        .join(Rov, Rov.vessel_id == Vessel.id)
        .outerjoin(
            MonthlyEntry,
            (MonthlyEntry.rov_id == Rov.id)
            & (MonthlyEntry.year == year)
            & (MonthlyEntry.month == month),
        )
        .group_by(Vessel.id, Vessel.name, Vessel.contractor)
        .order_by(Vessel.name)
    )
    rows = q.all()
    return [
        VesselMonthlyRollup(
            vessel_id=r.vessel_id, vessel_name=r.vessel_name, contractor=r.contractor,
            year=year, month=month,
            total_bbs=int(r.total_bbs or 0), non_conforming=int(r.non_conforming or 0),
            c1=int(r.c1 or 0), c2=int(r.c2 or 0), c3=int(r.c3 or 0),
            c4_crm=int(r.c4_crm or 0), c4_elo=int(r.c4_elo or 0),
            entries_count=int(r.entries_count or 0),
        )
        for r in rows
    ]


def rollup_by_vessel_year(db: Session, year: int) -> list[VesselMonthlyRollup]:
    """One row per vessel with year totals (month=0 sentinel)."""
    q = (
        db.query(
            Vessel.id.label("vessel_id"),
            Vessel.name.label("vessel_name"),
            Vessel.contractor.label("contractor"),
            func.coalesce(func.sum(MonthlyEntry.total_bbs), 0).label("total_bbs"),
            func.coalesce(func.sum(MonthlyEntry.non_conforming), 0).label("non_conforming"),
            func.coalesce(func.sum(MonthlyEntry.c1), 0).label("c1"),
            func.coalesce(func.sum(MonthlyEntry.c2), 0).label("c2"),
            func.coalesce(func.sum(MonthlyEntry.c3), 0).label("c3"),
            func.coalesce(func.sum(MonthlyEntry.c4_crm), 0).label("c4_crm"),
            func.coalesce(func.sum(MonthlyEntry.c4_elo), 0).label("c4_elo"),
            func.count(MonthlyEntry.id).label("entries_count"),
        )
        .select_from(Vessel)
        .join(Rov, Rov.vessel_id == Vessel.id)
        .outerjoin(MonthlyEntry, (MonthlyEntry.rov_id == Rov.id) & (MonthlyEntry.year == year))
        .group_by(Vessel.id, Vessel.name, Vessel.contractor)
        .order_by(Vessel.name)
    )
    rows = q.all()
    return [
        VesselMonthlyRollup(
            vessel_id=r.vessel_id, vessel_name=r.vessel_name, contractor=r.contractor,
            year=year, month=0,
            total_bbs=int(r.total_bbs or 0), non_conforming=int(r.non_conforming or 0),
            c1=int(r.c1 or 0), c2=int(r.c2 or 0), c3=int(r.c3 or 0),
            c4_crm=int(r.c4_crm or 0), c4_elo=int(r.c4_elo or 0),
            entries_count=int(r.entries_count or 0),
        )
        for r in rows
    ]


def evolution_by_vessel(db: Session, year: int) -> dict[str, list[Optional[float]]]:
    """{vessel_name: [kpi_month_1, ..., kpi_month_12]} — None where no data."""
    q = (
        db.query(
            Vessel.name.label("vessel_name"),
            MonthlyEntry.month.label("month"),
            func.sum(MonthlyEntry.total_bbs).label("total_bbs"),
            func.sum(MonthlyEntry.non_conforming).label("non_conforming"),
        )
        .select_from(Vessel)
        .join(Rov, Rov.vessel_id == Vessel.id)
        .join(MonthlyEntry, (MonthlyEntry.rov_id == Rov.id) & (MonthlyEntry.year == year))
        .group_by(Vessel.name, MonthlyEntry.month)
        .order_by(Vessel.name, MonthlyEntry.month)
    )
    out: dict[str, list[Optional[float]]] = {}
    for r in q.all():
        row = out.setdefault(r.vessel_name, [None] * 12)
        total = int(r.total_bbs or 0)
        nc = int(r.non_conforming or 0)
        row[r.month - 1] = (total - nc) / total if total > 0 else None
    return out


def fleet_evolution(db: Session, year: int) -> list[Optional[float]]:
    """Fleet-wide KPI% per month for the year."""
    q = (
        db.query(
            MonthlyEntry.month.label("month"),
            func.sum(MonthlyEntry.total_bbs).label("total_bbs"),
            func.sum(MonthlyEntry.non_conforming).label("non_conforming"),
        )
        .filter(MonthlyEntry.year == year)
        .group_by(MonthlyEntry.month)
        .order_by(MonthlyEntry.month)
    )
    out: list[Optional[float]] = [None] * 12
    for r in q.all():
        total = int(r.total_bbs or 0)
        nc = int(r.non_conforming or 0)
        out[r.month - 1] = (total - nc) / total if total > 0 else None
    return out


def contractor_rollup(db: Session, year: int, month: Optional[int] = None) -> list[dict]:
    """KPI% by contractor for year (and optionally month)."""
    q = (
        db.query(
            Vessel.contractor.label("contractor"),
            func.coalesce(func.sum(MonthlyEntry.total_bbs), 0).label("total_bbs"),
            func.coalesce(func.sum(MonthlyEntry.non_conforming), 0).label("non_conforming"),
        )
        .select_from(Vessel)
        .join(Rov, Rov.vessel_id == Vessel.id)
        .join(MonthlyEntry, MonthlyEntry.rov_id == Rov.id)
        .filter(MonthlyEntry.year == year)
    )
    if month is not None:
        q = q.filter(MonthlyEntry.month == month)
    q = q.group_by(Vessel.contractor).order_by(Vessel.contractor)

    result = []
    for r in q.all():
        total = int(r.total_bbs or 0)
        nc = int(r.non_conforming or 0)
        result.append({
            "contractor": r.contractor,
            "total_bbs": total,
            "non_conforming": nc,
            "conforming": max(total - nc, 0),
            "kpi_pct": ((total - nc) / total) if total > 0 else None,
        })
    return result


def maturity_for(db: Session, vessel_id: int, year: int) -> Maturity:
    m = (
        db.query(VesselMaturity)
        .filter(VesselMaturity.vessel_id == vessel_id, VesselMaturity.year == year)
        .first()
    )
    return m.maturity if m else Maturity.INICIAL


def target_for(db: Session, vessel_id: int, year: int) -> float:
    return META_BY_MATURITY[maturity_for(db, vessel_id, year)]
