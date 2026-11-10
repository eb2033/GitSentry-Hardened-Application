# GitSentry Hardened App

Application repo for the final year project *"A Multi-Layered Shift-Left Approach to
Reducing Secret Leakage in GitOps Pipelines"*. This is the **hardened** variant; its
twin, `GitSentry-Baseline-App`, has identical application code but a deliberately weak
pipeline. ArgoCD watches a separate infra repo; CI here commits image digests to it.

## Layout

```
backend/     FastAPI + psycopg API (GET /health, GET/POST /items)
frontend/    Static HTML/JS served by nginx-unprivileged
.github/     CI workflow, Dependabot, CODEOWNERS
```
The database tier is a stock Postgres image deployed from the infra repo.

## Run locally

```
cp .env.example .env     # fill in values; .env is git-ignored
docker compose up --build
```
Open http://localhost:8080. Note `.env` values (e.g. `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_PORT`) must be set.

## Security controls

| File | Layer | Control |
|------|-------|---------|
| `.gitignore`, `.dockerignore`, `.env.example` | L0 Prevent | Keep secret-bearing files out of git and images |
| `.pre-commit-config.yaml`, `.gitleaks.toml` | L0 Prevent | Local Gitleaks hook blocks secrets before commit |
| `.github/CODEOWNERS` | L0 Prevent | Workflow changes require owner review |
| `.github/workflows/ci.yml` (gitleaks job) | L1 Detect | Full-history secret scan |
| `.github/workflows/ci.yml` (zizmor job) | L1 Detect | Workflow linting |
| `sonar-project.properties`, sonarqube job | L1 Detect | SAST in an isolated job; only job with `SONAR_TOKEN` |
| `.github/dependabot.yml` | L1 Detect | Weekly updates for actions, pip, docker |
| `ci.yml` build job (Trivy) | L1 Detect | Image scan for secrets and HIGH/CRITICAL vulns |
| `ci.yml` `permissions: {}`, SHA-pinned actions, `persist-credentials: false`, timeouts | L2 Contain | Least-privilege tokens, supply-chain pinning |
| `ci.yml` bump-infra job | L2 Contain | Short-lived GitHub App token scoped to the infra repo, used only there |
| `ci.yml` digest references | L3 Integrity | Infra repo gets `@sha256` digests, not mutable tags |
| `backend/Dockerfile`, `frontend/Dockerfile` | L2 Contain | Non-root, digest-pinned bases, no secrets in ARG/ENV |
