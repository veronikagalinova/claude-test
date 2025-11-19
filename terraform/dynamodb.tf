# DynamoDB table for brochure metadata
resource "aws_dynamodb_table" "brochure_metadata" {
  name           = "brochure-metadata-table-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "brochure_id"

  attribute {
    name = "brochure_id"
    type = "S"
  }

  attribute {
    name = "store_id"
    type = "S"
  }

  attribute {
    name = "upload_time"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  attribute {
    name = "file_hash"
    type = "S"
  }

  # GSI-1: Query by store and date
  global_secondary_index {
    name            = "store-date-index"
    hash_key        = "store_id"
    range_key       = "upload_time"
    projection_type = "ALL"
  }

  # GSI-2: Query by status
  global_secondary_index {
    name            = "status-index"
    hash_key        = "status"
    range_key       = "upload_time"
    projection_type = "ALL"
  }

  # GSI-3: Query by file hash (for deduplication)
  global_secondary_index {
    name            = "hash-index"
    hash_key        = "file_hash"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Name = "Brochure Metadata Table"
  }
}
