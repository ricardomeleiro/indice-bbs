from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON
from sqlalchemy.sql import func
from database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String(80), nullable=False)
    entity_type = Column(String(40))
    entity_id = Column(Integer)
    details = Column(JSON)
    ip_address = Column(String(64))
    created_at = Column(DateTime, default=func.now(), index=True)
