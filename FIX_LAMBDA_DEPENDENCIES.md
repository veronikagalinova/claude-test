# Fix Lambda Dependencies Error

## Problem

You're seeing this error when testing CrawlerLambda:
```json
{
    "errorMessage": "Unable to import module 'handler': No module named 'requests'",
    "errorType": "Runtime.ImportModuleError"
}
```

## Root Cause

The Lambda functions were deployed without their Python dependencies (requests, beautifulsoup4, etc.) packaged with them.

## Quick Fix (2 commands)

Run these commands from your local machine in the project directory:

```bash
# Step 1: Package Lambda functions with dependencies
./scripts/package-lambdas.sh

# Step 2: Update Lambda functions in AWS
./scripts/update-lambdas.sh
```

That's it! Now test again:
```bash
./scripts/test-deployment.sh
```

## What These Scripts Do

### package-lambdas.sh
- Creates `lambda_packages/` directory
- Installs Python dependencies for each Lambda function
- Creates deployment packages (crawler.zip, process_brochure.zip, etc.)
- Uses correct platform targeting for AWS Lambda (manylinux2014_x86_64)

### update-lambdas.sh
- Updates each Lambda function in AWS with the new packages
- Waits for updates to complete
- Verifies successful deployment

## Detailed Fix Steps

If you prefer to do it manually:

### 1. Package CrawlerLambda

```bash
cd claude-test

# Create temp directory
mkdir -p lambda_packages/crawler_temp

# Install dependencies
pip3 install -r lambda_functions/crawler/requirements.txt \
  -t lambda_packages/crawler_temp \
  --platform manylinux2014_x86_64 \
  --only-binary=:all:

# Copy code
cp lambda_functions/crawler/*.py lambda_packages/crawler_temp/

# Create zip
cd lambda_packages/crawler_temp
zip -r ../crawler.zip .
cd ../..
```

### 2. Update Lambda in AWS

```bash
aws lambda update-function-code \
  --function-name CrawlerLambda-dev \
  --zip-file fileb://lambda_packages/crawler.zip
```

### 3. Repeat for other Lambda functions

```bash
# Process Brochure
./scripts/package-lambdas.sh

# Then update all
./scripts/update-lambdas.sh
```

## Why This Happened

When you run `terraform apply` directly, Terraform expects the Lambda packages to already exist in `lambda_packages/`. 

The **correct deployment flow** is:

1. ✅ Run `./scripts/deploy.sh` (not `terraform apply` directly)
   - This script packages Lambda functions first
   - Then runs Terraform

**OR**

1. ✅ Run `./scripts/package-lambdas.sh` first
2. ✅ Then run `cd terraform && terraform apply`

## Prevent This in Future

**Option A: Use deploy.sh** (Recommended)
```bash
./scripts/deploy.sh
```
This script handles everything in the correct order.

**Option B: Manual workflow**
```bash
# 1. Package Lambda functions
./scripts/package-lambdas.sh

# 2. Deploy with Terraform
cd terraform
terraform apply

# 3. If you update Lambda code later
cd ..
./scripts/package-lambdas.sh
./scripts/update-lambdas.sh
```

## Verify Fix

After running the fix scripts, test:

```bash
./scripts/test-deployment.sh
```

You should see:
```json
{
    "statusCode": 200,
    "body": "{...}"
}
```

## Check Lambda Package Contents

To verify a package contains dependencies:

```bash
# List contents of crawler.zip
unzip -l lambda_packages/crawler.zip | grep -E "(requests|beautifulsoup4|bs4)"
```

You should see:
```
requests/
bs4/
beautifulsoup4/
```

## Common Issues

### Issue: "No such file or directory: lambda_packages/crawler.zip"

**Fix:** You need to create the packages first:
```bash
./scripts/package-lambdas.sh
```

### Issue: "Module not found" for a different module

**Fix:** Package and update all functions:
```bash
./scripts/package-lambdas.sh
./scripts/update-lambdas.sh
```

### Issue: Package too large (>50MB)

**Fix:** Lambda packages are compressed and should be <10MB each. If larger:
- Remove unnecessary files from temp directory
- Use `--no-deps` for boto3 (already available in Lambda)
- Exclude test files

### Issue: Platform compatibility errors

**Fix:** The package-lambdas.sh script uses `--platform manylinux2014_x86_64` to ensure compatibility with Lambda's runtime environment.

## Dependencies for Each Lambda

**CrawlerLambda:**
- requests
- beautifulsoup4
- lxml
- boto3 (included in Lambda runtime)

**ProcessBrochureLambda:**
- PyPDF2
- boto3

**TextractCallbackLambda:**
- boto3

**KeywordSearchLambda:**
- boto3

## Still Not Working?

Check CloudWatch logs:
```bash
aws logs tail /aws/lambda/CrawlerLambda-dev --follow --since 10m
```

Look for:
- Import errors
- Module not found errors
- Specific missing dependencies

Then update requirements.txt and repackage.
