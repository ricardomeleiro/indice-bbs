import enum
from sqlalchemy import Column, Integer, String, Enum, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class RovKind(str, enum.Enum):
    UHD = "UHD"
    SURVEY = "SURVEY"


class Rov(Base):
    __tablename__ = "rovs"

    id = Column(Integer, primary_key=True, index=True)
    rov_id = Column(String(40), unique=True, index=True, nullable=False)
    rov_num = Column(Integer, nullable=False)
    kind = Column(Enum(RovKind), nullable=False)
    vessel_id = Column(Integer, ForeignKey("vessels.id"), nullable=False)
    created_at = Column(DateTime, default=func.now())

    vessel = relationship("Vessel", back_populates="rovs")
    entries = relationship("MonthlyEntry", back_populates="rov", cascade="all, delete-orphan")
