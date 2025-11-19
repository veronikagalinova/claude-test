# 🚀 Quick Start Guide - Serverless Brochure Keyword Scanner

## ⚡ Deploy in 5 Minutes

### Prerequisites
```bash
# Install AWS CLI
aws --version

# Install Terraform
terraform --version

# Configure AWS credentials
aws configure
```

### Deployment Steps

**1. Run deployment script:**
```bash
cd /path/to/claude-test
./scripts/deploy.sh
```

**2. Verify email (IMPORTANT!):**
- Check **vgvalentinova@gmail.com**
- Click the AWS SNS verification link

**3. Upload configuration:**
```bash
cd terraform
SOURCE_BUCKET=$(terraform output -raw brochures_source_bucket)
cd ..
aws s3 cp config/keyword-config.json s3://${SOURCE_BUCKET}/config/keyword-config.json
```

**4. Test immediately:**
```bash
./scripts/test-deployment.sh
```

**5. Check email:**
- Wait 1-2 minutes
- Check **vgvalentinova@gmail.com** for keyword matches

## 📅 Automated Schedule

**Weekly crawling:** Every Sunday at 10:00 AM UTC (12:00 PM Bulgarian time)

**Keywords monitored:**
- lupilu
- baby
- бебе (Bulgarian)
- бебешки (Bulgarian)
- играчка (Bulgarian)
- lavazza crema (phrase)

**Store:** Lidl Bulgaria

## 📂 Project Structure

```
claude-test/
├── terraform/                    # Infrastructure as Code
│   ├── main.tf                   # Provider configuration
│   ├── variables.tf              # Input variables
│   ├── outputs.tf                # Deployment outputs
│   ├── s3.tf                     # S3 buckets
│   ├── dynamodb.tf               # DynamoDB table
│   ├── lambda.tf                 # Lambda functions
│   ├── iam.tf                    # IAM roles/policies
│   ├── sns.tf                    # SNS topics
│   ├── eventbridge.tf            # Weekly schedule
│   ├── cloudwatch.tf             # Logs and alarms
│   └── terraform.tfvars          # Your configuration
│
├── lambda_functions/             # Lambda code
│   ├── crawler/                  # Downloads brochures
│   │   ├── handler.py
│   │   ├── scraper.py           # Web scraping logic
│   │   └── requirements.txt
│   ├── process_brochure/        # Textract orchestration
│   │   ├── handler.py
│   │   └── requirements.txt
│   ├── textract_callback/       # Async result retrieval
│   │   ├── handler.py
│   │   └── requirements.txt
│   └── keyword_search/          # Keyword matching
│       ├── handler.py
│       └── requirements.txt
│
├── scripts/                      # Deployment automation
│   ├── deploy.sh                 # Main deployment script
│   └── test-deployment.sh        # Testing script
│
├── config/                       # Configuration files
│   └── keyword-config.json       # Store URLs and keywords
│
├── DEPLOYMENT_README.md          # Full deployment guide
└── QUICKSTART.md                 # This file
```

## 🔍 Monitor Logs

```bash
# Watch crawler logs
aws logs tail /aws/lambda/CrawlerLambda-dev --follow

# Watch all logs (4 terminal windows)
aws logs tail /aws/lambda/CrawlerLambda-dev --follow
aws logs tail /aws/lambda/ProcessBrochureLambda-dev --follow
aws logs tail /aws/lambda/TextractCallbackLambda-dev --follow
aws logs tail /aws/lambda/KeywordSearchLambda-dev --follow
```

## 🧪 Manual Testing

```bash
# Trigger immediate crawl (don't wait for Sunday)
./scripts/test-deployment.sh

# Check DynamoDB records
aws dynamodb scan --table-name brochure-metadata-table-dev --max-items 5

# Check S3 uploads
SOURCE_BUCKET=$(cd terraform && terraform output -raw brochures_source_bucket)
aws s3 ls s3://${SOURCE_BUCKET}/lidl_bg/ --recursive
```

## 🛠️ Troubleshooting

### No Email Received?

1. **Check SES verification:**
   ```bash
   aws ses get-identity-verification-attributes --identities vgvalentinova@gmail.com
   ```

2. **Check spam folder**

3. **Check logs:**
   ```bash
   aws logs tail /aws/lambda/KeywordSearchLambda-dev --since 10m
   ```

### Web Scraping Failed?

1. **Check Lidl URL is still valid**
2. **Update URL in config/keyword-config.json**
3. **Reupload config to S3**

### Lambda Timeout?

1. **Increase timeout in terraform/variables.tf**
2. **Run:** `cd terraform && terraform apply`

## 📧 Email Notification Format

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
└──────────┴──────┴────────────────────────────────────┘
```

## 🔄 Update Configuration

```bash
# Edit keywords
nano config/keyword-config.json

# Upload to S3
SOURCE_BUCKET=$(cd terraform && terraform output -raw brochures_source_bucket)
aws s3 cp config/keyword-config.json s3://${SOURCE_BUCKET}/config/keyword-config.json
```

## 🗑️ Cleanup

```bash
cd terraform
terraform destroy
```

## 📚 Full Documentation

See **DEPLOYMENT_README.md** for:
- Complete architecture diagram
- Detailed troubleshooting
- Configuration reference
- Monitoring setup
- Advanced features

## 🎯 What Happens Next?

1. **Every Sunday at 10 AM UTC:**
   - CrawlerLambda downloads Lidl Bulgaria brochure
   - Web scraping extracts PDF from viewer page
   - SHA-256 hash checks for duplicates

2. **Automatic processing:**
   - Textract extracts text (supports Cyrillic)
   - Keyword search finds matches
   - Email sent to vgvalentinova@gmail.com

3. **You receive email:**
   - Only when keywords are found
   - HTML formatted with context
   - Page numbers for each match

## ✅ Success Checklist

- [ ] Deployed with `./scripts/deploy.sh`
- [ ] Email verified (clicked SNS link)
- [ ] Config uploaded to S3
- [ ] Test run completed successfully
- [ ] Email notification received
- [ ] Logs show no errors
- [ ] EventBridge schedule is enabled

## 🆘 Need Help?

1. Check **DEPLOYMENT_README.md** (comprehensive guide)
2. Review CloudWatch logs
3. Check AWS service quotas
4. Verify IAM permissions

---

**Email:** vgvalentinova@gmail.com  
**Schedule:** Weekly Sunday 10 AM UTC  
**Keywords:** lupilu, baby, бебе, бебешки, играчка, lavazza crema
