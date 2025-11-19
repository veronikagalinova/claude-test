variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "notification_email" {
  description = "Email address for keyword match notifications"
  type        = string
  default     = "vgvalentinova@gmail.com"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "brochure-scanner"
}

variable "owner" {
  description = "Resource owner"
  type        = string
  default     = "vgvalentinova"
}

variable "crawler_schedule" {
  description = "EventBridge cron schedule for crawler (Weekly Sunday 10 AM UTC)"
  type        = string
  default     = "cron(0 10 ? * SUN *)"
}

variable "lambda_runtime" {
  description = "Python runtime version for Lambda functions"
  type        = string
  default     = "python3.12"
}

variable "crawler_memory" {
  description = "Memory allocation for CrawlerLambda in MB"
  type        = number
  default     = 512
}

variable "crawler_timeout" {
  description = "Timeout for CrawlerLambda in seconds"
  type        = number
  default     = 300
}

variable "processor_memory" {
  description = "Memory allocation for ProcessBrochureLambda in MB"
  type        = number
  default     = 1024
}

variable "processor_timeout" {
  description = "Timeout for ProcessBrochureLambda in seconds"
  type        = number
  default     = 300
}

variable "keyword_search_memory" {
  description = "Memory allocation for KeywordSearchLambda in MB"
  type        = number
  default     = 1024
}

variable "keyword_search_timeout" {
  description = "Timeout for KeywordSearchLambda in seconds"
  type        = number
  default     = 180
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 90
}

locals {
  common_tags = {
    Project     = "BrochureScanner"
    Environment = var.environment
    Owner       = var.owner
    ManagedBy   = "Terraform"
  }

  # Get AWS account ID dynamically
  account_id = data.aws_caller_identity.current.account_id
}

data "aws_caller_identity" "current" {}
