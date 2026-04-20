"""
Periodization helpers: block plans per methodology, block/week resolution.

The single source of truth for "which block is week N in?" is the `block_plan`
JSONB column on the macrocycle — this module provides (a) a default plan per
methodology, and (b) a resolver for the current block + week-in-block.
"""
from typing import Optional

from app.models.training import Methodology, BlockType, BlockPlanItem


# Default block plans per methodology. Adjustable by the user after creation.
METHODOLOGY_BLOCK_PLANS: dict[Methodology, list[BlockPlanItem]] = {
    Methodology.HWPO: [
        BlockPlanItem(type=BlockType.ACCUMULATION, weeks=3),
        BlockPlanItem(type=BlockType.DELOAD, weeks=1),
        BlockPlanItem(type=BlockType.INTENSIFICATION, weeks=3),
        BlockPlanItem(type=BlockType.DELOAD, weeks=1),
        BlockPlanItem(type=BlockType.REALIZATION, weeks=2),
        BlockPlanItem(type=BlockType.TEST, weeks=1),
        BlockPlanItem(type=BlockType.TRANSITION, weeks=1),
    ],  # 12 weeks total
    Methodology.MAYHEM: [
        BlockPlanItem(type=BlockType.ACCUMULATION, weeks=9),
        BlockPlanItem(type=BlockType.INTENSIFICATION, weeks=10),
        BlockPlanItem(type=BlockType.REALIZATION, weeks=8),
        BlockPlanItem(type=BlockType.INTENSIFICATION, weeks=8),
        BlockPlanItem(type=BlockType.REALIZATION, weeks=8),
    ],  # 43 weeks total
    Methodology.COMPTRAIN: [
        BlockPlanItem(type=BlockType.ACCUMULATION, weeks=4),
        BlockPlanItem(type=BlockType.DELOAD, weeks=1),
        BlockPlanItem(type=BlockType.INTENSIFICATION, weeks=4),
        BlockPlanItem(type=BlockType.DELOAD, weeks=1),
        BlockPlanItem(type=BlockType.REALIZATION, weeks=2),
    ],  # 12 weeks total
    Methodology.CUSTOM: [],  # user provides their own
}


def total_weeks(block_plan: list[BlockPlanItem]) -> int:
    return sum(b.weeks for b in block_plan)


def default_block_plan_for(methodology: Methodology) -> list[BlockPlanItem]:
    """Return a *copy* of the default plan for a methodology."""
    return [BlockPlanItem(type=b.type, weeks=b.weeks) for b in METHODOLOGY_BLOCK_PLANS[methodology]]


def resolve_block_and_week_in_block(
    block_plan: list[BlockPlanItem],
    week_index_in_macro: int,
) -> tuple[Optional[BlockType], Optional[int], Optional[int]]:
    """
    Given a block_plan and a 1-based week_index_in_macro, return
    (block_type, week_index_in_block, total_weeks_in_block).

    Returns (None, None, None) when the week index is beyond the plan.
    """
    if week_index_in_macro < 1:
        return None, None, None

    cumulative = 0
    for block in block_plan:
        if week_index_in_macro <= cumulative + block.weeks:
            return block.type, week_index_in_macro - cumulative, block.weeks
        cumulative += block.weeks
    return None, None, None


def next_block_after(
    block_plan: list[BlockPlanItem],
    week_index_in_macro: int,
) -> Optional[BlockPlanItem]:
    """Return the block that follows the one containing `week_index_in_macro`, or None."""
    cumulative = 0
    current_idx = None
    for idx, block in enumerate(block_plan):
        if week_index_in_macro <= cumulative + block.weeks:
            current_idx = idx
            break
        cumulative += block.weeks
    if current_idx is None or current_idx + 1 >= len(block_plan):
        return None
    return block_plan[current_idx + 1]
