# terraform-aws-cost-anomaly-detection

Terraform module: Send AWS Cost Anomaly Detection alerts to Slack (via SNS + Lambda + Webhook)

## Overview

This module creates an AWS Cost Anomaly Detection (CAD) Anomaly Monitor and Anomaly Subscription, publishes notifications to an SNS topic, and forwards them to Slack via an Incoming Webhook using a small Lambda function.

It provisions:
- SNS topic (optionally encrypted with KMS)
- Cost Anomaly Monitor (DIMENSIONAL/CUSTOM/COST_CATEGORY)
- Cost Anomaly Subscription (SNS subscriber)
- Lambda function subscribed to the SNS topic to post to Slack Incoming Webhook

Note: You must create a Slack Incoming Webhook URL (via Slack App > Incoming Webhooks) and provide it to this module.

## Quick start

```hcl
module "cost_anomaly_to_slack" {
  # If published to the Terraform Registry, e.g.:
  # source = "antero-software/cost-anomaly-detection/aws"
  # For local development against this repo:
  # source = "../.."

  name_prefix            = "finops"
  subscription_frequency = "IMMEDIATE" # IMMEDIATE | DAILY | WEEKLY

  # Slack webhook URL (Incoming Webhook)
  slack_webhook_url = "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX"

  # Default monitor: DIMENSIONAL + SERVICE
  monitor_type      = "DIMENSIONAL"
  monitor_dimension = "SERVICE"

  # Optional: KMS key for SNS
  # sns_kms_master_key_id = "arn:aws:kms:us-east-1:123456789012:key/abcd-efgh-ijkl"

  tags = {
    Project = "finops"
    Owner   = "platform"
  }
}
```

See `examples/simple` for a complete working example.

## Inputs

- `name_prefix` (string, required): Prefix for resource names.
- `monitor_name` (string, optional): Name for the CAD monitor. Defaults to a value derived from `name_prefix`.
- `monitor_type` (string, default `DIMENSIONAL`): One of `DIMENSIONAL` | `CUSTOM` | `COST_CATEGORY`.
- `monitor_dimension` (string, default `SERVICE`): For `DIMENSIONAL` monitors, e.g. `SERVICE`, `LINKED_ACCOUNT`.
- `monitor_specification` (string, optional): JSON spec for `CUSTOM`/`COST_CATEGORY` monitors.
- `subscription_name` (string, optional): Name for the CAD subscription; defaults from `name_prefix`.
- `subscription_frequency` (string, default `IMMEDIATE`): `IMMEDIATE` | `DAILY` | `WEEKLY`.
- `subscription_threshold` (number, default `100`): Absolute USD threshold. Note provider schema may vary; see Notes.
// Removed: `threshold_expression` input. The module now uses a provider-native `threshold_expression` block built from `subscription_threshold`.
- `sns_kms_master_key_id` (string, optional): KMS key for SNS encryption.
- `enable_slack` (bool, default `true`): Whether to enable Slack notifications (via Lambda + webhook).
- `slack_webhook_url` (string, optional, sensitive): Slack Incoming Webhook URL that will receive messages.
- `tags` (map(string), default `{}`): Tags to apply.

## Outputs

- `sns_topic_arn`: ARN of the created SNS topic.
- `anomaly_monitor_arn`: ARN of the CAD Monitor.
- `anomaly_subscription_id`: ID of the CAD Subscription.
- `slack_lambda_function_arn`: ARN of the Lambda function that posts to Slack (if enabled).


## Prerequisites

1. Create a Slack Incoming Webhook and keep the URL handy.
2. Provide AWS credentials for Terraform (e.g., via `AWS_PROFILE`, `AWS_REGION`).

## Notes and limitations

- The module sets a default `threshold_expression` block that triggers when the absolute anomaly impact is greater than or equal to `subscription_threshold` USD. If you need a custom expression, open an issue or PR to add a structured input.
- Provide a valid Slack webhook URL. The module sends a concise summary (ID, time window, estimated impact, top root cause) when the payload contains structured anomaly details. Otherwise, it forwards the raw message text.
- This module focuses on notifications. For advanced formatting or routing, customize the Lambda function.

## Develop locally

```sh
# format
terraform fmt -recursive

# plan from the example (downloads providers)
cd examples/simple
terraform init
terraform plan
```

### CI/CD

- On pushes to `master`, CI runs `terraform fmt -check` and `terraform validate`.
- A release workflow automatically computes the next semantic version (based on conventional commits),
  tags the commit, and creates a GitHub Release.

> Note: `terraform init/plan` requires internet access and valid AWS credentials.

---

License: See the `LICENSE` file in this repository.
