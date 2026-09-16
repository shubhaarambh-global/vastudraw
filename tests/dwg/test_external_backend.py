import pytest
from pydantic import ValidationError

from ai_vastu.dwg import ExternalCommandBackendConfig


def test_external_command_templates_require_explicit_paths() -> None:
    with pytest.raises(ValidationError):
        ExternalCommandBackendConfig(
            backend_id="oda-wrapper",
            backend_version="1",
            converter_executable="convert.exe",
            converter_args=("--input", "missing-placeholder"),
            inspector_executable="inspect.exe",
            inspector_args=("{input_dwg}",),
        )
