#!/bin/bash

# Package Lambda functions with dependencies
# Run this script to create deployment packages for all Lambda functions

set -e

echo "========================================="
echo "Packaging Lambda Functions"
echo "========================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check prerequisites
echo "Checking prerequisites..."

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}ERROR: python3 not found${NC}"
    exit 1
fi

if ! command -v pip3 &> /dev/null; then
    echo -e "${RED}ERROR: pip3 not found${NC}"
    exit 1
fi

if ! command -v zip &> /dev/null; then
    echo -e "${RED}ERROR: zip not found${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Prerequisites OK${NC}"
echo ""

# Create lambda_packages directory
mkdir -p lambda_packages
echo -e "${GREEN}✓ Created lambda_packages directory${NC}"
echo ""

# Package each Lambda function
LAMBDA_FUNCTIONS=("crawler" "process_brochure" "textract_callback" "keyword_search")

for func in "${LAMBDA_FUNCTIONS[@]}"; do
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Packaging: $func"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # Create temporary directory
    TEMP_DIR="lambda_packages/${func}_temp"
    rm -rf "$TEMP_DIR"
    mkdir -p "$TEMP_DIR"

    # Install dependencies if requirements.txt exists
    if [ -f "lambda_functions/${func}/requirements.txt" ]; then
        echo "  Installing dependencies..."
        pip3 install -r "lambda_functions/${func}/requirements.txt" \
          -t "$TEMP_DIR" \
          --platform manylinux2014_x86_64 \
          --only-binary=:all: \
          --upgrade \
          -q
        
        if [ $? -ne 0 ]; then
            echo -e "${YELLOW}  Warning: Some dependencies may not be compatible${NC}"
            # Try without platform restriction
            pip3 install -r "lambda_functions/${func}/requirements.txt" \
              -t "$TEMP_DIR" \
              --upgrade \
              -q
        fi
    fi

    # Copy Lambda code
    echo "  Copying source files..."
    cp lambda_functions/${func}/*.py "$TEMP_DIR/" 2>/dev/null || true

    # Create zip file
    echo "  Creating zip package..."
    cd "$TEMP_DIR"
    zip -r "../../lambda_packages/${func}.zip" . -q
    cd - > /dev/null

    # Get package size
    SIZE=$(du -h "lambda_packages/${func}.zip" | cut -f1)
    echo -e "  ${GREEN}✓ Created ${func}.zip (${SIZE})${NC}"

    # Cleanup
    rm -rf "$TEMP_DIR"
    echo ""
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}All Lambda functions packaged!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Packages created in lambda_packages/:"
ls -lh lambda_packages/*.zip
echo ""
echo "Next steps:"
echo "  1. Update Lambda functions in AWS:"
echo "     ./scripts/update-lambdas.sh"
echo ""
echo "  2. Or redeploy with Terraform:"
echo "     cd terraform && terraform apply"
