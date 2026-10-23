.PHONY: format check

format:
	cd backend && npm run format
	cd frontend && npm run format

check:
	cd backend && npm run db:validate && npm run typecheck && npm test && npm run format:check && npm run build
