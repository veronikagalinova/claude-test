#!/bin/bash

# Test deployment script for Serverless Brochure Scanner
# Triggers a manual test run without waiting for the weekly schedule

set -e

echo "========================================="
echo "Testing Serverless Brochure Scanner"
echo "========================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Get AWS region
AWS_REGION=$(aws configure get region || echo "us-east-1")

echo "Step 1: Getting Lambda function name..."
FUNCTION_NAME="CrawlerLambda-dev"
echo -e "${GREEN}✓ Function: $FUNCTION_NAME${NC}"
echo ""

# Prepare test payload
echo "Step 2: Preparing test payload..."
TEST_PAYLOAD='{
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
      ]
    }
  ]
}'

echo -e "${GREEN}✓ Payload prepared${NC}"
echo ""

# Invoke Lambda
echo "Step 3: Invoking CrawlerLambda..."
echo ""
echo -e "${YELLOW}This will:${NC}"
echo "  1. Download the brochure from Lidl Bulgaria (with web scraping if needed)"
echo "  2. Upload it to S3"
echo "  3. Trigger Textract processing"
echo "  4. Search for keywords"
echo "  5. Send email notification if matches found"
echo ""

aws lambda invoke \
  --function-name "$FUNCTION_NAME" \
  --payload "$TEST_PAYLOAD" \
  --cli-binary-format raw-in-base64-out \
  --region "$AWS_REGION" \
  output.json

echo ""
echo "Lambda response:"
cat output.json | python3 -m json.tool
echo ""

# Monitor logs
echo ""
echo "Step 4: Monitoring logs (press Ctrl+C to stop)..."
echo ""
sleep 2

aws logs tail "/aws/lambda/$FUNCTION_NAME" \
  --follow \
  --region "$AWS_REGION" \
  --since 1m

echo ""
echo -e "${GREEN}========================================="
echo "Test Complete!"
echo "=========================================${NC}"
echo ""
echo "Check your email (vgvalentinova@gmail.com) for keyword match notifications."
echo ""
echo "To view all logs:"
echo "  aws logs tail /aws/lambda/CrawlerLambda-dev --follow"
echo "  aws logs tail /aws/lambda/ProcessBrochureLambda-dev --follow"
echo "  aws logs tail /aws/lambda/KeywordSearchLambda-dev --follow"
echo ""

rm -f output.json
