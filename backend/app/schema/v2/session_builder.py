"""
Session builder — constrói Session derivando metadata da MovementLibrary.

Resolve: equipment_required declarado manualmente ficava defasado.
Centraliza derivação aqui. Sempre usar build_session() em vez de
construir Session() diretamente.
"""

from datetime import date as DateType
from typing import Optional

from movements import MovementLibrary
from workout_schema import (
    Session, SessionTemplate, Stimulus, WorkoutBlock,
)


def build_session(
    *,
    id: str,
    date: DateType,
    template: SessionTemplate,
    blocks: list[WorkoutBlock],
    primary_stimulus: Stimulus,
    library: MovementLibrary,
    title: Optional[str] = None,
    estimated_duration_minutes: Optional[int] = None,
    extra_equipment: Optional[list[str]] = None,
) -> Session:
    """Constrói Session com equipment e duração derivados automaticamente."""
    movement_ids = [
        mp.movement_id
        for block in blocks
        for mp in block.movements
    ]

    missing = library.validate_ids(movement_ids)
    if missing:
        raise ValueError(f"movement_ids ausentes do catálogo: {sorted(set(missing))}")

    equipment = set(library.derive_equipment(movement_ids))
    if extra_equipment:
        equipment.update(extra_equipment)

    duration = estimated_duration_minutes
    if duration is None:
        duration = sum(b.duration_minutes or 0 for b in blocks)
        if duration == 0:
            duration = 60

    return Session(
        id=id,
        date=date,
        template=template,
        title=title,
        blocks=blocks,
        primary_stimulus=primary_stimulus,
        equipment_required=sorted(equipment),
        estimated_duration_minutes=duration,
    )