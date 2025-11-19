# AWS Configuration
aws_region = "us-east-1"
environment = "dev"
owner = "vgvalentinova"

# Notification Configuration
notification_email = "vgvalentinova@gmail.com"

# Crawler Schedule (Weekly Sunday 10 AM UTC)
crawler_schedule = "cron(0 10 ? * SUN *)"

# Lambda Configuration
crawler_memory = 512
crawler_timeout = 300
processor_memory = 1024
processor_timeout = 300
keyword_search_memory = 1024
keyword_search_timeout = 180

# CloudWatch Configuration
log_retention_days = 90
