start:
	docker-compose up

stop:
	docker-compose down

remove:
	docker-compose down -v --remove-orphans

build:
	docker-compose build

rebuild:
	make stop
	make build
	make start

format:
	docker compose run --rm fast-api python -m black .
	docker compose run --rm fast-api python -m isort .

packages:
	docker compose run --rm fast-api python -m pip list

test:
	docker compose run --rm fast-api pytest
