.PHONY: lint lint-fix fmt

ENV?=

lint:
	$(ENV) ruff check

lint-fix:
	$(ENV) ruff check --fix

fmt:
	$(ENV) ruff format
