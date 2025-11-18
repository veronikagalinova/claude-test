# Technical Specification: Serverless Brochure Keyword Scanner

## 1. System Overview & Goals

### 1.1 Features
- Automated ingestion of retail brochures from multiple sources (manual S3 upload, scheduled URL crawling)
- OCR processing using AWS Textract with intelligent selection between synchronous and asynchronous APIs
- Keyword detection across extracted text with configurable keyword lists per store
- Email notifications via Amazon SES when keywords are detected, including match context and metadata
- Deduplication to prevent reprocessing unchanged brochures
- Audit trail of all scans and keyword matches
- Support for multi-page PDFs and image-based brochures (PNG, JPEG, TIFF)
- Configurable scheduling for periodic brochure fetching
- Multi-store support with independent configuration per retailer

### 1.2 Non-Functional Requirements
- **Availability**: 99.5% uptime (relies on AWS service SLAs for S3, Lambda, Textract)
- **Latency**: Keyword match notifications delivered within 2 hours of brochure availability for typical workloads
- **RPO**: 24 hours (acceptable to re-scan last day's brochures if state is lost)
- **RTO**: 4 hours (time to restore service after catastrophic failure)
- **Scalability**: Handle 100-500 brochures per day across 20-50 stores without manual intervention
- **Cost**: Target under $200/month for 300 brochures/month (10 pages average, 50 keyword matches)
- **Security**: Least-privilege IAM, encryption at rest, restricted SES sending, no public endpoints
- **Observability**: CloudWatch metrics and logs with 90-day retention, alerting on failures

---

## 2. Architecture Diagram (Textual)

### 2.1 Component Map
```
[EventBridge Schedule: scan-schedule-rule]
        |
        v
[Lambda: CrawlerLambda] -----> [S3: brochures-source-bucket]
                                        |
                                        | (S3 Event Notification on PUT)
                                        v
                              [Lambda: ProcessBrochureLambda]
                                        |
                    +-------------------+-------------------+
                    |                                       |
                    v                                       v
          [Textract Sync API]                    [Textract Async API]
          (small files < 5 pages)                (large files >= 5 pages)
                    |                                       |
                    |                                       v
                    |                            [SNS: textract-job-completion-topic]
                    |                                       |
                    |                                       v
                    |                            [Lambda: TextractCallbackLambda]
                    |                                       |
                    +-------------------+-------------------+
                                        |
                                        v
                              [S3: textract-output-bucket]
                              (Textract JSON results)
                                        |
                                        | (S3 Event Notification on PUT)
                                        v
                              [Lambda: KeywordSearchLambda]
                                        |
                                        | (on keyword match)
                                        v
                              [SNS: keyword-found-topic]
                                        |
                                        v
                              [SES: Email Notification]

[DynamoDB: brochure-metadata-table] <--- Updated by all Lambda functions
                (stores: brochure status, match history, deduplication hashes)
```

### 2.2 Event Flow Summary
1. EventBridge triggers CrawlerLambda on schedule (daily/weekly)
2. CrawlerLambda downloads brochures from configured URLs, uploads to brochures-source-bucket
3. S3 PUT event triggers ProcessBrochureLambda
4. ProcessBrochureLambda inspects file size/page count and chooses Textract API:
   - Synchronous for small files (< 5 pages, < 5MB)
   - Asynchronous for large files
5. Textract async jobs notify via SNS when complete
6. TextractCallbackLambda retrieves results and stores in textract-output-bucket
7. S3 PUT event on textract-output-bucket triggers KeywordSearchLambda
8. KeywordSearchLambda parses JSON, searches for keywords, publishes to keyword-found-topic
9. SNS delivers to SES subscription for email notification
10. All stages update DynamoDB with status and metadata

### 2.3 S3 Key Naming Conventions
- **brochures-source-bucket**: `{store_id}/{year}/{month}/{day}/{brochure_filename}.{ext}`
  - Example: `walmart/2025/11/18/weekly-ad-2025-11-18.pdf`
- **textract-output-bucket**: `{store_id}/{year}/{month}/{day}/{brochure_id}/textract-result.json`
  - Example: `walmart/2025/11/18/abc123def456/textract-result.json`
- **Configuration file**: `config/keyword-config.json` (stored in brochures-source-bucket or separate config bucket)

---

## 3. Components and Responsibilities

### 3.1 S3: brochures-source-bucket

**Purpose**: Primary landing zone for all brochure files (PDFs and images).

**Responsibilities**:
- Store raw brochure files uploaded manually or by CrawlerLambda
- Trigger ProcessBrochureLambda on PUT events via S3 Event Notifications
- Maintain lifecycle rules to transition old brochures to Glacier after 90 days
- Store configuration file for keyword lists and store metadata

**Configuration**:
- Bucket name: `brochures-source-{environment}-{account_id}` (e.g., `brochures-source-prod-123456789012`)
- Region: us-east-1 (or closest to Textract availability)
- Encryption: SSE-S3 (default S3-managed encryption)
- Versioning: Disabled (not required; deduplication handled via hash)
- Object lock: Disabled
- Event notifications: Send `s3:ObjectCreated:*` events to ProcessBrochureLambda
- Lifecycle policy: Move to Glacier-IR after 90 days, delete after 2 years

**Access patterns**:
- CrawlerLambda: PUT objects, GET config file
- ProcessBrochureLambda: GET objects
- Manual upload: PUT objects via AWS Console, CLI, or pre-signed URLs

**Failure modes**:
- Upload fails: Retry at source (crawler or manual)
- Corrupted files: ProcessBrochureLambda validates and logs error, sends to DLQ
- Missing config file: ProcessBrochureLambda falls back to default keywords or fails gracefully with alert

**Monitoring**:
- CloudWatch metric: NumberOfObjects, BucketSizeBytes
- Alarm: BucketSizeBytes > 100 GB (cost control)

---

### 3.2 S3: textract-output-bucket

**Purpose**: Store Textract OCR results as JSON for keyword searching.

**Responsibilities**:
- Receive Textract result JSON from TextractCallbackLambda (async flow) or ProcessBrochureLambda (sync flow)
- Trigger KeywordSearchLambda on PUT events
- Retain results for audit and re-processing

**Configuration**:
- Bucket name: `textract-output-{environment}-{account_id}`
- Region: Same as brochures-source-bucket
- Encryption: SSE-S3
- Versioning: Disabled
- Event notifications: Send `s3:ObjectCreated:*` events to KeywordSearchLambda
- Lifecycle policy: Move to Glacier-IR after 180 days, delete after 3 years

**Access patterns**:
- ProcessBrochureLambda (sync flow): PUT JSON results
- TextractCallbackLambda (async flow): PUT JSON results
- KeywordSearchLambda: GET JSON results

**Failure modes**:
- Write fails: Lambda retries with exponential backoff (2 retries), sends to DLQ
- Malformed JSON: KeywordSearchLambda validates schema and logs error

**Monitoring**:
- CloudWatch metric: NumberOfObjects, BucketSizeBytes
- Alarm: BucketSizeBytes > 50 GB

---

### 3.3 EventBridge: scan-schedule-rule

**Purpose**: Trigger scheduled crawling of brochure URLs.

**Responsibilities**:
- Fire at configured intervals (daily, weekly, or cron-based)
- Invoke CrawlerLambda with event payload containing store list
- Support multiple schedules for different store groups (e.g., weekly for Store A, daily for Store B)

**Configuration**:
- Rule name: `scan-schedule-rule-{environment}`
- Schedule expression examples:
  - Daily: `cron(0 10 * * ? *)` (10 AM UTC daily)
  - Weekly: `cron(0 10 ? * SUN *)` (10 AM UTC every Sunday)
- Target: CrawlerLambda with constant JSON input containing store metadata

**Event payload format**:
- JSON object with `stores` array containing `{store_id, name, brochure_url, keywords[]}`

**Failure modes**:
- CrawlerLambda fails: EventBridge does not retry; rely on Lambda DLQ and CloudWatch alarms
- Schedule misconfiguration: Test in non-prod environment first

**Monitoring**:
- CloudWatch metric: Invocations, FailedInvocations
- Alarm: FailedInvocations > 0

---

### 3.4 Lambda: CrawlerLambda

**Purpose**: Download brochures from store URLs and upload to brochures-source-bucket.

**Responsibilities**:
- Parse EventBridge event for store list
- For each store:
  - Fetch brochure from URL (HTTP/HTTPS GET)
  - Validate file type (PDF, PNG, JPEG, TIFF)
  - Compute SHA-256 hash for deduplication
  - Check DynamoDB for existing hash (skip if duplicate)
  - Upload to brochures-source-bucket with proper S3 key naming
  - Record metadata in DynamoDB (store_id, upload_time, source_url, file_hash, status=UPLOADED)
- Handle HTTP errors (404, 500) gracefully and log failures
- Support retry with exponential backoff for transient network errors
- Respect robots.txt if scraping public websites

**Configuration**:
- Function name: `CrawlerLambda-{environment}`
- Runtime: Python 3.12 or Node.js 20.x
- Memory: 512 MB
- Timeout: 300 seconds (5 minutes)
- Environment variables:
  - `SOURCE_BUCKET_NAME`: brochures-source-bucket name
  - `METADATA_TABLE_NAME`: DynamoDB table name
  - `STORE_CONFIG_S3_KEY`: S3 key for store configuration (optional, can use event payload)
- Layers: None (use SDK built-ins)
- Reserved concurrency: 5 (limit concurrent downloads to avoid overwhelming upstream servers)

**IAM permissions (high-level)**:
- s3:PutObject on brochures-source-bucket
- s3:GetObject on config bucket (if separate)
- dynamodb:Query, dynamodb:PutItem on brochure-metadata-table
- logs:CreateLogGroup, logs:CreateLogStream, logs:PutLogEvents

**Failure modes**:
- Network timeout fetching URL: Retry 3 times with exponential backoff, then log failure and send to DLQ
- Invalid file type: Log error, skip file, record in DynamoDB as status=INVALID_FORMAT
- S3 upload fails: Retry 2 times, send to DLQ
- DynamoDB write fails: Retry 2 times, send to DLQ

**Monitoring**:
- CloudWatch metric: Invocations, Errors, Duration, Throttles
- Custom metric: BrochuresDownloaded, BrochuresFailed, DuplicatesSkipped
- Alarm: Errors > 0, Throttles > 0
- Logs: Structured JSON with store_id, url, status, error_message

**Testing approach**:
- Unit tests: Mock HTTP client, S3 client, DynamoDB client
- Integration tests: Use localstack or real S3/DynamoDB with test fixtures
- Test cases: successful download, 404 error, network timeout, duplicate hash, malformed URL

---

### 3.5 Lambda: ProcessBrochureLambda

**Purpose**: Orchestrate Textract processing for uploaded brochures.

**Responsibilities**:
- Triggered by S3 PUT events on brochures-source-bucket
- Parse S3 event to extract bucket and key
- Retrieve file metadata (size, content-type)
- Determine Textract processing strategy:
  - **Synchronous API** if file is single-page image (PNG, JPEG, TIFF) or PDF < 5 pages AND < 5 MB
  - **Asynchronous API** if multi-page PDF or file >= 5 MB
- For synchronous flow:
  - Call Textract DetectDocumentText synchronously
  - Parse response and write JSON to textract-output-bucket immediately
- For asynchronous flow:
  - Call Textract StartDocumentTextDetection with SNS topic for completion notification
  - Store job ID and metadata in DynamoDB (status=TEXTRACT_IN_PROGRESS)
- Handle Textract API throttling (exponential backoff, max 3 retries)
- Update DynamoDB with processing status

**Configuration**:
- Function name: `ProcessBrochureLambda-{environment}`
- Runtime: Python 3.12
- Memory: 1024 MB (for PDF parsing and size checks)
- Timeout: 300 seconds (sync Textract can take 30-60s for complex pages)
- Environment variables:
  - `SOURCE_BUCKET_NAME`: brochures-source-bucket
  - `OUTPUT_BUCKET_NAME`: textract-output-bucket
  - `METADATA_TABLE_NAME`: DynamoDB table
  - `TEXTRACT_SNS_TOPIC_ARN`: textract-job-completion-topic ARN
  - `TEXTRACT_ROLE_ARN`: IAM role for Textract to publish to SNS
  - `SYNC_PAGE_THRESHOLD`: 5 (max pages for sync API)
  - `SYNC_SIZE_THRESHOLD_MB`: 5
- Reserved concurrency: 10 (limit concurrent Textract jobs to stay within service quotas)

**IAM permissions**:
- s3:GetObject on brochures-source-bucket
- s3:PutObject on textract-output-bucket
- textract:DetectDocumentText (sync API)
- textract:StartDocumentTextDetection (async API)
- dynamodb:UpdateItem, dynamodb:GetItem on brochure-metadata-table
- sns:Publish on textract-job-completion-topic (for async role)
- logs:*

**Failure modes**:
- Unsupported file type: Log error, update DynamoDB status=UNSUPPORTED_FORMAT, send notification to ops SNS topic
- Textract throttling: Retry with exponential backoff (2s, 4s, 8s), send to DLQ after 3 attempts
- Textract service error (500): Retry 3 times, send to DLQ
- Invalid file (corrupted PDF): Textract returns error, log and update DynamoDB status=OCR_FAILED
- S3 write failure: Retry 2 times, send to DLQ

**Monitoring**:
- CloudWatch metric: Invocations, Errors, Duration, ConcurrentExecutions
- Custom metric: TextractSyncJobs, TextractAsyncJobs, ProcessingErrors
- Alarm: Errors > 5 in 5 minutes, ConcurrentExecutions > 8 (near quota)
- Logs: Include brochure_id, file_size, page_count, textract_job_id, processing_mode (sync/async)

**Testing approach**:
- Unit tests: Mock S3 event, Textract client responses
- Integration tests: Use sample PDFs (1-page, 5-page, 20-page, corrupted)
- Test cases: sync flow success, async flow success, throttling retry, invalid file format, size threshold edge cases

---

### 3.6 SNS: textract-job-completion-topic

**Purpose**: Receive Textract asynchronous job completion notifications.

**Responsibilities**:
- Configured as the SNS topic for Textract async jobs (StartDocumentTextDetection)
- Deliver completion events to TextractCallbackLambda
- Support retries if Lambda is throttled

**Configuration**:
- Topic name: `textract-job-completion-{environment}`
- Subscription: TextractCallbackLambda
- Delivery policy: 3 retries with exponential backoff
- Dead-letter queue: textract-callback-dlq (SQS)

**Access control**:
- Textract service principal allowed to publish
- TextractCallbackLambda allowed to subscribe

**Failure modes**:
- Lambda unavailable: SNS retries, sends to DLQ after 3 attempts
- Malformed message: Lambda logs error and drops message

**Monitoring**:
- CloudWatch metric: NumberOfMessagesPublished, NumberOfNotificationsFailed
- Alarm: NumberOfNotificationsFailed > 0

---

### 3.7 Lambda: TextractCallbackLambda

**Purpose**: Retrieve Textract async job results and store in S3.

**Responsibilities**:
- Triggered by SNS message from textract-job-completion-topic
- Parse SNS message to extract Textract job ID and status
- Call Textract GetDocumentTextDetection to retrieve full results (may require pagination)
- Aggregate all pages of results into single JSON file
- Write JSON to textract-output-bucket with key matching original brochure
- Update DynamoDB with status=OCR_COMPLETE, include page_count and result_s3_key
- Handle pagination (Textract returns max 1000 blocks per call, use NextToken)

**Configuration**:
- Function name: `TextractCallbackLambda-{environment}`
- Runtime: Python 3.12
- Memory: 1024 MB (large JSON results)
- Timeout: 300 seconds (pagination can take time for 100+ page documents)
- Environment variables:
  - `OUTPUT_BUCKET_NAME`: textract-output-bucket
  - `METADATA_TABLE_NAME`: DynamoDB table
- Reserved concurrency: 10

**IAM permissions**:
- textract:GetDocumentTextDetection
- s3:PutObject on textract-output-bucket
- dynamodb:UpdateItem on brochure-metadata-table
- logs:*

**Failure modes**:
- Job failed in Textract: Update DynamoDB status=OCR_FAILED, log reason, send notification
- GetDocumentTextDetection throttling: Retry with exponential backoff, send to DLQ
- S3 write failure: Retry, send to DLQ
- Pagination error: Retry, send to DLQ

**Monitoring**:
- CloudWatch metric: Invocations, Errors, Duration
- Custom metric: TextractPagesRetrieved, ResultSizeBytes
- Alarm: Errors > 3 in 10 minutes
- Logs: Include job_id, brochure_id, page_count, result_size

**Testing approach**:
- Unit tests: Mock Textract GetDocumentTextDetection with pagination
- Integration tests: Trigger with real async job completion event
- Test cases: single-page result, multi-page with pagination, job failure status

---

### 3.8 Lambda: KeywordSearchLambda

**Purpose**: Search Textract OCR results for configured keywords and trigger notifications.

**Responsibilities**:
- Triggered by S3 PUT events on textract-output-bucket
- Download Textract JSON result from S3
- Parse JSON to extract all text blocks with page numbers and bounding boxes
- Load keyword configuration from DynamoDB or S3 (per-store keyword lists)
- Perform case-insensitive keyword matching across full text
- For each match:
  - Record page number, line number, and surrounding context (50 characters before/after)
  - Extract confidence score from Textract (if available)
- Aggregate all matches per brochure
- If matches found:
  - Publish event to keyword-found-topic (SNS) with match details
  - Update DynamoDB with match records (status=MATCH_FOUND, keyword_matches array)
- If no matches:
  - Update DynamoDB status=NO_MATCHES

**Configuration**:
- Function name: `KeywordSearchLambda-{environment}`
- Runtime: Python 3.12
- Memory: 1024 MB
- Timeout: 180 seconds
- Environment variables:
  - `OUTPUT_BUCKET_NAME`: textract-output-bucket
  - `METADATA_TABLE_NAME`: DynamoDB table
  - `KEYWORD_FOUND_TOPIC_ARN`: SNS topic ARN
  - `KEYWORD_CONFIG_S3_KEY`: Optional S3 key for global keyword config
- Reserved concurrency: 20

**IAM permissions**:
- s3:GetObject on textract-output-bucket
- s3:GetObject on config bucket (for keyword lists)
- dynamodb:GetItem, dynamodb:UpdateItem, dynamodb:PutItem on brochure-metadata-table
- sns:Publish on keyword-found-topic
- logs:*

**Failure modes**:
- Malformed Textract JSON: Validate schema, log error, update DynamoDB status=PARSE_ERROR
- Missing keyword config: Fall back to default keywords or fail with notification
- SNS publish failure: Retry 3 times, send to DLQ
- DynamoDB write failure: Retry, send to DLQ

**Monitoring**:
- CloudWatch metric: Invocations, Errors, Duration
- Custom metric: KeywordsMatched, BrochuresWithMatches, BrochuresWithoutMatches
- Alarm: Errors > 5 in 10 minutes, BrochuresWithMatches = 0 for 24 hours (possible config issue)
- Logs: Include brochure_id, keywords_matched, match_count, pages_with_matches

**Testing approach**:
- Unit tests: Mock Textract JSON with known keywords, test case-insensitive matching, context extraction
- Integration tests: Real Textract JSON from sample brochures
- Test cases: single match, multiple matches on same page, no matches, keyword at page boundary, special characters in keywords

**Keyword matching algorithm details**:
- Normalize text: lowercase, remove extra whitespace
- Support whole-word matching (avoid matching "organic" in "reorganic")
- Support phrase matching ("buy one get one free")
- Record all occurrences with page numbers
- Limit context extraction to avoid truncating words

---

### 3.9 SNS: keyword-found-topic

**Purpose**: Fan-out keyword match notifications to multiple subscribers (email, future Slack/webhooks).

**Responsibilities**:
- Receive keyword match events from KeywordSearchLambda
- Deliver to all subscribers (initially SES subscription)
- Support future subscriptions (SQS for archival, Lambda for Slack integration)

**Configuration**:
- Topic name: `keyword-found-{environment}`
- Subscriptions:
  - Email protocol for SES-verified recipients (for email delivery)
  - Optional: SQS for audit trail
- Delivery policy: 3 retries with exponential backoff
- Dead-letter queue: keyword-notification-dlq (SQS)

**Message format**:
- JSON with fields: `brochure_id`, `store_id`, `store_name`, `brochure_filename`, `s3_key`, `upload_time`, `keywords_matched[]`, `match_details[]` (each with `keyword`, `page`, `context`, `confidence`)

**Access control**:
- KeywordSearchLambda allowed to publish
- SES allowed to consume (if using email subscription)
- Ops team IAM roles allowed to subscribe additional endpoints

**Failure modes**:
- Email delivery failure (invalid recipient): SNS marks as failed delivery, logs error
- Subscriber Lambda throttled: SNS retries, sends to DLQ

**Monitoring**:
- CloudWatch metric: NumberOfMessagesPublished, NumberOfNotificationsFailed, NumberOfNotificationsDelivered
- Alarm: NumberOfNotificationsFailed > 0

---

### 3.10 SES: Email Notification Configuration

**Purpose**: Send email notifications to configured recipients when keywords are detected.

**Responsibilities**:
- Deliver emails with match details to verified email addresses
- Format email with plain text and simple HTML versions
- Include brochure metadata, matched keywords, page numbers, and text snippets
- Support multiple recipients per store (To, CC, BCC)
- Respect SES sending limits (sandbox: 200 emails/day, production: request limit increase)

**Configuration**:
- Region: us-east-1 (or match Lambda region)
- Sender email: `noreply@example.com` (must be verified in SES)
- Recipient emails: Verified in SES (sandbox) or domain-verified (production)
- Configuration set: `brochure-scanner-{environment}` for tracking bounces and complaints
- Suppression list: Enabled to auto-suppress hard bounces
- DKIM: Enabled for domain authentication
- SPF: Configure DNS records for sending domain

**Email template structure**:
- Subject line: `Keyword Match Found: {store_name} - {brochure_filename}`
- Plain text body:
  - Store name and brochure filename
  - Upload date/time
  - List of matched keywords with page numbers
  - Text snippets showing context
  - Link to S3 presigned URL (optional, for internal users only)
- HTML body:
  - Formatted table with match details
  - Highlighted keywords in context
  - Footer with audit information (brochure ID, processing time)

**Recipient configuration storage**:
- Store in DynamoDB brochure-metadata-table or separate config file
- Schema: `{store_id, recipients: [{email, type: TO/CC/BCC}]}`

**IAM permissions** (for Lambda invoking SES):
- ses:SendEmail
- ses:SendRawEmail (if using templates)

**Failure modes**:
- Unverified email in sandbox: SES rejects, Lambda logs error and sends to ops alert
- Soft bounce (mailbox full): SES retries automatically for 12 hours
- Hard bounce (invalid email): SES adds to suppression list, logs event
- Complaint (spam report): SES adds to suppression list, triggers CloudWatch alarm

**Monitoring**:
- CloudWatch metric: NumberOfEmailsSent (custom metric), SES Send metrics (Delivery, Bounce, Complaint)
- Alarm: Bounce rate > 5%, Complaint rate > 0.1%
- SES Event Publishing: Send delivery, bounce, complaint events to SNS or CloudWatch Logs

**Testing approach**:
- Use SES mailbox simulator addresses (success@simulator.amazonses.com, bounce@simulator.amazonses.com)
- Test plain text and HTML rendering
- Verify all metadata fields are populated correctly
- Test multiple recipients (To, CC, BCC)

**SES Sandbox restrictions**:
- 200 emails per 24 hours
- 1 email per second
- Only verified emails can receive
- Request production access before go-live

**Production access request**:
- Submit SES sending limit increase request
- Provide use case description (automated retail brochure monitoring)
- Request daily sending quota: 10,000 emails/day
- Request rate: 10 emails/second
- Maintain low bounce/complaint rates to preserve reputation

---

### 3.11 DynamoDB: brochure-metadata-table

**Purpose**: Store metadata for all brochures, processing status, and keyword matches.

**Responsibilities**:
- Track brochure lifecycle from upload to keyword detection
- Enable deduplication via file hash lookups
- Store keyword match history for auditing and analytics
- Support queries by store_id, date, and status

**Schema**:

**Primary Key**:
- Partition key: `brochure_id` (String) - UUID or S3 key-based hash
- Sort key: None (simple primary key)

**Attributes**:
- `brochure_id` (String, PK) - Unique identifier
- `store_id` (String) - Retailer identifier
- `store_name` (String) - Human-readable store name
- `brochure_filename` (String) - Original filename
- `s3_bucket` (String) - Source bucket name
- `s3_key` (String) - Full S3 key
- `file_hash` (String) - SHA-256 hash for deduplication
- `file_size_bytes` (Number) - File size
- `upload_time` (String, ISO8601) - When uploaded to S3
- `status` (String) - Lifecycle status: UPLOADED, TEXTRACT_IN_PROGRESS, OCR_COMPLETE, MATCH_FOUND, NO_MATCHES, FAILED, INVALID_FORMAT, UNSUPPORTED_FORMAT, OCR_FAILED, PARSE_ERROR
- `textract_job_id` (String) - Textract async job ID (if applicable)
- `textract_mode` (String) - SYNC or ASYNC
- `textract_result_s3_key` (String) - S3 key for Textract JSON output
- `page_count` (Number) - Number of pages in brochure
- `ocr_complete_time` (String, ISO8601) - When OCR finished
- `keywords_matched` (List of Strings) - List of matched keywords
- `match_count` (Number) - Total number of keyword occurrences
- `match_details` (List of Maps) - Each map: `{keyword, page, line, context, confidence}`
- `notification_sent` (Boolean) - Whether email notification was sent
- `notification_time` (String, ISO8601) - When notification was sent
- `error_message` (String) - Error details if processing failed
- `created_at` (String, ISO8601) - Record creation time
- `updated_at` (String, ISO8601) - Last update time

**Global Secondary Indexes**:

**GSI-1: store-date-index**:
- Partition key: `store_id` (String)
- Sort key: `upload_time` (String)
- Purpose: Query all brochures for a store within date range
- Projected attributes: ALL

**GSI-2: status-index**:
- Partition key: `status` (String)
- Sort key: `upload_time` (String)
- Purpose: Query all brochures by processing status (e.g., all FAILED)
- Projected attributes: ALL

**GSI-3: hash-index**:
- Partition key: `file_hash` (String)
- Sort key: None
- Purpose: Deduplication lookups
- Projected attributes: brochure_id, s3_key, upload_time

**Capacity settings**:
- Billing mode: PAY_PER_REQUEST (on-demand) for unpredictable workload
- Alternative: PROVISIONED with auto-scaling (RCU: 5-50, WCU: 5-50) if cost-optimizing for steady load

**TTL**:
- Optional: Enable TTL on `ttl_timestamp` attribute to auto-delete records older than 2 years

**Encryption**:
- Encryption at rest: Enabled with AWS-managed keys (default)

**Point-in-time recovery**:
- Enabled for production environment

**Access patterns**:
- CrawlerLambda: Query hash-index for deduplication, PutItem
- ProcessBrochureLambda: GetItem, UpdateItem
- TextractCallbackLambda: UpdateItem
- KeywordSearchLambda: GetItem, UpdateItem
- Operational queries: Query by store_id and date range, query by status

**Failure modes**:
- Throttling: Retry with exponential backoff in Lambda code
- Conditional write failures: Retry with updated condition
- Item size > 400 KB: Unlikely with current schema, but if match_details grows large, consider offloading to S3

**Monitoring**:
- CloudWatch metric: ConsumedReadCapacityUnits, ConsumedWriteCapacityUnits, UserErrors, SystemErrors
- Alarm: UserErrors > 10 in 5 minutes, SystemErrors > 0

**Backup strategy**:
- Point-in-time recovery for production
- On-demand backups before major schema changes
- Export to S3 monthly for long-term archival

**Testing approach**:
- Unit tests: Mock DynamoDB client in Lambda tests
- Integration tests: Use DynamoDB Local or real table in dev environment
- Test cases: deduplication logic, concurrent updates, GSI queries, TTL expiration

---

## 4. Detailed Data Flow

### 4.1 Happy Path: Scheduled Crawl to Notification

1. **EventBridge schedule fires** at configured time (e.g., 10 AM daily)
2. **CrawlerLambda invoked** with store list payload
3. **For each store**:
   - HTTP GET brochure URL
   - Compute SHA-256 hash of file content
   - Query DynamoDB hash-index for duplicate
   - If duplicate found: Skip, log "duplicate detected", continue to next store
   - If new: Generate brochure_id (UUID), construct S3 key `{store_id}/{YYYY}/{MM}/{DD}/{filename}`
   - PUT object to brochures-source-bucket
   - PutItem to DynamoDB with status=UPLOADED, file_hash, upload_time
4. **S3 event notification** triggers ProcessBrochureLambda for each uploaded file
5. **ProcessBrochureLambda**:
   - GetObject metadata from S3 (size, content-type)
   - If PDF: Extract page count using PDF library
   - If small (< 5 pages, < 5 MB): Call Textract DetectDocumentText (sync)
     - Receive immediate response with text blocks
     - Write JSON to textract-output-bucket with key `{store_id}/{YYYY}/{MM}/{DD}/{brochure_id}/textract-result.json`
     - UpdateItem in DynamoDB: status=OCR_COMPLETE, textract_mode=SYNC, page_count, ocr_complete_time
   - If large: Call Textract StartDocumentTextDetection (async)
     - Receive job_id in response
     - UpdateItem in DynamoDB: status=TEXTRACT_IN_PROGRESS, textract_job_id, textract_mode=ASYNC
6. **For async flow**:
   - Textract processes file (may take 1-30 minutes for large documents)
   - Textract publishes completion message to textract-job-completion-topic
   - **TextractCallbackLambda invoked** by SNS
   - Parse SNS message for job_id and status
   - Call GetDocumentTextDetection (with pagination if needed)
   - Aggregate all pages into single JSON
   - Write JSON to textract-output-bucket
   - UpdateItem in DynamoDB: status=OCR_COMPLETE, page_count, ocr_complete_time
7. **S3 event notification** triggers KeywordSearchLambda when JSON written to textract-output-bucket
8. **KeywordSearchLambda**:
   - GetObject Textract JSON from S3
   - Parse JSON to extract all text blocks with page numbers
   - Load keyword configuration for store_id from DynamoDB or S3 config
   - Perform keyword matching (case-insensitive, whole-word)
   - If matches found:
     - Build match_details array with keyword, page, context
     - Publish message to keyword-found-topic (SNS) with full match details
     - UpdateItem in DynamoDB: status=MATCH_FOUND, keywords_matched, match_count, match_details
   - If no matches:
     - UpdateItem in DynamoDB: status=NO_MATCHES
9. **SNS keyword-found-topic** delivers message to email subscription
10. **SES sends email** to configured recipients
    - Subject: "Keyword Match Found: {store_name} - {brochure_filename}"
    - Body includes match details, page numbers, text snippets
11. **Recipient receives email** within seconds to minutes of SNS publish

**End-to-end latency**:
- Sync flow: 2-5 minutes (upload → OCR → keyword search → email)
- Async flow: 5-45 minutes (depends on Textract job queue time and document size)

---

### 4.2 Failure Paths and Recovery

**Scenario 1: CrawlerLambda fails to download brochure (HTTP 404)**:
- CrawlerLambda logs error with store_id, URL, HTTP status
- Does not upload to S3, does not write to DynamoDB
- Custom CloudWatch metric incremented: BrochuresFailed
- CloudWatch alarm triggers if BrochuresFailed > 0
- Ops team notified via SNS, investigates broken URL
- Manual remediation: Update store configuration with correct URL, re-run crawler

**Scenario 2: ProcessBrochureLambda receives corrupted PDF**:
- ProcessBrochureLambda attempts to read PDF metadata, fails
- Catches exception, logs error with brochure_id and S3 key
- UpdateItem in DynamoDB: status=INVALID_FORMAT, error_message
- Does not invoke Textract
- Custom CloudWatch metric incremented: InvalidFiles
- Ops team reviews DynamoDB for INVALID_FORMAT records, contacts store to request corrected file

**Scenario 3: Textract async job fails (unsupported image format in PDF)**:
- Textract publishes failure status to textract-job-completion-topic
- TextractCallbackLambda receives failure notification
- UpdateItem in DynamoDB: status=OCR_FAILED, error_message from Textract
- Publishes error event to ops-alert-topic (SNS)
- Ops team investigates, may need to pre-process file or contact store

**Scenario 4: KeywordSearchLambda receives malformed Textract JSON**:
- KeywordSearchLambda attempts to parse JSON, validation fails
- Logs error with brochure_id, S3 key, and validation error details
- UpdateItem in DynamoDB: status=PARSE_ERROR, error_message
- Does not publish to keyword-found-topic
- CloudWatch alarm triggers if ParseErrors > 5 in 10 minutes
- Ops team reviews Textract JSON manually, files AWS support ticket if Textract bug suspected

**Scenario 5: SNS publish to keyword-found-topic fails (throttling)**:
- KeywordSearchLambda SNS publish call returns throttling error
- Lambda SDK automatically retries with exponential backoff (3 attempts)
- If all retries fail, Lambda invocation fails
- S3 event source re-invokes Lambda (up to 2 retries by default)
- If still failing, event sent to Lambda DLQ
- CloudWatch alarm on DLQ message count > 0
- Ops team processes DLQ: manually re-publishes SNS message or fixes throttling (increase SNS rate limit)

**Scenario 6: SES email send fails (recipient email bounces)**:
- SES attempts delivery, receives hard bounce from recipient mail server
- SES publishes bounce event to SES configuration set SNS topic
- Bounce notification logged to CloudWatch Logs
- SES adds email to suppression list
- Ops team reviews suppression list, corrects recipient email in configuration, removes from suppression list

**Scenario 7: DynamoDB write throttling**:
- Lambda UpdateItem call throttled (exceeded provisioned capacity or on-demand limits)
- Lambda SDK retries automatically with exponential backoff
- If retries exhausted, Lambda invocation fails
- Event source (S3) re-invokes Lambda
- If persistent throttling: CloudWatch alarm on DynamoDB ThrottleRequests
- Ops team increases provisioned capacity or investigates burst traffic pattern

**Scenario 8: Lambda function timeout (Textract sync call takes > 5 minutes)**:
- ProcessBrochureLambda timeout kills function mid-execution
- DynamoDB may be partially updated (status=TEXTRACT_IN_PROGRESS but no result)
- S3 event source re-invokes Lambda
- Lambda detects duplicate processing by checking DynamoDB status
- Implements idempotency: If status already TEXTRACT_IN_PROGRESS and timestamp > 10 minutes old, re-start OCR; otherwise skip
- Logs warning and continues

---

### 4.3 Deduplication Strategy

**Goal**: Avoid reprocessing identical brochure files uploaded multiple times.

**Approach**:
1. CrawlerLambda computes SHA-256 hash of downloaded file content before upload
2. Query DynamoDB hash-index (GSI-3) for existing record with same file_hash
3. If match found:
   - Check upload_time of existing record
   - If existing record is < 30 days old: Skip upload, log "duplicate detected"
   - If existing record is > 30 days old: Allow re-upload (stores may republish same brochure periodically)
4. If no match found: Proceed with upload and DynamoDB write

**Edge cases**:
- Store publishes brochure with same content but different filename: Detected as duplicate by hash
- Store publishes brochure with minor changes (1 word difference): Different hash, processed as new
- Hash collision (extremely unlikely with SHA-256): Accept risk, no mitigation needed

**Alternative approach for URL-based crawling**:
- Store last-modified HTTP header from brochure URL
- Compare with previous crawl's last-modified timestamp
- Only download if changed
- Fallback to hash-based deduplication if last-modified not available

---

### 4.4 Handling Textract Service Limits

**Textract Quotas (default, region-specific)**:
- Synchronous API: 10 transactions per second (TPS)
- Asynchronous API: 100 concurrent jobs, 10 StartDocumentTextDetection TPS
- Maximum document size: 512 MB
- Maximum pages: 3000 pages per document

**Mitigation strategies**:

**Limit concurrent Lambda invocations**:
- Set reserved concurrency on ProcessBrochureLambda to 10 (prevents > 10 concurrent Textract async jobs)
- Set reserved concurrency on TextractCallbackLambda to 10 (prevents overwhelming GetDocumentTextDetection calls)

**Implement backoff and retry in Lambda**:
- Catch ProvisionedThroughputExceededException
- Retry with exponential backoff: 2s, 4s, 8s
- Max 3 retries, then send to DLQ

**Batching and rate limiting**:
- If processing > 100 brochures in single crawl, introduce delay between ProcessBrochureLambda invocations
- Use SQS between S3 and ProcessBrochureLambda to buffer uploads and control processing rate (optional enhancement)

**Monitor quota utilization**:
- CloudWatch metric: Custom metric for ConcurrentTextractJobs (increment on StartDocumentTextDetection, decrement on job completion)
- Alarm if ConcurrentTextractJobs > 80 (approaching quota)

**Request quota increase**:
- Submit AWS Support request to increase concurrent async jobs to 500 if processing > 300 brochures/day
- Provide use case justification and expected growth

**Document size handling**:
- Warn if brochure > 100 pages, consider splitting (future enhancement)
- Reject files > 3000 pages, log error, update DynamoDB status=UNSUPPORTED_FORMAT

---

### 4.5 Cleanup and Lifecycle Management

**S3 lifecycle policies**:
- **brochures-source-bucket**:
  - Transition to Glacier Instant Retrieval after 90 days (reduce storage cost by ~70%)
  - Delete after 2 years (compliance retention)
- **textract-output-bucket**:
  - Transition to Glacier Instant Retrieval after 180 days
  - Delete after 3 years (longer retention for audit)

**DynamoDB TTL**:
- Add `ttl_timestamp` attribute set to upload_time + 2 years (Unix epoch seconds)
- Enable TTL on brochure-metadata-table
- DynamoDB automatically deletes expired records within 48 hours

**Temporary file cleanup**:
- Lambda /tmp directory: Automatically cleared after function execution
- No manual cleanup needed

**Cost optimization**:
- Periodically review S3 storage class distribution (use S3 Storage Lens)
- Delete test data from dev environment monthly

---

## 5. Storage Schema & Metadata

### 5.1 DynamoDB Schema (detailed)
See section 3.11 for full schema definition.

### 5.2 S3 Key Patterns

**brochures-source-bucket**:
- Pattern: `{store_id}/{YYYY}/{MM}/{DD}/{original_filename}.{ext}`
- Example: `walmart/2025/11/18/weekly-ad-2025-11-18.pdf`
- Benefits: Date partitioning for lifecycle rules, easy visual browsing in console

**textract-output-bucket**:
- Pattern: `{store_id}/{YYYY}/{MM}/{DD}/{brochure_id}/textract-result.json`
- Example: `walmart/2025/11/18/a1b2c3d4-e5f6-7890-abcd-ef1234567890/textract-result.json`
- Benefits: Links to source brochure by store/date, unique brochure_id prevents collisions

### 5.3 Configuration File Schema (keyword-config.json)

Stored in brochures-source-bucket or separate config bucket.

**Structure**:
```
{
  "version": "1.0",
  "updated_at": "2025-11-18T10:00:00Z",
  "stores": [
    {
      "store_id": "walmart",
      "store_name": "Walmart",
      "brochure_url": "https://www.walmart.com/weekly-ad.pdf",
      "keywords": ["organic", "sale", "clearance", "buy one get one"],
      "recipients": [
        {"email": "alerts@example.com", "type": "TO"},
        {"email": "archive@example.com", "type": "BCC"}
      ],
      "crawl_schedule": "daily"
    }
  ]
}
```

**Validation rules**:
- store_id must be unique, alphanumeric + hyphens only
- keywords array must have at least 1 entry, max 100 keywords per store
- recipients must include at least 1 TO recipient
- email addresses must be SES-verified (in sandbox) or domain-verified (production)

**Configuration updates**:
- Edit JSON file in S3
- No Lambda restarts needed (Lambda loads config on each invocation)
- Version control: Store in Git, deploy via CI/CD
- Schema evolution: Include version field, handle backward compatibility in Lambda code

### 5.4 Textract JSON Result Structure

Textract DetectDocumentText and GetDocumentTextDetection return similar JSON structures.

**Key elements**:
- `Blocks`: Array of detected elements (PAGE, LINE, WORD)
- Each block has:
  - `BlockType`: PAGE, LINE, WORD
  - `Text`: Detected text content (for LINE and WORD)
  - `Confidence`: OCR confidence score (0-100)
  - `Page`: Page number (1-indexed)
  - `Geometry`: Bounding box coordinates

**KeywordSearchLambda processing**:
- Filter blocks where BlockType = LINE or WORD
- Concatenate text by page to build full page text
- Perform keyword search on concatenated text
- Cross-reference match position back to LINE blocks to get page number and context

---

## 6. IAM & Security

### 6.1 Least-Privilege IAM Roles

**CrawlerLambda execution role**:
- Policy name: CrawlerLambdaPolicy
- Permissions:
  - s3:PutObject on brochures-source-bucket (with condition: prefix = specific store_id paths)
  - s3:GetObject on config bucket (keyword-config.json)
  - dynamodb:Query on brochure-metadata-table hash-index
  - dynamodb:PutItem on brochure-metadata-table
  - logs:CreateLogGroup, logs:CreateLogStream, logs:PutLogEvents
- Trust relationship: lambda.amazonaws.com

**ProcessBrochureLambda execution role**:
- Policy name: ProcessBrochureLambdaPolicy
- Permissions:
  - s3:GetObject on brochures-source-bucket
  - s3:PutObject on textract-output-bucket
  - textract:DetectDocumentText
  - textract:StartDocumentTextDetection
  - iam:PassRole (for Textract to publish to SNS, scoped to TextractServiceRole)
  - dynamodb:GetItem, dynamodb:UpdateItem on brochure-metadata-table
  - logs:*
- Trust relationship: lambda.amazonaws.com

**TextractCallbackLambda execution role**:
- Policy name: TextractCallbackLambdaPolicy
- Permissions:
  - textract:GetDocumentTextDetection
  - s3:PutObject on textract-output-bucket
  - dynamodb:UpdateItem on brochure-metadata-table
  - logs:*
- Trust relationship: lambda.amazonaws.com

**KeywordSearchLambda execution role**:
- Policy name: KeywordSearchLambdaPolicy
- Permissions:
  - s3:GetObject on textract-output-bucket
  - s3:GetObject on config bucket (keyword config)
  - dynamodb:GetItem, dynamodb:UpdateItem, dynamodb:PutItem on brochure-metadata-table
  - sns:Publish on keyword-found-topic
  - logs:*
- Trust relationship: lambda.amazonaws.com

**Textract service role** (for async jobs):
- Policy name: TextractServiceRolePolicy
- Permissions:
  - sns:Publish on textract-job-completion-topic
- Trust relationship: textract.amazonaws.com

**SES sending role** (if using Lambda to send directly, not used if SNS→SES):
- Policy name: SESEmailSendPolicy
- Permissions:
  - ses:SendEmail
  - ses:SendRawEmail
- Scoped to specific sender email and verified recipients (in sandbox)

### 6.2 S3 Bucket Policies

**brochures-source-bucket policy**:
- Deny unencrypted uploads (enforce SSE-S3)
- Allow only CrawlerLambda and authorized IAM roles to PutObject
- Block public access (all four settings enabled)

**textract-output-bucket policy**:
- Deny unencrypted uploads
- Allow only ProcessBrochureLambda and TextractCallbackLambda to PutObject
- Allow KeywordSearchLambda GetObject
- Block public access

**Sample policy statement** (conceptual, not code):
- Effect: Deny
- Principal: *
- Action: s3:PutObject
- Resource: arn:aws:s3:::brochures-source-bucket/*
- Condition: StringNotEquals s3:x-amz-server-side-encryption: AES256

### 6.3 Encryption

**S3 encryption at rest**:
- Use SSE-S3 (AWS-managed keys) for both buckets
- Simplifies key management, no additional cost
- Alternative: SSE-KMS for audit trail and key rotation control (adds cost and complexity)

**DynamoDB encryption**:
- Use AWS-managed keys (default encryption)
- No customer action required

**Data in transit**:
- All AWS API calls use HTTPS (enforced by SDK)
- Textract, S3, DynamoDB, SES all communicate over TLS 1.2+

**Secrets management**:
- Store SES SMTP credentials (if needed) in AWS Secrets Manager
- Lambda retrieves secrets at runtime via SDK
- Rotate secrets annually or on compromise

### 6.4 SES Security

**Domain verification**:
- Verify sending domain via DNS TXT records (reduces spam likelihood)
- DKIM signing: Generate DKIM keys in SES, add CNAME records to DNS
- SPF record: Add SPF TXT record to DNS authorizing SES to send for domain

**Sender restrictions**:
- Use dedicated sending identity (e.g., noreply@brochurealerts.example.com)
- Do not use personal email addresses as sender

**Recipient restrictions (sandbox)**:
- All recipient emails must be verified
- Request production access before go-live

**Rate limiting**:
- Monitor sending rate to stay within quota
- Implement backoff if approaching limit (track via CloudWatch metric)

**Bounce and complaint handling**:
- Enable SES configuration set with SNS notifications for bounces and complaints
- Automatically remove hard-bounced emails from recipient list
- Investigate complaints, ensure email content is not spam-like

### 6.5 Network Security

**Lambda VPC configuration**:
- Not required (all AWS services accessible via public endpoints)
- If required by org policy: Place Lambda in private subnet with NAT Gateway for outbound internet access (for URL crawling)
- VPC endpoints: Use for S3, DynamoDB, SES if in VPC (reduces NAT costs)

**No public endpoints**:
- All components are AWS-managed or serverless
- No EC2 instances, no load balancers, no public IPs

### 6.6 Logging and Audit

**CloudWatch Logs**:
- All Lambda functions log to /aws/lambda/{function-name}
- Retention: 90 days for production, 30 days for dev
- Log level: INFO for normal operations, DEBUG for troubleshooting

**CloudTrail**:
- Enable CloudTrail for S3 data events (PutObject, GetObject) on both buckets
- Audit DynamoDB PutItem/UpdateItem via CloudTrail management events
- Retention: 1 year in S3, use S3 lifecycle to archive to Glacier

**SES event publishing**:
- Publish delivery, bounce, complaint events to CloudWatch Logs via configuration set
- Retention: 90 days

**DynamoDB streams** (optional):
- Enable DynamoDB stream on brochure-metadata-table to audit all changes
- Stream to Lambda for real-time analytics or archive to S3 via Kinesis Data Firehose

### 6.7 Compliance Considerations

**Data residency**:
- All data stored in single AWS region (e.g., us-east-1)
- Textract, S3, DynamoDB in same region for compliance and latency

**PII handling**:
- Brochures unlikely to contain PII, but if they do:
  - Do not log brochure content to CloudWatch
  - Redact email addresses from logs
  - Use S3 Object Lock for immutability if required by regulation

**Data retention**:
- 2-year retention aligns with typical retail compliance requirements
- Adjust based on org policy (GDPR: right to deletion may require shorter retention)

---

## 7. Operational Concerns

### 7.1 Monitoring Metrics

**CloudWatch Metrics to Create (Custom)**:
- **CrawlerLambda**:
  - BrochuresDownloaded (Count, per store_id dimension)
  - BrochuresFailed (Count, per store_id)
  - DuplicatesSkipped (Count, per store_id)
  - CrawlDuration (Milliseconds, per store_id)
- **ProcessBrochureLambda**:
  - TextractSyncJobs (Count)
  - TextractAsyncJobs (Count)
  - ProcessingErrors (Count)
  - UnsupportedFormats (Count)
- **KeywordSearchLambda**:
  - KeywordsMatched (Count, per keyword dimension)
  - BrochuresWithMatches (Count)
  - BrochuresWithoutMatches (Count)
  - MatchesByStore (Count, per store_id)
- **Overall pipeline**:
  - EndToEndLatency (Milliseconds, upload to notification)
  - TotalCost (USD, estimated daily, requires custom calculation from usage metrics)

**AWS-Provided Metrics**:
- Lambda: Invocations, Errors, Duration, Throttles, ConcurrentExecutions, IteratorAge (for stream-based invocations)
- S3: NumberOfObjects, BucketSizeBytes
- DynamoDB: ConsumedReadCapacityUnits, ConsumedWriteCapacityUnits, UserErrors, SystemErrors, ThrottledRequests
- SNS: NumberOfMessagesPublished, NumberOfNotificationsFailed
- SES: Send, Delivery, Bounce, Complaint (requires configuration set)
- Textract: No direct metrics; track via Lambda custom metrics

### 7.2 CloudWatch Alarms

**Critical alarms** (page ops team):
- Lambda function errors > 10 in 5 minutes (any function)
- DynamoDB SystemErrors > 0
- SES Complaint rate > 0.1%
- Keyword-found-topic NumberOfNotificationsFailed > 0
- DLQ message count > 0 (any DLQ)

**Warning alarms** (email ops team):
- Lambda function errors > 5 in 10 minutes
- S3 BucketSizeBytes > 100 GB (cost control)
- DynamoDB ThrottledRequests > 10 in 5 minutes
- ConcurrentTextractJobs > 80 (approaching quota)
- BrochuresWithMatches = 0 for 48 hours (possible config issue)

**Cost alarms**:
- Estimated monthly charges > $250 (CloudWatch Billing alarm)
- Textract page count > 10,000 in 24 hours (runaway processing)

### 7.3 CloudWatch Dashboards

**Dashboard: Brochure Scanner Overview**:
- Widgets:
  - Time series: Brochures processed per day (by store)
  - Time series: Keyword matches per day (by keyword)
  - Number: Total brochures in last 7 days
  - Number: Total matches in last 7 days
  - Time series: Lambda errors (all functions)
  - Time series: End-to-end latency (p50, p95, p99)
  - Pie chart: Brochure status distribution (from DynamoDB)

**Dashboard: Operational Health**:
- Widgets:
  - Lambda concurrent executions (all functions)
  - DynamoDB consumed capacity
  - S3 bucket size trend
  - SES bounce and complaint rates
  - DLQ message counts

**Dashboard: Cost Tracking**:
- Widgets:
  - Textract page count (daily)
  - Lambda invocation count (by function)
  - S3 GET/PUT request count
  - SES email send count
  - Estimated daily cost (custom metric, requires Lambda to calculate and publish)

### 7.4 Log Retention and Analysis

**CloudWatch Logs Insights queries**:

**Query: Failed brochure processing**:
- Filter: level = ERROR
- Fields: timestamp, brochure_id, store_id, error_message
- Sort by timestamp desc

**Query: Top keywords matched**:
- Filter: keyword_matched exists
- Stats: count() by keyword
- Sort by count desc

**Query: Average OCR processing time**:
- Filter: textract_mode = SYNC or ASYNC
- Stats: avg(ocr_duration) by textract_mode

**Log retention**:
- Production: 90 days in CloudWatch Logs, export to S3 for long-term archive
- Dev: 30 days, no archive

### 7.5 Runbook for Common Failures

**Issue: Crawler fails to download brochure (HTTP 404)**:
- Detection: CloudWatch alarm on BrochuresFailed > 0
- Diagnosis: Check CloudWatch Logs for CrawlerLambda errors, identify store_id and URL
- Resolution: Verify URL is correct, contact store if URL changed, update keyword-config.json
- Prevention: Implement URL validation in config, periodic link-checking Lambda

**Issue: Textract async job stuck (no completion notification after 2 hours)**:
- Detection: Manual check or custom metric for JobsPendingCompletion
- Diagnosis: Query DynamoDB for records with status=TEXTRACT_IN_PROGRESS and ocr_start_time > 2 hours ago
- Resolution: Call Textract DescribeDocumentTextDetection with job_id to check status, manually trigger TextractCallbackLambda if job complete but notification missed
- Prevention: Implement timeout monitor Lambda that periodically checks stale jobs

**Issue: Email notifications not received**:
- Detection: User report or monitoring BrochuresWithMatches > 0 but no emails sent
- Diagnosis: Check SES sending metrics for bounces/complaints, check SNS topic delivery status, verify recipient emails in config
- Resolution: If bounce: remove invalid email, re-verify. If SNS throttling: increase rate limit. If SES sandbox: request production access.
- Prevention: Pre-validate all recipient emails before adding to config

**Issue: High Textract costs**:
- Detection: CloudWatch billing alarm
- Diagnosis: Query DynamoDB for page_count distribution, check for large documents or duplicate processing
- Resolution: Implement page count limit (reject > 100 pages), improve deduplication logic
- Prevention: Add cost projection before processing (estimate pages × Textract price)

**Issue: DynamoDB throttling**:
- Detection: CloudWatch alarm on ThrottledRequests
- Diagnosis: Check consumed capacity vs. provisioned (if using provisioned mode), identify hot partition key
- Resolution: Switch to on-demand mode, or increase provisioned capacity, or shard partition key
- Prevention: Use on-demand mode for unpredictable workloads

### 7.6 Disaster Recovery

**Scenario: Accidental deletion of brochures-source-bucket**:
- Prevention: Enable S3 versioning (trade-off: increased storage cost) and MFA delete
- Recovery: If versioning enabled, restore objects. If not, re-crawl brochures from source URLs (if available) or request re-upload from stores.

**Scenario: DynamoDB table deleted**:
- Prevention: Enable point-in-time recovery, tag table to prevent accidental deletion
- Recovery: Restore table from point-in-time backup (RPO: up to 5 minutes)

**Scenario: Region outage**:
- Prevention: Multi-region deployment (significant complexity increase)
- Recovery: Wait for region restoration (AWS SLA: 99.99% for S3, Lambda, DynamoDB), typical RTO < 4 hours for major outages

**Scenario: Lambda function corrupted (bad deployment)**:
- Prevention: Use Lambda function versions and aliases, deploy to alias, rollback if errors spike
- Recovery: Revert alias to previous version, redeploy known-good code

### 7.7 Scaling Considerations

**Current design handles 100-500 brochures/day**:
- Lambda: Auto-scales to 1000 concurrent executions (default account limit)
- Textract: 100 concurrent async jobs (quota)
- DynamoDB: On-demand mode supports up to 40,000 RCU/WCU (automatically)
- S3: Unlimited scalability

**Scaling to 5,000 brochures/day**:
- Request Textract quota increase to 500 concurrent jobs
- Increase Lambda reserved concurrency proportionally
- Monitor DynamoDB on-demand costs, consider switching to provisioned with auto-scaling
- Implement SQS buffering between S3 and ProcessBrochureLambda to rate-limit Textract calls

**Scaling to 50,000 brochures/day**:
- Introduce SQS FIFO queues for ordering and deduplication
- Use Step Functions for complex orchestration (replace direct Lambda→Lambda)
- Partition DynamoDB table by store_id (multiple tables) to avoid hot partitions
- Use Textract bulk processing or batch API if available
- Consider cost optimization: Use Textract asynchronous API exclusively (cheaper than sync for scale)

---

## 8. Testing & QA Plan

### 8.1 Unit Test Targets

**CrawlerLambda**:
- Test: Successful HTTP download
- Test: HTTP 404 error handling
- Test: Network timeout and retry logic
- Test: SHA-256 hash computation accuracy
- Test: Duplicate detection via DynamoDB query
- Test: S3 key construction with date partitioning

**ProcessBrochureLambda**:
- Test: File size and page count extraction
- Test: Sync vs. async decision logic (boundary conditions: exactly 5 pages, exactly 5 MB)
- Test: Textract API response parsing (sync)
- Test: Textract job submission (async)
- Test: DynamoDB status updates
- Test: Error handling for unsupported file types

**TextractCallbackLambda**:
- Test: SNS message parsing
- Test: Textract GetDocumentTextDetection pagination
- Test: JSON aggregation for multi-page results
- Test: S3 write and DynamoDB update

**KeywordSearchLambda**:
- Test: Textract JSON parsing
- Test: Keyword matching (case-insensitive, whole-word, phrase)
- Test: Context extraction (before/after 50 characters)
- Test: Page number correlation
- Test: SNS message formatting
- Test: No matches scenario

**Mocking strategy**:
- Use moto library (Python) for AWS service mocks (S3, DynamoDB, SNS, Textract)
- Mock HTTP requests with responses library (Python) or nock (Node.js)
- Fixtures: Sample PDF files, Textract JSON responses, SNS event payloads

### 8.2 Integration Test Scenarios

**End-to-end test: Manual upload to notification**:
- Setup: Deploy all components to test environment
- Action: Upload test PDF to brochures-source-bucket with known keywords
- Verification:
  - ProcessBrochureLambda invoked (check CloudWatch Logs)
  - Textract result written to textract-output-bucket
  - KeywordSearchLambda detects keywords
  - SNS message published to keyword-found-topic
  - Email received by test recipient (use mailbox simulator)
  - DynamoDB record shows status=MATCH_FOUND
- Expected duration: < 5 minutes for small PDF (sync flow)

**End-to-end test: Scheduled crawl to notification**:
- Setup: Configure EventBridge rule to trigger immediately, set test store URL
- Action: Trigger EventBridge rule manually
- Verification: Same as above, plus verify CrawlerLambda downloaded file from URL

**Test: Large multi-page PDF (async flow)**:
- Setup: Upload 20-page PDF with keywords on pages 1, 10, 20
- Verification:
  - ProcessBrochureLambda chooses async flow
  - Textract job completes (wait up to 5 minutes)
  - TextractCallbackLambda retrieves all pages
  - KeywordSearchLambda finds keywords on all 3 pages
  - Email lists all 3 matches with correct page numbers

**Test: Duplicate detection**:
- Setup: Upload same PDF twice (same content hash)
- Verification:
  - First upload: Processed normally
  - Second upload: CrawlerLambda skips, logs "duplicate detected", no Textract job

**Test: Error handling (corrupted PDF)**:
- Setup: Upload corrupted PDF file
- Verification:
  - ProcessBrochureLambda logs error
  - DynamoDB status=INVALID_FORMAT
  - No Textract job submitted
  - CloudWatch alarm triggered (if configured)

**Test: Textract throttling simulation**:
- Setup: Submit 20 concurrent brochures (exceeds reserved concurrency)
- Verification:
  - Some Lambda invocations throttled
  - S3 event retries throttled invocations
  - All brochures eventually processed
  - CloudWatch throttle metric > 0

### 8.3 Load Testing

**Objective**: Verify system handles 500 brochures in single batch.

**Approach**:
- Use AWS Step Functions or custom script to upload 500 test PDFs to S3 over 10 minutes
- Monitor all CloudWatch metrics and alarms
- Verify all brochures processed within 2 hours
- Check for throttling, errors, DLQ messages

**Success criteria**:
- 100% of brochures processed (status in DynamoDB is OCR_COMPLETE or later)
- Error rate < 1%
- No DLQ messages
- Email notifications delivered for all matches

**Load test variations**:
- Test 1: 500 small PDFs (sync flow)
- Test 2: 500 large PDFs (async flow)
- Test 3: Mixed (250 small, 250 large)
- Test 4: Spike load (500 in 1 minute)

### 8.4 Acceptance Criteria

**MVP acceptance**:
- Manual upload of 5 different brochures (varying sizes and formats) results in 5 successful OCR results and keyword matches
- Scheduled crawl retrieves brochures from 3 test store URLs
- Email notifications delivered within 10 minutes for small brochures, 1 hour for large
- No errors in CloudWatch Logs for happy path
- DynamoDB records accurate metadata for all brochures
- Deduplication prevents reprocessing of identical files

**Production readiness**:
- All unit tests pass (> 90% code coverage)
- All integration tests pass
- Load test with 500 brochures succeeds
- Security review completed (IAM roles, S3 policies, encryption verified)
- CloudWatch dashboards and alarms configured
- Runbook documented and tested (simulate 3 failure scenarios)
- SES production access granted, sender domain verified
- Cost estimate validated (actual spend within 10% of estimate after 1-week pilot)

---

## 9. Deployment & Infrastructure Suggestions

### 9.1 Infrastructure as Code (IaC)

**Recommended tool**: AWS SAM (Serverless Application Model) or Terraform.

**SAM benefits**:
- Native Lambda and API Gateway support
- Simplified CloudFormation syntax
- Built-in local testing with sam local
- CI/CD integration with sam deploy

**Terraform benefits**:
- Multi-cloud portability (future-proofing)
- Mature ecosystem, extensive AWS provider
- State management with remote backends

**Choice**: Use SAM for pure serverless, Terraform if org already standardized on it.

**Project structure** (conceptual, no code):
- /infra: SAM template.yaml or Terraform .tf files
- /lambdas: Each Lambda function in separate directory
- /config: Environment-specific configurations (dev, staging, prod)
- /scripts: Deployment scripts, CloudWatch dashboard JSON exports

**IaC components to define**:
- S3 buckets with lifecycle policies
- Lambda functions with environment variables, IAM roles, layers
- DynamoDB table with GSIs
- EventBridge rules
- SNS topics and subscriptions
- IAM roles and policies
- CloudWatch Alarms (use Terraform or CloudFormation)
- SES configuration sets (limited CloudFormation support; may require manual setup)

### 9.2 CI/CD Pipeline

**Pipeline stages**:
1. **Source**: Git repository (GitHub, GitLab, AWS CodeCommit)
2. **Build**:
   - Lint Lambda code (pylint, eslint)
   - Run unit tests
   - Package Lambda functions (zip with dependencies)
   - Validate SAM/Terraform templates
3. **Deploy to Dev**:
   - Deploy infra and Lambda functions to dev environment
   - Run integration tests
   - Verify CloudWatch Logs
4. **Deploy to Staging**:
   - Deploy to staging environment
   - Run load tests
   - Manual approval gate
5. **Deploy to Production**:
   - Deploy to production environment
   - Monitor CloudWatch metrics for 30 minutes
   - Rollback on alarm

**Pipeline tools**:
- AWS CodePipeline + CodeBuild (native AWS)
- GitHub Actions (popular for open-source and SaaS)
- GitLab CI/CD (if using GitLab)

**Deployment commands** (conceptual):
- SAM: sam build, sam deploy --guided (first time), sam deploy (subsequent)
- Terraform: terraform init, terraform plan, terraform apply

**Rollback strategy**:
- Lambda: Use function versions and aliases, update alias to previous version
- DynamoDB/S3: Cannot rollback; use backups if schema changes
- Infra: Terraform/CloudFormation rollback via previous state

### 9.3 Environment Variables and Configuration

**Lambda environment variables** (per function):
- CrawlerLambda:
  - SOURCE_BUCKET_NAME
  - METADATA_TABLE_NAME
  - STORE_CONFIG_S3_KEY
  - LOG_LEVEL (INFO, DEBUG)
- ProcessBrochureLambda:
  - SOURCE_BUCKET_NAME
  - OUTPUT_BUCKET_NAME
  - METADATA_TABLE_NAME
  - TEXTRACT_SNS_TOPIC_ARN
  - TEXTRACT_ROLE_ARN
  - SYNC_PAGE_THRESHOLD
  - SYNC_SIZE_THRESHOLD_MB
  - LOG_LEVEL
- TextractCallbackLambda:
  - OUTPUT_BUCKET_NAME
  - METADATA_TABLE_NAME
  - LOG_LEVEL
- KeywordSearchLambda:
  - OUTPUT_BUCKET_NAME
  - METADATA_TABLE_NAME
  - KEYWORD_FOUND_TOPIC_ARN
  - KEYWORD_CONFIG_S3_KEY
  - LOG_LEVEL

**Configuration management**:
- Store environment-specific values in SAM/Terraform parameter files (dev.json, prod.json)
- Never hardcode bucket names, ARNs, or secrets in Lambda code
- Use AWS Systems Manager Parameter Store for non-sensitive config (optional, adds complexity)
- Use AWS Secrets Manager for SES credentials or API keys (if needed)

### 9.4 Secrets Management

**Secrets to manage**:
- SES SMTP credentials (if using SMTP instead of SES API)
- API keys for store brochure URLs (if required)
- Future: Slack webhook URLs, third-party integrations

**Approach**:
- Store in AWS Secrets Manager
- Grant Lambda IAM role secretsmanager:GetSecretValue permission
- Retrieve at Lambda initialization (cache for function lifetime)
- Rotate secrets annually or on compromise

### 9.5 Pre-Deployment Checklist

- [ ] SES sender email verified
- [ ] SES recipient emails verified (sandbox) or production access granted
- [ ] SES DKIM and SPF DNS records configured
- [ ] S3 bucket names available (unique globally)
- [ ] DynamoDB table name available (unique per region/account)
- [ ] IAM roles and policies reviewed for least-privilege
- [ ] CloudWatch Logs retention configured
- [ ] EventBridge schedule expression validated
- [ ] keyword-config.json uploaded to S3 config bucket
- [ ] Test brochures prepared (small, large, corrupted)
- [ ] All Lambda functions packaged with dependencies
- [ ] SAM/Terraform templates validated (sam validate or terraform validate)
- [ ] Cost estimate reviewed and approved

---

## 10. Estimated Cost Model

### 10.1 Cost Drivers

**Assumptions** for cost estimate:
- 300 brochures/month
- Average 10 pages per brochure
- 50 keyword matches per month
- 80% async Textract (240 brochures), 20% sync (60 brochures)
- 10 stores monitored
- Daily crawl schedule (30 crawls/month)

**Textract**:
- Sync DetectDocumentText: $1.50 per 1000 pages
  - 60 brochures × 10 pages = 600 pages
  - Cost: 600 / 1000 × $1.50 = $0.90/month
- Async StartDocumentTextDetection: $1.50 per 1000 pages
  - 240 brochures × 10 pages = 2400 pages
  - Cost: 2400 / 1000 × $1.50 = $3.60/month
- **Total Textract: $4.50/month**

**Lambda**:
- Invocations:
  - CrawlerLambda: 30 invocations/month (daily crawl)
  - ProcessBrochureLambda: 300 invocations
  - TextractCallbackLambda: 240 invocations (async jobs only)
  - KeywordSearchLambda: 300 invocations
  - Total: 870 invocations/month
- Lambda free tier: 1M requests/month, 400,000 GB-seconds/month
- **Cost: $0 (within free tier)**
- If exceeding free tier: $0.20 per 1M requests + $0.0000166667 per GB-second
  - Estimate: 870 × 5 seconds avg × 1 GB = 4,350 GB-seconds = $0.07/month

**S3**:
- Storage:
  - 300 brochures × 2 MB avg = 600 MB source
  - 300 Textract JSON × 500 KB avg = 150 MB output
  - Total: 750 MB/month (cumulative growth: 9 GB/year)
  - Cost: 9 GB × $0.023/GB = $0.21/month (by end of year)
- Requests:
  - PUT: 300 (uploads) + 300 (Textract results) = 600
  - GET: 300 (ProcessBrochure) + 300 (KeywordSearch) = 600
  - Cost: 600 PUT × $0.005/1000 + 600 GET × $0.0004/1000 = $0.003 + $0.0002 = $0.0032/month
- **Total S3: ~$0.25/month**

**DynamoDB**:
- On-demand pricing: $1.25 per million write requests, $0.25 per million read requests
- Write requests: 300 (brochure metadata) + 300 (status updates) × 3 avg = 1,200/month
- Read requests: 300 (deduplication checks) + 300 (keyword config) = 600/month
- Cost: 1,200 / 1,000,000 × $1.25 + 600 / 1,000,000 × $0.25 = $0.0015 + $0.00015 = $0.002/month
- Storage: 300 items × 5 KB avg = 1.5 MB, Cost: 1.5 MB × $0.25/GB = negligible
- **Total DynamoDB: ~$0.01/month**

**SNS**:
- Publishes: 240 (Textract callbacks) + 50 (keyword matches) = 290/month
- Email deliveries: 50/month
- Cost: 290 / 1,000,000 × $0.50 (publish) + 50 × $0 (email via SES, not SNS-to-email) = $0.0001/month
- **Total SNS: ~$0.01/month**

**SES**:
- 50 emails/month
- Cost: First 62,000 emails/month free (if sent from EC2 or Lambda)
- **Total SES: $0/month**

**CloudWatch**:
- Logs ingestion: Assume 10 MB/month
- Cost: First 5 GB free
- Metrics: 10 custom metrics × $0.30 = $3.00/month
- Alarms: 5 alarms × $0.10 = $0.50/month
- **Total CloudWatch: $3.50/month**

**Data transfer**:
- CrawlerLambda downloads: 300 × 2 MB = 600 MB/month
- Data transfer in: Free
- Data transfer out: Minimal (email sends are small), within free tier
- **Total data transfer: $0/month**

**Total estimated cost: ~$8.25/month**

### 10.2 Cost Optimization Strategies

**Reduce Textract costs** (largest driver):
- Use synchronous API for all single-page images (cheaper startup overhead)
- Implement page count limit (reject > 50 pages) to avoid runaway costs
- Cache OCR results for duplicate files (already implemented via deduplication)
- Negotiate with stores to provide text-based PDFs instead of scanned images (avoid OCR entirely)

**Reduce CloudWatch costs**:
- Reduce custom metric count (consolidate related metrics)
- Use CloudWatch Logs Insights instead of metric filters (pay per query vs. continuous)
- Reduce alarm count (use composite alarms)

**Reduce S3 costs**:
- Implement lifecycle rules aggressively (move to Glacier after 30 days instead of 90)
- Delete Textract JSON after 180 days (if no longer needed)
- Compress Textract JSON before storing (gzip can reduce size by 70%)

**Reduce Lambda costs**:
- Optimize memory allocation (reduce from 1024 MB to 512 MB if performance allows)
- Reduce timeout values (shorter timeout = lower cost if function completes faster)

**Monitor actual costs**:
- Enable AWS Cost Explorer
- Tag all resources with project=brochure-scanner for cost allocation
- Set up daily cost reports
- Review monthly and adjust estimates

### 10.3 Scaling Cost Impact

**At 1,000 brochures/month**:
- Textract: $15/month
- Lambda: $0.20/month (likely still in free tier)
- S3: $1/month
- DynamoDB: $0.05/month
- CloudWatch: $3.50/month
- **Total: ~$20/month**

**At 10,000 brochures/month**:
- Textract: $150/month
- Lambda: $2/month
- S3: $10/month
- DynamoDB: $0.50/month
- CloudWatch: $5/month
- **Total: ~$168/month**

**Cost guardrails**:
- Set AWS Budgets alert at $50/month
- CloudWatch alarm on daily Textract page count > 500 (indicates 15,000/month pace)
- Require manual approval for processing brochures > 50 pages

---

## 11. Assumptions

### 11.1 Technical Assumptions
- Average brochure size: 2 MB
- Average brochure page count: 10 pages
- 80% of brochures require async Textract (>= 5 pages)
- Textract async job completion time: 5-30 minutes
- Textract OCR accuracy: > 95% (AWS-provided estimate for clear text)
- Keyword matching is case-insensitive and whole-word
- Brochure file formats: PDF, PNG, JPEG, TIFF (no other formats supported)
- Stores publish brochures at consistent URLs (no authentication required)
- Brochures are publicly accessible (no paywall or login)

### 11.2 Business Assumptions
- Number of stores monitored: 10-50
- Keyword list per store: 5-100 keywords
- Brochure publication frequency: Weekly or daily per store
- Expected keyword match rate: 15-20% (50 matches per 300 brochures)
- Email notification recipients: 1-5 per store
- Acceptable notification latency: 2 hours
- System availability requirement: 99.5% (acceptable for non-critical monitoring)

### 11.3 Operational Assumptions
- Dev team has AWS experience (Lambda, S3, DynamoDB, IAM)
- On-call support available for production issues (4-hour response time)
- Budget for AWS costs: $200/month initially, can scale to $500/month
- SES production access can be obtained within 2 weeks
- Store URLs remain stable (no frequent changes)
- No PII or sensitive data in brochures (no GDPR/HIPAA requirements)
- English-language brochures only (no multi-language OCR required)

### 11.4 Constraints
- AWS-only solution (no third-party OCR services)
- Serverless architecture (no EC2, ECS, or Kubernetes)
- Minimal managed infrastructure (no RDS, ElastiCache)
- No custom machine learning models (use Textract as-is)
- Email notifications only (no Slack, SMS, or webhooks in MVP)
- Single AWS region deployment (no multi-region for MVP)

### 11.5 Future Enhancements Not in Scope
- Real-time brochure monitoring (webhook-based instead of scheduled crawling)
- Image analysis (detect product images, logos, barcodes)
- Advanced NLP (sentiment analysis, pricing extraction)
- Multi-language OCR and translation
- User interface for managing stores and keywords (API-only in MVP)
- Integration with CRM or marketing automation platforms
- Historical analytics dashboard (trend analysis, keyword frequency over time)
- Mobile app notifications

---

## 12. Appendices

### 12.1 Glossary
- **Brochure**: Retail marketing document (PDF or image) containing product promotions
- **OCR**: Optical Character Recognition, converting images to searchable text
- **Textract**: AWS managed OCR service
- **Keyword matching**: Searching for specific words/phrases in OCR text
- **Store**: Retail business entity (e.g., Walmart, Target)
- **Deduplication**: Preventing reprocessing of identical files based on content hash

### 12.2 References
- AWS Textract documentation: https://docs.aws.amazon.com/textract/
- AWS Lambda best practices: https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html
- AWS SES developer guide: https://docs.aws.amazon.com/ses/latest/dg/
- DynamoDB best practices: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html

### 12.3 Revision History
- Version 1.0 (2025-11-18): Initial technical specification

---

**End of Technical Specification**
