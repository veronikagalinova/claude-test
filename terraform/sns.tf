# SNS topic for Textract job completion
resource "aws_sns_topic" "textract_completion" {
  name = "textract-job-completion-topic-${var.environment}"

  tags = {
    Name = "Textract Job Completion Topic"
  }
}

# SNS subscription for TextractCallbackLambda
resource "aws_sns_topic_subscription" "textract_callback" {
  topic_arn = aws_sns_topic.textract_completion.arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.textract_callback.arn
}

# SNS topic for keyword match notifications
resource "aws_sns_topic" "keyword_found" {
  name = "keyword-found-topic-${var.environment}"

  tags = {
    Name = "Keyword Found Notification Topic"
  }
}

# Email subscription for keyword notifications
resource "aws_sns_topic_subscription" "keyword_email" {
  topic_arn = aws_sns_topic.keyword_found.arn
  protocol  = "email"
  endpoint  = var.notification_email
}

# Policy to allow Textract to publish to completion topic
resource "aws_sns_topic_policy" "textract_completion" {
  arn = aws_sns_topic.textract_completion.arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowTextractPublish"
        Effect = "Allow"
        Principal = {
          Service = "textract.amazonaws.com"
        }
        Action   = "SNS:Publish"
        Resource = aws_sns_topic.textract_completion.arn
      }
    ]
  })
}
