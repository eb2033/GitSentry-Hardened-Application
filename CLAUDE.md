# FYP context: Multi-Layered Shift-Left Secret Leakage Controls for GitOps

Read this file first. It is the short brief; `docs/PLAN.md` holds the full design and is the source of truth when the two disagree.

Last updated: 16 November 2026.

## The project

- **Title:** A Multi-Layered Shift-Left Approach to Reducing Secret Leakage in GitOps Pipelines
- **Student:** Georgy Bodrov, K00299992, final year IT, TUS Midwest. Background in networks and cybersecurity.
- **What it is:** a design, build and evaluation project. A hardened GitOps pipeline on AWS (GitHub Actions, ArgoCD, k3s on EC2) is compared with a baseline pipeline that has only a single late scanner. A Python harness runs seeded fake secrets and a harmless "compromised" GitHub Action through both.

## Research questions

1. Which pipeline stages achieve the highest detection rate for seeded secrets, and how does the rate vary by secret type and location?
2. How much does each additional layer add to overall detection coverage compared with a single-scanner baseline?
3. At which stage are leaked secrets first intercepted, and how long does feedback take, compared with a traditional pipeline?
4. How many usable credentials, and with what validity period, can a compromised third-party component capture in the traditional pipeline compared with the hardened pipeline?

## Weak points and control layers

| ID | Weak point | Layer | Control |
| --- | --- | --- | --- |
| W1 | Hardcoded secrets committed | L0 | Gitleaks pre-commit hook, GitHub push protection |
| W2 | Secrets persisting in Git history | L1 | Gitleaks full-history scan, SonarQube Cloud |
| W3 | Poisoned pipeline execution | L2 | zizmor, safe triggers, empty default permissions |
| W4 | Mutable action tags, malicious dependencies | L2, L3 | SHA pinning, Dependabot, Trivy dependency scan |
| W5 | Long-lived credentials visible to every step | L2 | OIDC to AWS, job isolation, GitHub App token |
| W6 | Secrets in image layers | L3 | Trivy image scan, digest-pinned base images |
| W7 | Plaintext credentials in Terraform code or state | L4 | Checkov, encrypted state, write-only arguments |
| W8 | base64 Kubernetes Secrets in Git | L5 | External Secrets Operator with Parameter Store |
| W9 | Unauthorised manual cluster changes | L6 | ArgoCD auto-sync with self-heal |

## Repositories

| Repo | Role |
| --- | --- |
| `fyp-app` | Hardened App repo: API, Dockerfiles, seven isolated CI jobs |
| `fyp-iac` | Hardened IaC repo: `terraform/` (applied through OIDC) and `k8s/` (watched by ArgoCD) |
| `fyp-app-baseline` | Baseline App repo: one job, tag references, static keys, late Gitleaks |
| `fyp-iac-baseline` | Baseline IaC repo: receives commits only, nothing is deployed from it |
| `fyp-test-action` | Instrumented action for RQ4 (moved tag and pinned-SHA scenarios) |
| `fyp-eval` | Local only, no workflows: corpus, harness scripts, results |

Names above are placeholders until the real ones are filled in below.

## Decisions already made

- **30 Oct 2026:** fixes from `claude/Proposal Review - Holes and Fixes.md` adopted. The baseline has one late scanner, RQ4 adds a pinned-SHA scenario, evidence comes from the GitHub API, and the corpus follows SecretBench categories.
- **10 Nov 2026:** five repositories plus the local harness. Terraform and manifests share `fyp-iac`, guarded by pull-request-only `main`, a path check on bot pull requests and an approval gate on `terraform apply`.
- **15 Nov 2026:** reduced scope. No Prometheus or Grafana, no frontend, baseline never deployed, no nightly destroy workflow, cluster up only for building and the demo. k3s and ArgoCD stay.
- **16 Nov 2026:** Parameter Store values use Terraform write-only arguments (`value_wo`), and `k3s-node` uses a custom policy instead of `AmazonSSMManagedInstanceCore`. See `docs/sources/wp1-persistent-stack.md`.

## Status

- Behind the Gantt chart. The AWS and Terraform phase (WP0 to WP2) is not signed off; see `docs/checklists/aws-terraform-signoff.md`.
- WP1 sources collected on 12 November 2026.
- Next: run the two prompts in `docs/prompts/` for the design chapter, then a minimal AWS pass.

## Deadlines

| Deliverable | Date |
| --- | --- |
| Analysis and Design | 6 Dec 2026 |
| Implementation | 31 Jan 2027 |
| Evaluation | 21 Feb 2027 |
| Dissertation and poster | 28 Mar 2027 |
| Technical interview | 29 Mar to 2 Apr 2027 |

## Open questions for the supervisor

- Should the baseline Terraform run `plan` only, with a low-privilege static key?
- Public or private repositories?
- Are the path check and approval gate on `fyp-iac` enough, or is the shared repo a residual risk?
- Is dropping the monitoring stack and the frontend acceptable, given both are in the approved proposal?

## Values to fill in

- GitHub owner: `eb2033`
- Real repository names: `GitSentry-Baseline-Application,GitSentry-Hardened-Application,GitSentry-Baseline-IaC,GitSentry-Hardened-IaC`
- AWS region: `eu-west-1`
- Terraform version: `1.11` (1.11 or later, for write-only arguments)
- AWS provider version: `~> 6.73` (6.73.0, released 2026-11-11; `value_wo` on `aws_ssm_parameter` is supported in 6.x)
- Scanner versions (checked 2026-11-16): Gitleaks `8.30.1`, Trivy `0.76.2`, Checkov `3.4.5`, zizmor `1.32.0`

## Rules for working on this project

- **Never use a real secret.** Seeded secrets are Canarytokens or fake values. The test action records names and metadata, never values.
- **References:** Harvard (TUS style). Never invent a source. The handbook warns that a reference that does not exist can fail the project, so mark anything unverified as "to verify".
- **Dissertation text:** British English, neutral academic register, no contractions, no "I think".
- **Code:** Python by default. Georgy is a beginner in C++, so explain any C++ or unfamiliar Bash.
- **Scope:** do not add components the plan has cut. Propose changes; do not make them silently.
- **When a source contradicts the plan:** add it to the work package's file in `docs/sources/` under "Changes the plan", update `docs/PLAN.md`, then add a dated line under "Decisions already made" here.
- **Keep this file short.** Detail belongs in `docs/PLAN.md`.

## Files

| File | Contents |
| --- | --- |
| `docs/PLAN.md` | Full design, work packages WP0 to WP10, evaluation method, timeline, risks |
| `docs/prompts/architecture-diagram.md` | Prompt for Figures A and B |
| `docs/prompts/threat-model.md` | Prompt for the threat model |
| `docs/sources/wp1-persistent-stack.md` | Sources for WP1 and the plan changes they caused |
| `docs/sources/_TEMPLATE.md` | Template for the other work packages |
| `docs/checklists/aws-terraform-signoff.md` | Sign-off checklist for WP0 to WP2 |

Also in the claude.ai project: the proposal PDF, the FYP handbook PDF and the proposal review notes.
