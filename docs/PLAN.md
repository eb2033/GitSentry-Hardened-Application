# FYP Implementation Plan: Multi-Layered Shift-Left Secret Leakage Controls for GitOps

Georgy Bodrov (K00299992). Created 10 November 2026, last updated 17 November 2026.

This is the canonical plan. `CLAUDE.md` summarises it; the prompts live in `docs/prompts/` and the evidence behind each work package in `docs/sources/`.

## Scope and assumptions

The build is two pipelines over one small application (API and PostgreSQL) on AWS: a hardened GitOps pipeline with controls at layers L0 to L6, and a baseline pipeline to compare it against. A Python evaluation harness runs a seeded-secret corpus and a simulated compromised GitHub Action through both and answers RQ1 to RQ4.

This plan follows the proposal of 28 April 2026 and adopts every fix from the review of 30 October 2026. The changes that alter the design are:

- **Baseline is one definition.** It is a pipeline with a single late scanner (Gitleaks after the build), tag-referenced actions, one job, static AWS keys and push protection switched off. It is not a pipeline with no security.
- **RQ4 gets a second scenario.** Malicious code sitting at the pinned SHA is tested as well as a moved tag, so job isolation and token scoping are measured, not only pinning.
- **Evidence lives in GitHub, not Prometheus.** A Python collector pulls workflow run and job data from the GitHub API into CSV. Prometheus and Grafana are dropped; ArgoCD's own sync history shows drift being reverted.
- **The corpus follows a published taxonomy.** Secret types come from SecretBench categories, and each tool's detection rate is reported only over the locations it is built to scan.
- **"Eliminate" is stated accurately.** External Secrets Operator removes secrets from Git. They still exist in Parameter Store and in the k3s datastore, so both are encrypted and access-scoped.
- **Captures are read from the action's own log.** Canarytoken alerts are supporting evidence only, since bots scraping public repos also trigger them.

**Reduced scope (15 November 2026).** Four cuts that no research question depends on: no Prometheus or Grafana, a two-tier app (API and PostgreSQL), a baseline that is never deployed, and no nightly destroy workflow. The cluster runs only for building, screenshots and the demo. k3s and ArgoCD stay.

Out of scope is unchanged from proposal Section 3.1.1: high availability, private subnets with NAT, service mesh, SSO, artefact signing, SLSA provenance, runner egress monitoring, and a compromised workstation or platform.

Open questions to settle with your supervisor before the Analysis and Design submission:

- [ ] Should Terraform in the baseline IaC repo run plan only, with a low-privilege static key, so the real infrastructure is provisioned once from the hardened repo?
- [ ] Are the repositories public or private? Public gives free push protection and SonarQube Cloud, but exposes the corpus to scrapers.
- [ ] Are the path check and approval gate on the hardened IaC repo enough, or should the threat model record Terraform and manifests sharing a repository as a residual risk?
- [ ] Prometheus and Grafana, and a three-tier app, are named in the approved proposal. Does your supervisor accept dropping the monitoring stack and the frontend?

## Architecture and design

Each control sits in its own CI job with the narrowest token it needs, so a compromised step can only reach what that one job holds. The cluster pulls its configuration from Git, so CI never holds cluster credentials.

Architecture, top to bottom:

1. **Developer workstation (L0):** Gitleaks pre-commit hook.
2. **GitHub push protection (L0):** blocks known token formats at push time; off in the baseline repos.
3. **GitHub Actions on `fyp-app` (L1 to L4):** seven isolated jobs. Five scan jobs hold no cloud credentials; only `publish` and `promote` can write.
4. **`fyp-iac`:** Terraform folder (L4, applied through OIDC behind an approval gate) and manifests folder (L5, images by digest, ExternalSecret references only).
5. **AWS account:** persistent resources (state bucket, OIDC provider, roles, Parameter Store) and a per-session EC2 instance running k3s with ArgoCD and External Secrets Operator (L6).

A change moves top to bottom: it must pass the hook and push protection, then every scan job, before the two write-capable jobs run. Terraform reaches AWS only through the OIDC role, and the cluster reads Parameter Store with its own node role.

### Repositories

| Repository | Holds | Pipeline |
| --- | --- | --- |
| `fyp-app` | Hardened App repo: API, Dockerfiles, hardened workflows, pre-commit config | Hardened CI (seven jobs) |
| `fyp-app-baseline` | Baseline App repo: same source, one baseline workflow, push protection off | Baseline CI (one job) |
| `fyp-iac` | Hardened IaC repo: Terraform (`terraform/persistent`, `terraform/session`) and the manifests ArgoCD watches (`k8s/`), with ExternalSecret references only | Checkov, kubeconform and zizmor on pull requests; Terraform plan and gated apply through OIDC; protected `main` |
| `fyp-iac-baseline` | Baseline IaC repo: baseline manifests with a base64 Kubernetes Secret holding a fake value, and Terraform using a static key. Receives commits only; nothing is deployed from it | One job, no scans; Terraform plan only |
| `fyp-test-action` | The harmless "compromised" action for RQ4 | None |
| `fyp-eval` (local, not on a pipeline) | Corpus manifest, seeding scripts, tool runners, collector, results | None |

Each pipeline has its own App repo and IaC repo, matching your four-repository setup. The action needs a fifth repository because it must be referenced by tag in one pipeline and by SHA in the other. The harness stays outside all of them so its fake secrets and decoys do not trip the scanners.

The promote job can write to `fyp-iac`, which also holds the Terraform. Three settings keep it away from infrastructure code: `main` accepts pull requests only, a required check fails any bot pull request that touches files outside `k8s/`, and `terraform apply` runs from an environment that needs your approval.

### Hardened pipeline (`fyp-app`)

| Job | Tool | Layer and weak point | Token permissions | Secrets held |
| --- | --- | --- | --- | --- |
| `lint-workflows` | zizmor, actionlint | L2: W3, W4 | `contents: read` | None |
| `secret-scan` | Gitleaks over full history (`fetch-depth: 0`) | L1: W2 | `contents: read` | None |
| `sast` | SonarQube Cloud secrets rules | L1: W2 | `contents: read` | `SONAR_TOKEN` |
| `iac-scan` | Checkov on Dockerfiles and YAML | L4: W7 | `contents: read` | None |
| `build-scan` | Docker build, Trivy image and dependency scan | L3: W4, W6 | `contents: read` | None |
| `publish` | Push image to GHCR, output its digest | L2: W5 | `contents: read`, `packages: write` | `GITHUB_TOKEN` only |
| `promote` | GitHub App token, pull request to `fyp-iac` with the new digest | L2: W5 | None on this repo | App private key, from a protected environment |

Rules that apply to every workflow:

- Top-level `permissions: {}`; each job declares its own.
- Triggers are `push` to `main` or to `scenario/**` branches, and `pull_request`. No `pull_request_target`, no `workflow_run`. The `scenario/**` branches carry the harness's seeded cases for integrated runs (RQ3, RQ4); `publish` and `promote` still run only on `main`, so a scenario branch never promotes.
- `publish` and `promote` run only on `main` and `need` every scan job.
- Every action is pinned to a full commit SHA. The repository Actions policy and zizmor's unpinned-uses check both enforce it.
- Checkout uses `persist-credentials: false`, so the token is not left in `.git/config`.
- Scanners run as release binaries verified by checksum, or as container images pinned by digest. This covers the transitive-dependency gap that SHA pinning alone leaves.
- Base images in Dockerfiles are pinned by digest. Dependabot proposes updates to pins.

Layer L0 sits before CI: a `pre-commit` hook running Gitleaks on staged changes, and GitHub push protection on the remote.

### Baseline pipeline (`fyp-app-baseline`)

One job with `permissions: write-all` runs checkout, build, push, promote, then Gitleaks as the last step. Actions are referenced by tag. Static AWS keys and a classic personal access token are stored as repository secrets and exposed to the whole job. The AWS keys belong to an IAM user with no useful permissions and are deleted when testing ends. Push protection and pre-commit are off.

The baseline promotes by committing the new image tag to `fyp-iac-baseline` with the personal access token, and stops there. Nothing is deployed from that repository, because no research question measures the baseline's deploy leg; its stored credentials still count for RQ4. Terraform in that repo runs `plan` only with the low-privilege static key; the real infrastructure is provisioned once, from `fyp-iac`.

### AWS and cluster

**Persistent stack** (created once):

- S3 state bucket with KMS encryption, versioning, public access block and native lock file.
- IAM OIDC provider for GitHub, and role `gha-terraform`. Its trust policy accepts only `repo:<owner>/fyp-iac:environment:production`. A permissions boundary denies creating IAM users and access keys and denies changes to the role or the boundary.
- Instance role `k3s-node` with a custom policy, not `AmazonSSMManagedInstanceCore`. That managed policy allows `ssm:GetParameter(s)` on every resource, which would defeat the path scoping. The custom policy keeps only the Session Manager actions (`ssmmessages:*`, `ec2messages:*`, `ssm:UpdateInstanceInformation`), plus `ssm:GetParameter(s)` on `/fyp/app/*` and `kms:Decrypt` on its key. See `docs/sources/wp1-persistent-stack.md`.
- Parameter Store SecureString parameters written with the write-only argument `value_wo` and a `value_wo_version` counter, so the value never enters plan or state files. Not `value` with `ignore_changes`: Terraform still refreshes the live value into state. Write-only arguments need Terraform 1.11 or later and a recent AWS provider; check the registry for the minimum version (the community SSM module requires provider 6.8 or later, which is a safe floor). Fallback: create the parameters outside Terraform with the CLI and reference them only by name.
- AWS Budgets alert, created before anything else.

**Session stack** (created and destroyed each working session):

- VPC, one public subnet, internet gateway.
- Security group with no inbound admin ports. Only the application port is open, to your own IP.
- One `t3.medium` EC2 instance (move to `t3.large` if memory is short), encrypted root volume, IMDSv2 required with hop limit 2.
- User data installs k3s with `--secrets-encryption`, installs ArgoCD and applies the root Application.

The k3s API and ArgoCD are reached only through Session Manager port forwarding. The cluster is up only for building, screenshots and the demo; evaluation runs need GitHub and the persistent stack, so EC2 stays off for them.

**In the cluster**, all delivered by ArgoCD from `fyp-iac` as an app-of-apps:

- ArgoCD with automated sync, prune and self-heal, and read-only access to the repo.
- External Secrets Operator with one ClusterSecretStore for Parameter Store, authenticating with the node role.
- A NetworkPolicy in every namespace that blocks egress to `169.254.169.254`, except for the External Secrets namespace.
- No monitoring stack. ArgoCD's UI and sync history show drift and self-heal.
- The application: a FastAPI backend and PostgreSQL as a StatefulSet, with no separate frontend. The database password arrives through an ExternalSecret.

### Credential inventory

This table is the design input for RQ4: it lists what each pipeline can leak.

| Credential | Baseline | Hardened |
| --- | --- | --- |
| AWS access for Terraform | Static IAM user key in repo secrets, no expiry, visible to every step | OIDC role, 1-hour credentials, Terraform job only, behind an approval gate |
| Write access to `fyp-iac` | Classic personal access token, long-lived, all repos | GitHub App installation token, 1 hour, that one repo, `promote` job only |
| Registry push | `GITHUB_TOKEN` with write-all, every step | `GITHUB_TOKEN` with `packages: write`, `publish` job only |
| `SONAR_TOKEN` | Not used | Long-lived, `sast` job only (residual risk) |
| GitHub App private key | Not used | Long-lived, environment secret, `promote` job only (residual risk) |
| Database password | A base64 Kubernetes Secret in Git with a fake value, never deployed | Parameter Store, then a Kubernetes Secret, with datastore encryption and metadata blocked for other pods |
| Cluster credentials in CI | None | None |

### Design trade-offs

| Decision | Alternative | Reason |
| --- | --- | --- |
| External Secrets Operator | Sealed Secrets, SOPS | No ciphertext in Git at all. Sealed Secrets is the fallback if time runs short |
| k3s on one EC2 instance | Amazon EKS | The EKS control plane alone costs far more than the whole budget (confirm on AWS pricing) |
| Parameter Store | Secrets Manager | Standard parameters are free; Secrets Manager charges per secret |
| GitHub App token | Personal access token, deploy key | Short-lived, scoped to one repo, not tied to your user account |
| Scanner binaries by checksum | Marketplace actions | An action pinned by SHA can still fetch unpinned code at run time |
| Promote by pull request | Direct push to `main` | Branch protection on `fyp-iac` stays on; a required check gates auto-merge |
| Separate baseline repository | Baseline branch | Push protection and secrets are repository settings, not branch settings |

## Implementation plan

Build in the order below: each work package depends only on the ones above it, and each has a check that proves it is finished. The platform (WP0 to WP4) and the baseline (WP5) come first so the controls are added to something that already works.

| WP | Build | Done when |
| --- | --- | --- |
| WP0 Guardrails | Root MFA, an admin identity with MFA, no root access keys, AWS Budgets alert, CloudTrail. Create the four pipeline repositories and the action repository, branch protection, the GitHub App | A test budget alert arrives by email; `main` rejects a direct push on `fyp-iac` |
| WP1 Persistent stack | State bucket, OIDC provider, `gha-terraform` role and boundary, `k3s-node` role with a custom policy, Parameter Store parameters through `value_wo` | `terraform plan` runs from Actions with no stored keys; the role is denied when it tries to create an IAM user; no SecureString value appears in `terraform state pull`; the node role is denied a parameter outside `/fyp/app/*` |
| WP2 Session stack | VPC, security group, EC2, k3s user data; destroy by hand after each session | Apply to a Ready node in under 10 minutes; destroy leaves nothing billable; an external port scan shows only the application port |
| WP3 Application | FastAPI backend and PostgreSQL; multi-stage Dockerfiles, non-root user, base images by digest | The stack runs under Docker Compose and the images build in CI |
| WP4 GitOps delivery | Infra repo manifests and ArgoCD app-of-apps. The database password sits in a hand-made Secret until WP7 | A merged digest change goes live with no CI access to the cluster; a manual `kubectl edit` is reverted |
| WP5 Baseline pipeline | One-job workflow in `fyp-app-baseline`, static keys, tag references, late Gitleaks; fyp-iac-baseline with its own manifests and plan-only Terraform | Green end to end; a seeded secret reaches GHCR before the Gitleaks step fails |
| WP6 Detection layers | pre-commit, push protection, Gitleaks, SonarQube Cloud, Trivy, Checkov as separate jobs with SARIF or JSON output | Each job fails on one known seeded secret in its own location and passes on a clean commit |
| WP7 Identity and supply chain | Empty top-level `permissions`, job isolation, SHA pinning, zizmor, App token in `promote`, environment approval on Terraform, Dependabot, External Secrets Operator, metadata NetworkPolicy | zizmor reports no findings; no long-lived AWS or GitHub user credential exists in any repository's secrets; no Secret is created by hand; an application pod cannot reach 169.254.169.254 |
| WP8 Drift check | No monitoring stack. Use ArgoCD's UI, CLI and sync history | A manual change is reverted, and the time to self-heal is read from ArgoCD's sync history |
| WP9 Evaluation harness | Corpus manifest, seeding scripts, tool runners, GitHub API collector, `fyp-test-action` | A dry run with five secrets produces a complete CSV for both modes |
| WP10 Evaluation runs | Full isolated and integrated runs, RQ4 scenarios, analysis notebooks | Every table and chart for RQ1 to RQ4 regenerates from the raw CSVs with one command |

### Repository layout

```text
fyp-app/                       # hardened App repo
  backend/  docker-compose.yml
  .pre-commit-config.yaml      # Gitleaks hook
  .gitleaks.toml               # shared by hook and CI
  ci/install-*.sh              # scanner installers, version and SHA-256 pinned
  .github/workflows/ci.yml     # the seven jobs
  .github/dependabot.yml

fyp-iac/                       # hardened IaC repo
  terraform/persistent/        # state, OIDC, roles, boundary, parameters, budget
  terraform/session/           # VPC, security group, EC2, user-data.sh
  k8s/bootstrap/root-app.yaml  # app-of-apps
  k8s/platform/                # external-secrets, network-policies
  k8s/apps/app/                # Deployments, Services, ExternalSecret
  .github/workflows/terraform.yml  manifests.yml
  .github/workflows/pr-paths.yml   # fails bot pull requests outside k8s/

fyp-app-baseline/              # same source as fyp-app
  .github/workflows/baseline.yml   # one job, tag references, late Gitleaks

fyp-iac-baseline/              # baseline IaC repo
  terraform/                   # plan only, static key
  k8s/apps/app/                # same app, base64 Secret, fake value; not deployed

fyp-test-action/               # instrumented action for RQ4
  action.yml  record.sh

fyp-eval/                      # local repository, no workflows
  corpus/manifest.yaml  corpus/templates/
  seed.py  run_isolated.py  run_integrated.py  collect_runs.py  analyse.py
  results/raw/  results/tables/  results/figures/
```

### Implementation details that are easy to get wrong

**Workflow skeleton.** Permissions are denied at the top and granted per job. The scanned image is passed to `publish` as an artefact so the image pushed is the image scanned.

```yaml
on:
  push: { branches: [main, "scenario/**"] }
  pull_request:
permissions: {}
jobs:
  secret-scan:
    runs-on: ubuntu-24.04
    permissions: { contents: read }
    steps:
      - uses: actions/checkout@<full-commit-sha>   # comment the version
        with: { fetch-depth: 0, persist-credentials: false }
      - run: ./ci/install-gitleaks.sh
      - run: gitleaks git --redact --report-format sarif --report-path gitleaks.sarif
  publish:
    if: github.ref == 'refs/heads/main'
    needs: [lint-workflows, secret-scan, sast, iac-scan, build-scan]
    permissions: { contents: read, packages: write }
  promote:
    needs: publish
    environment: promote
    permissions: {}
```

**OIDC trust condition.** Match the subject exactly; a wildcard on the repository or branch lets other workflows assume the role.

```json
"Condition": {
  "StringEquals": {
    "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
    "token.actions.githubusercontent.com:sub": "repo:<owner>/fyp-iac:environment:production"
  }
}
```

**Metadata block.** One policy per namespace, omitted from the External Secrets namespace.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: deny-metadata, namespace: app }
spec:
  podSelector: {}
  policyTypes: [Egress]
  egress:
    - to:
        - ipBlock:
            cidr: 0.0.0.0/0
            except: [169.254.169.254/32]
```

Other points to hold to:

- Bootstrap the state bucket with local state once, then migrate to the S3 backend. Keep `persistent/` and `session/` in separate state files.
- Pass Parameter Store values to `value_wo` from an ephemeral source or a variable entered at apply time, never from a committed `.tfvars` file. Bump `value_wo_version` to rotate a value.
- Use the same `.gitleaks.toml` in the hook and in CI, so L0 and L1 differ only in scope (staged changes against full history).
- Record every tool version and rule-set version in `fyp-eval`; detection results are only reproducible against a fixed version.
- Keep a build journal with screenshots as you go. The Implementation chapter must let someone else reproduce the build.

## Evaluation

The same seeded corpus goes through both pipelines in two modes, and a test action runs in every job under three compromise scenarios. Every reported number is computed by script from raw CSV, so the Testing chapter can be regenerated.

### Corpus

A proposed size is about 100 cases: 5 secret types across 7 locations with 2 variants each (70 seeded secrets), plus 30 decoys. Adjust the count once the first dry run shows how long a full pass takes.

| Dimension | Values |
| --- | --- |
| Secret types (after SecretBench categories) | Cloud provider keys (AWS Canarytokens), API tokens with known prefixes, private keys in PEM form, database connection strings, generic passwords with no prefix |
| Locations | Current source code, Git history (added then removed), Dockerfile `ENV` or `ARG`, image layer (file copied then deleted), Terraform variables, Kubernetes manifests, workflow files |
| Decoys | UUIDs, hashes, documented example keys, base64 of non-secret text, placeholder strings |

Each case is one row in `corpus/manifest.yaml`: id, type, location, file path, whether it is a decoy, and which tools are in scope for that location. `seed.py` builds the test repositories from the manifest, so the corpus is versioned and repeatable. No real credential is ever used.

Fix the in-scope matrix before running anything, from each tool's documentation. A tool's detection rate is then reported only over locations it is designed to scan. The starting assumption to verify:

| Location | Gitleaks hook | Push protection | Gitleaks CI | SonarQube Cloud | Trivy | Checkov |
| --- | --- | --- | --- | --- | --- | --- |
| Current source code | Yes | Yes | Yes | Yes | Yes | No |
| Git history | No | Yes | Yes | No | No | No |
| Dockerfile | Yes | Yes | Yes | Verify | Yes | Yes |
| Image layer | No | No | No | No | Yes | No |
| Terraform variables | Yes | Yes | Yes | Verify | Verify | Yes |
| Kubernetes manifests | Yes | Yes | Yes | Verify | Verify | Yes |
| Workflow files | Yes | Yes | Yes | No | No | Yes |

### Isolated mode (RQ1, RQ2)

Each tool runs alone, in a container at a fixed version, against a checkout holding the whole corpus. `run_isolated.py` parses each tool's SARIF or JSON output and matches findings to cases by file path and line.

- **RQ1:** recall per tool, broken down by secret type and location, over in-scope cases only.
- **RQ2:** cumulative coverage as layers are added in pipeline order, starting from Gitleaks alone; unique detections per tool; precision and false-positive rate from the decoys.

### Integrated mode (RQ3)

One case per run, through the real pipelines with fail-fast behaviour. Use a stratified sample of about 30 cases, not the full corpus, to keep the run count manageable. Each sampled case runs under two scenarios in each pipeline, about 120 runs in total.

| Scenario | Developer behaviour |
| --- | --- |
| A: controls respected | Hook installed, push protection obeyed |
| B: early controls bypassed | Commit with `--no-verify`, push protection bypassed where GitHub offers it |

`run_integrated.py` pushes each case on its own branch and `collect_runs.py` reads the result from the GitHub API. Recorded per run:

- Stage of first interception (hook, push, or the first failing job).
- Time to feedback: commit to hook result locally, or push time to the failing job's completion time.
- Furthest point reached: local only, remote history, image in GHCR, `fyp-iac` (the last stop before ArgoCD deploys it).

Repeat each timed run three times and report the median, since runner queue times vary.

### Compromised action (RQ4)

`fyp-test-action` is placed in every job of both pipelines. It records names and metadata only, never values, and writes them to the job summary and an artefact.

| Scenario | Setup | What it tests |
| --- | --- | --- |
| S1 Moved tag | Tag `v1` is moved to a modified commit. Baseline references `@v1`; hardened references the original SHA | SHA pinning (control case, outcome expected) |
| S2 Compromise at the pinned SHA | Hardened pins the modified commit itself, as after a bad Dependabot bump or an upstream compromise before pinning | Job isolation, token scoping, secret-free scan jobs |
| S3 Transitive (stretch) | A clean, pinned action downloads an unpinned script at run time | The limit of SHA pinning |

Per job, the action records:

- Names of environment variables that look like credentials.
- Whether an OIDC token can be requested from the job.
- What `GITHUB_TOKEN` can do, probed with read-only API calls.
- Credential files on disk: AWS config, Docker config, Git credentials left by checkout.
- Type and expiry of each credential found.

Metrics are the number of usable credentials per job and per pipeline, each one's validity period, and what each could reach.

### Research questions to evidence

| RQ | Mode | Metrics | Source |
| --- | --- | --- | --- |
| RQ1 | Isolated | Recall per layer by type and location, in-scope cases only | `results/raw/isolated.csv` |
| RQ2 | Isolated | Cumulative coverage, unique detections, precision, false-positive rate | Same file |
| RQ3 | Integrated | Stage of first interception, time to feedback, furthest point reached | GitHub API through `collect_runs.py`; local hook timings |
| RQ4 | S1 to S3 | Whether the code ran, credentials per job, validity period, reach | Test action artefacts |

A drift test supports the L6 claim without being a research question: change a Deployment by hand ten times and report median time to self-heal from ArgoCD's sync history.

### Limits to state in the dissertation

- You wrote the corpus knowing the tools. The published taxonomy and the pre-fixed in-scope matrix reduce this bias but do not remove it.
- Results hold for the tool versions and default rule sets recorded, on one small application.
- Push protection behaviour is set by GitHub and can change during the project; record the dates of each run.
- The project involves no participants or third-party data. Confirm with your supervisor that no ethical approval form is needed, and say so in the Methodology.

## Timeline

The build runs to the Implementation deadline on 31 January 2027 and evaluation to 21 February 2027, following the ten phases of your Gantt chart (proposal Figure 2).

| Phase (Gantt chart) | Approximate dates | Deadline |
| --- | --- | --- |
| AWS and Terraform | 8 Oct to 6 Nov 2026 | Behind schedule |
| k3s, app, ArgoCD, baseline | 1 to 30 Nov 2026 | |
| Analysis and Design | 6 Nov to 6 Dec 2026 | 6 Dec 2026 |
| Secret detection layers | 18 Dec 2026 to 18 Jan 2027 | |
| OIDC, ESO, hardening | 1 to 31 Jan 2027 | 31 Jan 2027 (Implementation) |
| Evaluation | 22 Jan to 21 Feb 2027 | 21 Feb 2027 |
| Dissertation and poster | 21 Feb to 28 Mar 2027 | 28 Mar 2027 |
| Interview and poster | 29 Mar to 2 Apr 2027 | |

Bar start dates are read off the Gantt chart and are approximate; the deadlines are the ones it labels. As of 16 November 2026 the AWS and Terraform phase is not yet signed off. Catch-up order: run the two prompts for the design chapter, do a minimal AWS pass (state bucket, OIDC role, session stack, clean destroy), and leave the permissions boundary, approval gate and Checkov in CI for January. No work is planned for the December exam weeks.

What each gate needs from this plan:

- **Analysis and Design, 6 December 2026 (5%).** The architecture figure, the threat model, the credential inventory, the trade-off table and the evaluation design. The two prompts in `docs/prompts/` produce the first two.
- **Implementation, 31 January 2027 (5%).** WP0 to WP9 complete, written up from the build journal with screenshots.
- **Evaluation, 21 February 2027 (5%).** WP10 complete, with tables and charts for all four research questions.
- **Dissertation and poster, 28 March 2027**, then the **interview, 29 March to 2 April 2027**. A live demo: seed one secret, show where each pipeline stops it, then show the test action's capture from both.

The Gantt chart has no phase for the evaluation harness (WP9). Build the corpus and the isolated-mode runner in December alongside the detection layers, since they need no AWS resources. Evaluation can then start on time in late January.

## Risks and fallbacks

Time is the largest risk, so every fallback below cuts scope without touching a research question.

| Risk | Likelihood | Impact | Mitigation or fallback |
| --- | --- | --- | --- |
| Platform work overruns into the controls phase | Medium | High | Replace External Secrets Operator with Sealed Secrets; drop scenario S3; cut the integrated sample from 30 to 20 cases |
| AWS costs exceed the estimate | Medium | Medium | Budgets alert before any resource exists; destroy by hand after every session and check the EC2 console; cluster up only for building and the demo; no NAT gateway or load balancer |
| `t3.medium` runs out of memory with ArgoCD, External Secrets and the app | Medium | Low | Less likely now the monitoring stack is cut; if it happens, move to `t3.large` |
| A scanner or action in the pipeline is itself compromised | Low | High | Binaries verified by checksum, actions pinned by SHA, scan jobs hold no secrets, corpus contains no real credentials |
| SonarQube Cloud's free tier or secrets rules do not fit the project | Medium | Low | Test it first in WP6; if unsuitable, report it as a finding and keep Gitleaks as the only L1 detector |
| Push protection treats fake tokens inconsistently | Medium | Medium | Record its behaviour as a measured result; seed the baseline repository where it is off |
| Scrapers act on seeded secrets in public repositories | High | Low | Canarytokens and fake values only; RQ4 evidence comes from the test action's own log |
| The baseline's static AWS keys are misused | Low | Medium | IAM user with no useful permissions; keys deleted the day testing ends |
| Evidence is lost when a session is destroyed | Medium | High | All raw results and API responses are committed to `fyp-eval` at the end of every session |
| GitHub changes Actions or API behaviour mid-project | Low | Medium | Store raw API responses, record run dates and tool versions, rerun a small sample before writing up |
