# GitSentry Hardened App

Application repo for the final year project *"A Multi-Layered Shift-Left Approach to
Reducing Secret Leakage in GitOps Pipelines"*. This is the **hardened** variant; its
twin, `GitSentry-Baseline-Application`, has the same application (FastAPI backend and
PostgreSQL) but a deliberately weak pipeline. ArgoCD watches `GitSentry-Hardened-IaC`;
CI here proposes image digests to it by pull request. See `docs/PLAN.md`, WP3.

## Layout

```
backend/     FastAPI + psycopg API (GET /health, GET/POST /items)
.github/     CI workflow, Dependabot, CODEOWNERS
```
There is no separate frontend (cut on 15 Nov 2026, see `docs/PLAN.md`). The database
tier is a stock Postgres image, deployed from the IaC repo as a StatefulSet.

## Run locally

```sh
cp .env.example .env     # fill in fake values only; .env is git-ignored
docker compose up --build
curl http://localhost:8000/health
curl -X POST http://localhost:8000/items -H 'Content-Type: application/json' -d '{"name":"test"}'
curl http://localhost:8000/items
```
`DB_NAME`, `DB_USER`, `DB_PASSWORD` and `DB_PORT` must be set. `DB_PORT` is the port
Postgres listens on inside the Compose network, so keep it at `5432`. The backend exits
at startup if any required variable is missing.

## Security controls

| File | Layer | Control |
|------|-------|---------|
| `.gitignore`, `.dockerignore`, `.env.example` | L0 Prevent | Keep secret-bearing files out of git and images |
| `.pre-commit-config.yaml`, `.gitleaks.toml` | L0 Prevent | Local Gitleaks hook blocks secrets before commit |
| `.github/CODEOWNERS` | L0 Prevent | Workflow changes require owner review |
| `.github/workflows/ci.yml` (secret-scan job) | L1 Detect | Gitleaks full-history scan |
| `.github/workflows/ci.yml` (lint-workflows job) | L1 Detect | zizmor workflow linting |
| `sonar-project.properties`, sast job | L1 Detect | SonarQube Cloud SAST; only job with `SONAR_TOKEN` |
| `.github/dependabot.yml` | L1 Detect | Weekly updates for actions, pip, docker |
| `ci.yml` build-scan job (Trivy) | L1 Detect | Image scan for secrets and HIGH/CRITICAL vulns before push |
| `ci.yml` `permissions: {}`, SHA-pinned actions, `persist-credentials: false`, timeouts | L2 Contain | Least-privilege tokens, supply-chain pinning |
| `ci.yml` promote job | L2 Contain | Short-lived GitHub App token scoped to the IaC repo, used only there |
| `ci.yml` digest references | L3 Integrity | IaC repo gets `@sha256` digests, not mutable tags |
| `backend/Dockerfile` | L2 Contain | Multi-stage, non-root (UID 10001), digest-pinned base, no secrets in ARG/ENV |
