.PHONY: format check db-up db-down db-logs workers-install workers-format workers-check

workers-install:
	python3.12 -m venv workers/.venv
	workers/.venv/bin/python -m pip install -r workers/requirements-dev.txt

workers-format:
	workers/.venv/bin/ruff format workers
	workers/.venv/bin/ruff check --fix workers

workers-check:
	workers/.venv/bin/ruff format --check workers
	workers/.venv/bin/ruff check workers
	workers/.venv/bin/python -m unittest workers.test_workers -v

db-up:
	docker compose up -d --wait postgres

db-down:
	docker compose down

db-logs:
	docker compose logs -f postgres

format:
	cd backend && npm run format
	cd frontend && npm run format
	$(MAKE) workers-format

check:
	cd backend && npm run generate && npm run db:validate && npm run typecheck && npm test && npm run format:check && npm run build
	$(MAKE) workers-check
