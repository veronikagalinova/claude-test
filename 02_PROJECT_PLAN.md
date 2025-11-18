# Project Plan: Serverless Brochure Keyword Scanner

## 1. Milestones

### Milestone 1: MVP - Core Scanning Pipeline (Weeks 1-4)

**Goal**: Deploy a working end-to-end pipeline that can process manually uploaded brochures, extract text via Textract, detect keywords, and send email notifications.

**Scope**:
- Manual brochure upload to S3
- Textract OCR processing (sync and async flows)
- Keyword detection and matching
- Email notifications via SES
- Basic DynamoDB metadata tracking
- CloudWatch logging
- Single environment (dev/test)

**Success Criteria**:
- Successfully process 10 test brochures of varying sizes
- Detect keywords and send email notifications
- All components deployed via IaC
- Basic monitoring and error logging in place

**Out of Scope for MVP**:
- Scheduled crawling
- Advanced deduplication
- Production-grade monitoring dashboards
- Multi-environment deployment
- Cost optimization features

---

### Milestone 2: Automation & Reliability (Weeks 5-6)

**Goal**: Add scheduled crawling, robust error handling, deduplication, and production-grade observability.

**Scope**:
- Scheduled brochure crawling via EventBridge
- Hash-based deduplication
- Dead Letter Queues for all Lambda functions
- Comprehensive CloudWatch dashboards
- CloudWatch alarms for critical failures
- Retry logic and exponential backoff
- Production environment deployment
- SES production access

**Success Criteria**:
- Automated daily crawls successfully retrieve brochures from 5 test stores
- Duplicate brochures are skipped
- All failure scenarios trigger appropriate alarms
- End-to-end monitoring dashboard shows pipeline health
- Production environment fully operational

---

### Milestone 3: Optimization & Scaling (Weeks 7-8)

**Goal**: Optimize costs, improve performance, add operational tooling, and prepare for scale.

**Scope**:
- S3 lifecycle policies for cost optimization
- DynamoDB TTL configuration
- Lambda memory and timeout optimization
- Enhanced deduplication (HTTP Last-Modified headers)
- Runbook automation (self-healing for common failures)
- Load testing with 500+ brochures
- Cost tracking and optimization
- Configuration management UI or improved workflow
- Documentation and handoff to operations

**Success Criteria**:
- Successfully process 500 brochures in load test
- Monthly cost under target ($50 for 300 brochures/month)
- All operational runbooks tested
- System handles 10x current load without modification
- Complete documentation for operations team

---

## 2. Detailed TODO Lists by Milestone

### Milestone 1: MVP - Core Scanning Pipeline

#### Phase 1A: Foundation & Infrastructure (Week 1)

**TODO-001: Set up project repository and structure**
- Complexity: S
- Priority: P0 (Critical)
- Description: Initialize Git repository, create directory structure, set up .gitignore
- Dependencies: None
- Owner: DevOps/Platform

**TODO-002: Design and create S3 bucket configuration**
- Complexity: S
- Priority: P0
- Description: Define bucket names, encryption settings, S3 key naming conventions
- Dependencies: TODO-001
- Owner: Infrastructure

**TODO-003: Create DynamoDB table schema**
- Complexity: M
- Priority: P0
- Description: Define primary key, attributes, GSIs for brochure-metadata-table
- Dependencies: TODO-001
- Owner: Backend

**TODO-004: Set up IAM roles and policies skeleton**
- Complexity: M
- Priority: P0
- Description: Create IAM roles for all Lambda functions with minimal permissions
- Dependencies: TODO-001
- Owner: Security/Infrastructure

**TODO-005: Configure SES for sandbox testing**
- Complexity: S
- Priority: P0
- Description: Verify sender email and test recipient emails in SES sandbox
- Dependencies: None
- Owner: Infrastructure

**TODO-006: Create IaC foundation (SAM or Terraform)**
- Complexity: M
- Priority: P0
- Description: Set up base infrastructure template with S3, DynamoDB, IAM roles
- Dependencies: TODO-002, TODO-003, TODO-004
- Owner: DevOps

**TODO-007: Set up CloudWatch Logs groups**
- Complexity: S
- Priority: P1
- Description: Create log groups for all Lambda functions with retention policies
- Dependencies: TODO-001
- Owner: Infrastructure

---

#### Phase 1B: Core Lambda Functions (Week 2)

**TODO-008: Implement ProcessBrochureLambda skeleton**
- Complexity: M
- Priority: P0
- Description: Create Lambda function to handle S3 events, file type detection, size checks
- Dependencies: TODO-006
- Owner: Backend

**TODO-009: Integrate Textract synchronous API**
- Complexity: M
- Priority: P0
- Description: Implement sync Textract DetectDocumentText for small files
- Dependencies: TODO-008
- Owner: Backend

**TODO-010: Integrate Textract asynchronous API**
- Complexity: L
- Priority: P0
- Description: Implement async Textract StartDocumentTextDetection with SNS notification
- Dependencies: TODO-008, TODO-009
- Owner: Backend

**TODO-011: Create SNS topic for Textract job completion**
- Complexity: S
- Priority: P0
- Description: Configure textract-job-completion-topic with subscriptions
- Dependencies: TODO-006
- Owner: Infrastructure

**TODO-012: Implement TextractCallbackLambda**
- Complexity: M
- Priority: P0
- Description: Create Lambda to handle Textract async completion, retrieve results with pagination
- Dependencies: TODO-010, TODO-011
- Owner: Backend

**TODO-013: Implement Textract result storage to S3**
- Complexity: S
- Priority: P0
- Description: Write Textract JSON results to textract-output-bucket
- Dependencies: TODO-012
- Owner: Backend

**TODO-014: Implement DynamoDB metadata updates**
- Complexity: M
- Priority: P0
- Description: Update brochure status throughout processing pipeline
- Dependencies: TODO-003, TODO-008, TODO-012
- Owner: Backend

---

#### Phase 1C: Keyword Detection & Notifications (Week 3)

**TODO-015: Implement KeywordSearchLambda skeleton**
- Complexity: M
- Priority: P0
- Description: Create Lambda to parse Textract JSON and extract text blocks
- Dependencies: TODO-013
- Owner: Backend

**TODO-016: Implement keyword matching engine**
- Complexity: M
- Priority: P0
- Description: Case-insensitive, whole-word keyword matching with context extraction
- Dependencies: TODO-015
- Owner: Backend

**TODO-017: Create keyword configuration schema**
- Complexity: S
- Priority: P0
- Description: Define keyword-config.json structure and validation rules
- Dependencies: TODO-001
- Owner: Backend

**TODO-018: Implement keyword config loading**
- Complexity: S
- Priority: P0
- Description: Load keywords from S3 config file or DynamoDB
- Dependencies: TODO-017
- Owner: Backend

**TODO-019: Create SNS topic for keyword matches**
- Complexity: S
- Priority: P0
- Description: Configure keyword-found-topic with email subscription
- Dependencies: TODO-006
- Owner: Infrastructure

**TODO-020: Implement SNS notification publishing**
- Complexity: M
- Priority: P0
- Description: Publish match events to keyword-found-topic with full metadata
- Dependencies: TODO-016, TODO-019
- Owner: Backend

**TODO-021: Design email notification template**
- Complexity: S
- Priority: P0
- Description: Create plain text and HTML email templates for keyword matches
- Dependencies: TODO-005
- Owner: Frontend/Design

**TODO-022: Configure SES email delivery**
- Complexity: M
- Priority: P0
- Description: Set up SES to send emails via SNS subscription with templates
- Dependencies: TODO-019, TODO-021
- Owner: Infrastructure

**TODO-023: Implement match metadata storage**
- Complexity: S
- Priority: P0
- Description: Store keyword match details in DynamoDB
- Dependencies: TODO-014, TODO-016
- Owner: Backend

---

#### Phase 1D: Integration & Testing (Week 4)

**TODO-024: Configure S3 event notifications**
- Complexity: M
- Priority: P0
- Description: Set up S3 triggers for ProcessBrochureLambda and KeywordSearchLambda
- Dependencies: TODO-008, TODO-015
- Owner: Infrastructure

**TODO-025: Create test brochure fixtures**
- Complexity: S
- Priority: P0
- Description: Prepare PDF and image samples (1-page, 5-page, 20-page, corrupted)
- Dependencies: None
- Owner: QA

**TODO-026: Implement end-to-end integration tests**
- Complexity: L
- Priority: P0
- Description: Test complete flow from upload to email notification
- Dependencies: TODO-024, TODO-025
- Owner: QA/Backend

**TODO-027: Add error handling and logging**
- Complexity: M
- Priority: P0
- Description: Implement try-catch blocks, structured logging, error propagation
- Dependencies: TODO-008, TODO-012, TODO-015
- Owner: Backend

**TODO-028: Configure Lambda timeout and memory settings**
- Complexity: S
- Priority: P1
- Description: Optimize Lambda configurations based on test results
- Dependencies: TODO-026
- Owner: DevOps

**TODO-029: Update IAM policies with actual permissions**
- Complexity: M
- Priority: P0
- Description: Refine IAM roles based on actual API calls needed
- Dependencies: TODO-026
- Owner: Security

**TODO-030: Deploy MVP to dev environment**
- Complexity: M
- Priority: P0
- Description: Full deployment using IaC, validate all components
- Dependencies: TODO-006, TODO-026
- Owner: DevOps

**TODO-031: Conduct MVP acceptance testing**
- Complexity: M
- Priority: P0
- Description: Process 10 test brochures, verify all notifications received
- Dependencies: TODO-030
- Owner: QA

---

### Milestone 2: Automation & Reliability

#### Phase 2A: Scheduled Crawling (Week 5)

**TODO-032: Implement CrawlerLambda skeleton**
- Complexity: M
- Priority: P0
- Description: Create Lambda to download brochures from URLs
- Dependencies: TODO-030
- Owner: Backend

**TODO-033: Implement HTTP download with retry logic**
- Complexity: M
- Priority: P0
- Description: Add exponential backoff for network failures, timeout handling
- Dependencies: TODO-032
- Owner: Backend

**TODO-034: Implement file hash computation**
- Complexity: S
- Priority: P0
- Description: Compute SHA-256 hash for deduplication
- Dependencies: TODO-032
- Owner: Backend

**TODO-035: Implement deduplication query**
- Complexity: M
- Priority: P0
- Description: Query DynamoDB hash-index GSI to detect duplicates
- Dependencies: TODO-034
- Owner: Backend

**TODO-036: Implement brochure upload to S3**
- Complexity: S
- Priority: P0
- Description: Upload downloaded files with proper S3 key naming
- Dependencies: TODO-033
- Owner: Backend

**TODO-037: Create EventBridge schedule rule**
- Complexity: S
- Priority: P0
- Description: Configure scan-schedule-rule with cron expression
- Dependencies: TODO-006
- Owner: Infrastructure

**TODO-038: Configure EventBridge to invoke CrawlerLambda**
- Complexity: S
- Priority: P0
- Description: Set up event target with store configuration payload
- Dependencies: TODO-032, TODO-037
- Owner: Infrastructure

**TODO-039: Test scheduled crawling**
- Complexity: M
- Priority: P0
- Description: Trigger manual execution, verify downloads and deduplication
- Dependencies: TODO-038
- Owner: QA

---

#### Phase 2B: Error Handling & Observability (Week 5-6)

**TODO-040: Create Dead Letter Queues for all Lambdas**
- Complexity: M
- Priority: P0
- Description: Set up SQS DLQs for each Lambda function
- Dependencies: TODO-006
- Owner: Infrastructure

**TODO-041: Configure Lambda DLQ destinations**
- Complexity: S
- Priority: P0
- Description: Attach DLQs to all Lambda functions
- Dependencies: TODO-040
- Owner: Infrastructure

**TODO-042: Implement retry logic in Lambda functions**
- Complexity: M
- Priority: P0
- Description: Add exponential backoff for AWS API calls (Textract, DynamoDB, S3)
- Dependencies: TODO-027
- Owner: Backend

**TODO-043: Create custom CloudWatch metrics**
- Complexity: M
- Priority: P0
- Description: Implement metrics for brochures processed, keywords matched, errors
- Dependencies: TODO-007
- Owner: Backend

**TODO-044: Design CloudWatch dashboard**
- Complexity: M
- Priority: P1
- Description: Create dashboard with key metrics, error rates, pipeline health
- Dependencies: TODO-043
- Owner: DevOps

**TODO-045: Create CloudWatch alarms for critical failures**
- Complexity: M
- Priority: P0
- Description: Set up alarms for Lambda errors, DLQ messages, Textract throttling
- Dependencies: TODO-043
- Owner: DevOps

**TODO-046: Create ops alert SNS topic**
- Complexity: S
- Priority: P1
- Description: Configure SNS topic for operational alerts, subscribe ops team
- Dependencies: TODO-006
- Owner: Infrastructure

**TODO-047: Configure alarm notifications**
- Complexity: S
- Priority: P1
- Description: Connect CloudWatch alarms to ops alert topic
- Dependencies: TODO-045, TODO-046
- Owner: Infrastructure

---

#### Phase 2C: Production Deployment (Week 6)

**TODO-048: Request SES production access**
- Complexity: S
- Priority: P0
- Description: Submit AWS Support request with use case justification
- Dependencies: TODO-031
- Owner: Infrastructure

**TODO-049: Configure DKIM and SPF for sending domain**
- Complexity: M
- Priority: P0
- Description: Add DNS records for domain verification and authentication
- Dependencies: TODO-048
- Owner: Infrastructure

**TODO-050: Create production environment in IaC**
- Complexity: M
- Priority: P0
- Description: Duplicate dev configuration with prod-specific parameters
- Dependencies: TODO-030
- Owner: DevOps

**TODO-051: Set up CI/CD pipeline**
- Complexity: L
- Priority: P0
- Description: Create pipeline for build, test, deploy stages (dev → staging → prod)
- Dependencies: TODO-030
- Owner: DevOps

**TODO-052: Implement environment-specific configuration**
- Complexity: M
- Priority: P0
- Description: Parameterize bucket names, ARNs, email addresses per environment
- Dependencies: TODO-050
- Owner: DevOps

**TODO-053: Deploy to production environment**
- Complexity: M
- Priority: P0
- Description: Execute production deployment via CI/CD pipeline
- Dependencies: TODO-048, TODO-050, TODO-051
- Owner: DevOps

**TODO-054: Conduct production smoke tests**
- Complexity: M
- Priority: P0
- Description: Verify all components functional in prod, process test brochures
- Dependencies: TODO-053
- Owner: QA

**TODO-055: Set up production monitoring and alerting**
- Complexity: M
- Priority: P0
- Description: Verify all alarms and dashboards operational in prod
- Dependencies: TODO-053
- Owner: DevOps

---

### Milestone 3: Optimization & Scaling

#### Phase 3A: Cost Optimization (Week 7)

**TODO-056: Configure S3 lifecycle policies**
- Complexity: M
- Priority: P1
- Description: Implement transitions to Glacier and deletion rules
- Dependencies: TODO-053
- Owner: Infrastructure

**TODO-057: Enable DynamoDB TTL**
- Complexity: S
- Priority: P1
- Description: Configure TTL on brochure-metadata-table for auto-cleanup
- Dependencies: TODO-053
- Owner: Infrastructure

**TODO-058: Optimize Lambda memory allocations**
- Complexity: M
- Priority: P1
- Description: Test and adjust memory settings to balance cost and performance
- Dependencies: TODO-054
- Owner: DevOps

**TODO-059: Implement Textract cost controls**
- Complexity: M
- Priority: P1
- Description: Add page count limits, warn on large documents before processing
- Dependencies: TODO-042
- Owner: Backend

**TODO-060: Create cost tracking dashboard**
- Complexity: M
- Priority: P1
- Description: Dashboard showing daily costs by service (Textract, Lambda, S3)
- Dependencies: TODO-044
- Owner: DevOps

**TODO-061: Set up AWS Budget alerts**
- Complexity: S
- Priority: P1
- Description: Configure budget alerts for monthly spending thresholds
- Dependencies: None
- Owner: Finance/DevOps

---

#### Phase 3B: Performance & Scaling (Week 7)

**TODO-062: Configure Lambda reserved concurrency**
- Complexity: S
- Priority: P1
- Description: Set concurrency limits to respect Textract quotas
- Dependencies: TODO-053
- Owner: DevOps

**TODO-063: Implement enhanced deduplication with HTTP headers**
- Complexity: M
- Priority: P2
- Description: Check Last-Modified header before downloading brochures
- Dependencies: TODO-039
- Owner: Backend

**TODO-064: Optimize Textract result parsing**
- Complexity: M
- Priority: P2
- Description: Improve JSON parsing efficiency for large documents
- Dependencies: TODO-054
- Owner: Backend

**TODO-065: Add compression for Textract results**
- Complexity: S
- Priority: P2
- Description: Gzip JSON before storing in S3 to reduce storage costs
- Dependencies: TODO-013
- Owner: Backend

**TODO-066: Implement batch processing for multiple brochures**
- Complexity: L
- Priority: P2
- Description: Optimize for burst uploads (process multiple files efficiently)
- Dependencies: TODO-054
- Owner: Backend

---

#### Phase 3C: Load Testing & Validation (Week 8)

**TODO-067: Create load test scripts**
- Complexity: M
- Priority: P1
- Description: Scripts to upload 500+ brochures and measure system behavior
- Dependencies: TODO-025
- Owner: QA

**TODO-068: Execute load test (500 brochures)**
- Complexity: L
- Priority: P1
- Description: Run load test, monitor all metrics, identify bottlenecks
- Dependencies: TODO-067
- Owner: QA

**TODO-069: Analyze load test results**
- Complexity: M
- Priority: P1
- Description: Review CloudWatch metrics, identify issues, document findings
- Dependencies: TODO-068
- Owner: QA/DevOps

**TODO-070: Implement load test improvements**
- Complexity: M
- Priority: P1
- Description: Fix bottlenecks identified in load testing
- Dependencies: TODO-069
- Owner: Backend/DevOps

**TODO-071: Validate cost model against actual usage**
- Complexity: S
- Priority: P1
- Description: Compare estimated vs actual costs, adjust projections
- Dependencies: TODO-068
- Owner: Finance/DevOps

---

#### Phase 3D: Documentation & Handoff (Week 8)

**TODO-072: Write operational runbooks**
- Complexity: M
- Priority: P0
- Description: Document procedures for common failure scenarios and recovery
- Dependencies: TODO-055
- Owner: DevOps

**TODO-073: Create architecture documentation**
- Complexity: M
- Priority: P1
- Description: Architecture diagrams, component descriptions, data flows
- Dependencies: TODO-053
- Owner: Architect

**TODO-074: Document deployment procedures**
- Complexity: S
- Priority: P1
- Description: Step-by-step deployment guide, rollback procedures
- Dependencies: TODO-051
- Owner: DevOps

**TODO-075: Create configuration management guide**
- Complexity: S
- Priority: P1
- Description: How to add stores, update keywords, manage recipients
- Dependencies: TODO-053
- Owner: Backend

**TODO-076: Conduct knowledge transfer sessions**
- Complexity: M
- Priority: P0
- Description: Train operations team on system monitoring and troubleshooting
- Dependencies: TODO-072, TODO-073
- Owner: Team Lead

**TODO-077: Create production support checklist**
- Complexity: S
- Priority: P0
- Description: Checklist for ops team (monitoring, incident response, escalation)
- Dependencies: TODO-076
- Owner: DevOps

**TODO-078: Final production validation**
- Complexity: M
- Priority: P0
- Description: End-to-end production test with real stores and keywords
- Dependencies: TODO-070
- Owner: QA

---

## 3. Anticipated File Tree

```
brochure-scanner/
├── README.md
├── CHANGELOG.md
├── .gitignore
├── infra/
│   ├── sam-template.yaml                 # SAM template for all resources
│   ├── terraform/                        # Alternative: Terraform files
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   ├── lambda.tf
│   │   ├── s3.tf
│   │   ├── dynamodb.tf
│   │   ├── iam.tf
│   │   ├── cloudwatch.tf
│   │   └── environments/
│   │       ├── dev.tfvars
│   │       ├── staging.tfvars
│   │       └── prod.tfvars
│   ├── parameters/
│   │   ├── dev-params.json
│   │   ├── staging-params.json
│   │   └── prod-params.json
│   └── dashboards/
│       ├── overview-dashboard.json
│       └── operational-health-dashboard.json
├── lambdas/
│   ├── common/
│   │   ├── __init__.py
│   │   ├── logger.py                     # Structured logging utilities
│   │   ├── metrics.py                    # CloudWatch metrics helper
│   │   ├── aws_clients.py                # Shared AWS SDK clients
│   │   └── exceptions.py                 # Custom exception classes
│   ├── crawler/
│   │   ├── handler.py                    # CrawlerLambda entry point
│   │   ├── requirements.txt
│   │   ├── downloader.py                 # HTTP download logic
│   │   ├── hash_utils.py                 # SHA-256 hash computation
│   │   └── tests/
│   │       ├── test_handler.py
│   │       ├── test_downloader.py
│   │       └── fixtures/
│   ├── process_brochure/
│   │   ├── handler.py                    # ProcessBrochureLambda entry point
│   │   ├── requirements.txt
│   │   ├── file_inspector.py             # File type and size detection
│   │   ├── textract_sync.py              # Synchronous Textract calls
│   │   ├── textract_async.py             # Asynchronous Textract job submission
│   │   └── tests/
│   │       ├── test_handler.py
│   │       ├── test_file_inspector.py
│   │       └── fixtures/
│   │           ├── sample-1page.pdf
│   │           ├── sample-5page.pdf
│   │           └── sample-corrupted.pdf
│   ├── textract_callback/
│   │   ├── handler.py                    # TextractCallbackLambda entry point
│   │   ├── requirements.txt
│   │   ├── result_retriever.py           # GetDocumentTextDetection with pagination
│   │   └── tests/
│   │       ├── test_handler.py
│   │       └── test_result_retriever.py
│   ├── keyword_search/
│   │   ├── handler.py                    # KeywordSearchLambda entry point
│   │   ├── requirements.txt
│   │   ├── textract_parser.py            # Parse Textract JSON
│   │   ├── keyword_matcher.py            # Keyword matching engine
│   │   ├── config_loader.py              # Load keyword configuration
│   │   └── tests/
│   │       ├── test_handler.py
│   │       ├── test_keyword_matcher.py
│   │       └── fixtures/
│   │           └── sample-textract-result.json
│   └── layers/
│       └── python-dependencies/
│           └── requirements.txt          # Shared dependencies layer
├── config/
│   ├── keyword-config.json               # Sample keyword configuration
│   ├── keyword-config.schema.json        # JSON schema for validation
│   └── email-template.html               # Email notification template
├── tests/
│   ├── integration/
│   │   ├── test_end_to_end.py            # Full pipeline integration tests
│   │   ├── test_sync_flow.py             # Sync Textract flow
│   │   ├── test_async_flow.py            # Async Textract flow
│   │   └── test_crawler.py               # Scheduled crawling tests
│   ├── load/
│   │   ├── upload_brochures.py           # Script to upload multiple brochures
│   │   └── analyze_results.py            # Analyze load test metrics
│   └── fixtures/
│       ├── brochures/                    # Test brochure files
│       └── textract-responses/           # Mock Textract JSON responses
├── scripts/
│   ├── deploy.sh                         # Deployment wrapper script
│   ├── run-tests.sh                      # Test execution script
│   ├── validate-config.py                # Validate keyword-config.json
│   ├── cleanup-dev.sh                    # Clean up dev environment resources
│   └── seed-test-data.py                 # Populate test data in dev environment
├── docs/
│   ├── 01_TECHNICAL_SPEC.md              # Technical specification (from Step 1)
│   ├── 02_PROJECT_PLAN.md                # This document
│   ├── architecture/
│   │   ├── overview.md
│   │   ├── data-flows.md
│   │   └── diagrams/
│   ├── runbooks/
│   │   ├── incident-response.md
│   │   ├── common-failures.md
│   │   └── deployment-rollback.md
│   ├── operations/
│   │   ├── monitoring.md
│   │   ├── cost-optimization.md
│   │   └── scaling-guide.md
│   └── development/
│       ├── local-setup.md
│       ├── testing-guide.md
│       └── contributing.md
├── .github/                              # OR .gitlab/ depending on Git provider
│   └── workflows/
│       ├── ci.yml                        # Continuous integration pipeline
│       ├── deploy-dev.yml                # Deploy to dev environment
│       ├── deploy-staging.yml            # Deploy to staging
│       └── deploy-prod.yml               # Deploy to production
└── ci/
    ├── buildspec.yml                     # AWS CodeBuild spec (alternative to GitHub Actions)
    └── pipeline.yml                      # AWS CodePipeline definition
```

---

## 4. Module Boundaries & Responsibilities

### 4.1 Infrastructure Modules (infra/)

**SAM Template / Terraform Configuration**:
- Responsibility: Define all AWS resources declaratively
- Resources managed:
  - S3 buckets with policies and lifecycle rules
  - DynamoDB tables with GSIs
  - Lambda functions with configurations
  - IAM roles and policies
  - SNS topics and subscriptions
  - EventBridge rules
  - CloudWatch alarms and dashboards
- Inputs: Environment parameters (dev/staging/prod)
- Outputs: Resource ARNs, bucket names, table names

**Parameter Files**:
- Responsibility: Environment-specific configuration values
- Contains: Bucket names, schedule expressions, email addresses, memory allocations
- Versioned in Git for traceability

**Dashboard Definitions**:
- Responsibility: CloudWatch dashboard JSON exports
- Deployed via IaC or imported manually
- Enables version control of monitoring setup

---

### 4.2 Lambda Function Modules (lambdas/)

**Common Module** (lambdas/common/):
- Responsibility: Shared utilities and helpers for all Lambda functions
- Components:
  - logger.py: Structured JSON logging with correlation IDs
  - metrics.py: CloudWatch PutMetricData wrapper for custom metrics
  - aws_clients.py: Singleton AWS SDK clients (S3, DynamoDB, Textract, SNS)
  - exceptions.py: Custom exceptions (DuplicateBrochureError, TextractThrottlingError, etc.)
- Used by: All Lambda functions
- Dependencies: AWS SDK (boto3), logging

**CrawlerLambda** (lambdas/crawler/):
- Responsibility: Download brochures from URLs and upload to S3
- Entry point: handler.lambda_handler(event, context)
- Event input: EventBridge scheduled event with store configuration
- Key functions:
  - download_brochure(url): HTTP GET with retry logic
  - compute_hash(file_bytes): SHA-256 hash computation
  - check_duplicate(hash): Query DynamoDB hash-index
  - upload_to_s3(file_bytes, s3_key): Upload with metadata
- Outputs: S3 PutObject, DynamoDB PutItem
- Error handling: Log and continue for individual store failures, send to DLQ for Lambda-level failures

**ProcessBrochureLambda** (lambdas/process_brochure/):
- Responsibility: Orchestrate Textract processing based on file characteristics
- Entry point: handler.lambda_handler(event, context)
- Event input: S3 PUT event notification
- Key functions:
  - inspect_file(s3_bucket, s3_key): Determine file type, size, page count
  - process_sync(file_bytes): Call Textract DetectDocumentText, store result
  - process_async(s3_bucket, s3_key): Call Textract StartDocumentTextDetection
  - update_metadata(brochure_id, status): DynamoDB UpdateItem
- Outputs: Textract API calls, S3 PutObject (sync flow), DynamoDB UpdateItem
- Error handling: Retry on throttling, send unsupported formats to ops alert

**TextractCallbackLambda** (lambdas/textract_callback/):
- Responsibility: Retrieve async Textract results and store to S3
- Entry point: handler.lambda_handler(event, context)
- Event input: SNS message from textract-job-completion-topic
- Key functions:
  - parse_sns_message(event): Extract job_id and status
  - retrieve_results(job_id): Call GetDocumentTextDetection with pagination
  - aggregate_pages(results): Combine paginated responses
  - store_results(s3_bucket, s3_key, json_data): S3 PutObject
- Outputs: S3 PutObject, DynamoDB UpdateItem
- Error handling: Handle job failures, retry on API throttling

**KeywordSearchLambda** (lambdas/keyword_search/):
- Responsibility: Parse Textract results, match keywords, trigger notifications
- Entry point: handler.lambda_handler(event, context)
- Event input: S3 PUT event notification (textract-output-bucket)
- Key functions:
  - load_textract_result(s3_bucket, s3_key): Download and parse JSON
  - load_keyword_config(store_id): Get keywords for specific store
  - search_keywords(text_blocks, keywords): Find all matches with context
  - publish_notification(matches): Send to SNS
  - store_matches(brochure_id, matches): DynamoDB PutItem
- Outputs: SNS Publish, DynamoDB UpdateItem
- Error handling: Validate Textract JSON schema, handle missing config gracefully

---

### 4.3 Configuration Module (config/)

**keyword-config.json**:
- Responsibility: Define stores, brochure URLs, keywords, and recipients
- Format: JSON with schema validation
- Deployment: Uploaded to S3 or stored in DynamoDB
- Updates: Manual edits followed by S3 upload, no Lambda restart needed

**Email Template**:
- Responsibility: Define notification email format
- Contains: HTML structure with placeholders for dynamic content
- Used by: SES (via SNS email subscription or Lambda direct send)

---

### 4.4 Testing Modules (tests/)

**Integration Tests** (tests/integration/):
- Responsibility: Validate end-to-end workflows in deployed environment
- Approach: Upload real test files to S3, verify DynamoDB records and email delivery
- Environment: Dev or staging only (not production)
- Execution: CI/CD pipeline after deployment, or manual via script

**Load Tests** (tests/load/):
- Responsibility: Validate system performance under high volume
- Approach: Programmatically upload hundreds of brochures, measure latency and error rates
- Tools: Python scripts using boto3, or AWS-native tools (Step Functions, Distributed Load Testing)
- Metrics: Collected via CloudWatch, analyzed post-test

**Fixtures** (tests/fixtures/):
- Responsibility: Provide consistent test data
- Contents: Sample PDFs, images, Textract JSON responses, SNS event payloads
- Usage: Unit tests and integration tests

---

### 4.5 Documentation Module (docs/)

**Technical Documentation** (docs/architecture/, docs/operations/):
- Responsibility: Maintain system knowledge base
- Audience: Developers, DevOps, operations team
- Updates: Versioned with code, updated during development

**Runbooks** (docs/runbooks/):
- Responsibility: Operational procedures for incident response
- Format: Step-by-step instructions with commands and expected outputs
- Validation: Test during runbook drills or real incidents

---

### 4.6 CI/CD Module (ci/, .github/workflows/)

**CI Pipeline**:
- Responsibility: Build, lint, test on every commit
- Stages: Checkout code, install dependencies, run linters, run unit tests, package Lambdas
- Triggers: Push to any branch, pull request

**CD Pipeline**:
- Responsibility: Deploy to environments sequentially
- Stages: Deploy to dev (automatic), run integration tests, deploy to staging (automatic), manual approval, deploy to prod
- Triggers: Merge to main branch (or environment-specific branches)

---

## 5. Interface & Contract Descriptions

### 5.1 Lambda Event Contracts

#### CrawlerLambda Input (EventBridge)

**Event structure**:
```
{
  "version": "0",
  "id": "event-id",
  "detail-type": "Scheduled Event",
  "source": "aws.events",
  "account": "123456789012",
  "time": "2025-11-18T10:00:00Z",
  "region": "us-east-1",
  "resources": ["arn:aws:events:us-east-1:123456789012:rule/scan-schedule-rule"],
  "detail": {
    "stores": [
      {
        "store_id": "walmart",
        "store_name": "Walmart",
        "brochure_url": "https://www.walmart.com/weekly-ad.pdf"
      }
    ]
  }
}
```

**Handler output**: None (async operation, success/failure logged)

---

#### ProcessBrochureLambda Input (S3 Event)

**Event structure**:
```
{
  "Records": [
    {
      "eventVersion": "2.1",
      "eventSource": "aws:s3",
      "eventName": "ObjectCreated:Put",
      "s3": {
        "bucket": {
          "name": "brochures-source-prod-123456789012"
        },
        "object": {
          "key": "walmart/2025/11/18/weekly-ad-2025-11-18.pdf",
          "size": 2048576
        }
      }
    }
  ]
}
```

**Handler output**: None (async operation, results stored in S3/DynamoDB)

---

#### TextractCallbackLambda Input (SNS)

**Event structure**:
```
{
  "Records": [
    {
      "EventSource": "aws:sns",
      "Sns": {
        "Message": "{\"JobId\": \"abc123def456\", \"Status\": \"SUCCEEDED\", \"Timestamp\": \"2025-11-18T10:05:00Z\", \"DocumentLocation\": {\"S3ObjectName\": \"walmart/2025/11/18/weekly-ad-2025-11-18.pdf\", \"S3Bucket\": \"brochures-source-prod-123456789012\"}}"
      }
    }
  ]
}
```

**Message payload** (JSON string in Sns.Message):
```
{
  "JobId": "abc123def456",
  "Status": "SUCCEEDED",
  "Timestamp": "2025-11-18T10:05:00Z",
  "DocumentLocation": {
    "S3ObjectName": "walmart/2025/11/18/weekly-ad-2025-11-18.pdf",
    "S3Bucket": "brochures-source-prod-123456789012"
  }
}
```

**Handler output**: None (stores results to S3, updates DynamoDB)

---

#### KeywordSearchLambda Input (S3 Event)

**Event structure**: Same as ProcessBrochureLambda (S3 PUT event), but for textract-output-bucket

**Handler output**: None (publishes to SNS, updates DynamoDB)

---

### 5.2 SNS Message Contracts

#### keyword-found-topic Message

**Message structure** (JSON):
```
{
  "brochure_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "store_id": "walmart",
  "store_name": "Walmart",
  "brochure_filename": "weekly-ad-2025-11-18.pdf",
  "s3_bucket": "brochures-source-prod-123456789012",
  "s3_key": "walmart/2025/11/18/weekly-ad-2025-11-18.pdf",
  "upload_time": "2025-11-18T10:00:00Z",
  "ocr_complete_time": "2025-11-18T10:05:00Z",
  "notification_time": "2025-11-18T10:05:30Z",
  "keywords_matched": ["organic", "sale"],
  "match_count": 5,
  "match_details": [
    {
      "keyword": "organic",
      "page": 1,
      "line": 12,
      "context": "...fresh organic produce on sale this week only...",
      "confidence": 99.8
    },
    {
      "keyword": "sale",
      "page": 1,
      "line": 12,
      "context": "...fresh organic produce on sale this week only...",
      "confidence": 99.8
    },
    {
      "keyword": "organic",
      "page": 3,
      "line": 45,
      "context": "...certified organic milk, now available...",
      "confidence": 98.5
    }
  ]
}
```

**Subject line** (for email subscription): "Keyword Match Found: {store_name} - {brochure_filename}"

---

### 5.3 DynamoDB Item Structure

**brochure-metadata-table item** (example):
```
{
  "brochure_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "store_id": "walmart",
  "store_name": "Walmart",
  "brochure_filename": "weekly-ad-2025-11-18.pdf",
  "s3_bucket": "brochures-source-prod-123456789012",
  "s3_key": "walmart/2025/11/18/weekly-ad-2025-11-18.pdf",
  "file_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "file_size_bytes": 2048576,
  "upload_time": "2025-11-18T10:00:00Z",
  "status": "MATCH_FOUND",
  "textract_job_id": "abc123def456",
  "textract_mode": "ASYNC",
  "textract_result_s3_key": "walmart/2025/11/18/a1b2c3d4-e5f6-7890-abcd-ef1234567890/textract-result.json",
  "page_count": 10,
  "ocr_complete_time": "2025-11-18T10:05:00Z",
  "keywords_matched": ["organic", "sale"],
  "match_count": 5,
  "match_details": [
    {
      "keyword": "organic",
      "page": 1,
      "line": 12,
      "context": "...fresh organic produce on sale this week only...",
      "confidence": 99.8
    }
  ],
  "notification_sent": true,
  "notification_time": "2025-11-18T10:05:30Z",
  "created_at": "2025-11-18T10:00:00Z",
  "updated_at": "2025-11-18T10:05:30Z",
  "ttl_timestamp": 1763030400
}
```

---

### 5.4 S3 Key Patterns

**brochures-source-bucket**:
- Pattern: `{store_id}/{YYYY}/{MM}/{DD}/{filename}.{ext}`
- Example: `walmart/2025/11/18/weekly-ad-2025-11-18.pdf`
- Constraints: store_id alphanumeric + hyphens, filename preserves original

**textract-output-bucket**:
- Pattern: `{store_id}/{YYYY}/{MM}/{DD}/{brochure_id}/textract-result.json`
- Example: `walmart/2025/11/18/a1b2c3d4-e5f6-7890-abcd-ef1234567890/textract-result.json`
- Constraints: brochure_id is UUID v4

**config bucket** (if separate):
- Pattern: `config/keyword-config.json`
- Versioning: Optional S3 versioning enabled for rollback

---

### 5.5 Textract JSON Structure (Subset)

**Synchronous DetectDocumentText response**:
```
{
  "Blocks": [
    {
      "BlockType": "PAGE",
      "Id": "page-1",
      "Page": 1,
      "Geometry": {...}
    },
    {
      "BlockType": "LINE",
      "Id": "line-1",
      "Text": "Fresh organic produce on sale this week only",
      "Confidence": 99.8,
      "Page": 1,
      "Geometry": {...}
    },
    {
      "BlockType": "WORD",
      "Id": "word-1",
      "Text": "Fresh",
      "Confidence": 99.9,
      "Page": 1,
      "Geometry": {...}
    }
  ],
  "DocumentMetadata": {
    "Pages": 1
  }
}
```

**KeywordSearchLambda consumes**: Blocks where BlockType = LINE or WORD, extracts Text and Page fields

---

## 6. Environments & Deployment Plan

### 6.1 Environment Definitions

#### Development Environment (dev)
- **Purpose**: Feature development, unit testing, integration testing
- **Deployment**: Automated on every commit to dev branch
- **Data**: Test data only, mock store configurations
- **SES**: Sandbox mode, verified test emails only
- **Cost controls**: Aggressive (low Lambda memory, fast lifecycle transitions)
- **Monitoring**: Basic CloudWatch Logs, no alarms
- **Access**: All engineers

#### Staging Environment (staging)
- **Purpose**: Pre-production validation, load testing, UAT
- **Deployment**: Automated on merge to staging branch, manual approval gate
- **Data**: Production-like test data, real store URLs (if available)
- **SES**: Sandbox or production access with test recipients
- **Cost controls**: Production-like settings
- **Monitoring**: Full dashboards and alarms (same as prod)
- **Access**: QA team, DevOps, select engineers

#### Production Environment (prod)
- **Purpose**: Live operations
- **Deployment**: Automated on merge to main branch, requires manual approval
- **Data**: Real stores, real brochures, real recipients
- **SES**: Production access, verified domain
- **Cost controls**: Optimized for balance of cost and performance
- **Monitoring**: Full dashboards, alarms, on-call rotation
- **Access**: DevOps, operations team (read-only for most engineers)

---

### 6.2 Deployment Workflow

**Standard deployment sequence**:

1. **Developer workflow**:
   - Create feature branch from main
   - Develop and commit changes
   - Run local tests (unit tests)
   - Push to remote, create pull request

2. **CI pipeline** (triggered on PR):
   - Checkout code
   - Install dependencies
   - Run linters (pylint, flake8)
   - Run unit tests
   - Package Lambda functions
   - Validate IaC templates
   - Report results to PR

3. **Merge to dev branch** (automatic deployment):
   - CI pipeline runs again
   - Deploy to dev environment via IaC
   - Run integration tests in dev
   - Report deployment status

4. **Promotion to staging** (manual or automatic):
   - Merge dev to staging branch (or tag release)
   - Deploy to staging environment
   - Run load tests and UAT
   - Manual QA approval

5. **Promotion to production** (manual approval required):
   - Merge staging to main (or promote tag)
   - Manual approval in CI/CD tool
   - Deploy to production
   - Run production smoke tests
   - Monitor CloudWatch metrics for 30 minutes
   - Rollback if errors spike

---

### 6.3 Secrets Management

**Secrets to manage**:
- SES SMTP credentials (if using SMTP, not SES API)
- API keys for store brochure download (if required)
- Notification webhook URLs (future: Slack, Teams)

**Approach**:
- **AWS Secrets Manager**: Store all secrets
- **Lambda environment variables**: Reference secret ARNs, not values
- **IAM permissions**: Grant Lambda secretsmanager:GetSecretValue
- **Secret retrieval**: Lambda init code retrieves and caches for function lifetime
- **Rotation**: Manual rotation annually, automatic rotation via Lambda if AWS supports

**Example secret structure** (in Secrets Manager):
```
{
  "ses_smtp_username": "AKIAIOSFODNN7EXAMPLE",
  "ses_smtp_password": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
  "store_api_keys": {
    "walmart": "api-key-12345",
    "target": "api-key-67890"
  }
}
```

---

### 6.4 SES Verification Steps

**Sandbox mode** (dev/staging):
1. Verify sender email: noreply@example.com via SES console
2. Verify each test recipient email individually
3. Send test email to confirm delivery
4. Note: 200 emails/day limit, 1 email/second

**Production access request**:
1. Navigate to SES → Account Dashboard → Request Production Access
2. Provide use case: "Automated retail brochure keyword monitoring system for internal alerts"
3. Request daily sending quota: 10,000 emails/day
4. Request sending rate: 10 emails/second
5. Describe bounce/complaint handling: "Automated suppression via SES configuration set"
6. Submit and wait for AWS approval (typically 24-48 hours)

**Domain verification** (production):
1. Add TXT record to DNS: _amazonses.example.com with verification token
2. Wait for DNS propagation (up to 72 hours)
3. SES verifies domain ownership
4. Add DKIM CNAME records (3 records provided by SES)
5. Add SPF TXT record: "v=spf1 include:amazonses.com ~all"
6. Verify DKIM and SPF status in SES console

---

### 6.5 Configuration Management

**Keyword configuration updates**:
- Edit keyword-config.json in Git repository
- Validate schema using scripts/validate-config.py
- Commit and merge to appropriate branch
- CI/CD pipeline uploads to S3 during deployment
- Lambda functions reload config on next invocation (no restart needed)

**Store additions**:
- Add new store object to keyword-config.json
- Include store_id, name, brochure_url, keywords, recipients
- Deploy via CI/CD
- Test with manual brochure upload or scheduled crawl

**Recipient email changes**:
- Update recipients array in keyword-config.json for specific store
- If SES sandbox: Verify new email addresses in SES console first
- Deploy configuration update
- Test with sample keyword match

---

## 7. QA and Release Checklist

### 7.1 Pre-Deployment Checklist

**Infrastructure**:
- [ ] All IaC templates validated (SAM validate or Terraform plan)
- [ ] Environment parameters configured correctly (dev/staging/prod)
- [ ] S3 bucket names unique and available
- [ ] DynamoDB table names unique
- [ ] IAM roles have least-privilege permissions
- [ ] CloudWatch Logs retention set appropriately
- [ ] CloudWatch alarms configured and tested
- [ ] SNS topics and subscriptions verified

**Lambda Functions**:
- [ ] All unit tests passing (> 90% code coverage)
- [ ] Dependencies packaged correctly (requirements.txt up-to-date)
- [ ] Environment variables configured per environment
- [ ] Memory and timeout settings optimized
- [ ] Reserved concurrency limits set
- [ ] DLQ configured for each function

**Configuration**:
- [ ] keyword-config.json validated against schema
- [ ] SES sender email verified
- [ ] SES recipient emails verified (sandbox) or domain verified (production)
- [ ] DKIM and SPF DNS records configured
- [ ] Test brochures prepared and uploaded to test fixtures

**Testing**:
- [ ] Integration tests passing in dev environment
- [ ] End-to-end test with sample brochure successful
- [ ] Email notification received and formatted correctly
- [ ] DynamoDB records populated accurately
- [ ] CloudWatch Logs show expected log entries

---

### 7.2 Deployment Checklist

**Pre-Deployment**:
- [ ] Deployment scheduled during low-traffic window (if production)
- [ ] On-call engineer notified and available
- [ ] Rollback plan documented and tested
- [ ] Backup of current production state (DynamoDB, S3 if needed)

**During Deployment**:
- [ ] CI/CD pipeline executes successfully
- [ ] All CloudFormation/Terraform stacks reach CREATE_COMPLETE or UPDATE_COMPLETE
- [ ] Smoke tests pass in target environment
- [ ] CloudWatch Logs show Lambda functions initializing correctly
- [ ] No errors in CloudWatch Logs during initial invocations

**Post-Deployment**:
- [ ] Monitor CloudWatch metrics for 30 minutes
- [ ] Verify no alarms triggered
- [ ] Test end-to-end flow with sample brochure
- [ ] Confirm email notification delivery
- [ ] Review DynamoDB for correct metadata
- [ ] Check cost estimate vs. actual usage (after 24 hours)

---

### 7.3 Production Release Checklist

**Before go-live**:
- [ ] SES production access granted
- [ ] Domain verification complete (DKIM, SPF)
- [ ] All production email recipients configured
- [ ] keyword-config.json updated with real store URLs
- [ ] Load test completed successfully (500+ brochures)
- [ ] Cost model validated against actual staging usage
- [ ] Operations team trained on monitoring and runbooks
- [ ] Incident response plan documented and reviewed
- [ ] On-call rotation established

**Go-live**:
- [ ] Deploy to production environment
- [ ] Run production smoke tests
- [ ] Trigger manual crawl for 1-2 stores to validate
- [ ] Monitor for 24 hours with active alerting
- [ ] Review first batch of keyword matches for accuracy
- [ ] Collect feedback from email recipients

**Post-launch**:
- [ ] Monitor costs daily for first week
- [ ] Review CloudWatch dashboards for anomalies
- [ ] Conduct retrospective with team
- [ ] Document lessons learned
- [ ] Plan next iteration improvements

---

### 7.4 Acceptance Criteria Summary

**MVP acceptance** (Milestone 1):
- [ ] Manually upload 10 brochures, 100% processed successfully
- [ ] Keyword matches detected with < 1% false negative rate
- [ ] Email notifications delivered within 10 minutes (sync flow) or 60 minutes (async flow)
- [ ] DynamoDB metadata accurate for all brochures
- [ ] No critical errors in CloudWatch Logs
- [ ] CloudWatch dashboards populated with metrics

**Automation acceptance** (Milestone 2):
- [ ] Scheduled crawl retrieves brochures from 5 stores automatically
- [ ] Deduplication prevents reprocessing of identical files
- [ ] DLQ remains empty under normal operations
- [ ] All alarms functional and tested (manual trigger)
- [ ] Production environment deployed and operational
- [ ] SES production access active

**Scaling acceptance** (Milestone 3):
- [ ] Load test with 500 brochures completes with < 1% error rate
- [ ] End-to-end latency p95 < 30 minutes
- [ ] Monthly cost within 10% of estimate
- [ ] S3 lifecycle policies active and working
- [ ] Runbooks tested during simulated incidents
- [ ] Knowledge transfer to operations team complete

---

## 8. Risk Register & Mitigation

### 8.1 Technical Risks

**Risk: Textract throttling under high load**
- **Likelihood**: Medium
- **Impact**: High (processing delays, failed jobs)
- **Mitigation**: Reserved concurrency limits, exponential backoff, request quota increase
- **Owner**: Backend/DevOps

**Risk: SES sandbox limitations block testing**
- **Likelihood**: High (initially)
- **Impact**: Medium (delays testing)
- **Mitigation**: Verify all test emails early, request production access in parallel
- **Owner**: Infrastructure

**Risk: Cost overruns from large documents**
- **Likelihood**: Medium
- **Impact**: High (budget exceeded)
- **Mitigation**: Page count limits, cost alerts, pre-processing validation
- **Owner**: DevOps/Finance

---

### 8.2 Operational Risks

**Risk: Store URLs change frequently**
- **Likelihood**: Medium
- **Impact**: Medium (missed brochures)
- **Mitigation**: Alarms on crawl failures, periodic URL validation, store relationships
- **Owner**: Operations

**Risk: False positives/negatives in keyword matching**
- **Likelihood**: Medium
- **Impact**: Medium (missed opportunities or alert fatigue)
- **Mitigation**: Whole-word matching, configurable keywords, feedback loop from users
- **Owner**: Product/Backend

**Risk: Email deliverability issues (bounces, spam)**
- **Likelihood**: Low
- **Impact**: High (notifications not received)
- **Mitigation**: DKIM/SPF configuration, bounce monitoring, suppression list management
- **Owner**: Infrastructure

---

### 8.3 Schedule Risks

**Risk: SES production access delayed**
- **Likelihood**: Medium
- **Impact**: High (blocks production launch)
- **Mitigation**: Request early (during Milestone 1), use staging for validation meanwhile
- **Owner**: Infrastructure/PM

**Risk: Integration issues between components**
- **Likelihood**: Medium
- **Impact**: Medium (delays testing)
- **Mitigation**: Contract-based development, early integration testing, mocking
- **Owner**: Backend

---

## 9. Success Metrics

### 9.1 Development Metrics
- Code coverage > 90%
- All lint checks passing
- Zero critical security vulnerabilities (Snyk, Dependabot scans)
- PR review turnaround < 24 hours

### 9.2 Operational Metrics
- System uptime > 99.5%
- P95 end-to-end latency < 30 minutes
- Error rate < 1%
- Email delivery rate > 99%
- Monthly cost within budget ($50 for 300 brochures)

### 9.3 Business Metrics
- Number of stores monitored
- Brochures processed per day
- Keyword match rate (target 15-20%)
- Average matches per brochure
- User satisfaction with notifications (qualitative feedback)

---

**End of Project Plan**
