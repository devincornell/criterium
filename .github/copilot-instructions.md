# Project Context
This is a Python project managed as a `uv` workspace. It contains both a library and an application.

## Structure
- Root `pyproject.toml` defines the workspace members (`src/*` and `app`).
- `src/criterium/`: The Python library package being developed.
- `app/`: The Python application that consumes the `criterium` library as a local dependency.

## Development Workflow
- Always use `uv` commands from the root directory when possible.
- A `Makefile` is available in the root for common tasks:
  - `make run`: Runs the app (`uv run --project app app`).
  - `make sync`: Installs/syncs workspace dependencies (`uv sync`).
  - `make clean`: Removes caches and the `.venv` directory.

## Python Environment
- Do NOT use `pip` directly. Always use `uv add <package>` or `uv sync` to manage dependencies.
- The virtual environment is shared and located at the root `.venv`.
