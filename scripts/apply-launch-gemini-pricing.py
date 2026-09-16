from __future__ import annotations

from pathlib import Path

ROOT = Path(".")


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def write(relative: str, text: str) -> None:
    (ROOT / relative).write_text(text, encoding="utf-8")


# 1. Providers __init__.
path = "python/ai_vastu/requirements/providers/__init__.py"
text = read(path)
import_block = '''from .gemini_generate_content import (
    GeminiGenerateContentRequirementsProvider,
    GeminiRequirementsConfigurationError,
)
'''
if "GeminiGenerateContentRequirementsProvider" not in text:
    marker = "from .fixture import FixtureRequirementsProvider\n"
    if marker not in text:
        raise SystemExit("Could not patch providers/__init__.py")
    text = text.replace(marker, marker + import_block, 1)
    text = text.replace(
        '    "FixtureRequirementsProvider",\n',
        '    "FixtureRequirementsProvider",\n'
        '    "GeminiGenerateContentRequirementsProvider",\n'
        '    "GeminiRequirementsConfigurationError",\n',
        1,
    )
write(path, text)

# 2. Provider factory.
path = "python/ai_vastu/requirements/service.py"
text = read(path)
if "GeminiGenerateContentRequirementsProvider" not in text:
    text = text.replace(
        "    FixtureRequirementsProvider,\n",
        "    FixtureRequirementsProvider,\n"
        "    GeminiGenerateContentRequirementsProvider,\n",
        1,
    )
if 'if provider_name == "gemini":' not in text:
    marker = '''    if provider_name == "openai":
        return OpenAIResponsesRequirementsProvider.from_environment()
'''
    if marker not in text:
        raise SystemExit("Could not patch requirements provider factory")
    text = text.replace(
        marker,
        marker
        + '''    if provider_name == "gemini":
        return GeminiGenerateContentRequirementsProvider.from_environment()
''',
        1,
    )
write(path, text)

# 3. httpx must be a runtime dependency because both OpenAI and Gemini providers use it.
path = "pyproject.toml"
text = read(path)
runtime_httpx = '  "httpx>=0.28,<1",\n'
if runtime_httpx not in text.split("[project.optional-dependencies]", 1)[0]:
    marker = '  "fastapi>=0.116,<1",\n'
    if marker not in text:
        raise SystemExit("Could not add httpx runtime dependency")
    text = text.replace(marker, marker + runtime_httpx, 1)
# Remove duplicate dev declaration if present after optional-dependencies header.
head, sep, tail = text.partition("[project.optional-dependencies]")
if sep:
    tail = tail.replace(runtime_httpx, "", 1)
    text = head + sep + tail
write(path, text)

# 4. Billing catalog: prices + public generation-limit metadata.
path = "python/ai_vastu/billing/catalog.py"
text = read(path)
if "generation_limit_per_project" not in text:
    text = text.replace(
        "    billing_period: str | None = None\n",
        "    billing_period: str | None = None\n"
        "    generation_limit_per_project: int | None = None\n",
        1,
    )
text = text.replace("amount_paise=39_900", "amount_paise=49_900")
text = text.replace("amount_paise=339_900", "amount_paise=489_900")
text = text.replace("amount_paise=249_900", "amount_paise=999_900")
text = text.replace("amount_paise=2_499_900", "amount_paise=6_999_900")

single = '''        amount_paise=49_900,
        project_credits=1,
'''
if "generation_limit_per_project=3" not in text:
    if single not in text:
        raise SystemExit("Could not attach single-project generation metadata")
    text = text.replace(
        single,
        single + "        generation_limit_per_project=3,\n",
        1,
    )
pack = '''        amount_paise=489_900,
        project_credits=10,
'''
if "generation_limit_per_project=5" not in text:
    if pack not in text:
        raise SystemExit("Could not attach pack generation metadata")
    text = text.replace(
        pack,
        pack + "        generation_limit_per_project=5,\n",
        1,
    )
if '"generation_limit_per_project": item.generation_limit_per_project' not in text:
    marker = '            "billing_period": item.billing_period,\n'
    if marker not in text:
        raise SystemExit("Could not patch public billing catalog")
    text = text.replace(
        marker,
        marker
        + '            "generation_limit_per_project": '
        + "item.generation_limit_per_project,\n",
        1,
    )
write(path, text)

# 5. Production settings: allow either Gemini or OpenAI, provider-specific secrets.
path = "python/ai_vastu/production/settings.py"
text = read(path)
if "gemini_model: str | None" not in text:
    text = text.replace(
        "    openai_model: str | None\n",
        "    openai_model: str | None\n    gemini_model: str | None\n",
        1,
    )
if '"gemini_model": self.gemini_model' not in text:
    text = text.replace(
        '            "openai_model": self.openai_model,\n',
        '            "openai_model": self.openai_model,\n'
        '            "gemini_model": self.gemini_model,\n',
        1,
    )
old_provider = '''    provider = env.get(
        "AI_VASTU_REQUIREMENTS_PROVIDER",
        "fixture",
    ).strip().lower()
    if provider != "openai":
        raise ProductionConfigurationError(
            "Commercial launch requires AI_VASTU_REQUIREMENTS_PROVIDER=openai."
        )
    _required(env, "OPENAI_API_KEY")
    openai_model = _required(env, "AI_VASTU_OPENAI_MODEL")
'''
new_provider = '''    provider = env.get(
        "AI_VASTU_REQUIREMENTS_PROVIDER",
        "fixture",
    ).strip().lower()
    if provider not in {"openai", "gemini"}:
        raise ProductionConfigurationError(
            "Commercial launch requires a supported live requirements provider."
        )

    openai_model: str | None = None
    gemini_model: str | None = None
    if provider == "openai":
        _required(env, "OPENAI_API_KEY")
        openai_model = _required(env, "AI_VASTU_OPENAI_MODEL")
    else:
        _required(env, "GEMINI_API_KEY")
        gemini_model = _required(env, "AI_VASTU_GEMINI_MODEL")
'''
if old_provider in text:
    text = text.replace(old_provider, new_provider, 1)
elif 'provider not in {"openai", "gemini"}' not in text:
    raise SystemExit("Could not patch production requirements provider policy")
if "gemini_model=gemini_model" not in text:
    marker = "        openai_model=openai_model,\n"
    if marker not in text:
        raise SystemExit("Could not patch ProductionSettings constructor")
    text = text.replace(
        marker,
        marker + "        gemini_model=gemini_model,\n",
        1,
    )
write(path, text)

# 6. Append safe env examples (no secrets).
for relative in (".env.example", ".env.production.example"):
    env_path = ROOT / relative
    if not env_path.is_file():
        continue
    text = env_path.read_text(encoding="utf-8")
    if "AI_VASTU_GEMINI_MODEL" not in text:
        text += '''

# Gemini requirements interpreter
# Set AI_VASTU_REQUIREMENTS_PROVIDER=gemini to enable.
GEMINI_API_KEY=
AI_VASTU_GEMINI_MODEL=gemini-2.5-flash
'''
        env_path.write_text(text, encoding="utf-8")

print("Gemini 2.5 Flash + launch pricing metadata integrated.")
