# criterium
Tool for researching and comparing products according to a predefined criteria.

## Structure

- `src/criterium/`: installable Python library
- `app/src/app/`: FastAPI application workspace member
- `tests/`: library unit tests
- `app/tests/`: server tests using FastAPI's in-process test client
- `notebooks/`: API examples

## Development

```bash
make sync
make test
make run
```

Tests replace external Gemini and Firecrawl calls with deterministic fakes. Live API calls are not part of the default test suite.
