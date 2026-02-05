variable "name_prefix" {
  description = "Prefix used to name created resources (SNS topic, roles, etc.)."
  type        = string
}

variable "monitor_name" {
  description = "Name of the Cost Anomaly Detection monitor. If null, a name will be derived from name_prefix."
  type        = string
  default     = null
}

variable "monitor_type" {
  description = "Type of anomaly monitor. Typical values: DIMENSIONAL, CUSTOM, or COST_CATEGORY."
  type        = string
  default     = "DIMENSIONAL"
}

variable "monitor_dimension" {
  description = "When monitor_type is DIMENSIONAL, which dimension to monitor (e.g., SERVICE, LINKED_ACCOUNT)."
  type        = string
  default     = "SERVICE"
}

variable "monitor_specification" {
  description = "When monitor_type is CUSTOM or COST_CATEGORY, provide the JSON specification per AWS API."
  type        = string
  default     = null
}

variable "subscription_name" {
  description = "Name of the Cost Anomaly Detection subscription. If null, a name will be derived from name_prefix."
  type        = string
  default     = null
}

variable "subscription_threshold_absolute" {
  description = "Absolute dollar threshold that triggers a notification (USD)."
  type        = number
  default     = 10
}

variable "subscription_threshold_percentage" {
  description = "Percentage threshold that triggers a notification."
  type        = number
  default     = 50
}

variable "subscription_frequency" {
  description = "How often to receive anomaly notifications. Allowed: IMMEDIATE, DAILY, WEEKLY."
  type        = string
  default     = "IMMEDIATE"
  validation {
    condition     = contains(["IMMEDIATE", "DAILY", "WEEKLY"], var.subscription_frequency)
    error_message = "subscription_frequency must be one of IMMEDIATE, DAILY, or WEEKLY."
  }
}

variable "sns_kms_master_key_id" {
  description = "Optional KMS key ID/ARN for encrypting the SNS topic."
  type        = string
  default     = null
}

variable "enable_slack" {
  description = "Whether to send notifications to Slack via a webhook (Lambda subscriber)."
  type        = bool
  default     = true
}

variable "slack_webhook_url" {
  description = "Slack Incoming Webhook URL to post anomaly notifications."
  type        = string
  default     = null
  sensitive   = true
}

// threshold_expression input removed: the module now defines a provider-native
// threshold_expression block using subscription_threshold. If you need a
// custom expression later, we can re-introduce this as a structured input.

variable "tags" {
  description = "Tags to apply to taggable resources."
  type        = map(string)
  default     = {}
}
