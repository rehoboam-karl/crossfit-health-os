"""
Training history — agregacoes e analises sobre SessionResults.

Funcoes principais:
- detect_prs(): novos 1RMs (com dedupe por movement_id+achieved_at+value_kg)
- compliance_rate(): % de sessoes executadas vs planejadas em janela
- average_rpe(): media de RPE em janela
- volume_per_movement(): tonelagem por movimento
- stimulus_minutes(): minutos por stimulus (precisa sessions_index)
- overreaching_signals(): heuristicas de alerta
"""

from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel

from athlete import Athlete, OneRepMax
from results import CompletionStatus, SessionResult
from workout_schema import Session, Stimulus


class PR(BaseModel):
    movement_id: str
    value_kg: float
    previous_value_kg: Optional[float] = None
    achieved_at: datetime
    session_id: str
    rep_max: int = 1


class TrainingHistory:
    """Container de SessionResults com queries e analytics."""

    def __init__(
        self,
        results: list[SessionResult],
        sessions_index: Optional[dict[str, Session]] = None,
    ):
        self.results = sorted(results, key=lambda r: r.executed_at)
        self.sessions_index = sessions_index or {}

    def for_athlete(self, athlete_id: str) -> list[SessionResult]:
        return [r for r in self.results if r.athlete_id == athlete_id]

    def in_window(
        self, athlete_id: str, days_back: int, ref: Optional[datetime] = None,
    ) -> list[SessionResult]:
        ref = ref or datetime.now()
        cutoff = ref - timedelta(days=days_back)
        return [r for r in self.for_athlete(athlete_id) if r.executed_at >= cutoff]

    def detect_prs(self, athlete: Athlete, ref: Optional[datetime] = None) -> list[PR]:
        """Encontra 1RMs novos. Dedupe por (movement_id, achieved_at, value_kg)."""
        prs: list[PR] = []
        for result in self.for_athlete(athlete.id):
            for block in result.block_results:
                # Score-level detection: actual_load_kg + score contains "RM"
                if block.actual_load_kg and block.actual_score and "RM" in (block.actual_score or ""):
                    for mr in block.movement_results:
                        prev = athlete.get_1rm(mr.movement_id)
                        if prev is None or block.actual_load_kg > prev:
                            prs.append(PR(
                                movement_id=mr.movement_id,
                                value_kg=block.actual_load_kg,
                                previous_value_kg=prev,
                                achieved_at=result.executed_at,
                                session_id=result.session_id,
                                rep_max=1,
                            ))
                # Movement-level: actual_reps==1 AND actual_load_kg > current 1RM
                for mr in block.movement_results:
                    if mr.actual_reps == 1 and mr.actual_load_kg:
                        prev = athlete.get_1rm(mr.movement_id)
                        if prev is None or mr.actual_load_kg > prev:
                            prs.append(PR(
                                movement_id=mr.movement_id,
                                value_kg=mr.actual_load_kg,
                                previous_value_kg=prev,
                                achieved_at=result.executed_at,
                                session_id=result.session_id,
                                rep_max=1,
                            ))
        # Dedupe
        seen = set()
        unique = []
        for pr in prs:
            key = (pr.movement_id, pr.achieved_at, pr.value_kg)
            if key not in seen:
                seen.add(key)
                unique.append(pr)
        return unique

    def compliance_rate(self, athlete_id: str, days_back: int = 28,
                        ref: Optional[datetime] = None) -> float:
        results = self.in_window(athlete_id, days_back, ref)
        if not results:
            return 0.0
        completed = sum(1 for r in results if r.status != CompletionStatus.SKIPPED)
        return completed / len(results)

    def average_rpe(self, athlete_id: str, days_back: int = 14,
                     ref: Optional[datetime] = None) -> Optional[float]:
        results = self.in_window(athlete_id, days_back, ref)
        rpes = [r.overall_rpe for r in results if r.overall_rpe is not None]
        return sum(rpes) / len(rpes) if rpes else None

    def volume_per_movement(
        self, athlete_id: str, days_back: int = 14,
        ref: Optional[datetime] = None,
    ) -> dict[str, float]:
        volume: dict[str, float] = {}
        for result in self.in_window(athlete_id, days_back, ref):
            for block in result.block_results:
                for mr in block.movement_results:
                    if mr.actual_load_kg and mr.actual_reps:
                        kg = mr.actual_load_kg * mr.actual_reps
                        volume[mr.movement_id] = volume.get(mr.movement_id, 0) + kg
        return dict(sorted(volume.items(), key=lambda x: -x[1]))

    def stimulus_minutes(
        self, athlete_id: str, days_back: int = 14,
        ref: Optional[datetime] = None,
    ) -> dict[Stimulus, int]:
        if not self.sessions_index:
            return {}
        minutes: dict[Stimulus, int] = {}
        for result in self.in_window(athlete_id, days_back, ref):
            session = self.sessions_index.get(result.session_id)
            if not session:
                continue
            for block in session.blocks:
                if block.stimulus is None:
                    continue
                br = next(
                    (b for b in result.block_results if b.block_order == block.order),
                    None,
                )
                if br is None or br.status == CompletionStatus.SKIPPED:
                    continue
                dur = br.actual_duration_minutes or block.duration_minutes or 0
                minutes[block.stimulus] = minutes.get(block.stimulus, 0) + dur
        return dict(sorted(minutes.items(), key=lambda x: -x[1]))

    def overreaching_signals(
        self, athlete_id: str, ref: Optional[datetime] = None,
    ) -> list[str]:
        signals = []
        rpe_recent = self.average_rpe(athlete_id, days_back=7, ref=ref)
        rpe_baseline = self.average_rpe(athlete_id, days_back=28, ref=ref)
        if rpe_recent and rpe_recent > 8.5:
            signals.append(f"RPE medio ultimos 7d = {rpe_recent:.1f} (>8.5)")
        if rpe_recent and rpe_baseline and rpe_recent > rpe_baseline + 0.5:
            signals.append(f"RPE recente ({rpe_recent:.1f}) > baseline ({rpe_baseline:.1f})")
        recent = self.in_window(athlete_id, days_back=7, ref=ref)
        sleep_scores = [r.sleep_quality_prev_night for r in recent
                        if r.sleep_quality_prev_night is not None]
        if sleep_scores and sum(sleep_scores) / len(sleep_scores) < 5:
            signals.append("Sleep quality medio < 5 nos ultimos 7d")
        if recent:
            comp = self.compliance_rate(athlete_id, days_back=7, ref=ref)
            if comp < 0.6:
                signals.append(f"Compliance 7d = {comp:.0%} (<60%)")
        soreness_scores = [r.soreness for r in recent if r.soreness is not None]
        if soreness_scores and sum(soreness_scores) / len(soreness_scores) > 7:
            signals.append("Soreness medio > 7/10 na ultima semana")
        return signals


def apply_prs_to_athlete(athlete: Athlete, prs: list[PR]) -> Athlete:
    """Retorna Athlete atualizado com novos 1RMs (imutavel)."""
    new_orms = dict(athlete.one_rep_maxes)
    for pr in prs:
        if pr.rep_max != 1:
            continue
        new_orms[pr.movement_id] = OneRepMax(
            movement_id=pr.movement_id,
            value_kg=pr.value_kg,
            tested_date=pr.achieved_at.date(),
            confidence="tested",
        )
    return athlete.model_copy(update={"one_rep_maxes": new_orms})