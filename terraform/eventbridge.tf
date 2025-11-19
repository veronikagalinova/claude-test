# EventBridge rule for weekly crawler schedule
resource "aws_cloudwatch_event_rule" "crawler_schedule" {
  name                = "scan-schedule-rule-${var.environment}"
  description         = "Trigger CrawlerLambda weekly on Sunday at 10 AM UTC"
  schedule_expression = var.crawler_schedule

  tags = {
    Name = "Crawler Schedule Rule"
  }
}

# EventBridge target to invoke CrawlerLambda
resource "aws_cloudwatch_event_target" "crawler" {
  rule      = aws_cloudwatch_event_rule.crawler_schedule.name
  target_id = "CrawlerLambdaTarget"
  arn       = aws_lambda_function.crawler.arn

  input = jsonencode({
    stores = [
      {
        store_id = "lidl_bg"
        store_name = "Lidl Bulgaria"
        brochure_url = "https://www.lidl.bg/l/bg/broshura/17-11-23-11-11fef3/view/menu/page/1"
        keywords = [
          "lupilu",
          "baby",
          "бебе",
          "бебешки",
          "играчка",
          "lavazza crema"
        ]
      }
    ]
  })
}

# Lambda permission to allow EventBridge to invoke
resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.crawler.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.crawler_schedule.arn
}
