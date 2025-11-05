output "sns_topic_arn" {
  description = "ARN of the SNS topic receiving Cost Anomaly Detection notifications."
  value       = aws_sns_topic.anomaly.arn
}

output "anomaly_monitor_arn" {
  description = "ARN of the Cost Anomaly Detection monitor."
  value       = aws_ce_anomaly_monitor.this.arn
}

output "anomaly_subscription_id" {
  description = "ID of the Cost Anomaly Detection subscription."
  value       = aws_ce_anomaly_subscription.this.id
}

output "slack_lambda_function_arn" {
  description = "ARN of the Lambda that posts to the Slack webhook (if enabled)."
  value       = try(aws_lambda_function.slack_notifier[0].arn, null)
}

output "module_version" {
  description = "The semantic version of this module, read from the VERSION file."
  value       = local.module_version
}
