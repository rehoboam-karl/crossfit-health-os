"""
Seed inicial do catálogo de movimentos.

Cobre ~40 movimentos essenciais do CrossFit competitivo + warm-up/mobility
usados nos exemplos. Estende livremente — toda adição deve incluir tags
do vocabulário em movements.TAGS_PATTERNS para manter queries consistentes.

Padrões de scaling:
- Movements técnicos (BMU, RMU, OHS, snatch, HSPU) têm scaling explícito
- Movements simples (squat, deadlift) usam load_factor e reps_factor
- Mobility/warm-up não têm scaling (não fazem sentido)
"""

from .movements import Movement, MovementLibrary, MovementScaling
from .workout_schema import ScalingTier as ST


def _m(
    id_: str, name: str, category: str, modalities: list, skill: int,
    equipment: list[str], tags: list[str], *,
    name_pt: str | None = None, bilateral: bool = True,
    is_warmup_only: bool = False,
    scaling: dict | None = None,
) -> Movement:
    return Movement(
        id=id_, name=name, name_pt=name_pt, category=category,
        modalities=modalities, skill_level=skill, equipment=equipment,
        tags=tags, bilateral=bilateral, is_warmup_only=is_warmup_only,
        default_scaling=scaling or {},
    )


# ============================================================
# BARBELL
# ============================================================

BARBELL = [
    _m("back_squat", "Back Squat", "barbell", ["W"], 2,
       ["barbell", "plates", "rack"],
       ["squatting", "knee_dominant", "bracing"],
       name_pt="Agachamento Costas",
       scaling={
           ST.SCALED: MovementScaling(load_factor=0.7),
           ST.FOUNDATION: MovementScaling(substitute_movement_id="goblet_squat"),
       }),
    _m("front_squat", "Front Squat", "barbell", ["W"], 3,
       ["barbell", "plates", "rack"],
       ["squatting", "knee_dominant", "bracing", "midline"],
       name_pt="Agachamento Frontal"),
    _m("overhead_squat", "Overhead Squat", "barbell", ["W"], 4,
       ["barbell", "plates"],
       ["squatting", "overhead", "midline", "bracing"],
       name_pt="Agachamento Sobrecabeça"),
    _m("deadlift", "Deadlift", "barbell", ["W"], 2,
       ["barbell", "plates"],
       ["hip_hinge", "hip_dominant", "pulling_vertical", "bracing"],
       name_pt="Levantamento Terra",
       scaling={ST.SCALED: MovementScaling(load_factor=0.7)}),
    _m("romanian_deadlift", "Romanian Deadlift", "barbell", ["W"], 2,
       ["barbell", "plates"],
       ["hip_hinge", "hip_dominant"],
       name_pt="Stiff / RDL"),
    _m("snatch", "Squat Snatch", "barbell", ["W"], 5,
       ["barbell", "plates"],
       ["olympic", "explosive", "ballistic", "overhead", "squatting"],
       name_pt="Arranque",
       scaling={
           ST.SCALED: MovementScaling(substitute_movement_id="power_snatch"),
           ST.FOUNDATION: MovementScaling(substitute_movement_id="db_snatch_alt"),
       }),
    _m("power_snatch", "Power Snatch", "barbell", ["W"], 4,
       ["barbell", "plates"],
       ["olympic", "explosive", "ballistic", "overhead"],
       name_pt="Arranque de Força"),
    _m("clean", "Squat Clean", "barbell", ["W"], 5,
       ["barbell", "plates"],
       ["olympic", "explosive", "ballistic", "squatting"],
       name_pt="Arremesso (Clean)"),
    _m("power_clean", "Power Clean", "barbell", ["W"], 4,
       ["barbell", "plates"],
       ["olympic", "explosive", "ballistic"],
       name_pt="Clean de Força"),
    _m("clean_jerk", "Clean & Jerk", "barbell", ["W"], 5,
       ["barbell", "plates"],
       ["olympic", "explosive", "ballistic", "overhead"],
       name_pt="Arremesso completo"),
    _m("push_press", "Push Press", "barbell", ["W"], 2,
       ["barbell", "plates", "rack"],
       ["pressing_vertical", "overhead", "explosive"],
       name_pt="Push Press"),
    _m("strict_press", "Strict Press", "barbell", ["W"], 2,
       ["barbell", "plates", "rack"],
       ["pressing_vertical", "overhead"],
       name_pt="Desenvolvimento Militar"),
    _m("thruster", "Thruster", "barbell", ["W"], 3,
       ["barbell", "plates"],
       ["squatting", "pressing_vertical", "overhead", "explosive"],
       name_pt="Thruster"),
    _m("bench_press", "Bench Press", "barbell", ["W"], 2,
       ["barbell", "plates", "bench"],
       ["pressing_horizontal"],
       name_pt="Supino"),
]


# ============================================================
# DUMBBELL
# ============================================================

DUMBBELL = [
    _m("db_snatch_alt", "Alternating DB Snatch", "dumbbell", ["W"], 2,
       ["dumbbells"],
       ["olympic", "explosive", "overhead", "single_leg"],
       name_pt="Arranque DB Alternado", bilateral=False),
    _m("db_thruster", "DB Thruster", "dumbbell", ["W"], 3,
       ["dumbbells"],
       ["squatting", "pressing_vertical", "overhead"],
       name_pt="Thruster com DB"),
    _m("db_box_step_up", "DB Box Step-Up", "dumbbell", ["W"], 2,
       ["dumbbells", "box"],
       ["lunging", "single_leg", "knee_dominant"],
       name_pt="Step-Up no Box com DB", bilateral=False),
    _m("db_walking_lunge", "DB Walking Lunge", "dumbbell", ["W"], 2,
       ["dumbbells"],
       ["lunging", "single_leg", "carrying"],
       name_pt="Avanço com DB", bilateral=False),
]


# ============================================================
# KETTLEBELL / WALL BALL
# ============================================================

KB_WB = [
    _m("kb_swing_american", "American KB Swing", "kettlebell", ["W", "G"], 3,
       ["kettlebell"],
       ["hip_hinge", "ballistic", "overhead", "explosive"],
       name_pt="KB Swing Americano"),
    _m("wall_ball", "Wall Ball", "odd_object", ["W", "G"], 2,
       ["wall_ball", "wall_target"],
       ["squatting", "pressing_vertical", "overhead", "ballistic"],
       name_pt="Wall Ball"),
]


# ============================================================
# GYMNASTIC
# ============================================================

GYMNASTIC = [
    _m("pull_up", "Pull-Up (Kipping)", "gymnastic", ["G"], 3,
       ["pull_up_bar"],
       ["pulling_vertical"],
       name_pt="Barra Fixa Kipping",
       scaling={
           ST.SCALED: MovementScaling(substitute_movement_id="ring_row"),
           ST.FOUNDATION: MovementScaling(substitute_movement_id="ring_row",
                                          notes="elevado, pés caminhando"),
       }),
    _m("chest_to_bar", "Chest-to-Bar Pull-Up", "gymnastic", ["G"], 4,
       ["pull_up_bar"],
       ["pulling_vertical"],
       name_pt="Peito na Barra",
       scaling={ST.SCALED: MovementScaling(substitute_movement_id="pull_up")}),
    _m("bar_muscle_up", "Bar Muscle-Up", "gymnastic", ["G"], 5,
       ["pull_up_bar"],
       ["pulling_vertical", "pressing_vertical", "explosive"],
       name_pt="Muscle-Up na Barra",
       scaling={
           ST.SCALED: MovementScaling(substitute_movement_id="chest_to_bar",
                                      reps_factor=2.0,
                                      notes="dobra reps de C2B"),
       }),
    _m("toes_to_bar", "Toes-to-Bar", "gymnastic", ["G"], 3,
       ["pull_up_bar"],
       ["spinal_flexion", "midline", "pulling_vertical"],
       name_pt="Pés na Barra",
       scaling={
           ST.SCALED: MovementScaling(substitute_movement_id="hanging_knee_raise"),
           ST.FOUNDATION: MovementScaling(substitute_movement_id="sit_up"),
       }),
    _m("hspu", "Kipping Handstand Push-Up", "gymnastic", ["G"], 4,
       ["wall"],
       ["pressing_vertical", "overhead", "explosive"],
       name_pt="HSPU",
       scaling={
           ST.SCALED: MovementScaling(substitute_movement_id="pike_push_up"),
           ST.FOUNDATION: MovementScaling(substitute_movement_id="db_push_press"),
       }),
    _m("push_up", "Push-Up", "gymnastic", ["G"], 1,
       [],
       ["pressing_horizontal", "midline"],
       name_pt="Flexão"),
    _m("ring_row", "Ring Row", "gymnastic", ["G"], 1,
       ["rings"],
       ["pulling_horizontal"],
       name_pt="Remada nas Argolas"),
    _m("burpee", "Burpee", "gymnastic", ["G"], 2,
       [],
       ["squatting", "pressing_horizontal", "explosive", "high_impact"],
       name_pt="Burpee"),
    _m("box_jump_over", "Box Jump Over", "gymnastic", ["G"], 2,
       ["box"],
       ["explosive", "high_impact", "knee_dominant"],
       name_pt="Box Jump Over",
       scaling={ST.SCALED: MovementScaling(substitute_movement_id="box_step_up")}),
    _m("box_step_up", "Box Step-Up", "gymnastic", ["G"], 1,
       ["box"],
       ["lunging", "single_leg", "low_impact"],
       name_pt="Step-Up", bilateral=False),
    _m("rope_climb", "Rope Climb", "gymnastic", ["G"], 4,
       ["rope"],
       ["pulling_vertical"],
       name_pt="Subida na Corda"),
    _m("hanging_knee_raise", "Hanging Knee Raise", "gymnastic", ["G"], 2,
       ["pull_up_bar"],
       ["spinal_flexion", "midline"],
       name_pt="Joelhos no Peito"),
    _m("sit_up", "AbMat Sit-Up", "gymnastic", ["G"], 1,
       ["abmat"],
       ["spinal_flexion", "midline"],
       name_pt="Abdominal"),
    _m("pike_push_up", "Pike Push-Up", "gymnastic", ["G"], 2,
       [],
       ["pressing_vertical", "overhead"],
       name_pt="Flexão Pike"),
    _m("goblet_squat", "Goblet Squat", "kettlebell", ["W"], 1,
       ["kettlebell"],
       ["squatting", "knee_dominant"],
       name_pt="Goblet Squat"),
    _m("db_push_press", "DB Push Press", "dumbbell", ["W"], 2,
       ["dumbbells"],
       ["pressing_vertical", "overhead", "explosive"],
       name_pt="Push Press com DB"),
]


# ============================================================
# MONOSTRUCTURAL
# ============================================================

CARDIO = [
    _m("run", "Run", "monostructural", ["M"], 1, [],
       ["cyclical", "high_impact", "ground_contact"],
       name_pt="Corrida"),
    _m("row", "Row (Concept2)", "monostructural", ["M"], 1, ["rower"],
       ["cyclical", "low_impact", "pulling_horizontal"],
       name_pt="Remo"),
    _m("bike", "Assault/Echo Bike", "monostructural", ["M"], 1, ["assault_bike"],
       ["cyclical", "low_impact"],
       name_pt="Bike"),
    _m("ski", "SkiErg", "monostructural", ["M"], 1, ["skierg"],
       ["cyclical", "low_impact", "pulling_vertical"],
       name_pt="Ski"),
    _m("double_under", "Double Under", "monostructural", ["M", "G"], 3, ["jump_rope"],
       ["cyclical", "high_impact", "explosive"],
       name_pt="Double Under",
       scaling={ST.SCALED: MovementScaling(substitute_movement_id="single_under",
                                            reps_factor=2.0)}),
    _m("single_under", "Single Under", "monostructural", ["M"], 1, ["jump_rope"],
       ["cyclical", "high_impact"],
       name_pt="Single Under"),
]


# ============================================================
# ACCESSORY / WARM-UP
# ============================================================

ACCESSORY = [
    _m("banded_glute_bridge", "Banded Glute Bridge", "accessory", ["G"], 1,
       ["band"],
       ["hip_hinge", "hip_dominant"],
       name_pt="Glute Bridge com Mini Band"),
    _m("dead_bug", "Dead Bug", "accessory", ["G"], 1, [],
       ["midline", "anti_rotation", "isometric"],
       name_pt="Dead Bug"),
    _m("hollow_hold", "Hollow Hold", "accessory", ["G"], 2, [],
       ["midline", "isometric", "spinal_flexion"],
       name_pt="Hollow Hold"),
    _m("plank", "Plank", "accessory", ["G"], 1, [],
       ["midline", "isometric"],
       name_pt="Prancha"),
]


WARMUP_MOBILITY = [
    _m("world_greatest_stretch", "World's Greatest Stretch", "accessory", ["G"], 1,
       [], [], name_pt="World's Greatest Stretch", is_warmup_only=True),
    _m("cossack_squat", "Cossack Squat", "accessory", ["G"], 2, [],
       ["squatting", "single_leg"],
       name_pt="Agachamento Cossaco", is_warmup_only=True),
    _m("couch_stretch", "Couch Stretch", "accessory", ["G"], 1, [], [],
       name_pt="Couch Stretch", is_warmup_only=True),
    _m("box_breathing", "Box Breathing", "accessory", [], 1, [], [],
       name_pt="Respiração Box", is_warmup_only=True),
]


# ============================================================
# LOADER
# ============================================================

ALL_MOVEMENTS = (
    BARBELL + DUMBBELL + KB_WB + GYMNASTIC + CARDIO
    + ACCESSORY + WARMUP_MOBILITY
)


def load_default_library() -> MovementLibrary:
    return MovementLibrary(ALL_MOVEMENTS)
