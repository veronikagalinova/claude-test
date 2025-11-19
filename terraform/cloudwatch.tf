# CloudWatch alarm for CrawlerLambda errors
resource "aws_cloudwatch_metric_alarm" "crawler_errors" {
  alarm_name          = "crawler-lambda-errors-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 600 # 10 minutes
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "Alert when CrawlerLambda has more than 5 errors in 10 minutes"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.crawler.function_name
  }

  tags = {
    Name = "Crawler Lambda Errors Alarm"
  }
}

# CloudWatch alarm for ProcessBrochureLambda errors
resource "aws_cloudwatch_metric_alarm" "process_brochure_errors" {
  alarm_name          = "process-brochure-lambda-errors-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 600
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "Alert when ProcessBrochureLambda has more than 5 errors in 10 minutes"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.process_brochure.function_name
  }

  tags = {
    Name = "Process Brochure Lambda Errors Alarm"
  }
}

# CloudWatch alarm for KeywordSearchLambda errors
resource "aws_cloudwatch_metric_alarm" "keyword_search_errors" {
  alarm_name          = "keyword-search-lambda-errors-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 600
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "Alert when KeywordSearchLambda has more than 5 errors in 10 minutes"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.keyword_search.function_name
  }

  tags = {
    Name = "Keyword Search Lambda Errors Alarm"
  }
}
