"""
Unit tests for periodization (macrocycles, microcycles, planned sessions).

Covers:
- Block plan resolution (which block is week N in?)
- Methodology default plans (HWPO is 12 weeks)
- datetime utilities (snap_to_monday, week_bounds)
- Pydantic model validation
- API endpoints (macrocycle + planned_session CRUD)
"""
from datetime import date, timedelta, time
from uuid import uuid4

import pytest
from httpx import AsyncClient
from pydantic import ValidationError

from app.core.datetime_utils import snap_to_monday, week_bounds
from app.core.engine.periodization import (
    METHODOLOGY_BLOCK_PLANS,
    default_block_plan_for,
    next_block_after,
    resolve_block_and_week_in_block,
    total_weeks,
)
from app.models.training import (
    BlockPlanItem,
    BlockType,
    MacrocycleCreate,
    Methodology,
    PlannedSessionCreate,
    Shift,
    WorkoutType,
)


# ==========================================================
# datetime_utils
# ==========================================================

class TestDatetimeUtils:
    def test_snap_to_monday_from_any_weekday(self):
        # Wednesday 2026-04-22
        d = date(2026, 4, 22)
        assert snap_to_monday(d) == date(2026, 4, 20)

    def test_snap_to_monday_is_idempotent_on_monday(self):
        d = date(2026, 4, 20)
        assert snap_to_monday(d) == d

    def test_snap_to_monday_from_sunday(self):
        d = date(2026, 4, 26)  # Sunday
        assert snap_to_monday(d) == date(2026, 4, 20)

    def test_week_bounds_returns_mon_sun(self):
        mon, sun = week_bounds(date(2026, 4, 22))
        assert mon == date(2026, 4, 20)
        assert sun == date(2026, 4, 26)


# ==========================================================
# periodization helpers
# ==========================================================

class TestBlockPlans:
    def test_hwpo_default_plan_is_12_weeks(self):
        plan = METHODOLOGY_BLOCK_PLANS[Methodology.HWPO]
        assert total_weeks(plan) == 12

    def test_comptrain_default_plan_is_12_weeks(self):
        plan = METHODOLOGY_BLOCK_PLANS[Methodology.COMPTRAIN]
        assert total_weeks(plan) == 12

    def test_mayhem_default_plan_is_43_weeks(self):
        plan = METHODOLOGY_BLOCK_PLANS[Methodology.MAYHEM]
        assert total_weeks(plan) == 43

    def test_custom_default_plan_is_empty(self):
        assert METHODOLOGY_BLOCK_PLANS[Methodology.CUSTOM] == []

    def test_default_block_plan_returns_copy(self):
        a = default_block_plan_for(Methodology.HWPO)
        b = default_block_plan_for(Methodology.HWPO)
        assert a == b
        assert a is not b  # different instances

    def test_resolve_block_and_week_in_block_hwpo(self):
        plan = METHODOLOGY_BLOCK_PLANS[Methodology.HWPO]
        # Weeks 1-3 = accumulation
        assert resolve_block_and_week_in_block(plan, 1)[0] == BlockType.ACCUMULATION
        assert resolve_block_and_week_in_block(plan, 3) == (BlockType.ACCUMULATION, 3, 3)
        # Week 4 = deload (1 week)
        assert resolve_block_and_week_in_block(plan, 4) == (BlockType.DELOAD, 1, 1)
        # Weeks 5-7 = intensification (3 weeks, so week_in_block = 1..3)
        assert resolve_block_and_week_in_block(plan, 5) == (BlockType.INTENSIFICATION, 1, 3)
        assert resolve_block_and_week_in_block(plan, 7) == (BlockType.INTENSIFICATION, 3, 3)
        # Week 8 = deload
        assert resolve_block_and_week_in_block(plan, 8) == (BlockType.DELOAD, 1, 1)
        # Weeks 9-10 = realization
        assert resolve_block_and_week_in_block(plan, 9)[0] == BlockType.REALIZATION
        assert resolve_block_and_week_in_block(plan, 10)[0] == BlockType.REALIZATION
        # Week 11 = test
        assert resolve_block_and_week_in_block(plan, 11) == (BlockType.TEST, 1, 1)
        # Week 12 = transition
        assert resolve_block_and_week_in_block(plan, 12) == (BlockType.TRANSITION, 1, 1)

    def test_resolve_beyond_plan_returns_none(self):
        plan = METHODOLOGY_BLOCK_PLANS[Methodology.HWPO]
        assert resolve_block_and_week_in_block(plan, 13) == (None, None, None)

    def test_resolve_zero_or_negative_returns_none(self):
        plan = METHODOLOGY_BLOCK_PLANS[Methodology.HWPO]
        assert resolve_block_and_week_in_block(plan, 0) == (None, None, None)
        assert resolve_block_and_week_in_block(plan, -3) == (None, None, None)

    def test_next_block_after(self):
        plan = METHODOLOGY_BLOCK_PLANS[Methodology.HWPO]
        # In week 3 (accumulation), next should be deload
        nxt = next_block_after(plan, 3)
        assert nxt is not None
        assert nxt.type == BlockType.DELOAD
        # In the final block (transition, week 12), no next block
        assert next_block_after(plan, 12) is None


# ==========================================================
# Pydantic model validation
# ==========================================================

class TestPeriodizationModels:
    def test_block_plan_item_weeks_constraint(self):
        BlockPlanItem(type=BlockType.ACCUMULATION, weeks=4)  # ok
        with pytest.raises(ValidationError):
            BlockPlanItem(type=BlockType.ACCUMULATION, weeks=0)
        with pytest.raises(ValidationError):
            BlockPlanItem(type=BlockType.ACCUMULATION, weeks=20)

    def test_macrocycle_create_minimal(self):
        m = MacrocycleCreate(
            name="HWPO Cycle",
            methodology=Methodology.HWPO,
            start_date=date(2026, 4, 20),
        )
        assert m.block_plan is None  # server fills default
        assert m.methodology == Methodology.HWPO

    def test_macrocycle_create_with_custom_plan(self):
        m = MacrocycleCreate(
            name="Custom",
            methodology=Methodology.CUSTOM,
            start_date=date(2026, 4, 20),
            block_plan=[
                BlockPlanItem(type=BlockType.ACCUMULATION, weeks=2),
                BlockPlanItem(type=BlockType.DELOAD, weeks=1),
            ],
        )
        assert total_weeks(m.block_plan) == 3

    def test_planned_session_order_in_day_range(self):
        PlannedSessionCreate(
            date=date(2026, 4, 22),
            order_in_day=1,
            workout_type=WorkoutType.STRENGTH,
        )
        # 5 sessions allowed
        PlannedSessionCreate(
            date=date(2026, 4, 22),
            order_in_day=5,
            workout_type=WorkoutType.METCON,
        )
        with pytest.raises(ValidationError):
            PlannedSessionCreate(
                date=date(2026, 4, 22),
                order_in_day=6,
                workout_type=WorkoutType.METCON,
            )
        with pytest.raises(ValidationError):
            PlannedSessionCreate(
                date=date(2026, 4, 22),
                order_in_day=0,
                workout_type=WorkoutType.METCON,
            )

    def test_planned_session_duration_range(self):
        PlannedSessionCreate(
            date=date(2026, 4, 22), order_in_day=1,
            duration_minutes=240, workout_type=WorkoutType.MIXED,
        )
        with pytest.raises(ValidationError):
            PlannedSessionCreate(
                date=date(2026, 4, 22), order_in_day=1,
                duration_minutes=10, workout_type=WorkoutType.MIXED,
            )
        with pytest.raises(ValidationError):
            PlannedSessionCreate(
                date=date(2026, 4, 22), order_in_day=1,
                duration_minutes=300, workout_type=WorkoutType.MIXED,
            )

    def test_planned_session_accepts_shift_and_time(self):
        ps = PlannedSessionCreate(
            date=date(2026, 4, 22),
            order_in_day=2,
            shift=Shift.EVENING,
            start_time=time(18, 30),
            duration_minutes=60,
            workout_type=WorkoutType.METCON,
        )
        assert ps.shift == Shift.EVENING
        assert ps.start_time == time(18, 30)


# ==========================================================
# API endpoints
# ==========================================================

class TestMacrocycleEndpoints:
    @pytest.mark.asyncio
    async def test_create_macrocycle_hwpo_default(
        self, authenticated_client: AsyncClient, db_session, seeded_user
    ):
        """Creating an HWPO macrocycle generates 12 microcycles."""
        resp = await authenticated_client.post(
            "/api/v1/schedule/macrocycles",
            json={
                "name": "HWPO Prep",
                "methodology": "hwpo",
                "start_date": "2026-04-22",  # Wednesday — should snap to Monday 04-20
                "goal": "Compete",
            },
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["methodology"] == "hwpo"
        assert body["start_date"] == "2026-04-20"  # snapped to Monday
        # HWPO = 12 weeks
        assert len(body["microcycles"]) == 12
        # First microcycle spans Mon 20/04 to Sun 26/04
        assert body["microcycles"][0]["start_date"] == "2026-04-20"
        assert body["microcycles"][0]["end_date"] == "2026-04-26"
        assert body["microcycles"][0]["week_index_in_macro"] == 1
        # Block plan sums to 12
        assert sum(b["weeks"] for b in body["block_plan"]) == 12

    @pytest.mark.asyncio
    async def test_create_macrocycle_custom_requires_block_plan(
        self, authenticated_client: AsyncClient, db_session, seeded_user
    ):
        resp = await authenticated_client.post(
            "/api/v1/schedule/macrocycles",
            json={
                "name": "Custom",
                "methodology": "custom",
                "start_date": "2026-04-20",
            },
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_create_macrocycle_with_custom_block_plan(
        self, authenticated_client: AsyncClient, db_session, seeded_user
    ):
        resp = await authenticated_client.post(
            "/api/v1/schedule/macrocycles",
            json={
                "name": "Short custom",
                "methodology": "custom",
                "start_date": "2026-04-20",
                "block_plan": [
                    {"type": "accumulation", "weeks": 2},
                    {"type": "deload", "weeks": 1},
                ],
            },
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert len(body["microcycles"]) == 3

    @pytest.mark.asyncio
    async def test_add_two_sessions_same_day(
        self, authenticated_client: AsyncClient, db_session, seeded_user
    ):
        """Adding AM strength + PM metcon on the same day persists both."""
        # First create a macrocycle to get a microcycle
        create = await authenticated_client.post(
            "/api/v1/schedule/macrocycles",
            json={
                "name": "Two-a-day test",
                "methodology": "hwpo",
                "start_date": "2026-04-20",
            },
        )
        assert create.status_code == 201, create.text
        micro_id = create.json()["microcycles"][0]["id"]

        # Session 1: AM Strength
        r1 = await authenticated_client.post(
            f"/api/v1/schedule/microcycles/{micro_id}/sessions",
            json={
                "date": "2026-04-22",
                "order_in_day": 1,
                "shift": "morning",
                "start_time": "06:00",
                "duration_minutes": 60,
                "workout_type": "strength",
            },
        )
        assert r1.status_code == 201, r1.text

        # Session 2: PM MetCon same day
        r2 = await authenticated_client.post(
            f"/api/v1/schedule/microcycles/{micro_id}/sessions",
            json={
                "date": "2026-04-22",
                "order_in_day": 2,
                "shift": "evening",
                "start_time": "18:30",
                "duration_minutes": 45,
                "workout_type": "metcon",
            },
        )
        assert r2.status_code == 201, r2.text
        assert r1.json()["id"] != r2.json()["id"]
        assert r1.json()["order_in_day"] == 1
        assert r2.json()["order_in_day"] == 2

    @pytest.mark.asyncio
    async def test_add_session_outside_microcycle_rejects(
        self, authenticated_client: AsyncClient, db_session, seeded_user
    ):
        """Session date must be inside the microcycle bounds."""
        create = await authenticated_client.post(
            "/api/v1/schedule/macrocycles",
            json={
                "name": "Boundary",
                "methodology": "hwpo",
                "start_date": "2026-04-20",
            },
        )
        micro_id = create.json()["microcycles"][0]["id"]
        # First micro is 04-20..04-26; 04-27 is outside
        bad = await authenticated_client.post(
            f"/api/v1/schedule/microcycles/{micro_id}/sessions",
            json={
                "date": "2026-04-27",
                "order_in_day": 1,
                "duration_minutes": 60,
                "workout_type": "strength",
            },
        )
        assert bad.status_code == 400
