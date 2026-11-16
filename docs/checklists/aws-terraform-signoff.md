# AWS and Terraform stage: sign-off checklist

Covers WP0 to WP2 of `docs/PLAN.md` (Gantt phase "AWS and Terraform"). The k3s install, ArgoCD and the app belong to the next phase. Updated 16 November 2026 for the reduced scope and the WP1 source corrections.

## Account guardrails (WP0)

- [ ] Root account has MFA and no access keys; day-to-day work uses a separate MFA-protected admin identity
- [ ] AWS Budgets alert exists, and a test alert reached your email
- [ ] CloudTrail is on
- [ ] `fyp-iac` and `fyp-iac-baseline` exist, with branch protection on `main` of `fyp-iac`

## Persistent stack (WP1)

- [ ] Terraform 1.11 or later, and an AWS provider version that supports `value_wo` on `aws_ssm_parameter`, are pinned in the configuration
- [ ] S3 state bucket is KMS-encrypted and versioned, with public access blocked and state locking on
- [ ] State is migrated from local to the S3 backend, and `persistent` and `session` use separate state files
- [ ] GitHub OIDC provider and `gha-terraform` role exist; the trust policy matches one repository and one environment, with no wildcards
- [ ] Permissions boundary is attached and tested: the role is denied when it tries to create an IAM user or access key *(can wait until January)*
- [ ] `k3s-node` uses a custom policy, not `AmazonSSMManagedInstanceCore`; it can read only `/fyp/app/*`, and a read outside that path is denied
- [ ] Parameter Store SecureStrings are written with `value_wo` and `value_wo_version`; `terraform state pull` contains no secret value
- [ ] `terraform plan` runs from GitHub Actions through OIDC with no AWS keys in repository secrets
- [ ] Apply runs only from a GitHub Environment that needs your approval *(can wait until January)*

## Session stack (WP2)

- [ ] VPC, public subnet, internet gateway and security group apply cleanly from the pipeline
- [ ] Security group has no inbound admin ports; an external port scan shows only the application port
- [ ] EC2 instance has an encrypted root volume and IMDSv2 required with hop limit 2
- [ ] You can open a shell and port-forward through Session Manager with the custom node policy
- [ ] Apply to a reachable node takes under 10 minutes
- [ ] `terraform destroy` leaves nothing billable behind; check Cost Explorer or the EC2 and EBS consoles
- [ ] Checkov runs on the Terraform in CI and its findings are fixed or documented *(can wait until January)*

## Evidence for the Implementation chapter

- [ ] Screenshots of the trust policy, permissions boundary, bucket settings, the denied IAM action and the denied parameter read
- [ ] Build journal covers any problems you hit and how you fixed them
- [ ] Rough cost for the phase, to check against the €5 per month estimate

## Short version for your supervisor

The items that prove the design claims are the OIDC trust policy, the denied IAM action, the state file with no secret values, the closed security group and the clean destroy. The rest is hygiene.
