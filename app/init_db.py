"""Create tables and seed vessels/ROVs on container start (idempotent)."""
import sys
from database import Base, engine, SessionLocal
from models import Vessel, Rov, RovKind  # noqa: F401 — register all models
from models import User, VesselMaturity, MonthlyEntry, AuditLog  # noqa: F401
from seed_data import VESSELS, ROVS


def run():
    print("[init_db] creating tables...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Seed vessels
        existing_vessels = {v.name: v for v in db.query(Vessel).all()}
        for name, contractor in VESSELS:
            if name in existing_vessels:
                continue
            db.add(Vessel(name=name, contractor=contractor))
        db.commit()

        vessels_by_name = {v.name: v for v in db.query(Vessel).all()}

        # Seed rovs
        existing_rov_ids = {r.rov_id for r in db.query(Rov).all()}
        for rov_id, rov_num, vessel_name, kind in ROVS:
            if rov_id in existing_rov_ids:
                continue
            v = vessels_by_name.get(vessel_name)
            if not v:
                print(f"[init_db] WARN: vessel {vessel_name!r} missing for ROV {rov_id}")
                continue
            db.add(Rov(rov_id=rov_id, rov_num=rov_num, kind=RovKind(kind), vessel_id=v.id))
        db.commit()

        print(f"[init_db] vessels={db.query(Vessel).count()}, rovs={db.query(Rov).count()}")
    finally:
        db.close()


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        print(f"[init_db] error: {e}", file=sys.stderr)
        sys.exit(1)
