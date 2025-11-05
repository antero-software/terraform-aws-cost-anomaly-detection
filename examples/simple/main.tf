terraform {
  required_version = ">= 1.3.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  type        = string
  description = "AWS region to deploy example resources"
  default     = "us-east-1"
}

# Example usage of the module
module "cost_anomaly_to_slack" {
  source = "../.."

  name_prefix            = "example"
  subscription_frequency = "IMMEDIATE"

  # Slack webhook URL (Incoming Webhook) – replace with your URL
  slack_webhook_url = "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX"

  # Optional: for DIMENSIONAL monitors, watch spend by AWS Service
  monitor_type      = "DIMENSIONAL"
  monitor_dimension = "SERVICE"

  # Optional: use a KMS key for the SNS topic
  # sns_kms_master_key_id = "arn:aws:kms:us-east-1:123456789012:key/abcd-efgh-ijkl"

  tags = {
    Project = "cost-anomaly-demo"
    Owner   = "finops"
  }
}
