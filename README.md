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

The application uses the file-backed SQLite database `criterium.db` by default, so collections, jobs, and research results survive server restarts. Override its location with `DB_URL`; in-memory databases are intentionally unsupported.

A collection stores only its user-facing research criteria: field types, descriptions, object properties, and array items. Criterium adds structured-output requirements at LLM call time, so every configured property is returned and unavailable values become explicit `null` values.

Research uses a shared built-in prompt. Collections may optionally add `research_instructions` for cross-cutting scope, source, methodology, or interpretation rules that do not fit naturally in field descriptions.

## Collection Suggestions

`POST /collections/suggest-schema` accepts a plain-language collection description and returns a proposed name, validated research schema, and optional research instructions when special guidance is needed. The new-collection form exposes the same workflow through **Generate Starter**.

## Batch Research

`POST /collections/{collection_id}/research-jobs` accepts up to 100 unique product names as `{"product_infos": ["First", "Second"]}` and returns one queued job per product in the same order. Each job is processed independently and can be monitored through the research-job endpoints. Three research workers run concurrently by default; set `RESEARCH_WORKER_CONCURRENCY` from 1 to 16 to tune provider concurrency.
