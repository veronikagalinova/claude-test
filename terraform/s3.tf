# S3 bucket for source brochures
resource "aws_s3_bucket" "brochures_source" {
  bucket = "brochures-source-${var.environment}-${local.account_id}"

  tags = {
    Name = "Brochures Source Bucket"
  }
}

resource "aws_s3_bucket_versioning" "brochures_source" {
  bucket = aws_s3_bucket.brochures_source.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "brochures_source" {
  bucket = aws_s3_bucket.brochures_source.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "brochures_source" {
  bucket = aws_s3_bucket.brochures_source.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "brochures_source" {
  bucket = aws_s3_bucket.brochures_source.id

  rule {
    id     = "archive-old-brochures"
    status = "Enabled"

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    expiration {
      days = 730 # 2 years
    }
  }
}

# S3 notification to trigger ProcessBrochureLambda
resource "aws_s3_bucket_notification" "brochures_source" {
  bucket = aws_s3_bucket.brochures_source.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.process_brochure.arn
    events              = ["s3:ObjectCreated:Put", "s3:ObjectCreated:Post"]
    filter_prefix       = ""
    filter_suffix       = ".pdf"
  }

  depends_on = [aws_lambda_permission.allow_s3_source]
}

# S3 bucket for Textract output
resource "aws_s3_bucket" "textract_output" {
  bucket = "textract-output-${var.environment}-${local.account_id}"

  tags = {
    Name = "Textract Output Bucket"
  }
}

resource "aws_s3_bucket_versioning" "textract_output" {
  bucket = aws_s3_bucket.textract_output.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "textract_output" {
  bucket = aws_s3_bucket.textract_output.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "textract_output" {
  bucket = aws_s3_bucket.textract_output.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "textract_output" {
  bucket = aws_s3_bucket.textract_output.id

  rule {
    id     = "archive-textract-results"
    status = "Enabled"

    transition {
      days          = 180
      storage_class = "GLACIER"
    }
  }
}

# S3 notification to trigger KeywordSearchLambda
resource "aws_s3_bucket_notification" "textract_output" {
  bucket = aws_s3_bucket.textract_output.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.keyword_search.arn
    events              = ["s3:ObjectCreated:Put", "s3:ObjectCreated:Post"]
    filter_prefix       = ""
    filter_suffix       = ".json"
  }

  depends_on = [aws_lambda_permission.allow_s3_textract]
}
