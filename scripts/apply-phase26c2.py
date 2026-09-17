from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise SystemExit(f"Could not locate {label} in {path.relative_to(ROOT)}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def patch_solver_models() -> None:
    path = ROOT / "python/ai_vastu/solver/models.py"

    replace_once(
        path,
        """class PlannerNoticeSeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"


class PlannerConfig(FrozenModel):
""",
        """class PlannerNoticeSeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"


class PlannerSearchVariant(StrEnum):
    LOWER_LEFT = "LOWER_LEFT"
    LOWER_RIGHT = "LOWER_RIGHT"
    UPPER_LEFT = "UPPER_LEFT"
    UPPER_RIGHT = "UPPER_RIGHT"
    REVERSE_LOWER_LEFT = "REVERSE_LOWER_LEFT"
    REVERSE_UPPER_RIGHT = "REVERSE_UPPER_RIGHT"


class PlannerConfig(FrozenModel):
""",
        "PlannerSearchVariant enum",
    )

    replace_once(
        path,
        """class PlannerConfig(FrozenModel):
    solver_step_mm: PositiveMM
    clearance_reserve_mm: NonNegativeMM = 0
    max_time_ms: PositiveInt
""",
        """class PlannerConfig(FrozenModel):
    solver_step_mm: PositiveMM
    clearance_reserve_mm: NonNegativeMM = 0
    search_variant: PlannerSearchVariant = PlannerSearchVariant.LOWER_LEFT
    max_time_ms: PositiveInt
""",
        "PlannerConfig search_variant",
    )


def patch_solver_exports() -> None:
    path = ROOT / "python/ai_vastu/solver/__init__.py"
    text = path.read_text(encoding="utf-8")

    if "PlannerSearchVariant," not in text:
        text = text.replace(
            "    PlannerResult,\\n    PlannerStatus,\\n",
            "    PlannerResult,\\n    PlannerSearchVariant,\\n    PlannerStatus,\\n",
            1,
        )
        text = text.replace(
            '    "PlannerResult",\\n    "PlannerStatus",\\n',
            '    "PlannerResult",\\n    "PlannerSearchVariant",\\n    "PlannerStatus",\\n',
            1,
        )
    path.write_text(text, encoding="utf-8")


def patch_solver_search() -> None:
    path = ROOT / "python/ai_vastu/solver/rectangular_cp_sat.py"

    replace_once(
        path,
        """    PlannerResult,
    PlannerStatus,
    RoomPlacement,
""",
        """    PlannerResult,
    PlannerSearchVariant,
    PlannerStatus,
    RoomPlacement,
""",
        "PlannerSearchVariant import",
    )

    replace_once(
        path,
        """    ordered_rooms = tuple(sorted(problem.room_instances, key=lambda item: str(item.id)))

    for room in ordered_rooms:
""",
        """    ordered_rooms = tuple(sorted(problem.room_instances, key=lambda item: str(item.id)))
    if config.search_variant in {
        PlannerSearchVariant.REVERSE_LOWER_LEFT,
        PlannerSearchVariant.REVERSE_UPPER_RIGHT,
    }:
        ordered_rooms = tuple(reversed(ordered_rooms))

    for room in ordered_rooms:
""",
        "strategy-dependent room order",
    )

    replace_once(
        path,
        """    decision_vars: list[Any] = []
    for room in ordered_rooms:
        rv = room_vars[room.id]
        decision_vars.extend([rv.x, rv.y, rv.width, rv.depth])
    model.add_decision_strategy(decision_vars, cp_model.CHOOSE_FIRST, cp_model.SELECT_MIN_VALUE)

    solver = cp_model.CpSolver()
""",
        """    x_vars = [room_vars[room.id].x for room in ordered_rooms]
    y_vars = [room_vars[room.id].y for room in ordered_rooms]
    size_vars = [
        value
        for room in ordered_rooms
        for value in (room_vars[room.id].width, room_vars[room.id].depth)
    ]

    right_bias = config.search_variant in {
        PlannerSearchVariant.LOWER_RIGHT,
        PlannerSearchVariant.UPPER_RIGHT,
        PlannerSearchVariant.REVERSE_UPPER_RIGHT,
    }
    upper_bias = config.search_variant in {
        PlannerSearchVariant.UPPER_LEFT,
        PlannerSearchVariant.UPPER_RIGHT,
        PlannerSearchVariant.REVERSE_UPPER_RIGHT,
    }

    model.add_decision_strategy(
        x_vars,
        cp_model.CHOOSE_FIRST,
        cp_model.SELECT_MAX_VALUE if right_bias else cp_model.SELECT_MIN_VALUE,
    )
    model.add_decision_strategy(
        y_vars,
        cp_model.CHOOSE_FIRST,
        cp_model.SELECT_MAX_VALUE if upper_bias else cp_model.SELECT_MIN_VALUE,
    )
    model.add_decision_strategy(
        size_vars,
        cp_model.CHOOSE_FIRST,
        cp_model.SELECT_MIN_VALUE,
    )

    solver = cp_model.CpSolver()
""",
        "strategy-dependent fixed search",
    )


def patch_wizard_copy() -> None:
    path = ROOT / "apps/web/src/components/generation/Phase26CProjectWizard.tsx"
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        "Phase 26C.2 will send this confirmed brief into the deterministic multi-candidate engine.",
        "The deterministic multi-candidate engine is implemented. "
        "Wizard/API binding follows in Phase 26C.3.",
    )
    text = text.replace(
        "Generate alternatives — enabled in 26C.2",
        "Generate alternatives — UI binding in 26C.3",
    )
    path.write_text(text, encoding="utf-8")


def main() -> None:
    patch_solver_models()
    patch_solver_exports()
    patch_solver_search()
    patch_wizard_copy()
    print("Phase 26C.2 overlay applied.")


if __name__ == "__main__":
    main()
