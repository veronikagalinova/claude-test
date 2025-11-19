# CrawlerLambda Function
resource "aws_lambda_function" "crawler" {
  filename         = "${path.module}/../lambda_packages/crawler.zip"
  function_name    = "CrawlerLambda-${var.environment}"
  role             = aws_iam_role.crawler_lambda.arn
  handler          = "handler.lambda_handler"
  source_code_hash = filebase64sha256("${path.module}/../lambda_packages/crawler.zip")
  runtime          = var.lambda_runtime
  timeout          = var.crawler_timeout
  memory_size      = var.crawler_memory

  reserved_concurrent_executions = 5

  environment {
    variables = {
      SOURCE_BUCKET_NAME = aws_s3_bucket.brochures_source.bucket
      METADATA_TABLE_NAME = aws_dynamodb_table.brochure_metadata.name
      ENVIRONMENT = var.environment
    }
  }

  tags = {
    Name = "Crawler Lambda"
  }
}

resource "aws_cloudwatch_log_group" "crawler" {
  name              = "/aws/lambda/${aws_lambda_function.crawler.function_name}"
  retention_in_days = var.log_retention_days
}

# ProcessBrochureLambda Function
resource "aws_lambda_function" "process_brochure" {
  filename         = "${path.module}/../lambda_packages/process_brochure.zip"
  function_name    = "ProcessBrochureLambda-${var.environment}"
  role             = aws_iam_role.process_brochure_lambda.arn
  handler          = "handler.lambda_handler"
  source_code_hash = filebase64sha256("${path.module}/../lambda_packages/process_brochure.zip")
  runtime          = var.lambda_runtime
  timeout          = var.processor_timeout
  memory_size      = var.processor_memory

  reserved_concurrent_executions = 10

  environment {
    variables = {
      SOURCE_BUCKET = aws_s3_bucket.brochures_source.bucket
      OUTPUT_BUCKET = aws_s3_bucket.textract_output.bucket
      METADATA_TABLE_NAME = aws_dynamodb_table.brochure_metadata.name
      TEXTRACT_SNS_TOPIC_ARN = aws_sns_topic.textract_completion.arn
      TEXTRACT_ROLE_ARN = aws_iam_role.textract_service.arn
      ENVIRONMENT = var.environment
    }
  }

  tags = {
    Name = "Process Brochure Lambda"
  }
}

resource "aws_cloudwatch_log_group" "process_brochure" {
  name              = "/aws/lambda/${aws_lambda_function.process_brochure.function_name}"
  retention_in_days = var.log_retention_days
}

resource "aws_lambda_permission" "allow_s3_source" {
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.process_brochure.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.brochures_source.arn
}

# TextractCallbackLambda Function
resource "aws_lambda_function" "textract_callback" {
  filename         = "${path.module}/../lambda_packages/textract_callback.zip"
  function_name    = "TextractCallbackLambda-${var.environment}"
  role             = aws_iam_role.textract_callback_lambda.arn
  handler          = "handler.lambda_handler"
  source_code_hash = filebase64sha256("${path.module}/../lambda_packages/textract_callback.zip")
  runtime          = var.lambda_runtime
  timeout          = var.processor_timeout
  memory_size      = var.processor_memory

  environment {
    variables = {
      OUTPUT_BUCKET = aws_s3_bucket.textract_output.bucket
      METADATA_TABLE_NAME = aws_dynamodb_table.brochure_metadata.name
      ENVIRONMENT = var.environment
    }
  }

  tags = {
    Name = "Textract Callback Lambda"
  }
}

resource "aws_cloudwatch_log_group" "textract_callback" {
  name              = "/aws/lambda/${aws_lambda_function.textract_callback.function_name}"
  retention_in_days = var.log_retention_days
}

resource "aws_lambda_permission" "allow_sns_textract" {
  statement_id  = "AllowExecutionFromSNS"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.textract_callback.function_name
  principal     = "sns.amazonaws.com"
  source_arn    = aws_sns_topic.textract_completion.arn
}

# KeywordSearchLambda Function
resource "aws_lambda_function" "keyword_search" {
  filename         = "${path.module}/../lambda_packages/keyword_search.zip"
  function_name    = "KeywordSearchLambda-${var.environment}"
  role             = aws_iam_role.keyword_search_lambda.arn
  handler          = "handler.lambda_handler"
  source_code_hash = filebase64sha256("${path.module}/../lambda_packages/keyword_search.zip")
  runtime          = var.lambda_runtime
  timeout          = var.keyword_search_timeout
  memory_size      = var.keyword_search_memory

  reserved_concurrent_executions = 20

  environment {
    variables = {
      OUTPUT_BUCKET = aws_s3_bucket.textract_output.bucket
      SOURCE_BUCKET = aws_s3_bucket.brochures_source.bucket
      METADATA_TABLE_NAME = aws_dynamodb_table.brochure_metadata.name
      KEYWORD_FOUND_TOPIC_ARN = aws_sns_topic.keyword_found.arn
      ENVIRONMENT = var.environment
    }
  }

  tags = {
    Name = "Keyword Search Lambda"
  }
}

resource "aws_cloudwatch_log_group" "keyword_search" {
  name              = "/aws/lambda/${aws_lambda_function.keyword_search.function_name}"
  retention_in_days = var.log_retention_days
}

resource "aws_lambda_permission" "allow_s3_textract" {
  statement_id  = "AllowExecutionFromS3Textract"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.keyword_search.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.textract_output.arn
}
