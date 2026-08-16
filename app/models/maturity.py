import enum
from sqlalchemy import Column, Integer, Enum, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Maturity(str, enum.Enum):
    INICIAL = "INICIAL"
    ESTAVEL = "ESTAVEL"
    MADURO = "MADURO"


MATURITY_LABELS = {
    Maturity.INICIAL: "Inicial",
    Maturity.ESTAVEL: "Estável",
    Maturity.MADURO: "Maduro",
}

META_BY_MATURITY = {
    Maturity.INICIAL: 0.80,
    Maturity.ESTAVEL: 0.87,
    Maturity.MADURO: 0.92,
}


class VesselMaturity(Base):
    __tablename__ = "vessel_maturities"
    __table_args__ = (UniqueConstraint("vessel_id", "year", name="uq_vessel_year"),)

    id = Column(Integer, primary_key=True, index=True)
    vessel_id = Column(Integer, ForeignKey("vessels.id"), nullable=False)
    year = Column(Integer, nullable=False, index=True)
    maturity = Column(Enum(Maturity), default=Maturity.INICIAL, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    vessel = relationship("Vessel", back_populates="maturities")
