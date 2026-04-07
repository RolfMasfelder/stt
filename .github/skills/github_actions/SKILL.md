---
name: github_actions
display_name: GitHub Actions & Workflows
version: 1.0.0
author: Rolf Masfelder
description: Reference for GitHub Actions versions and workflow conventions used in this project
---

# GitHub Actions & Workflows

Use this skill when creating or editing GitHub Actions workflow files (`.github/workflows/*.yml`).

## Current Action Versions (Stand: April 2026)

Always use these versions when referencing actions. Do NOT use older major versions.

### Core Actions (GitHub)

| Action | Version | Node Runtime | Notes |
|--------|---------|-------------|-------|
| `actions/checkout` | `@v6` | Node 24 | Requires runner v2.329.0+ |
| `actions/setup-python` | `@v6` | Node 24 | Requires runner v2.327.1+ |
| `actions/setup-node` | `@v6` | Node 24 | Auto-caching since v5+ |
| `actions/upload-artifact` | `@v7` | Node 24 | Breaking: new `archive` param, ESM |

### Docker Actions

| Action | Version | Node Runtime | Notes |
|--------|---------|-------------|-------|
| `docker/setup-buildx-action` | `@v4` | Node 24 | `install` input removed |
| `docker/build-push-action` | `@v7` | Node 24 | ESM; deprecated env vars removed |
| `docker/login-action` | `@v4` | Node 24 | |

### Security & Signing

| Action | Version | Notes |
|--------|---------|-------|
| `sigstore/cosign-installer` | `@v4` | Installs Cosign v3; v3.x installer only supports Cosign v2 |
| `aquasecurity/trivy-action` | `@v0.35.0` | Uses `v` prefix tags after supply chain attack fix |

### Dependency & PR Management

| Action | Version | Node Runtime | Notes |
|--------|---------|-------------|-------|
| `peter-evans/create-pull-request` | `@v8` | Node 24 | |
| `dependabot/fetch-metadata` | `@v3` | Node 24 | |

### Infrastructure

| Action | Version | Notes |
|--------|---------|-------|
| `azure/k8s-set-context` | `@v4` | Node 20 (v4.0.2 latest) |

### Flutter

| Action | Version | Notes |
|--------|---------|-------|
| `subosito/flutter-action` | `@v2` | channel: stable, cache: true |

## Archived / DO NOT USE

| Action | Status | Replacement |
|--------|--------|-------------|
| `semgrep/semgrep-action` | **Archived** (April 2024) | `pip install semgrep && semgrep scan` |

## Project Conventions

### Workflow Files
- Location: `.github/workflows/`
- Python version: `3.13`
- Runner: `ubuntu-latest`
- All workflows set `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true`

### Security Scanning
- **pip-audit**: Dependency vulnerability scanning
- **bandit**: Static security analysis (SAST)

### Docker Build Convention
- Platform: `linux/amd64` only
- Registry: `192.168.178.80:5000` (self-signed, insecure-registry)
- Multi-stage build with `production` and `dev` targets

### Existing Workflows

| File | Purpose | Trigger |
|------|---------|---------|
| `backend-test.yml` | Tests & Coverage (pytest, PostgreSQL 17) | push/PR on dev, main (src/tests paths) |
| `backend-quality.yml` | Lint & Format (ruff), dev artifact checks | push/PR on dev, main (src/tests paths) |
| `backend-security.yml` | pip-audit + bandit SAST | push/PR on dev, main + weekly Monday |
| `docker-build.yml` | Build & verify prod/dev Docker images | push/PR on dev, main (Dockerfile/src paths) |
| `flutter-ci.yml` | Flutter lint, analyze, tests, E2E | push/PR on dev, main (mobile/ paths) |
| `dependabot-auto-merge.yml` | Auto-merge minor/patch Dependabot PRs | PR events (dependabot only) |
