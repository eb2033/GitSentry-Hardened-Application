# WP1 Persistent stack: sources

Collected 12 November 2026. Converted from `implementation_sources/wp1_persistent_stack_sources.txt` on 16 November 2026.

## Sources

| # | Source | Used for |
| --- | --- | --- |
| 1 | HashiCorp (2025) *Terraform 1.11 brings ephemeral values to managed resources with write-only arguments*. https://hashicorp.com/blog/terraform-1-11-ephemeral-values-managed-resources-write-only-arguments | Write-only arguments (`aws_ssm_parameter` `value_wo`) are never stored in plan or state files. `value_wo_version` is stored in state and must be incremented to trigger an update. |
| 2 | HashiCorp Discuss: "Why update values in the state when they are ignored?" https://discuss.hashicorp.com/t/why-update-values-in-the-state-when-they-are-ignored/38716 | `ignore_changes` only affects planning. Terraform still refreshes the live value into state, so `value` with `ignore_changes` would leak the real SecureString value into state. |
| 3 | AWS re:Post: "What resources do SSM managed instances actually need permissions for?" https://repost.aws/questions/QU42Uu_rEcRjagTuMTxVsLZQ/what-resources-do-ssm-managed-instances-actually-need-permissions-for | `AmazonSSMManagedInstanceCore` uses `Resource "*"` in every statement, including `ssm:GetParameter(s)`. Reading parameters is not needed for Session Manager, so a custom policy is recommended. |
| 4 | AWS Managed Policy reference: AmazonSSMManagedInstanceCore. https://docs.aws.amazon.com/aws-managed-policy/latest/reference/AmazonSSMManagedInstanceCore.html | The policy JSON (`ssm:GetParameter(s)` on `*`, plus `ssmmessages` and `ec2messages` actions) from which the custom `k3s-node` policy is derived. |

Sources 2 and 3 are forum posts. They are fine for building, but cite the HashiCorp and AWS documentation in the dissertation instead.

## Changes the plan

- **Parameter Store values:** use `value_wo` and `value_wo_version`, not `value` with `ignore_changes`. Needs Terraform 1.11 or later. The minimum AWS provider version for `value_wo` on `aws_ssm_parameter` is **to verify** in the Terraform registry; the community `terraform-aws-modules/ssm-parameter` module requires provider 6.8 or later.
- **`k3s-node` role:** custom policy with the Session Manager actions only, plus `ssm:GetParameter(s)` on `/fyp/app/*` and `kms:Decrypt` on its key. Do not attach `AmazonSSMManagedInstanceCore`.
- **New WP1 checks:** `terraform state pull` contains no SecureString value, and the node role is denied a parameter outside `/fyp/app/*`.

## Open

- Which exact actions the custom Session Manager policy needs. Start from source 4, drop the parameter reads, and confirm a session still opens.
