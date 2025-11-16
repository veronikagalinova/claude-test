# Technical Specification: Retail Brochure Monitoring System

**Version:** 1.0
**Date:** November 2025
**Status:** Implementation Ready

---

## 1. Executive Summary

This document outlines the technical architecture for a retail brochure monitoring system that automatically ingests promotional materials (PDFs, images, web catalogs), extracts text content via OCR, detects specified keywords, and delivers notifications to users when matches are found.

---

## 2. High-Level Architecture

### 2.1 System Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Data Sources   │────▶│  Ingestion Layer │────▶│  Processing     │
│  (PDFs, Images, │     │  (Scheduler +    │     │  Pipeline       │
│   Web Catalogs) │     │   Collectors)    │     │  (OCR + NLP)    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                          │
                                                          ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Notification   │◀────│  Keyword Match   │◀────│  Content Store  │
│  Service        │     │  Engine          │     │  (Database +    │
│  (Email/Alerts) │     │                  │     │   Search Index) │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

### 2.2 Core Components

| Component | Responsibility | Communication |
|-----------|---------------|---------------|
| **Scheduler Service** | Orchestrates periodic scans (cron-based) | Internal message queue |
| **Ingestion Module** | Fetches brochures from configured sources | HTTP/S, FTP, file system |
| **OCR Engine** | Extracts text from images/scanned PDFs | Synchronous processing |
| **Content Processor** | Normalizes and indexes extracted text | Internal service calls |
| **Keyword Detection Engine** | Pattern matching and search operations | Database/search queries |
| **Notification Service** | Dispatches alerts via configured channels | SMTP, webhook integrations |
| **Admin API** | Configuration management and monitoring | REST API |
| **Data Store** | Persists documents, metadata, and results | PostgreSQL + Elasticsearch |

### 2.3 Data Flow

1. **Ingestion**: Scheduler triggers collectors → Fetch documents from sources
2. **Pre-processing**: Determine document type → Route to appropriate processor
3. **Text Extraction**: OCR for images/scanned PDFs, direct parsing for digital PDFs
4. **Indexing**: Store extracted text with metadata in search-optimized format
5. **Detection**: Run keyword queries against indexed content
6. **Notification**: Generate and dispatch alerts for matches
7. **Archival**: Store results and update processing status

---

## 3. System Requirements

### 3.1 Functional Requirements

- **FR-1**: Support PDF documents (both digital and scanned)
- **FR-2**: Support image formats (JPG, PNG, TIFF, WebP)
- **FR-3**: Support web page scraping for online catalogs
- **FR-4**: Configure multiple keyword search terms per user/subscription
- **FR-5**: Schedule automated scans (daily, weekly, custom intervals)
- **FR-6**: Send email notifications with match details and context
- **FR-7**: Track processing history and match results
- **FR-8**: Provide administrative interface for configuration

### 3.2 Non-Functional Requirements

- **NFR-1**: Process 100+ documents per scan cycle
- **NFR-2**: OCR processing time < 30 seconds per page
- **NFR-3**: Notification delivery within 5 minutes of match detection
- **NFR-4**: System availability 99.5% uptime
- **NFR-5**: Support concurrent processing of multiple documents
- **NFR-6**: Retain historical data for 12 months minimum
- **NFR-7**: GDPR-compliant data handling and user consent

### 3.3 Infrastructure Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 4 cores | 8+ cores |
| RAM | 8 GB | 16+ GB |
| Storage | 100 GB SSD | 500 GB SSD |
| Network | 100 Mbps | 1 Gbps |

---

## 4. Technology Stack

### 4.1 Core Framework

- **Language**: Java 17+ (LTS)
- **Framework**: Spring Boot 3.x
- **Build Tool**: Maven or Gradle
- **Containerization**: Docker with Docker Compose

### 4.2 Data Layer

- **Primary Database**: PostgreSQL 15+
  - Document metadata, user configurations, processing history
- **Search Engine**: Elasticsearch 8.x
  - Full-text indexing and keyword search
- **Cache**: Redis 7.x
  - Session management, rate limiting, temporary storage
- **Message Queue**: RabbitMQ or Apache Kafka
  - Async processing, task distribution

### 4.3 OCR and Document Processing

- **Primary OCR**: Tesseract OCR 5.x (open-source)
  - Fallback: Google Cloud Vision API or AWS Textract
- **PDF Processing**: Apache PDFBox 3.x
- **Image Processing**: Apache Commons Imaging, ImageMagick
- **Web Scraping**: Jsoup for HTML parsing

### 4.4 Communication and Integration

- **Email Service**: Spring Mail with SMTP
  - Recommended providers: SendGrid, AWS SES, Mailgun
- **HTTP Client**: Spring WebClient (reactive)
- **REST API**: Spring Web MVC with OpenAPI 3.0 documentation

### 4.5 Monitoring and Operations

- **Logging**: SLF4J with Logback, structured JSON logs
- **Metrics**: Micrometer with Prometheus
- **Monitoring**: Grafana dashboards
- **Health Checks**: Spring Boot Actuator
- **APM**: Elastic APM or Jaeger for distributed tracing

---

## 5. Core Workflows

### 5.1 Document Ingestion Workflow

**Trigger**: Scheduled job or manual API call

**Steps**:
1. Scheduler service initiates scan based on configured schedule
2. Load active source configurations from database
3. For each source:
   - Validate source accessibility
   - Determine source type (URL, FTP, local path, S3 bucket)
   - Fetch document list (new/modified since last scan)
   - Download documents to temporary processing queue
4. Create processing job record with status PENDING
5. Enqueue job for OCR pipeline
6. Update source last-scan timestamp

**Failure Handling**:
- Retry failed downloads up to 3 times with exponential backoff
- Mark source as UNHEALTHY after consecutive failures
- Alert administrators for persistent source issues

### 5.2 OCR Processing Workflow

**Trigger**: New document in processing queue

**Steps**:
1. Dequeue document processing job
2. Classify document type:
   - Digital PDF → Extract text directly via PDFBox
   - Scanned PDF → Convert pages to images → OCR
   - Image files → Direct OCR processing
   - Web content → HTML parsing and text extraction
3. Pre-process for OCR:
   - Image enhancement (contrast, deskew, noise reduction)
   - Page segmentation for multi-column layouts
4. Execute OCR engine:
   - Process page-by-page for large documents
   - Apply language detection for optimal results
5. Post-process extracted text:
   - Remove artifacts and formatting noise
   - Normalize whitespace and special characters
   - Extract metadata (dates, store names, prices)
6. Store processed text and metadata
7. Index content in Elasticsearch
8. Update job status to PROCESSED
9. Trigger keyword detection phase

**Performance Optimization**:
- Process pages in parallel for multi-page documents
- Cache OCR models in memory
- Use GPU acceleration if available (CUDA support)

### 5.3 Keyword Detection Workflow

**Trigger**: Document indexed in search engine

**Steps**:
1. Load active keyword subscriptions
2. For each subscription:
   - Build search query with configured keywords
   - Apply filters (date range, source category, store)
   - Execute search against document content
3. For each match:
   - Extract context window (surrounding text)
   - Calculate confidence score
   - Identify specific page/location in document
4. Deduplicate results (avoid re-alerting on same content)
5. Store match results with references
6. Queue notifications for delivery

**Search Features**:
- Exact phrase matching
- Fuzzy matching for OCR errors (Levenshtein distance)
- Synonym expansion (diapers → nappies)
- Exclusion patterns (false positive filtering)
- Case-insensitive matching

### 5.4 Notification Workflow

**Trigger**: Keyword matches detected

**Steps**:
1. Aggregate matches by user/subscription
2. Apply notification preferences:
   - Immediate vs. digest mode
   - Minimum match threshold
   - Quiet hours configuration
3. Generate notification content:
   - Match summary with keyword and source
   - Context excerpt showing keyword in text
   - Link to original document (if permitted)
   - Confidence score and match location
4. Format for delivery channel (email HTML template)
5. Dispatch via configured provider
6. Record delivery status and timestamp
7. Handle bounces and delivery failures

**Email Template Structure**:
- Subject: "[Brochure Alert] {keyword} found in {source}"
- Header: Summary statistics
- Body: Match details with context
- Footer: Management links (unsubscribe, preferences)

---

## 6. Data Models

### 6.1 Core Entities

**Source Configuration**
- ID, name, type (PDF_URL, WEB_PAGE, FTP, S3)
- Connection details (URL, credentials)
- Scan schedule (cron expression)
- Status (ACTIVE, PAUSED, UNHEALTHY)
- Last scan timestamp

**Document**
- ID, source reference
- Original file path/URL
- Document type, page count
- Processing status
- Created/modified timestamps
- Content hash (deduplication)

**Extracted Content**
- Document reference
- Page number
- Raw text content
- Cleaned/normalized text
- OCR confidence score
- Processing metadata

**Keyword Subscription**
- ID, user reference
- Keyword patterns (list)
- Source filters
- Notification preferences
- Active/inactive status

**Match Result**
- Subscription reference
- Document reference
- Matched keyword
- Context excerpt
- Confidence score
- Match location (page, position)
- Notification status

### 6.2 Elasticsearch Index Schema

**Document Index**:
- document_id (keyword)
- source_id (keyword)
- content (text, analyzed)
- metadata (nested object)
- processed_date (date)
- source_category (keyword)

**Search Configuration**:
- Custom analyzer for retail terminology
- Edge n-gram tokenizer for partial matching
- Stop words filter
- Stemming for linguistic variations

---

## 7. Error Handling Strategy

### 7.1 Error Categories

| Category | Examples | Handling Approach |
|----------|----------|-------------------|
| **Transient** | Network timeout, service unavailable | Retry with exponential backoff |
| **Data Quality** | Corrupted PDF, unreadable image | Log warning, skip with notification |
| **Configuration** | Invalid credentials, missing settings | Alert admin, pause source |
| **Resource** | Out of memory, disk full | Circuit breaker, scale resources |
| **External Service** | OCR API failure, email bounce | Fallback provider, queue retry |

### 7.2 Retry Policies

- **Document Download**: 3 retries, 1s/2s/4s backoff
- **OCR Processing**: 2 retries, different engine on failure
- **Email Delivery**: 5 retries over 24 hours
- **Database Operations**: 3 retries with connection pool refresh

### 7.3 Circuit Breaker Configuration

- **Failure Threshold**: 50% failures in 10-request window
- **Open State Duration**: 60 seconds
- **Half-Open Probes**: 3 test requests
- **Monitored Operations**: External API calls, OCR processing

### 7.4 Dead Letter Queue

- Store persistently failed jobs for manual review
- Capture full context (document, error, retry history)
- Admin interface for reprocessing or dismissal
- Automatic cleanup after configurable retention period

---

## 8. Monitoring and Observability

### 8.1 Key Metrics

**Processing Metrics**:
- Documents ingested per hour
- Average OCR processing time
- OCR success/failure rate
- Queue depth and processing lag

**Business Metrics**:
- Keyword matches detected
- Notifications sent/delivered
- Active subscriptions
- Source health status

**Infrastructure Metrics**:
- CPU/memory utilization
- Database connection pool usage
- Elasticsearch query latency
- Disk space consumption

### 8.2 Alerting Rules

| Condition | Severity | Action |
|-----------|----------|--------|
| Processing queue > 1000 items | Warning | Scale workers |
| OCR failure rate > 10% | Critical | Check OCR service |
| Email delivery failures > 5% | High | Verify SMTP config |
| Database connections exhausted | Critical | Immediate investigation |
| Disk usage > 80% | Warning | Cleanup or expand |

### 8.3 Logging Standards

- **Log Levels**: ERROR (failures), WARN (degraded), INFO (business events), DEBUG (technical detail)
- **Structured Format**: JSON with consistent fields
- **Required Fields**: timestamp, service, correlation_id, event_type, message
- **Sensitive Data**: Mask emails, credentials, personal information
- **Retention**: 30 days hot storage, 1 year cold storage

### 8.4 Health Check Endpoints

- `/actuator/health`: Overall system health
- `/actuator/health/db`: Database connectivity
- `/actuator/health/elasticsearch`: Search engine status
- `/actuator/health/ocr`: OCR service availability
- `/actuator/health/mail`: Email service status

---

## 9. Security Considerations

### 9.1 Authentication and Authorization

- **API Authentication**: OAuth 2.0 with JWT tokens
- **Service-to-Service**: Mutual TLS or API keys
- **Admin Access**: Role-based access control (RBAC)
- **Rate Limiting**: Per-user and per-IP limits

### 9.2 Data Protection

- **At Rest**: AES-256 encryption for stored documents
- **In Transit**: TLS 1.3 for all communications
- **Credentials**: HashiCorp Vault or AWS Secrets Manager
- **PII Handling**: Minimize collection, anonymize where possible

### 9.3 Input Validation

- File type verification (magic bytes, not just extension)
- Maximum file size limits (prevent DoS)
- Sanitize extracted text before storage
- Validate all API inputs against schema

---

## 10. Scalability Considerations

### 10.1 Horizontal Scaling

**Stateless Services**:
- Multiple ingestion worker instances
- OCR processing pool (scale based on queue depth)
- Notification service replicas

**Scaling Triggers**:
- Auto-scale when queue depth > 100 items
- Scale down during low-activity periods
- Reserve capacity for scheduled scan peaks

### 10.2 Data Partitioning

**PostgreSQL**:
- Partition processing_history by date (monthly)
- Partition match_results by subscription_id
- Archive old data to cold storage

**Elasticsearch**:
- Index-per-month pattern for documents
- Configure index lifecycle management (ILM)
- Optimize shard allocation for query patterns

### 10.3 Caching Strategy

- **Source Configurations**: Cache with 5-minute TTL
- **Keyword Patterns**: Cache compiled regex patterns
- **User Preferences**: Cache with invalidation on update
- **Document Hashes**: Cache for deduplication checks

### 10.4 Performance Optimizations

- Batch processing for bulk document ingestion
- Connection pooling for all external services
- Async processing with backpressure handling
- Index optimization schedules (off-peak hours)

---

## 11. Required Third-Party Services

### 11.1 Cloud Infrastructure (Choose One)

**AWS**:
- EC2/ECS for compute
- RDS for PostgreSQL
- S3 for document storage
- SQS for message queuing
- SES for email delivery

**Google Cloud Platform**:
- GKE for container orchestration
- Cloud SQL for PostgreSQL
- Cloud Storage for documents
- Pub/Sub for messaging
- Cloud Vision API for OCR

**Azure**:
- AKS for Kubernetes
- Azure Database for PostgreSQL
- Blob Storage for documents
- Service Bus for messaging

### 11.2 Essential Services

| Service | Purpose | Providers |
|---------|---------|-----------|
| **OCR** | Text extraction | Tesseract (self-hosted), Google Vision, AWS Textract, Azure Computer Vision |
| **Email Delivery** | Notifications | SendGrid, AWS SES, Mailgun, Postmark |
| **Search** | Keyword matching | Elasticsearch (self-hosted), AWS OpenSearch, Elastic Cloud |
| **Secrets Management** | Credential storage | HashiCorp Vault, AWS Secrets Manager, Azure Key Vault |

### 11.3 Optional Enhancements

- **CDN**: CloudFront/CloudFlare for static assets
- **APM**: Datadog, New Relic, or Elastic APM
- **Error Tracking**: Sentry or Rollbar
- **Log Management**: ELK Stack, Splunk, or Datadog Logs

---

## 12. Deployment Architecture

### 12.1 Container Strategy

- **Base Images**: Eclipse Temurin (Java) on Alpine Linux
- **Multi-Stage Builds**: Separate build and runtime stages
- **Image Scanning**: Vulnerability scanning in CI/CD
- **Registry**: Private container registry with versioning

### 12.2 Orchestration

**Kubernetes Deployment**:
- Namespace isolation per environment
- ConfigMaps for application configuration
- Secrets for sensitive data
- Horizontal Pod Autoscaler for workers
- Persistent Volume Claims for OCR models

**Service Mesh** (Optional):
- Istio or Linkerd for advanced traffic management
- Automatic mTLS between services
- Observability integration

### 12.3 Environment Strategy

| Environment | Purpose | Data | Scale |
|-------------|---------|------|-------|
| **Development** | Feature development | Synthetic | Minimal |
| **Staging** | Integration testing | Anonymized production sample | Production-like |
| **Production** | Live system | Real data | Full scale |

---

## 13. Implementation Phases

### Phase 1: Foundation (Weeks 1-3)
- Project setup and infrastructure provisioning
- Core database schema and migrations
- Basic ingestion for PDF documents
- Initial OCR integration with Tesseract
- Simple keyword matching (exact match)

### Phase 2: Core Features (Weeks 4-6)
- Email notification service
- Scheduling service with cron support
- Web scraping capability
- Elasticsearch integration for full-text search
- Admin API for configuration

### Phase 3: Enhancement (Weeks 7-9)
- Advanced OCR (image preprocessing, multi-language)
- Fuzzy matching and synonym support
- User subscription management
- Monitoring and alerting setup
- Performance optimization

### Phase 4: Production Readiness (Weeks 10-12)
- Security hardening and audit
- Load testing and capacity planning
- Documentation and runbooks
- Disaster recovery procedures
- Production deployment and validation

---

## 14. Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Poor OCR accuracy | High | Medium | Multiple OCR engines, preprocessing pipeline |
| Source unavailability | Medium | High | Retry logic, health monitoring, fallback sources |
| Email deliverability issues | High | Medium | Reputable provider, proper DNS setup, monitoring |
| Data storage growth | Medium | High | Archival policy, compression, lifecycle management |
| Performance bottlenecks | High | Medium | Load testing, horizontal scaling, caching |
| Third-party API costs | Medium | Medium | Usage monitoring, budget alerts, cost optimization |

---

## 15. Success Criteria

- **Functional**: Successfully process 95%+ of submitted documents
- **Accuracy**: OCR text extraction accuracy > 90% for clear documents
- **Performance**: End-to-end processing under 2 minutes per document
- **Reliability**: 99.5% uptime for production system
- **Notification**: Delivery success rate > 98%
- **User Satisfaction**: Keyword matches correctly identified > 95% of time

---

## Appendix A: Glossary

- **OCR**: Optical Character Recognition - technology to extract text from images
- **Digital PDF**: PDF with embedded text (copy-paste capable)
- **Scanned PDF**: PDF containing images of pages (requires OCR)
- **Ingestion**: Process of collecting and importing documents into the system
- **Keyword Subscription**: User-defined search terms and notification preferences
- **Context Window**: Text surrounding a keyword match for relevance

---

## Appendix B: References

- Spring Boot Documentation: https://docs.spring.io/spring-boot/
- Tesseract OCR: https://github.com/tesseract-ocr/tesseract
- Elasticsearch Guide: https://www.elastic.co/guide/
- Apache PDFBox: https://pdfbox.apache.org/
- OWASP Security Guidelines: https://owasp.org/

---

**Document Owner**: Software Architecture Team
**Review Cycle**: Quarterly
**Next Review**: February 2026
