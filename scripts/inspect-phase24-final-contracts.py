from __future__ import annotations

import importlib
import inspect
import json
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / ".local" / "phase24-final-contracts.json"

MODULES = [
    "ai_vastu.plan_schema.models",
    "ai_vastu.projects.models",
    "ai_vastu.projects.service",
    "ai_vastu.projects.repository",
    "ai_vastu.scoring.models",
    "ai_vastu.scoring.evaluator",
    "ai_vastu.scoring.selector",
    "ai_vastu.vastu.models",
    "ai_vastu.vastu.compiler",
    "ai_vastu.vastu.evaluator",
]


def inspect_module(module_name: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "models": {},
        "functions": {},
        "classes": {},
    }
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:
        result["import_error"] = f"{type(exc).__name__}: {exc}"
        return result

    for name, value in vars(module).items():
        if (
            inspect.isclass(value)
            and issubclass(value, BaseModel)
            and value.__module__ == module.__name__
        ):
            result["models"][name] = value.model_json_schema()
        elif inspect.isfunction(value) and value.__module__ == module.__name__:
            result["functions"][name] = str(inspect.signature(value))
        elif inspect.isclass(value) and value.__module__ == module.__name__:
            methods: dict[str, str] = {}
            for method_name, method in inspect.getmembers(
                value,
                predicate=inspect.isfunction,
            ):
                if not method_name.startswith("_"):
                    methods[method_name] = str(inspect.signature(method))
            if methods:
                result["classes"][name] = methods

    return result


payload: dict[str, Any] = {
    "modules": {module_name: inspect_module(module_name) for module_name in MODULES}
}

# Also export the concrete FastAPI route surface. This is useful for choosing
# direct service integration vs. an existing authoritative API boundary.
api_path = ROOT / "apps" / "api"
sys.path.insert(0, str(api_path))
try:
    from app.main import app

    payload["api_routes"] = [
        {
            "path": route.path,
            "methods": sorted(route.methods or []),
            "name": route.name,
        }
        for route in app.routes
        if hasattr(route, "path")
    ]
except Exception as exc:
    payload["api_routes_error"] = f"{type(exc).__name__}: {exc}"

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(
    json.dumps(payload, indent=2, sort_keys=True),
    encoding="utf-8",
)

print(json.dumps(payload, indent=2, sort_keys=True))
print()
print(f"Wrote: {OUTPUT}")
