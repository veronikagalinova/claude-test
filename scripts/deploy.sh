#!/bin/bash

# Deployment script for Serverless Brochure Keyword Scanner
# This script packages Lambda functions and deploys infrastructure with Terraform

set -e  # Exit on error

echo "========================================="
echo "Serverless Brochure Scanner Deployment"
echo "========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
echo "Step 1: Checking prerequisites..."
echo ""

if ! command -v aws &> /dev/null; then
    echo -e "${RED}ERROR: AWS CLI not found. Please install it first.${NC}"
    exit 1
fi

if ! command -v terraform &> /dev/null; then
    echo -e "${RED}ERROR: Terraform not found. Please install it first.${NC}"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}ERROR: Python 3 not found. Please install it first.${NC}"
    exit 1
fi

if ! command -v pip3 &> /dev/null; then
    echo -e "${RED}ERROR: pip3 not found. Please install it first.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ All prerequisites found${NC}"
echo ""

# Check AWS credentials
echo "Step 2: Checking AWS credentials..."
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "")
AWS_REGION=$(aws configure get region || echo "us-east-1")

if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo -e "${RED}ERROR: Cannot determine AWS account. Please configure AWS CLI.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ AWS Account ID: $AWS_ACCOUNT_ID${NC}"
echo -e "${GREEN}✓ AWS Region: $AWS_REGION${NC}"
echo ""

# Create lambda_packages directory
echo "Step 3: Creating Lambda packages directory..."
mkdir -p lambda_packages
echo -e "${GREEN}✓ Created lambda_packages/${NC}"
echo ""

# Package Lambda functions
echo "Step 4: Packaging Lambda functions..."
echo ""

LAMBDA_FUNCTIONS=("crawler" "process_brochure" "textract_callback" "keyword_search")

for func in "${LAMBDA_FUNCTIONS[@]}"; do
    echo "  Packaging $func..."

    # Create temporary package directory
    TEMP_DIR="lambda_packages/${func}_temp"
    rm -rf "$TEMP_DIR"
    mkdir -p "$TEMP_DIR"

    # Install dependencies
    if [ -f "lambda_functions/${func}/requirements.txt" ]; then
        echo "    Installing dependencies..."
        pip3 install -r "lambda_functions/${func}/requirements.txt" -t "$TEMP_DIR" -q
    fi

    # Copy Lambda code
    cp lambda_functions/${func}/*.py "$TEMP_DIR/"

    # Create zip file
    cd "$TEMP_DIR"
    zip -r "../../lambda_packages/${func}.zip" . -q
    cd - > /dev/null

    # Cleanup
    rm -rf "$TEMP_DIR"

    echo -e "    ${GREEN}✓ Created ${func}.zip${NC}"
done

echo ""
echo -e "${GREEN}✓ All Lambda functions packaged${NC}"
echo ""

# Initialize Terraform
echo "Step 5: Initializing Terraform..."
cd terraform
terraform init
echo -e "${GREEN}✓ Terraform initialized${NC}"
echo ""

# Validate Terraform configuration
echo "Step 6: Validating Terraform configuration..."
terraform validate
echo -e "${GREEN}✓ Terraform configuration valid${NC}"
echo ""

# Plan deployment
echo "Step 7: Planning deployment..."
echo ""
terraform plan -out=tfplan
echo ""

# Confirm deployment
echo ""
echo -e "${YELLOW}Ready to deploy infrastructure to AWS.${NC}"
echo -e "${YELLOW}This will create:${NC}"
echo "  - 2 S3 buckets"
echo "  - 1 DynamoDB table"
echo "  - 4 Lambda functions"
echo "  - 2 SNS topics (with email subscription)"
echo "  - EventBridge schedule rule (Weekly Sunday 10 AM UTC)"
echo "  - IAM roles and policies"
echo "  - CloudWatch logs and alarms"
echo ""
read -p "Do you want to proceed with deployment? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Deployment cancelled."
    exit 0
fi

# Apply Terraform
echo ""
echo "Step 8: Deploying infrastructure..."
terraform apply tfplan
echo ""
echo -e "${GREEN}✓ Infrastructure deployed${NC}"
echo ""

# Get outputs
echo "Step 9: Retrieving deployment information..."
SOURCE_BUCKET=$(terraform output -raw brochures_source_bucket)
ACCOUNT_ID=$(terraform output -raw account_id)
REGION=$(terraform output -raw aws_region)
EMAIL=$(terraform output -raw notification_email)

echo ""
echo -e "${GREEN}========================================="
echo "Deployment Complete!"
echo "=========================================${NC}"
echo ""
echo "Next steps:"
echo ""
echo "1. Verify SES email subscription:"
echo -e "   ${YELLOW}Check your email (${EMAIL}) and click the verification link${NC}"
echo ""
echo "2. Upload keyword configuration:"
echo "   cd .."
echo "   aws s3 cp config/keyword-config.json s3://${SOURCE_BUCKET}/config/keyword-config.json"
echo ""
echo "3. Test the deployment:"
echo "   cd scripts"
echo "   ./test-deployment.sh"
echo ""
echo "4. Monitor logs:"
echo "   aws logs tail /aws/lambda/CrawlerLambda-dev --follow"
echo ""
echo "Your weekly crawler will run every Sunday at 10:00 AM UTC."
echo ""

cd ..
