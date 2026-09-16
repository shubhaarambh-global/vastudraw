from __future__ import annotations

import inspect
import json
from pathlib import Path

from pydantic import BaseModel

import ai_vastu.generation.models as generation_models
import ai_vastu.generation.service as generation_service

ROOT = Path(__file__).resolve().parents[1]
output_path = ROOT / ".local" / "phase24-generation-contract.json"
output_path.parent.mkdir(parents=True, exist_ok=True)

models: dict[str, object] = {}
for name, value in vars(generation_models).items():
    if (
        inspect.isclass(value)
        and issubclass(value, BaseModel)
        and value.__module__ == generation_models.__name__
    ):
        models[name] = value.model_json_schema()

functions: dict[str, str] = {}
classes: dict[str, dict[str, str]] = {}

for name, value in vars(generation_service).items():
    if inspect.isfunction(value) and value.__module__ == generation_service.__name__:
        functions[name] = str(inspect.signature(value))
    elif inspect.isclass(value) and value.__module__ == generation_service.__name__:
        methods: dict[str, str] = {}
        for method_name, method in inspect.getmembers(value, predicate=inspect.isfunction):
            if not method_name.startswith("_"):
                methods[method_name] = str(inspect.signature(method))
        classes[name] = methods

payload = {
    "generation_models": models,
    "generation_service_functions": functions,
    "generation_service_classes": classes,
}

output_path.write_text(
    json.dumps(payload, indent=2, sort_keys=True),
    encoding="utf-8",
)

print(json.dumps(payload, indent=2, sort_keys=True))
print()
print(f"Wrote: {output_path}")
