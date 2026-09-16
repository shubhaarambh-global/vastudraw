.PHONY: bootstrap validate test lint typecheck

bootstrap:
	./scripts/bootstrap-wsl.sh

validate:
	./scripts/validate.sh

test:
	. .venv/bin/activate && pytest && pnpm test

lint:
	. .venv/bin/activate && ruff check python apps/api tests && pnpm lint

typecheck:
	. .venv/bin/activate && mypy && pnpm typecheck
