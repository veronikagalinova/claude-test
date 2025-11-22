#!/bin/bash

# Update Lambda function code in AWS
# Run this after packaging with package-lambdas.sh

set -e

echo "========================================="
echo "Updating Lambda Functions in AWS"
echo "========================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo -e "${RED}ERROR: AWS CLI not found${NC}"
    exit 1
fi

# Check if packages exist
if [ ! -d "lambda_packages" ]; then
    echo -e "${RED}ERROR: lambda_packages directory not found${NC}"
    echo "Run ./scripts/package-lambdas.sh first"
    exit 1
fi

# Get AWS region
AWS_REGION=$(aws configure get region || echo "us-east-1")
echo "AWS Region: $AWS_REGION"
echo ""

# Environment
ENVIRONMENT="dev"

# Update each Lambda function
LAMBDA_FUNCTIONS=("CrawlerLambda" "ProcessBrochureLambda" "TextractCallbackLambda" "KeywordSearchLambda")
PACKAGE_NAMES=("crawler" "process_brochure" "textract_callback" "keyword_search")

for i in "${!LAMBDA_FUNCTIONS[@]}"; do
    FUNC_NAME="${LAMBDA_FUNCTIONS[$i]}-${ENVIRONMENT}"
    PACKAGE_NAME="${PACKAGE_NAMES[$i]}"
    ZIP_FILE="lambda_packages/${PACKAGE_NAME}.zip"

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Updating: $FUNC_NAME"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    if [ ! -f "$ZIP_FILE" ]; then
        echo -e "${RED}  ERROR: Package not found: $ZIP_FILE${NC}"
        continue
    fi

    echo "  Uploading code..."
    aws lambda update-function-code \
      --function-name "$FUNC_NAME" \
      --zip-file "fileb://$ZIP_FILE" \
      --region "$AWS_REGION" \
      --output json > /tmp/lambda-update-$PACKAGE_NAME.json

    # Wait for update to complete
    echo "  Waiting for update to complete..."
    aws lambda wait function-updated \
      --function-name "$FUNC_NAME" \
      --region "$AWS_REGION"

    echo -e "  ${GREEN}✓ Updated successfully${NC}"
    echo ""
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}All Lambda functions updated!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Next step: Test deployment"
echo "  ./scripts/test-deployment.sh"
