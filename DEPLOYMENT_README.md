# Serverless Brochure Keyword Scanner - Deployment Guide

Complete deployment guide for the Serverless Brochure Keyword Scanner with Terraform.

## 📋 Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Detailed Deployment Steps](#detailed-deployment-steps)
- [Configuration](#configuration)
- [Testing](#testing)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

## 🎯 Overview

This system automatically:
- **Crawls** brochures from store URLs weekly (Sunday 10 AM UTC)
- **Extracts** text using AWS Textract
- **Searches** for specific keywords (including Cyrillic/Bulgarian)
- **Notifies** via email when keywords are found

### Key Features

✅ **Weekly Automated Crawling** - EventBridge schedule (Sunday 10 AM UTC)  
✅ **Web Scraping** - Extracts PDFs from embedded viewers (Lidl, Issuu, etc.)  
✅ **Cyrillic Support** - Searches Bulgarian keywords (бебе, бебешки, играчка)  
✅ **Deduplication** - SHA-256 hash-based duplicate detection  
✅ **Email Notifications** - HTML formatted with match details  
✅ **Multi-word Phrases** - Searches for "lavazza crema" as single phrase  

## 📦 Prerequisites

### Required Tools

1. **AWS CLI** (v2.x or later)
   ```bash
   aws --version
   # aws-cli/2.x.x
   ```

2. **Terraform** (v1.0 or later)
   ```bash
   terraform --version
   # Terraform v1.x.x
   ```

3. **Python 3.9+** with pip
   ```bash
   python3 --version
   pip3 --version
   ```

### AWS Account Setup

1. **Configure AWS credentials:**
   ```bash
   aws configure
   # AWS Access Key ID: YOUR_KEY
   # AWS Secret Access Key: YOUR_SECRET
   # Default region: us-east-1
   # Default output format: json
   ```

2. **Verify AWS access:**
   ```bash
   aws sts get-caller-identity
   ```

3. **Required IAM permissions:**
   - S3: CreateBucket, PutObject, GetObject
   - DynamoDB: CreateTable, PutItem, GetItem, Query
   - Lambda: CreateFunction, UpdateFunctionCode
   - IAM: CreateRole, AttachRolePolicy
   - Textract: StartDocumentTextDetection, GetDocumentTextDetection
   - SNS: CreateTopic, Subscribe
   - EventBridge: PutRule, PutTargets
   - CloudWatch: PutMetricData, CreateLogGroup

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         EventBridge                              │
│              cron(0 10 ? * SUN *) - Weekly Sunday 10 AM UTC     │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                     CrawlerLambda                                │
│  - Downloads brochures (with web scraping for embedded viewers) │
│  - SHA-256 hash for deduplication                               │
│  - Uploads to S3                                                │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                   S3: brochures-source-dev                       │
│                    (S3 Event Trigger)                            │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                 ProcessBrochureLambda                            │
│  - Determines PDF page count                                    │
│  - Sync (<5 pages) or Async (≥5 pages) Textract                │
└─────────────┬───────────────────────────┬───────────────────────┘
              │                           │
         Sync │                           │ Async
              ▼                           ▼
      ┌──────────────┐            ┌─────────────────┐
      │   Textract   │            │   Textract      │
      │   (Sync)     │            │   (Async)       │
      └──────┬───────┘            └────────┬────────┘
             │                             │
             │                             ▼
             │                     ┌────────────────┐
             │                     │  SNS Topic     │
             │                     │ (Completion)   │
             │                     └───────┬────────┘
             │                             │
             │                             ▼
             │                   ┌───────────────────┐
             │                   │TextractCallback   │
             │                   │    Lambda         │
             │                   └─────────┬─────────┘
             │                             │
             └─────────────┬───────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                 S3: textract-output-dev                          │
│                    (S3 Event Trigger)                            │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                  KeywordSearchLambda                             │
│  - Searches for keywords (Cyrillic + Latin)                     │
│  - Case-insensitive whole-word matching                         │
│  - Multi-word phrase support ("lavazza crema")                  │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                   SNS: keyword-found-topic                       │
│              Email: vgvalentinova@gmail.com                      │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

**1. Clone and navigate:**
```bash
cd /path/to/claude-test
```

**2. Deploy everything:**
```bash
./scripts/deploy.sh
```

**3. Verify your email:**
- Check vgvalentinova@gmail.com
- Click the AWS SNS verification link

**4. Upload configuration:**
```bash
# Get bucket name from Terraform output
SOURCE_BUCKET=$(cd terraform && terraform output -raw brochures_source_bucket)

# Upload config
aws s3 cp config/keyword-config.json s3://${SOURCE_BUCKET}/config/keyword-config.json
```

**5. Test deployment:**
```bash
./scripts/test-deployment.sh
```

## 📝 Detailed Deployment Steps

### Step 1: Package Lambda Functions

The deployment script automatically packages Lambda functions with dependencies:

```bash
cd /path/to/claude-test

# This creates lambda_packages/*.zip files:
# - crawler.zip (with beautifulsoup4, lxml, requests)
# - process_brochure.zip (with PyPDF2)
# - textract_callback.zip
# - keyword_search.zip
```

### Step 2: Initialize Terraform

```bash
cd terraform
terraform init
```

This downloads the AWS provider and initializes the backend.

### Step 3: Review Plan

```bash
terraform plan -out=tfplan
```

**Verify these key configurations:**
- EventBridge schedule: `cron(0 10 ? * SUN *)`
- Email subscription: `vgvalentinova@gmail.com`
- Region: `us-east-1`
- Resource tags: Project=BrochureScanner, Owner=vgvalentinova

### Step 4: Deploy Infrastructure

```bash
terraform apply tfplan
```

This creates:
- **S3 Buckets**: brochures-source-dev, textract-output-dev
- **DynamoDB Table**: brochure-metadata-table-dev (with 3 GSIs)
- **Lambda Functions**: CrawlerLambda, ProcessBrochureLambda, TextractCallbackLambda, KeywordSearchLambda
- **SNS Topics**: textract-job-completion-topic, keyword-found-topic
- **EventBridge Rule**: scan-schedule-rule-dev
- **IAM Roles**: 4 Lambda roles + Textract service role
- **CloudWatch**: Log groups and alarms

### Step 5: Verify SES Email

**IMPORTANT:** AWS SES starts in sandbox mode. You must verify your email address.

1. **Check your email** (vgvalentinova@gmail.com)
2. **Look for:** "AWS Notification - Subscription Confirmation"
3. **Click the verification link**

**Verify status:**
```bash
aws ses get-identity-verification-attributes \
  --identities vgvalentinova@gmail.com
```

### Step 6: Upload Configuration

```bash
# Get bucket name
cd terraform
SOURCE_BUCKET=$(terraform output -raw brochures_source_bucket)

# Upload keyword config
cd ..
aws s3 cp config/keyword-config.json \
  s3://${SOURCE_BUCKET}/config/keyword-config.json

# Verify upload
aws s3 ls s3://${SOURCE_BUCKET}/config/
```

### Step 7: Test Deployment

```bash
./scripts/test-deployment.sh
```

This will:
1. Invoke CrawlerLambda manually
2. Download Lidl Bulgaria brochure (with web scraping)
3. Process with Textract
4. Search for keywords
5. Send email notification

**Expected timeline:**
- Crawler: ~10-30 seconds
- Textract: ~30-60 seconds
- Keyword search: ~5-10 seconds
- **Total: ~1-2 minutes**

## ⚙️ Configuration

### Keyword Configuration

File: `config/keyword-config.json`

```json
{
  "version": "1.0",
  "updated_at": "2025-01-19",
  "stores": [
    {
      "store_id": "lidl_bg",
      "store_name": "Lidl Bulgaria",
      "brochure_url": "https://www.lidl.bg/l/bg/broshura/17-11-23-11-11fef3/view/menu/page/1",
      "keywords": [
        "lupilu",
        "baby",
        "бебе",
        "бебешки",
        "играчка",
        "lavazza crema"
      ],
      "recipients": [
        {
          "email": "vgvalentinova@gmail.com",
          "type": "TO"
        }
      ],
      "crawl_schedule": "weekly"
    }
  ]
}
```

### Keyword Matching Rules

**Case-Insensitive:**
- "BABY" matches "baby"
- "БЕБЕ" matches "бебе"

**Whole-Word Matching:**
- "baby" matches "baby products"
- "baby" does NOT match "babysitter"

**Multi-Word Phrases:**
- "lavazza crema" searches as single phrase
- Must appear together (not "lavazza ... crema")

**Cyrillic Support:**
- Full UTF-8 encoding throughout pipeline
- Bulgarian keywords: бебе, бебешки, играчка
- Case conversion works for Cyrillic: бебе → БЕБЕ

### Weekly Schedule

**Cron Expression:** `cron(0 10 ? * SUN *)`

- **Day:** Every Sunday
- **Time:** 10:00 AM UTC
- **Bulgarian Time:** 12:00 PM EET (summer) / 11:00 AM EET (winter)

**To change schedule:**
Edit `terraform/terraform.tfvars`:
```hcl
crawler_schedule = "cron(0 10 ? * SUN *)"
# Daily: "cron(0 10 * * ? *)"
# Weekly Mon: "cron(0 10 ? * MON *)"
```

Then reapply:
```bash
cd terraform
terraform apply
```

### Email Notification

**Format:** HTML email with:
- Store name and brochure filename
- Upload timestamp
- Total matches and matched keywords
- Table with: Keyword | Page | Context
- Brochure ID and S3 key

**Example:**
```
Subject: Keyword Match Found: Lidl Bulgaria - brochure_20250119.pdf

Body:
🎯 Keyword Matches Found in Lidl Bulgaria Brochure

Brochure: brochure_20250119.pdf
Upload Time: 2025-01-19T10:15:30Z
Total Matches: 3
Matched Keywords: baby, lupilu

Match Details:
┌──────────┬──────┬────────────────────────────────────┐
│ Keyword  │ Page │ Context                            │
├──────────┼──────┼────────────────────────────────────┤
│ lupilu   │ 2    │ ...дрехи Lupilu за бебета от 0... │
│ baby     │ 2    │ ...baby products starting from...  │
│ lupilu   │ 5    │ ...хранителни продукти Lupilu...  │
└──────────┴──────┴────────────────────────────────────┘
```

## 🧪 Testing

### Manual Test

```bash
./scripts/test-deployment.sh
```

### Monitor Logs

**CrawlerLambda:**
```bash
aws logs tail /aws/lambda/CrawlerLambda-dev --follow
```

**ProcessBrochureLambda:**
```bash
aws logs tail /aws/lambda/ProcessBrochureLambda-dev --follow
```

**KeywordSearchLambda:**
```bash
aws logs tail /aws/lambda/KeywordSearchLambda-dev --follow
```

**All logs together:**
```bash
# Open 4 terminal windows and run each:
aws logs tail /aws/lambda/CrawlerLambda-dev --follow
aws logs tail /aws/lambda/ProcessBrochureLambda-dev --follow
aws logs tail /aws/lambda/TextractCallbackLambda-dev --follow
aws logs tail /aws/lambda/KeywordSearchLambda-dev --follow
```

### Check DynamoDB

```bash
aws dynamodb scan \
  --table-name brochure-metadata-table-dev \
  --max-items 10
```

### Check S3

```bash
# List brochures
aws s3 ls s3://brochures-source-dev-{ACCOUNT_ID}/lidl_bg/ --recursive

# List Textract results
aws s3 ls s3://textract-output-dev-{ACCOUNT_ID}/ --recursive
```

### Check EventBridge Schedule

```bash
aws events describe-rule --name scan-schedule-rule-dev
```

## 📊 Monitoring

### CloudWatch Metrics

**Custom Metrics (Namespace: BrochureScanner):**
- `BrochuresDownloaded` - Successful downloads
- `BrochureDownloadFailures` - Failed downloads
- `BrochuresScraped` - Web scraping used
- `DuplicateBrochures` - Duplicates detected

**View metrics:**
```bash
aws cloudwatch get-metric-statistics \
  --namespace BrochureScanner \
  --metric-name BrochuresDownloaded \
  --start-time 2025-01-18T00:00:00Z \
  --end-time 2025-01-19T00:00:00Z \
  --period 3600 \
  --statistics Sum
```

### CloudWatch Alarms

- **crawler-lambda-errors-dev**: >5 errors in 10 minutes
- **process-brochure-lambda-errors-dev**: >5 errors in 10 minutes
- **keyword-search-lambda-errors-dev**: >5 errors in 10 minutes

### Dashboard (Manual Creation)

Create CloudWatch dashboard to visualize:
- Lambda invocations
- Error rates
- Textract job status
- Keyword matches found

## 🔧 Troubleshooting

### Email Not Received

**Problem:** No email notification after test

**Solutions:**
1. **Check SES verification:**
   ```bash
   aws ses get-identity-verification-attributes \
     --identities vgvalentinova@gmail.com
   ```
   Status should be "Success"

2. **Check spam folder** in vgvalentinova@gmail.com

3. **Check SNS subscription:**
   ```bash
   aws sns list-subscriptions-by-topic \
     --topic-arn $(cd terraform && terraform output -raw keyword_found_topic_arn)
   ```
   Subscription should show "Confirmed"

4. **Check Lambda logs:**
   ```bash
   aws logs tail /aws/lambda/KeywordSearchLambda-dev --since 30m
   ```

### Web Scraping Failed

**Problem:** CrawlerLambda cannot extract PDF from Lidl page

**Symptoms:**
```
ScrapingError: Could not extract brochure URL from page
```

**Solutions:**
1. **Check URL is accessible:**
   ```bash
   curl -I "https://www.lidl.bg/l/bg/broshura/17-11-23-11-11fef3/view/menu/page/1"
   ```

2. **Update brochure URL** in config (Lidl changes URLs frequently)

3. **Check scraper logs** for specific error:
   ```bash
   aws logs filter-pattern "Scraping" \
     --log-group-name /aws/lambda/CrawlerLambda-dev
   ```

4. **Test locally:**
   ```python
   # Test scraping logic
   from lambda_functions.crawler.scraper import BrochureScraper
   scraper = BrochureScraper()
   url = scraper.extract_brochure_url("https://www.lidl.bg/...", "lidl_bg")
   print(url)
   ```

### Cyrillic Keywords Not Matching

**Problem:** Bulgarian keywords (бебе, играчка) not found in brochure

**Solutions:**
1. **Check text extraction:**
   ```bash
   # Download Textract output from S3
   aws s3 cp s3://textract-output-dev-{ACCOUNT}/lidl_bg_.../textract_output.json .

   # Check if Cyrillic text is present
   cat textract_output.json | grep -o "бебе"
   ```

2. **Textract may not extract Cyrillic well** - consider OCR alternatives

3. **Check keyword config encoding:**
   ```bash
   cat config/keyword-config.json | grep "бебе"
   ```
   Should display correctly, not as `\u0431\u0435\u0431\u0435`

### Lambda Timeout

**Problem:** Lambda function times out

**Solutions:**
1. **Increase timeout** in `terraform/variables.tf`:
   ```hcl
   variable "crawler_timeout" {
     default = 600  # Increase to 10 minutes
   }
   ```

2. **Increase memory** (more memory = faster CPU):
   ```hcl
   variable "crawler_memory" {
     default = 1024  # Increase to 1 GB
   }
   ```

3. **Reapply Terraform:**
   ```bash
   cd terraform
   terraform apply
   ```

### Duplicate Detection Not Working

**Problem:** Same brochure downloaded multiple times

**Solutions:**
1. **Check hash index:**
   ```bash
   aws dynamodb query \
     --table-name brochure-metadata-table-dev \
     --index-name hash-index \
     --key-condition-expression "file_hash = :hash" \
     --expression-attribute-values '{":hash":{"S":"YOUR_HASH"}}'
   ```

2. **Check deduplication logic** in CrawlerLambda logs

3. **Verify hash calculation** matches between runs

### Textract Job Fails

**Problem:** Async Textract job fails

**Symptoms:**
```
Status: FAILED in TextractCallbackLambda logs
```

**Solutions:**
1. **Check Textract limits:**
   - Max file size: 500 MB
   - Max pages: 3000

2. **Check IAM permissions** for Textract service role

3. **Review Textract job details:**
   ```bash
   aws textract get-document-text-detection --job-id JOB_ID
   ```

### EventBridge Not Triggering

**Problem:** Crawler doesn't run on schedule

**Solutions:**
1. **Check rule is enabled:**
   ```bash
   aws events describe-rule --name scan-schedule-rule-dev
   ```
   State should be "ENABLED"

2. **Check rule targets:**
   ```bash
   aws events list-targets-by-rule --rule scan-schedule-rule-dev
   ```

3. **Manually invoke to test:**
   ```bash
   aws events put-events --entries file://test-event.json
   ```

4. **Check Lambda permissions:**
   ```bash
   aws lambda get-policy --function-name CrawlerLambda-dev
   ```

## 🗑️ Cleanup

To destroy all resources:

```bash
cd terraform
terraform destroy
```

This will delete:
- All S3 buckets (including contents)
- DynamoDB table
- Lambda functions
- SNS topics
- EventBridge rules
- IAM roles
- CloudWatch logs and alarms

**Note:** SNS email subscriptions may need manual confirmation to delete.

## 📚 Additional Resources

- [AWS Textract Documentation](https://docs.aws.amazon.com/textract/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [EventBridge Cron Expressions](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-create-rule-schedule.html)
- [AWS SES Sandbox Mode](https://docs.aws.amazon.com/ses/latest/dg/request-production-access.html)

## 🆘 Support

For issues or questions:
1. Check logs in CloudWatch
2. Review this troubleshooting guide
3. Check AWS service quotas and limits
4. Verify IAM permissions

## 📄 License

MIT License - See project root for details.
