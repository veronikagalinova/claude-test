output "brochures_source_bucket" {
  description = "S3 bucket name for source brochures"
  value       = aws_s3_bucket.brochures_source.bucket
}

output "textract_output_bucket" {
  description = "S3 bucket name for Textract output"
  value       = aws_s3_bucket.textract_output.bucket
}

output "metadata_table_name" {
  description = "DynamoDB table name for brochure metadata"
  value       = aws_dynamodb_table.brochure_metadata.name
}

output "crawler_lambda_arn" {
  description = "ARN of CrawlerLambda function"
  value       = aws_lambda_function.crawler.arn
}

output "process_brochure_lambda_arn" {
  description = "ARN of ProcessBrochureLambda function"
  value       = aws_lambda_function.process_brochure.arn
}

output "textract_callback_lambda_arn" {
  description = "ARN of TextractCallbackLambda function"
  value       = aws_lambda_function.textract_callback.arn
}

output "keyword_search_lambda_arn" {
  description = "ARN of KeywordSearchLambda function"
  value       = aws_lambda_function.keyword_search.arn
}

output "keyword_found_topic_arn" {
  description = "ARN of keyword found SNS topic"
  value       = aws_sns_topic.keyword_found.arn
}

output "textract_completion_topic_arn" {
  description = "ARN of Textract completion SNS topic"
  value       = aws_sns_topic.textract_completion.arn
}

output "crawler_schedule_rule" {
  description = "EventBridge schedule rule for crawler"
  value       = aws_cloudwatch_event_rule.crawler_schedule.name
}

output "notification_email" {
  description = "Email address for notifications"
  value       = var.notification_email
}

output "crawler_schedule_expression" {
  description = "Cron expression for crawler schedule"
  value       = var.crawler_schedule
}

output "aws_region" {
  description = "AWS region"
  value       = var.aws_region
}

output "account_id" {
  description = "AWS account ID"
  value       = local.account_id
}
