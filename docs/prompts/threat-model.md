# Prompt: detailed threat model

Part of the FYP context set. Produces the threat model for the Analysis and Design chapter. Keep it in step with `docs/PLAN.md`.

This prompt is self-contained. It scopes the model to secret leakage, forces every threat to map to a weak point, a control and a test, and asks for residual risk so the dissertation does not overclaim.

```text
You are a senior application security engineer who specialises in CI/CD and
software supply-chain security. Produce a detailed threat model for the system
below. It will form part of the Analysis and Design chapter of an undergraduate
dissertation titled "A Multi-Layered Shift-Left Approach to Reducing Secret
Leakage in GitOps Pipelines", so it must be rigorous, traceable and honest
about what the design does not cover.

SCOPE
The security objective is narrow: prevent, detect, contain and limit the
leakage or theft of secrets (cloud credentials, API tokens, passwords, private
keys, CI tokens) across the software delivery pipeline. Model threats to that
objective only. Do not model general application vulnerabilities, denial of
service or availability unless they lead to secret exposure.

In scope as threat actors:
  A1 A developer who makes a mistake (commits or logs a secret; bypasses a
     hook with --no-verify).
  A2 An external attacker who can read the public repositories, registry
     and workflow logs, and can open pull requests from a fork.
  A3 A compromised third-party component that executes inside a CI job: a
     GitHub Action, a scanner binary, a container base image or a package
     dependency. Include compromise by moved tag, compromise at an already
     pinned commit, and a pinned action that fetches unpinned code at run time.
  A4 An attacker with code execution in one application pod.
  A5 A person with cluster access making unauthorised manual changes.
Out of scope (state these as assumptions, do not model them): a compromised
developer workstation, compromise of the GitHub or AWS platforms themselves,
physical attacks, and a malicious repository owner.

SYSTEM (hardened pipeline)
- Workstation: Git, pre-commit hook running Gitleaks on staged changes.
- GitHub: repositories fyp-app (source, Dockerfiles, workflows), fyp-iac
  (Kustomize manifests, ArgoCD Applications, ExternalSecret references,
  protected main; the same repository holds the Terraform in a separate
  folder). Push protection enabled.
  Images in GitHub Container Registry, referenced by digest.
- GitHub Actions in fyp-app, workflow-level permissions empty, triggers push
  to main and pull_request only, all actions pinned to full commit SHAs,
  checkout with persist-credentials false. Seven isolated jobs:
  lint-workflows (zizmor, actionlint; no secrets), secret-scan (Gitleaks full
  history; no secrets), sast (SonarQube Cloud; SONAR_TOKEN), iac-scan
  (Checkov; no secrets), build-scan (Docker build, Trivy; no secrets),
  publish (packages:write, main only), promote (GitHub App installation
  token, 1 hour, scoped to fyp-iac, opens a pull request with the new
  digest; App private key stored as a protected environment secret).
- GitHub Actions in fyp-iac: Checkov, terraform plan, apply behind an
  environment approval. AWS access only by OIDC federation: the role trust
  policy matches one repository and one environment; a permissions boundary
  denies creating IAM users or access keys and denies modifying the role.
- AWS: S3 remote state (KMS-encrypted, versioned), IAM OIDC provider,
  Parameter Store SecureString values written with Terraform write-only
  arguments (value_wo) so they are not in plan or state files, one EC2 instance in a public subnet with no inbound admin
  ports, IMDSv2 with hop limit 2, administration by Session Manager only.
- Cluster: single-node k3s with secrets encryption at rest. ArgoCD pulls
  from fyp-iac with auto-sync, prune and self-heal. External Secrets
  Operator authenticates with the node instance role, which can read one
  Parameter Store path, and writes Kubernetes Secrets. A NetworkPolicy blocks
  the metadata endpoint for every pod except External Secrets Operator.
  Application: FastAPI backend, PostgreSQL. No monitoring stack;
  ArgoCD's own sync status shows drift.

COMPARISON SYSTEM (baseline pipeline)
One CI job with write-all token permissions; actions referenced by mutable
tag; a static IAM user access key and a classic personal access token stored
as repository secrets and visible to every step; no pre-commit hook; push
protection disabled; a single Gitleaks scan as the last step. The baseline has
its own repositories, fyp-app-baseline and fyp-iac-baseline. Nothing is deployed from the
baseline repositories. Same
AWS account.

KNOWN WEAK POINTS AND CONTROL LAYERS (use these identifiers)
W1 hardcoded secrets committed | W2 secrets persisting in Git history |
W3 poisoned pipeline execution via unsafe triggers | W4 mutable action tags
and malicious dependencies | W5 long-lived credentials exposed to every
pipeline step | W6 secrets in container image layers | W7 plaintext
credentials in Terraform code or state | W8 base64 Kubernetes Secrets in Git |
W9 unauthorised manual cluster changes.
Layers: L0 workstation and push | L1 repository scans | L2 workflow, identity
and supply-chain hardening | L3 image and dependency scans | L4 IaC scans and
state | L5 GitOps secret references | L6 cluster reconciliation.
If you identify a threat that fits none of W1 to W9, give it a new identifier
starting at W10 and say so explicitly.

METHOD
1. Asset inventory: every secret and credential in the system, where it is
   stored, where it is used, its lifetime, and what it grants.
2. Data flow decomposition: list processes, data stores, external entities,
   data flows and trust boundaries in text form, suitable for drawing a data
   flow diagram. Number each element.
3. Threat enumeration: apply STRIDE to each element and each
   boundary-crossing flow, keeping only threats that bear on the scope.
4. Map each threat to the OWASP Top 10 CI/CD Security Risks (CICD-SEC-1 to
   CICD-SEC-10) and to a weak point identifier.
5. Rate each threat for likelihood and impact (Low, Medium, High) with one
   line of justification, for the baseline and for the hardened pipeline.
6. For each threat, name the control and layer that addresses it, classify
   the control as prevent, detect, contain or eliminate, and state the
   residual risk that remains after the control.
7. For each threat, say how it can be tested with seeded fake secrets or a
   harmless instrumented GitHub Action, and which research question the test
   supports:
     RQ1 detection rate per stage by secret type and location
     RQ2 added coverage of each layer over a single scanner
     RQ3 stage of first interception and time to feedback
     RQ4 number and validity period of credentials a compromised component
         can capture, baseline against hardened
8. Attack trees: write two, as indented text. (a) Attacker goal: obtain a
   usable AWS credential. (b) Attacker goal: deploy attacker-controlled code
   to the cluster. Mark each leaf as blocked, detected, contained or open in
   the hardened design.

GIVE SPECIFIC ATTENTION TO
- Every pod sharing the node instance role through the metadata endpoint.
- The Terraform OIDC role being highly privileged for up to an hour, and how
  quickly credentials were used in the tj-actions/changed-files (2025) and
  Trivy action (2026) incidents.
- Write access to fyp-iac as the path to deploying anything, and the fact
  that the same repository holds the Terraform code the OIDC role applies.
- Secrets at rest in Terraform state, in the k3s datastore and in Parameter
  Store, and what "eliminated from Git" does and does not mean.
- The long-lived secrets that remain in the hardened design: SONAR_TOKEN and
  the GitHub App private key.
- Secrets written to workflow logs, job summaries, artefacts and caches.
- Pull requests from forks, and what a fork-triggered run can access.
- Bypass of the pre-commit hook and of push protection.
- Tampering with the scanners' own configuration (allowlists, ignore files,
  inline suppressions) to hide a secret.
- The security tooling itself as attack surface.

OUTPUT FORMAT
1. Assumptions and scope statement (short).
2. Asset inventory table.
3. Data flow elements and trust boundaries (numbered lists).
4. Threat register as one table with columns: ID | Element or flow | Threat
   description | Actor | STRIDE | OWASP CICD-SEC | Weak point | Baseline
   likelihood and impact | Hardened likelihood and impact | Control and layer
   | Control type | Residual risk | Test and RQ.
5. The two attack trees.
6. Gaps: threats in scope that no current control addresses, each with a
   proportionate recommendation and whether it belongs in this project or in
   future work (artefact signing, SLSA provenance and runner egress
   monitoring are already designated future work).
7. A one-paragraph summary of the five highest residual risks.

RULES
- Be specific to this system. No generic advice that would apply to any
  pipeline.
- Do not invent components, controls, statistics or incident details. If you
  rely on a fact about a tool's or platform's behaviour that you are not sure
  of, mark it "to verify".
- Do not fabricate references. Name a source only if you are certain it
  exists, and mark every source as one I must check before citing.
- Neutral academic register, British English, no first person.
- If anything in this brief is ambiguous or contradictory, list the questions
  first, state the assumption you will proceed on, then continue.
```

Run the threat model before you freeze the design. Any new weak point it finds (W10 onward) either becomes a control in WP6 or WP7, or goes into the dissertation as a stated limitation.
