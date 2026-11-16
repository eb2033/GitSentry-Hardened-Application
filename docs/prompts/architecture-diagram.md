# Prompt: architecture diagram

Part of the FYP context set. Produces Figure A (hardened) and Figure B (baseline) for the Analysis and Design chapter. Keep it in step with `docs/PLAN.md`.

Paste this into any capable model. It asks for draw.io XML, which you can import, restyle and export at print resolution; change the output line if you prefer Mermaid or another tool.

```text
You are a cloud security architect preparing figures for an undergraduate
dissertation titled "A Multi-Layered Shift-Left Approach to Reducing Secret
Leakage in GitOps Pipelines". Produce two architecture diagrams of the system
described below: Figure A (hardened pipeline) and Figure B (baseline pipeline).
Use the same layout for both so a reader can compare them side by side.

OUTPUT
- One draw.io (diagrams.net) XML file per figure, importable as-is.
- After the XML, list any assumptions you made and anything in this brief that
  was ambiguous. Do not add components, flows or controls I have not listed.

LAYOUT
- Four zones as labelled containers, left to right: (1) Source control,
  (2) Continuous integration, (3) CD and platform, (4) AWS infrastructure.
- Place the developer machine at the top of zone 1 inside its own trust boundary, as in my existing Figure 1.
- Keep the conventions of my existing Figure 1: blue fill for security controls, numbered red circles for weak points W1 to W9, red dashed outlines for trust boundaries, solid arrows for code and data flow, dashed arrows for watch or pull, dotted arrows for short-lived credentials.
- Label fyp-app as "App repo" and fyp-iac as "Infra repo", as in Figure 1.
- Draw trust boundaries as dashed lines: workstation | GitHub | GitHub-hosted
  runner (one boundary per CI job in Figure A) | AWS account | k3s cluster |
  individual namespace.

COMPONENTS
Developer workstation: Git client; pre-commit hook running Gitleaks.
Zone 1, Source control (GitHub):
  - fyp-app repository (application source, Dockerfiles, workflows)
  - fyp-iac repository (Kustomize manifests, ArgoCD Applications,
    ExternalSecret references; protected main branch)
  - The fyp-iac repository also holds the Terraform (persistent and session
    stacks) in its own folder
  - fyp-test-action repository (the instrumented action used for RQ4)
  - GitHub push protection
  - GitHub Container Registry (GHCR)
Zone 2, Continuous integration (GitHub Actions), Figure A, seven separate jobs
in fyp-app, each its own box showing its token scope and secrets:
  1. lint-workflows: zizmor, actionlint; contents:read; no secrets
  2. secret-scan: Gitleaks, full history; contents:read; no secrets
  3. sast: SonarQube Cloud; contents:read; SONAR_TOKEN
  4. iac-scan: Checkov; contents:read; no secrets
  5. build-scan: Docker build, Trivy image and dependency scan;
     contents:read; no secrets
  6. publish: push image to GHCR by digest; packages:write; main only
  7. promote: short-lived GitHub App token; opens a pull request on
     fyp-iac with the new image digest; protected environment
  Plus, in fyp-iac, one Terraform job: Checkov, plan, apply behind an
  approval gate; authenticates to AWS by OIDC; no stored keys.
  External service: SonarQube Cloud.
Zone 3, CD and platform (single-node k3s on one EC2 instance):
  - ArgoCD (auto-sync, prune, self-heal; read-only pull from fyp-iac)
  - External Secrets Operator with a ClusterSecretStore
  - Application namespace: FastAPI backend, PostgreSQL
  - Kubernetes Secret created by External Secrets Operator (encrypted at
    rest with k3s secrets encryption)
  - NetworkPolicy blocking the instance metadata endpoint for all pods
    except External Secrets Operator
  - No monitoring stack; ArgoCD's own UI shows sync status and drift
Zone 4, AWS infrastructure:
  - Persistent: S3 remote state bucket (KMS-encrypted, versioned); IAM OIDC
    identity provider; role gha-terraform with a permissions boundary;
    instance role k3s-node scoped to one Parameter Store path; Systems
    Manager Parameter Store (SecureString); AWS Budgets
  - Per session: VPC, public subnet, internet gateway, security group with
    no inbound admin ports, EC2 instance (IMDSv2, hop limit 2)
  - Administrator access by Session Manager port forwarding only

FLOWS (number each arrow and label it; show direction)
1. Developer commits; pre-commit hook scans staged changes.
2. Developer pushes to fyp-app; push protection inspects the push.
3. Push or pull request triggers the CI jobs.
4. sast job sends analysis to SonarQube Cloud.
5. publish job pushes the image to GHCR.
6. promote job opens a pull request on fyp-iac with the image digest.
7. ArgoCD pulls manifests from fyp-iac (arrow starts at the cluster).
8. k3s pulls the image from GHCR by digest.
9. Terraform job requests an OIDC token from GitHub and exchanges it with AWS
   STS for 1-hour credentials.
10. Terraform reads and writes state in S3 and provisions both stacks.
11. External Secrets Operator reads Parameter Store using the node role and
    writes a Kubernetes Secret.
12. Backend reads the database password from that Secret.
13. ArgoCD compares the cluster with fyp-iac and reverts manual changes.

ANNOTATIONS
Mark each weak point with a numbered red circle at the place it occurs, and
each control layer with a badge on the component that implements it:
  W1 hardcoded secrets committed (workstation)        -> L0 hook, push protection
  W2 secrets persisting in Git history (fyp-app)      -> L1 Gitleaks CI, SonarQube
  W3 poisoned pipeline execution (workflow triggers)  -> L2 zizmor, safe triggers,
                                                         read-only default token
  W4 mutable action tags, malicious dependencies      -> L2 SHA pinning, Dependabot;
                                                         L3 Trivy dependency scan
  W5 long-lived credentials visible to every step     -> L2 OIDC, job isolation,
                                                         GitHub App token
  W6 secrets in container image layers                -> L3 Trivy image scan,
                                                         digest-pinned base images
  W7 plaintext credentials in Terraform code or state -> L4 Checkov, encrypted state
  W8 base64 Kubernetes Secrets in Git (fyp-iac)    -> L5 External Secrets Operator
  W9 unauthorised manual cluster changes              -> L6 ArgoCD self-heal
Include a legend for: zones, trust boundaries, weak-point markers, layer
badges, and line styles (push, pull, credential exchange).

FIGURE B, BASELINE (same zones and positions)
- Repositories fyp-app-baseline and fyp-iac-baseline replace fyp-app and
  fyp-iac; no pre-commit hook; push
  protection disabled.
- Zone 2 is ONE job with write-all token permissions: checkout, build, push
  to GHCR, commit to fyp-iac-baseline, then a Gitleaks scan as the last step.
- Actions referenced by mutable tag.
- Repository secrets visible to every step: static AWS access key for an IAM
  user, classic personal access token.
- No OIDC provider in use; no job isolation.
- Zone 4 unchanged. In zone 3 nothing is deployed from
  fyp-iac-baseline, so draw no pull arrow from it. Show W1 to W9 markers with no layer badges, except
  the single late Gitleaks step.

STYLE
- Must be legible in black-and-white print at A4 page width: minimum label
  size equivalent to 9 pt at that width, at most three accent colours, and
  never colour alone to carry meaning.
- Orthogonal connectors; avoid crossings; no arrow may pass through a box.
- Short labels (component name plus at most one line). British English.
- No title inside the figure; captions are added in the document.
- Generic shapes only, or official AWS and Kubernetes icon sets if available
  in draw.io. No decorative imagery.
```
