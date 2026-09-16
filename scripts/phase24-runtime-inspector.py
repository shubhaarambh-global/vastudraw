from __future__ import annotations

import importlib
import inspect
import json
import pkgutil
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / ".local" / "phase24-runtime-contracts.json"

API_PATH = ROOT / "apps" / "api"
if str(API_PATH) not in sys.path:
    sys.path.insert(0, str(API_PATH))


ROOT_PACKAGES = (
    "ai_vastu.projects",
    "ai_vastu.vastu",
    "ai_vastu.scoring",
    "ai_vastu.plan_schema",
)

APP_HINTS = (
    "project",
    "revision",
    "vastu",
    "scor",
    "generation",
    "repository",
    "factory",
    "persistence",
)


def discover_modules(package_name: str) -> list[str]:
    names = [package_name]
    try:
        package = importlib.import_module(package_name)
    except Exception:
        return names

    package_path = getattr(package, "__path__", None)
    if package_path is None:
        return names

    for item in pkgutil.walk_packages(package_path, package.__name__ + "."):
        names.append(item.name)
    return sorted(set(names))


def public_signature(value: object) -> str | None:
    try:
        return str(inspect.signature(value))
    except (TypeError, ValueError):
        return None


def inspect_class(cls: type[object]) -> dict[str, Any]:
    result: dict[str, Any] = {}

    init_sig = public_signature(cls)
    if init_sig is not None:
        result["constructor"] = init_sig

    methods: dict[str, str] = {}
    for name, member in inspect.getmembers(cls):
        if name.startswith("_"):
            continue
        if inspect.isfunction(member) or inspect.ismethod(member):
            sig = public_signature(member)
            if sig is not None:
                methods[name] = sig
    if methods:
        result["methods"] = methods

    return result


def inspect_module(module_name: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "functions": {},
        "classes": {},
        "models": {},
        "constants": {},
    }

    try:
        module = importlib.import_module(module_name)
    except Exception as exc:
        result["import_error"] = f"{type(exc).__name__}: {exc}"
        return result

    for name, value in vars(module).items():
        if name.startswith("_"):
            continue

        if (
            inspect.isclass(value)
            and issubclass(value, BaseModel)
            and value.__module__ == module.__name__
        ):
            result["models"][name] = {
                "constructor": public_signature(value),
                "schema": value.model_json_schema(),
            }
            continue

        if inspect.isclass(value) and value.__module__ == module.__name__:
            result["classes"][name] = inspect_class(value)
            continue

        if inspect.isfunction(value) and value.__module__ == module.__name__:
            sig = public_signature(value)
            if sig is not None:
                result["functions"][name] = sig
            continue

        if name.isupper() and isinstance(value, (str, int, float, bool, type(None))):
            result["constants"][name] = value

    return result


module_names: set[str] = set()
for root_package in ROOT_PACKAGES:
    module_names.update(discover_modules(root_package))

# Inspect relevant FastAPI application modules too.
try:
    app_package = importlib.import_module("app")
    app_path = getattr(app_package, "__path__", None)
    if app_path is not None:
        for item in pkgutil.walk_packages(app_path, "app."):
            if any(hint in item.name.lower() for hint in APP_HINTS):
                module_names.add(item.name)
except Exception:
    pass


payload: dict[str, Any] = {
    "modules": {
        name: inspect_module(name)
        for name in sorted(module_names)
    }
}

# Record FastAPI endpoint call signatures, not only paths.
try:
    from app.main import app

    routes: list[dict[str, Any]] = []
    for route in app.routes:
        path = getattr(route, "path", None)
        endpoint = getattr(route, "endpoint", None)
        if path is None:
            continue
        item: dict[str, Any] = {
            "path": path,
            "methods": sorted(getattr(route, "methods", None) or []),
            "name": getattr(route, "name", None),
        }
        if endpoint is not None:
            item["endpoint_module"] = getattr(endpoint, "__module__", None)
            item["endpoint_qualname"] = getattr(endpoint, "__qualname__", None)
            item["endpoint_signature"] = public_signature(endpoint)
        routes.append(item)
    payload["api_routes"] = routes
except Exception as exc:
    payload["api_routes_error"] = f"{type(exc).__name__}: {exc}"


OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(
    json.dumps(payload, indent=2, sort_keys=True),
    encoding="utf-8",
)

print(f"Wrote: {OUTPUT}")
print(f"Modules inspected: {len(payload['modules'])}")

important_terms = (
    "ProjectRevisionService",
    "create_project_repository",
    "create_repository",
    "RuleBundle",
    "load",
    "production",
    "score_and_select_alternatives",
    "append_revision",
)

serialized = json.dumps(payload)
for term in important_terms:
    print(f"{term}: {term in serialized}")
