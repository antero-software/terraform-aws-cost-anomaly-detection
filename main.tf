locals {
  monitor_name      = coalesce(var.monitor_name, "${var.name_prefix}-cad-monitor")
  subscription_name = coalesce(var.subscription_name, "${var.name_prefix}-cad-subscription")

  monitor_dimension     = var.monitor_type == "DIMENSIONAL" ? var.monitor_dimension : null
  monitor_specification = (var.monitor_type == "CUSTOM" || var.monitor_type == "COST_CATEGORY") ? var.monitor_specification : null

  # Module semantic version read from VERSION file (populated by CI release)
  module_version = trimspace(file("${path.module}/VERSION"))
}

resource "aws_sns_topic" "anomaly" {
  name              = "${var.name_prefix}-cad-sns"
  kms_master_key_id = var.sns_kms_master_key_id
  tags              = var.tags
}

resource "aws_ce_anomaly_monitor" "this" {
  name                  = local.monitor_name
  monitor_type          = var.monitor_type
  monitor_dimension     = local.monitor_dimension
  monitor_specification = local.monitor_specification
  tags                  = var.tags
}

resource "aws_ce_anomaly_subscription" "this" {
  name             = local.subscription_name
  frequency        = var.subscription_frequency
  monitor_arn_list = [aws_ce_anomaly_monitor.this.arn]

  # Provider expects a block for threshold_expression. We express a simple
  # absolute USD threshold using ANOMALY_TOTAL_IMPACT_ABSOLUTE with
  # GREATER_THAN_OR_EQUAL against var.subscription_threshold. Use a single
  # operand (no AND wrapper) to satisfy API requirement.
  threshold_expression {
    or {
      dimension {
        key           = "ANOMALY_TOTAL_IMPACT_ABSOLUTE"
        match_options = ["GREATER_THAN_OR_EQUAL"]
        values        = [tostring(var.subscription_threshold_absolute)]
      }
    }
    or {
      dimension {
        key           = "ANOMALY_TOTAL_IMPACT_PERCENTAGE"
        match_options = ["GREATER_THAN_OR_EQUAL"]
        values        = [tostring(var.subscription_threshold_percentage)]
      }
    }
  }

  subscriber {
    type    = "SNS"
    address = aws_sns_topic.anomaly.arn
  }
}

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "lambda" {
  count              = var.enable_slack ? 1 : 0
  name               = "${var.name_prefix}-cad-slack-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
  tags               = var.tags
}

data "aws_iam_policy_document" "cad_sns_policy" {
  statement {
    sid    = "AllowCostAnomalyDetectionToPublish"
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["costalerts.amazonaws.com"]
    }
    actions   = ["sns:Publish"]
    resources = [aws_sns_topic.anomaly.arn]
  }
}

resource "aws_sns_topic_policy" "cad" {
  arn    = aws_sns_topic.anomaly.arn
  policy = data.aws_iam_policy_document.cad_sns_policy.json
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  count      = var.enable_slack ? 1 : 0
  role       = aws_iam_role.lambda[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_lambda_function" "slack_notifier" {
  count            = var.enable_slack ? 1 : 0
  function_name    = "${var.name_prefix}-cad-slack-notifier"
  role             = aws_iam_role.lambda[0].arn
  runtime          = "python3.12"
  handler          = "main.handler"
  filename         = "${path.module}/lambda/cost-anomaly-detection.zip"
  source_code_hash = filebase64sha256("${path.module}/lambda/cost-anomaly-detection.zip")

  environment {
    variables = {
      SLACK_WEBHOOK_URL = var.slack_webhook_url
    }
  }

  tags = var.tags

  lifecycle {
    precondition {
      condition     = var.enable_slack == false || (var.slack_webhook_url != null && length(var.slack_webhook_url) > 0)
      error_message = "slack_webhook_url must be provided when enable_slack is true."
    }
  }
}

resource "aws_lambda_permission" "allow_sns" {
  count         = var.enable_slack ? 1 : 0
  statement_id  = "AllowExecutionFromSNS"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.slack_notifier[0].function_name
  principal     = "sns.amazonaws.com"
  source_arn    = aws_sns_topic.anomaly.arn
}

resource "aws_sns_topic_subscription" "lambda" {
  count     = var.enable_slack ? 1 : 0
  topic_arn = aws_sns_topic.anomaly.arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.slack_notifier[0].arn

  depends_on = [aws_lambda_permission.allow_sns]
}
