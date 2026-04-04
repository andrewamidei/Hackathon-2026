.PHONY: run stop clean test testhard

run: stop
	@echo "Building and starting the app..."
	docker compose up --build

stop:
	@echo "Cleaning up old containers..."
	docker compose down

clean: stop
	@echo "Nuking all project containers and networks..."
	docker compose down -v

testhard:
	@echo "installing libs and Starting unit test..."
	docker compose build --no-cache tester && docker compose run --rm tester
test:
	@echo "Starting unit test..."
	docker compose run --rm tester
