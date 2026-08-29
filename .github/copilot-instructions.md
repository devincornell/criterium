# Project Context
This is a Python project managed as a `uv` workspace. It contains both a library and an application.

## Structure
- Root `pyproject.toml` defines the `criterium` library and the `app` workspace member.
- `src/criterium/`: The Python library package.
- `app/`: The Python application that consumes the `criterium` library as a local dependency.
- `tests/`: Library unit tests.
- `app/tests/`: FastAPI server tests.

## Development Workflow
- Always use `uv` commands from the root directory when possible.
- A `Makefile` is available in the root for common tasks:
  - `make run`: Runs the app (`uv run --project app app`).
  - `make sync`: Installs/syncs all workspace dependencies (`uv sync --all-packages`).
  - `make test`: Runs pytest with branch coverage.
  - `make clean`: Removes caches and the `.venv` directory.

## Python Environment
- Do NOT use `pip` directly. Always use `uv add <package>` or `uv sync` to manage dependencies.
- The virtual environment is shared and located at the root `.venv`.
