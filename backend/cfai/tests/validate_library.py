"""
Validação Movement Library + integração com schema completo.

Demonstra:
1. Library carregada e queryable
2. Todos os movement_ids dos exemplos existem no catálogo
3. Filtros por tag/modality/equipment
4. Injury pattern matching (overhead, spinal_flexion, etc.)
5. Derivação automática de equipment_required
"""

from cfai.athlete import Athlete, Injury, InjurySeverity
from datetime import date

from cfai.examples import strength_day, engine_day, karl
from cfai.movements import Movement, MovementLibrary
from cfai.movements_seed import load_default_library


def collect_movement_ids_from_session(session) -> list[str]:
    ids = []
    for block in session.blocks:
        for mp in block.movements:
            ids.append(mp.movement_id)
    return ids


def is_movement_restricted(
    athlete: Athlete, movement_id: str, library: MovementLibrary
) -> Injury | None:
    """Versão library-aware: matching por tag (não só id explícito)."""
    movement = library.get_or_none(movement_id)
    for inj in athlete.active_injuries:
        if inj.resolved_date is not None:
            continue
        # Match direto por id
        if movement_id in inj.affected_movements:
            return inj
        # Match por tag/padrão
        if movement and any(p in movement.tags for p in inj.affected_patterns):
            return inj
    return None


# ============================================================
# RUN
# ============================================================

lib = load_default_library()
print(f"📚 Library carregada: {len(lib)} movimentos\n")


# ---------- 1. Validação de integridade ----------
print("─" * 60)
print("1. Validação: todos movement_ids dos exemplos existem?")
print("─" * 60)
all_ids = (
    collect_movement_ids_from_session(strength_day)
    + collect_movement_ids_from_session(engine_day)
)
missing = lib.validate_ids(all_ids)
if missing:
    print(f"❌ Faltando no catálogo: {missing}")
else:
    print(f"✅ Todos os {len(set(all_ids))} ids únicos existem no catálogo")


# ---------- 2. Filtros por modality / category ----------
print("\n" + "─" * 60)
print("2. Distribuição do catálogo")
print("─" * 60)
for mod in ["M", "G", "W"]:
    movs = lib.find_by_modality(mod)
    print(f"  Modality {mod}: {len(movs)} movimentos")
for cat in ["barbell", "dumbbell", "gymnastic", "monostructural", "accessory"]:
    movs = lib.find_by_category(cat)
    print(f"  Category {cat:15} {len(movs)}")


# ---------- 3. Query por tag (padrões) ----------
print("\n" + "─" * 60)
print("3. Query por padrão biomecânico")
print("─" * 60)
for tag in ["overhead", "spinal_flexion", "olympic", "high_impact"]:
    movs = lib.find_by_tag(tag)
    names = ", ".join(m.id for m in movs[:5])
    extra = f" (+{len(movs)-5} mais)" if len(movs) > 5 else ""
    print(f"  '{tag:20}' {len(movs):2} movs → {names}{extra}")


# ---------- 4. Filtro por equipamento disponível ----------
print("\n" + "─" * 60)
print("4. Karl em viagem — só com elásticos e DB")
print("─" * 60)
limited_eq = ["dumbbells", "band"]
available = lib.filter_by_equipment(limited_eq)
print(f"  Movimentos disponíveis: {len(available)}")
print(f"  → {[m.id for m in available]}")


# ---------- 5. Injury pattern matching ----------
print("\n" + "─" * 60)
print("5. Karl com tendinite no ombro (affected_patterns=['overhead'])")
print("─" * 60)

# Karl tem injury com pattern "overhead_high_volume" — vou ajustar para
# um pattern do nosso vocabulário ("overhead") para demo
karl_overhead_inj = Athlete(
    **{**karl.model_dump(),
       "active_injuries": [
           Injury(
               description="Tendinite ombro direito",
               severity=InjurySeverity.MODERATE,
               affected_patterns=["overhead"],
               start_date=date(2026, 4, 10),
           )
       ]}
)

# Quais movimentos da sessão de strength estão restritos?
restricted_in_strength = []
for mid in collect_movement_ids_from_session(strength_day):
    inj = is_movement_restricted(karl_overhead_inj, mid, lib)
    if inj:
        restricted_in_strength.append(mid)

print(f"  Movimentos restritos na sessão Strength Day:")
for mid in set(restricted_in_strength):
    mov = lib.get(mid)
    print(f"    ⚠️  {mid:25} (tags: {mov.tags})")


# ---------- 6. Derivação automática de equipment ----------
print("\n" + "─" * 60)
print("6. Equipment derivado automaticamente")
print("─" * 60)
for sess in [strength_day, engine_day]:
    ids = collect_movement_ids_from_session(sess)
    derived = lib.derive_equipment(ids)
    declared = sess.equipment_required
    extra = set(declared) - set(derived)
    missing_eq = set(derived) - set(declared)
    print(f"\n  📋 {sess.title}")
    print(f"     Declarado: {sorted(declared)}")
    print(f"     Derivado:  {derived}")
    if missing_eq:
        print(f"     ⚠️  Falta declarar: {sorted(missing_eq)}")
    if extra:
        print(f"     ℹ️  Declarado mas não usado: {sorted(extra)}")


# ---------- 7. Scaling lookup ----------
print("\n" + "─" * 60)
print("7. Default scaling — Bar Muscle-Up")
print("─" * 60)
bmu = lib.get("bar_muscle_up")
print(f"  Movimento: {bmu.name} (skill {bmu.skill_level}/5)")
for tier, scaling in bmu.default_scaling.items():
    sub = scaling.substitute_movement_id or "(mesmo movimento)"
    factor = ""
    if scaling.reps_factor:
        factor = f" reps×{scaling.reps_factor}"
    if scaling.load_factor:
        factor += f" load×{scaling.load_factor}"
    print(f"    {tier.value:12} → {sub}{factor}")
