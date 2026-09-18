.PHONY: test lint typecheck web-build docker-build

test:
	pytest

lint:
	ruff check .

typecheck:
	mypy apps/api/src packages tests

web-build:
	cd apps/web && npm install && npm run build

docker-build:
	docker build -f docker/api.Dockerfile -t oceantrace-api:dev .

