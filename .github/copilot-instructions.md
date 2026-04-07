# AI Coding Agent Instructions

## Critical Rules

- **Python 3.13**: Use Python 3.13 syntax and libraries only
- **Type-Hints**: Always use Type-Hints
- **Tests required**: ALL features/bugfixes MUST have tests (unit + integration)
- **Development with venv**: Use virtual environment for local dev (python -m venv .venv), always use "source venv/bin/activate" before running any commands, and in any terminal session
- **Git Commits**: Keep messages concise (feat/fix/refactor format). NO long descriptions. Only one line as commit-message
- **Docker first**: ALL commands via `docker compose exec [cmd]`

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

## Skills
- **GitHub Actions & Workflows**: See `.github/skills/github_actions/SKILL.md` for current action versions and workflow conventions

## STT Docker Setup

- Docker service names: `stt-server`, `stt-worker`, `db`, `caddy`
- Commands: `docker compose exec stt-server python manage.py ...`
- App label for migrations: `api` (not `stt_api`)
- DB: PostgreSQL 17 in `stt-db` container

## Kubernetes Setup
- use Kustomize: `kubectl apply -k k8s/base/`
- Helm chart: `helm install stt k8s/helm/stt/`
- Namespace: `stt`
- DB: PostgreSQL 17 in `stt-db` pod

## Container Registry & Deployment Workflow
- Registry: `192.168.178.80:5000` (cirrus7-neu, HTTPS self-signed, registry:2)
- Local Docker: configured as insecure-registry in daemon.json
- k3s: configured in `/etc/rancher/k3s/registries.yaml` with `insecure_skip_verify: true`
- Image deploy workflow (NOT docker save/import):
  1. Build: `docker compose build stt-server`
  2. Tag: `docker tag stt-server:latest 192.168.178.80:5000/stt-server:latest`
  3. Push: `docker push 192.168.178.80:5000/stt-server:latest`
  4. Deploy: `helm upgrade stt k8s/helm/stt/ -n stt -f k8s/helm/values-k3s.yaml`
- k3s values: `k8s/helm/values-k3s.yaml` (image pullPolicy: Always, repository: 192.168.178.80:5000/stt-server)
