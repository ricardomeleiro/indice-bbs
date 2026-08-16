from sqlalchemy import (
    Column, Integer, String, ForeignKey, DateTime, UniqueConstraint, CheckConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class MonthlyEntry(Base):
    __tablename__ = "monthly_entries"
    __table_args__ = (
        UniqueConstraint("year", "month", "rov_id", name="uq_year_month_rov"),
        CheckConstraint("month >= 1 AND month <= 12", name="ck_month_range"),
        CheckConstraint("total_bbs >= 0", name="ck_total_nonneg"),
        CheckConstraint("non_conforming >= 0", name="ck_nc_nonneg"),
        CheckConstraint("non_conforming <= total_bbs", name="ck_nc_le_total"),
    )

    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, nullable=False, index=True)
    month = Column(Integer, nullable=False, index=True)
    rov_id = Column(Integer, ForeignKey("rovs.id"), nullable=False, index=True)

    total_bbs = Column(Integer, default=0, nullable=False)
    non_conforming = Column(Integer, default=0, nullable=False)

    c1 = Column(Integer, default=0, nullable=False)
    c2 = Column(Integer, default=0, nullable=False)
    c3 = Column(Integer, default=0, nullable=False)
    c4_crm = Column(Integer, default=0, nullable=False)
    c4_elo = Column(Integer, default=0, nullable=False)

    observations = Column(String(500))

    created_by_id = Column(Integer, ForeignKey("users.id"))
    updated_by_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    rov = relationship("Rov", back_populates="entries")
    created_by = relationship("User", foreign_keys=[created_by_id])
    updated_by = relationship("User", foreign_keys=[updated_by_id])

    @property
    def conforming(self) -> int:
        return max(self.total_bbs - self.non_conforming, 0)

    @property
    def kpi_pct(self) -> float | None:
        if self.total_bbs <= 0:
            return None
        return self.conforming / self.total_bbs

    @property
    def non_conforming_pct(self) -> float | None:
        if self.total_bbs <= 0:
            return None
        return self.non_conforming / self.total_bbs
