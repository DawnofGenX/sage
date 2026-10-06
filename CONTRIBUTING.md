# Contributing to Sage

Thanks for your interest in contributing to Sage!

## Development Setup

1. Fork and clone the repo
2. Install dependencies:
   ```bash
   cd mcp-server && pip install -r requirements.txt
   cd web-simulator && npm install
   ```
3. Run tests:
   ```bash
   cd mcp-server && pytest
   cd web-simulator && npm test
   ```

## Pull Requests

1. Create a feature branch
2. Make your changes with tests
3. Ensure all tests pass
4. Submit a PR with a clear description

## Code Style

- Python: PEP 8, type hints
- TypeScript: ESLint, Prettier
- Commit messages: conventional commits (feat:, fix:, docs:)

## Issues

Check the issue tracker for open issues or create a new one.
