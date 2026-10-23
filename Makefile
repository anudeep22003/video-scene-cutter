.PHONY: format check db-up db-down db-logs

db-up:
	docker compose up -d --wait postgres

db-down:
	docker compose down

db-logs:
	docker compose logs -f postgres

format:
	cd backend && npm run format
	cd frontend && npm run format

check:
	cd backend && npm run generate && npm run db:validate && npm run typecheck && npm test && npm run format:check && npm run build
