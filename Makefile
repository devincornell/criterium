.PHONY: run sync test clean

# Run the application
run:
	uv run --project app app

# Sync workspace dependencies and update the virtual environment
sync:
	uv sync --all-packages

test:
	uv run --all-packages pytest --cov --cov-report=term-missing

build:
	sudo docker compose up --build

# Clean up python caches and the virtual environment
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .venv
