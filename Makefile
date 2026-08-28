.PHONY: run sync test clean

# Run the application
run:
	uv run --project app app

# Sync workspace dependencies and update the virtual environment
sync:
	uv sync

# Run tests (placeholder for future)
test:
	@echo "No tests configured yet. You can add pytest and run: uv run pytest"

# Clean up python caches and the virtual environment
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .venv
