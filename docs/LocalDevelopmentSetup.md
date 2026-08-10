# Local Development Setup

**Status: Planned.** There is no runnable code in `src/platform/` yet, so there is no local development workflow to document today. This guide will be filled in once the [Core Platform port from PAFN](../README.md#roadmap) lands.

## What this guide will cover

1. Python environment setup (target: Python 3.10+, see `pyproject.toml`)
2. Azure Functions Core Tools installation for running the Durable Functions orchestrator locally
3. `local.settings.json` configuration pointing at a dev Azure environment (Cosmos DB, Storage, Azure OpenAI, Document Intelligence)
4. Running the lint and test suite locally (`ruff check .`, `pytest`) - see [.github/workflows/ci.yml](../.github/workflows/ci.yml) for the same checks run in CI
5. Submitting a sample case bundle against a local run

## Today, you can

- Run the existing CI checks locally: `ruff check .` and `pytest -q` (both pass trivially today since there is no code yet to lint or test)
- Review [CONTRIBUTING.md](../CONTRIBUTING.md) for repository contribution conventions
