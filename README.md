# Serverless Brochure Keyword Scanner

A fully serverless AWS solution for automatically scanning retail brochures (PDFs and images) to detect configured keywords and send email notifications when matches are found.

## Features

- **Automated OCR Processing**: Uses AWS Textract for high-quality optical character recognition
- **Intelligent Processing**: Automatically chooses between synchronous and asynchronous Textract APIs based on file size and page count
- **Keyword Detection**: Case-insensitive, whole-word matching with context extraction
- **Email Notifications**: Sends detailed notifications via Amazon SES when keywords are found
- **Metadata Tracking**: Stores complete processing history and match details in DynamoDB
- **Serverless Architecture**: No servers to manage, automatic scaling, pay-per-use pricing
- **Production-Ready**: Includes error handling, retry logic, dead letter queues, and CloudWatch monitoring

## Architecture

The system consists of three main Lambda functions:

1. **ProcessBrochureLambda**: Triggered by S3 uploads, inspects files, and submits to Textract
2. **TextractCallbackLambda**: Handles Textract async job completions and stores results
3. **KeywordSearchLambda**: Searches OCR text for keywords and triggers notifications

## Project Structure

```
brochure-scanner/
├── lambdas/
│   ├── common/                      # Shared utilities
│   │   ├── logger.py                # Structured logging
│   │   ├── metrics.py               # CloudWatch metrics
│   │   ├── aws_clients.py           # AWS SDK clients
│   │   └── exceptions.py            # Custom exceptions
│   ├── process_brochure/            # ProcessBrochureLambda
│   │   ├── handler.py
│   │   ├── file_inspector.py
│   │   ├── textract_sync.py
│   │   └── textract_async.py
│   ├── textract_callback/           # TextractCallbackLambda
│   │   ├── handler.py
│   │   └── result_retriever.py
│   └── keyword_search/              # KeywordSearchLambda
│       ├── handler.py
│       ├── textract_parser.py
│       ├── keyword_matcher.py
│       └── config_loader.py
├── infra/
│   ├── template.yaml                # SAM infrastructure template
│   └── parameters/
│       └── dev-params.json          # Environment parameters
├── config/
│   └── keyword-config.json          # Keyword configuration
└── docs/
    ├── 01_TECHNICAL_SPEC.md         # Complete technical specification
    └── 02_PROJECT_PLAN.md           # Project plan with milestones
```

## Prerequisites

- AWS Account with appropriate permissions
- AWS CLI configured
- AWS SAM CLI installed
- Python 3.12
- SES verified email addresses (sandbox) or production access

## Deployment

### 1. Install Dependencies

```bash
cd lambdas/process_brochure
pip install -r requirements.txt -t .

cd ../textract_callback
pip install -r requirements.txt -t .

cd ../keyword_search
pip install -r requirements.txt -t .
```

### 2. Build with SAM

```bash
cd infra
sam build
```

### 3. Deploy to AWS

```bash
sam deploy --guided \
  --parameter-overrides file://parameters/dev-params.json \
  --stack-name brochure-scanner-dev \
  --capabilities CAPABILITY_NAMED_IAM
```

### 4. Upload Configuration

```bash
# After deployment, upload keyword configuration
aws s3 cp ../config/keyword-config.json s3://brochures-source-dev-<ACCOUNT_ID>/config/
```

### 5. Configure SES

```bash
# Verify sender email
aws ses verify-email-identity --email-address noreply@example.com

# Verify recipient emails (sandbox mode)
aws ses verify-email-identity --email-address alerts@example.com
```

### 6. Subscribe to SNS Topic

```bash
# Get topic ARN from CloudFormation outputs
TOPIC_ARN=$(aws cloudformation describe-stacks \
  --stack-name brochure-scanner-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`KeywordFoundTopicArn`].OutputValue' \
  --output text)

# Subscribe email
aws sns subscribe \
  --topic-arn $TOPIC_ARN \
  --protocol email \
  --notification-endpoint alerts@example.com
```

## Usage

### Upload a Brochure

```bash
# Upload brochure to S3 (triggers processing automatically)
aws s3 cp brochure.pdf s3://brochures-source-dev-<ACCOUNT_ID>/walmart/2025/11/18/weekly-ad.pdf
```

The system will:
1. Detect the file upload
2. Extract text using Textract
3. Search for configured keywords
4. Send email notification if matches found

### Monitor Processing

```bash
# View Lambda logs
sam logs --stack-name brochure-scanner-dev --name ProcessBrochureLambda --tail

# Check DynamoDB for brochure status
aws dynamodb scan --table-name brochure-metadata-dev \
  --projection-expression "brochure_id,status,store_id,upload_time"
```

### Update Keywords

1. Edit `config/keyword-config.json`
2. Upload to S3:
   ```bash
   aws s3 cp config/keyword-config.json s3://brochures-source-dev-<ACCOUNT_ID>/config/
   ```
3. New keywords take effect on next brochure processing

## Configuration

### Keyword Configuration Format

```json
{
  "version": "1.0",
  "stores": [
    {
      "store_id": "walmart",
      "store_name": "Walmart",
      "keywords": ["organic", "sale", "clearance"],
      "recipients": [
        {"email": "alerts@example.com", "type": "TO"}
      ]
    }
  ]
}
```

### Environment Variables

Each Lambda function uses environment variables for configuration:

- `SOURCE_BUCKET_NAME`: S3 bucket for source brochures
- `OUTPUT_BUCKET_NAME`: S3 bucket for Textract results
- `METADATA_TABLE_NAME`: DynamoDB table name
- `SYNC_PAGE_THRESHOLD`: Max pages for sync processing (default: 5)
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)

## Monitoring

### CloudWatch Dashboards

View metrics in CloudWatch:
- Brochures processed
- Keywords matched
- Lambda errors and duration
- DynamoDB capacity usage

### Alarms

The following alarms are configured:
- Lambda function errors > threshold
- Dead letter queue has messages
- DynamoDB throttling

### Logs

All Lambda functions use structured JSON logging:

```json
{
  "timestamp": "2025-11-18T10:00:00Z",
  "level": "INFO",
  "correlation_id": "abc-123",
  "function": "ProcessBrochureLambda",
  "message": "Processing brochure",
  "context": {
    "brochure_id": "xyz-789",
    "store_id": "walmart"
  }
}
```

## Cost Estimation

For 300 brochures/month (10 pages average):

- **Textract**: $4.50/month
- **Lambda**: $0 (within free tier)
- **S3**: $0.25/month
- **DynamoDB**: $0.01/month
- **SNS**: $0.01/month
- **SES**: $0 (within free tier)

**Total**: ~$5-8/month

See [01_TECHNICAL_SPEC.md](docs/01_TECHNICAL_SPEC.md) for detailed cost breakdown.

## Development

### Local Testing

```bash
# Run unit tests
python -m pytest lambdas/*/tests/

# Test Lambda function locally
sam local invoke ProcessBrochureLambda --event events/s3-put.json
```

### Code Structure

- **Common Module**: Shared utilities (logging, metrics, AWS clients)
- **Lambda Functions**: Each with handler and supporting modules
- **Error Handling**: Custom exceptions with context for better debugging
- **Retry Logic**: Exponential backoff for AWS API calls
- **Idempotency**: Uses correlation IDs and DynamoDB checks

## Troubleshooting

### Brochure not processed

1. Check CloudWatch Logs for ProcessBrochureLambda
2. Verify S3 event notification is configured
3. Check Lambda permissions for S3 bucket access

### No email notifications

1. Verify SES email addresses are verified
2. Check SNS topic subscription is confirmed
3. Check KeywordSearchLambda logs for errors
4. Verify keywords match text in brochure (case-insensitive)

### Textract errors

1. Check file format is supported (PDF, PNG, JPEG, TIFF)
2. Verify file size < 512 MB
3. Check for Textract service quotas (concurrency limits)
4. Review TextractCallbackLambda logs for job status

## Documentation

- [Technical Specification](docs/01_TECHNICAL_SPEC.md) - Complete system architecture and design
- [Project Plan](docs/02_PROJECT_PLAN.md) - Implementation roadmap and milestones

## Support

For issues and questions:
- Check CloudWatch Logs for error details
- Review DynamoDB metadata table for brochure status
- Check dead letter queues for failed messages

## License

This project is proprietary and confidential.

## Contributing

1. Create feature branch from main
2. Implement changes with tests
3. Update documentation
4. Submit pull request with description
5. Ensure CI/CD pipeline passes

## Roadmap

See [02_PROJECT_PLAN.md](docs/02_PROJECT_PLAN.md) for:
- Milestone 2: Scheduled crawling and automation
- Milestone 3: Cost optimization and scaling
- Future enhancements

---

Built with ❤️ using AWS Serverless technologies
