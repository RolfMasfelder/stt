# AI Coding Agent Instructions

## Critical Rules

**Development with Python 3.13**: Use Python 3.13 syntax and libraries only
**Tests required**: ALL features/bugfixes MUST have tests (unit + integration)
**Development with venv**: Use virtual environment for local dev (python -m venv .venv), always use "source venv/bin/activate" before running any commands, and in any terminal session
**Git Commits**: Keep messages concise (feat/fix/refactor format). NO long descriptions. Only one line as commit-message
**Docker first**: ALL commands via `docker-compose exec stt [cmd]`

## Architecture Basics


## Git Branches
- `main` → Stable branch, receives merges from `dev` at milestone/release points
- `dev` → Active development branch (default working branch)
- Always work on `dev`. Merge to `main` only for stable releases.

## Git Remotes
- `origin` → Local mirror (always push, NO CI)
- `github` → GitHub private repo (push only when explicitly requested, NOT automatic)
- Default: push to `origin` only. Push to `github` only on user request.

## Documentation (if needed)
- Check `TODO.md` for production-critical items if needed
- Use `docs/` folder for additional docs if needed
- Use `scripts/` folder for additional shell scripts

# AI Coding Agent Instructions

**Type-Hints**: Always use Type-Hints
