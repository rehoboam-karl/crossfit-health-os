"""Smoke test do MacrocycleAdapter — DB → schema cfai → validação Pydantic."""
from app.schema.v2 import MacrocycleAdapter
from cfai.movements_seed import load_default_library
from app.db.session import Session as SqlSession, engine
from app.db.models import Macrocycle, User


lib = load_default_library()
adapter = MacrocycleAdapter(lib)

db = SqlSession(bind=engine)

macro = db.query(Macrocycle).filter(
    Macrocycle.user_id == 10, Macrocycle.active == True,
).first()

if not macro:
    print("No active macrocycle for user 10")
else:
    user = db.get(User, 10)
    meso = adapter.from_db_macrocycle(db, macro, user, "10")
    print(f"Mesocycle: {meso.name}")
    print(f"Phase: {meso.phase.value}")
    print(f"Start: {meso.start_date}, Weeks: {meso.duration_weeks}")
    print(f"Weeks: {len(meso.weeks)}")
    for w in meso.weeks:
        print(f"  Week {w.week_number} (deload={w.deload}): {len(w.sessions)} sessions")
        for s in w.sessions:
            print(f"    {s.date} {s.template.value} - {len(s.blocks)} blocks")
    print("ALL VALIDATIONS PASSED")
