.PHONY: run stop clean

run: stop
	@echo "Building and starting the app..."
	docker compose up --build -d
	@echo "App is running at http://localhost:8501"

stop:
	@echo "Cleaning up old containers..."
	docker compose down

clean: stop
	@echo "Nuking all project containers and networks..."
	docker compose down -v
