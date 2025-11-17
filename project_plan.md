# Project Plan: Retail Brochure Monitoring System

**Version:** 1.0
**Created:** November 2025
**Based on:** Technical Specification v1.0

---

## Table of Contents

1. [Phase-Based TODO Lists](#phase-based-todo-lists)
2. [File Tree Structure](#file-tree-structure)
3. [Module Boundaries and Responsibilities](#module-boundaries-and-responsibilities)
4. [Interface Contracts](#interface-contracts)

---

## Phase-Based TODO Lists

### Phase 1: Foundation (Weeks 1-3)

#### Week 1: Project Setup and Infrastructure

- [ ] Initialize Spring Boot 3.x project with Maven/Gradle
- [ ] Configure project structure following domain-driven design
- [ ] Set up Docker and Docker Compose configuration
- [ ] Configure PostgreSQL 15+ database container
- [ ] Set up Redis 7.x container for caching
- [ ] Configure RabbitMQ container for message queuing
- [ ] Implement database migration framework (Flyway/Liquibase)
- [ ] Create initial database schema migrations
- [ ] Set up application profiles (dev, staging, production)
- [ ] Configure logging with SLF4J and Logback (JSON structured)
- [ ] Implement health check endpoints via Spring Boot Actuator
- [ ] Set up CI/CD pipeline skeleton
- [ ] Configure code quality tools (checkstyle, spotbugs)
- [ ] Create base exception handling framework
- [ ] Set up integration test infrastructure

#### Week 2: Core Data Models and Basic Ingestion

- [ ] Implement Source Configuration entity and repository
- [ ] Implement Document entity and repository
- [ ] Implement Extracted Content entity and repository
- [ ] Create database indexes for performance optimization
- [ ] Implement basic PDF document ingestion service
- [ ] Add support for digital PDF text extraction via PDFBox
- [ ] Implement document type detection (magic bytes validation)
- [ ] Create file storage abstraction layer
- [ ] Implement document hash calculation for deduplication
- [ ] Build basic HTTP client for URL-based document fetching
- [ ] Add retry logic with exponential backoff for downloads
- [ ] Implement processing job queue using RabbitMQ
- [ ] Create document processing status tracking
- [ ] Add input validation and sanitization
- [ ] Write unit tests for core entities (>80% coverage)

#### Week 3: Initial OCR Integration

- [ ] Integrate Tesseract OCR 5.x library
- [ ] Implement OCR configuration and language detection
- [ ] Create image preprocessing pipeline (contrast, deskew)
- [ ] Build scanned PDF to image converter
- [ ] Implement page-by-page OCR processing
- [ ] Add OCR confidence score calculation
- [ ] Create text post-processing (artifact removal, normalization)
- [ ] Implement simple exact keyword matching
- [ ] Create Keyword Subscription entity and repository
- [ ] Implement Match Result entity and repository
- [ ] Build basic keyword search against extracted text
- [ ] Add processing metrics collection
- [ ] Implement basic error handling for OCR failures
- [ ] Create OCR fallback mechanism structure
- [ ] Write integration tests for OCR pipeline

### Phase 2: Core Features (Weeks 4-6)

#### Week 4: Notification and Scheduling Services

- [ ] Integrate Spring Mail with SMTP configuration
- [ ] Create email template engine (Thymeleaf)
- [ ] Design HTML email templates for match notifications
- [ ] Implement notification preference entity
- [ ] Build notification aggregation service
- [ ] Add immediate vs. digest notification modes
- [ ] Implement quiet hours configuration
- [ ] Create email delivery tracking and status recording
- [ ] Add bounce and failure handling
- [ ] Implement scheduler service with Quartz or Spring Scheduler
- [ ] Create cron expression parser and validator
- [ ] Build scan job orchestration logic
- [ ] Implement source health monitoring
- [ ] Add consecutive failure tracking and source status updates
- [ ] Create admin alerts for source health issues

#### Week 5: Web Scraping and Search Integration

- [ ] Integrate Jsoup for HTML parsing
- [ ] Implement web page content extractor
- [ ] Add support for dynamic content loading detection
- [ ] Create web catalog structure parser
- [ ] Implement rate limiting for web scraping
- [ ] Set up Elasticsearch 8.x cluster configuration
- [ ] Design document index schema with custom analyzers
- [ ] Implement edge n-gram tokenizer for partial matching
- [ ] Configure stop words and stemming filters
- [ ] Create Elasticsearch indexing service
- [ ] Build full-text search query builder
- [ ] Implement fuzzy matching for OCR error tolerance
- [ ] Add synonym expansion capabilities
- [ ] Create exclusion pattern filtering
- [ ] Implement search result pagination and sorting

#### Week 6: Admin API Development

- [ ] Design REST API schema following OpenAPI 3.0
- [ ] Implement source configuration CRUD endpoints
- [ ] Create keyword subscription management endpoints
- [ ] Build user preference management API
- [ ] Add processing job status query endpoints
- [ ] Implement match result retrieval API
- [ ] Create system health and metrics endpoints
- [ ] Add API input validation using Bean Validation
- [ ] Implement request/response DTOs
- [ ] Add API versioning strategy
- [ ] Create API documentation with Springdoc OpenAPI
- [ ] Implement basic authentication (API keys)
- [ ] Add rate limiting per API client
- [ ] Create admin dashboard data endpoints
- [ ] Write API integration tests

### Phase 3: Enhancement (Weeks 7-9)

#### Week 7: Advanced OCR Features

- [ ] Implement image enhancement algorithms (noise reduction)
- [ ] Add page segmentation for multi-column layouts
- [ ] Integrate Google Cloud Vision API as fallback OCR
- [ ] Create OCR provider abstraction layer
- [ ] Implement automatic OCR provider selection based on quality
- [ ] Add multi-language OCR support
- [ ] Create language detection service
- [ ] Implement GPU acceleration detection (CUDA)
- [ ] Add parallel page processing for large documents
- [ ] Optimize OCR model caching strategy
- [ ] Implement image format support (JPG, PNG, TIFF, WebP)
- [ ] Add document metadata extraction (dates, prices, store names)
- [ ] Create confidence-based result filtering
- [ ] Implement OCR performance metrics tracking
- [ ] Write comprehensive OCR accuracy tests

#### Week 8: User Management and Advanced Matching

- [ ] Implement user entity and authentication service
- [ ] Add OAuth 2.0 with JWT token support
- [ ] Create role-based access control (RBAC)
- [ ] Implement user subscription management
- [ ] Build subscription quota and limits
- [ ] Add advanced keyword pattern syntax (regex support)
- [ ] Implement phrase matching with word proximity
- [ ] Create confidence score calculation for matches
- [ ] Add match location tracking (page, position)
- [ ] Implement deduplication logic for match results
- [ ] Create context window extraction for matches
- [ ] Build match result aggregation by subscription
- [ ] Add historical match analysis capabilities
- [ ] Implement user activity logging
- [ ] Create user preference inheritance and defaults

#### Week 9: Monitoring and Performance

- [ ] Integrate Micrometer for metrics collection
- [ ] Set up Prometheus metrics exposition
- [ ] Create Grafana dashboards for key metrics
- [ ] Implement processing queue depth monitoring
- [ ] Add OCR processing time tracking
- [ ] Create notification delivery success rate metrics
- [ ] Implement alerting rules configuration
- [ ] Add database connection pool monitoring
- [ ] Create Elasticsearch query latency tracking
- [ ] Implement disk space usage alerts
- [ ] Add distributed tracing with Elastic APM/Jaeger
- [ ] Create correlation ID propagation
- [ ] Implement circuit breaker patterns (Resilience4j)
- [ ] Add batch processing optimization
- [ ] Create connection pooling tuning

### Phase 4: Production Readiness (Weeks 10-12)

#### Week 10: Security Hardening

- [ ] Implement AES-256 encryption for stored documents
- [ ] Configure TLS 1.3 for all communications
- [ ] Integrate HashiCorp Vault for secrets management
- [ ] Add PII detection and anonymization
- [ ] Implement file type verification (magic bytes)
- [ ] Add maximum file size limits
- [ ] Create input sanitization for all user inputs
- [ ] Implement SQL injection prevention measures
- [ ] Add XSS protection for API responses
- [ ] Configure CORS policies
- [ ] Implement request signing for service-to-service
- [ ] Add audit logging for sensitive operations
- [ ] Create security event monitoring
- [ ] Perform dependency vulnerability scanning
- [ ] Conduct security code review

#### Week 11: Load Testing and Documentation

- [ ] Design load testing scenarios
- [ ] Implement load tests using JMeter/Gatling
- [ ] Test system with 100+ documents per scan cycle
- [ ] Validate OCR processing time < 30 seconds per page
- [ ] Test notification delivery within 5 minutes
- [ ] Perform capacity planning analysis
- [ ] Optimize database queries based on load test results
- [ ] Tune Elasticsearch indices for query performance
- [ ] Configure horizontal scaling parameters
- [ ] Create operational runbooks
- [ ] Write disaster recovery procedures
- [ ] Document backup and restore processes
- [ ] Create API usage documentation
- [ ] Write system architecture documentation
- [ ] Create troubleshooting guides

#### Week 12: Production Deployment

- [ ] Set up production Kubernetes cluster
- [ ] Configure namespace isolation
- [ ] Create ConfigMaps for production settings
- [ ] Set up Kubernetes Secrets management
- [ ] Configure Horizontal Pod Autoscaler
- [ ] Set up Persistent Volume Claims
- [ ] Implement blue-green deployment strategy
- [ ] Configure production monitoring and alerting
- [ ] Set up log aggregation (ELK Stack)
- [ ] Implement database backup automation
- [ ] Configure data retention policies (12 months)
- [ ] Set up index lifecycle management for Elasticsearch
- [ ] Perform production smoke tests
- [ ] Validate GDPR compliance measures
- [ ] Create incident response procedures

---

## File Tree Structure

```
retail-brochure-monitor/
    .github/
        workflows/
            ci.yml
            cd.yml
    docker/
        docker-compose.yml
        docker-compose.dev.yml
        docker-compose.prod.yml
        postgres/
            init.sql
        elasticsearch/
            elasticsearch.yml
        redis/
            redis.conf
        rabbitmq/
            rabbitmq.conf
    docs/
        api/
            openapi.yaml
        architecture/
            system-overview.md
            data-flow.md
        runbooks/
            deployment.md
            incident-response.md
            disaster-recovery.md
    k8s/
        base/
            namespace.yaml
            configmap.yaml
            secrets.yaml
        overlays/
            dev/
                kustomization.yaml
            staging/
                kustomization.yaml
            production/
                kustomization.yaml
        deployments/
            api-service.yaml
            ingestion-service.yaml
            ocr-service.yaml
            notification-service.yaml
            scheduler-service.yaml
        services/
            api-service.yaml
            ingestion-service.yaml
        hpa/
            ocr-worker-hpa.yaml
            ingestion-worker-hpa.yaml
        pvc/
            ocr-models-pvc.yaml
            document-storage-pvc.yaml
    src/
        main/
            java/
                com/
                    retailmonitor/
                        RetailMonitorApplication.java
                        config/
                            AppConfig.java
                            SecurityConfig.java
                            ElasticsearchConfig.java
                            RabbitMQConfig.java
                            RedisConfig.java
                            SchedulerConfig.java
                            WebClientConfig.java
                            OpenApiConfig.java
                        domain/
                            source/
                                Source.java
                                SourceType.java
                                SourceStatus.java
                                SourceRepository.java
                                SourceService.java
                                SourceServiceImpl.java
                            document/
                                Document.java
                                DocumentType.java
                                ProcessingStatus.java
                                DocumentRepository.java
                                DocumentService.java
                                DocumentServiceImpl.java
                            content/
                                ExtractedContent.java
                                ContentRepository.java
                                ContentService.java
                                ContentServiceImpl.java
                            subscription/
                                KeywordSubscription.java
                                NotificationPreference.java
                                SubscriptionRepository.java
                                SubscriptionService.java
                                SubscriptionServiceImpl.java
                            match/
                                MatchResult.java
                                MatchLocation.java
                                MatchRepository.java
                                MatchService.java
                                MatchServiceImpl.java
                            user/
                                User.java
                                UserRole.java
                                UserRepository.java
                                UserService.java
                                UserServiceImpl.java
                        ingestion/
                            IngestionService.java
                            IngestionServiceImpl.java
                            collector/
                                DocumentCollector.java
                                HttpDocumentCollector.java
                                FtpDocumentCollector.java
                                S3DocumentCollector.java
                                FileSystemCollector.java
                            validator/
                                DocumentValidator.java
                                FileTypeValidator.java
                                FileSizeValidator.java
                            storage/
                                DocumentStorage.java
                                LocalDocumentStorage.java
                                S3DocumentStorage.java
                            deduplication/
                                DeduplicationService.java
                                HashCalculator.java
                        ocr/
                            OcrService.java
                            OcrServiceImpl.java
                            engine/
                                OcrEngine.java
                                TesseractOcrEngine.java
                                GoogleVisionOcrEngine.java
                                AwsTextractOcrEngine.java
                            preprocessing/
                                ImagePreprocessor.java
                                ContrastEnhancer.java
                                DeskewProcessor.java
                                NoiseReducer.java
                                PageSegmenter.java
                            postprocessing/
                                TextPostProcessor.java
                                ArtifactRemover.java
                                WhitespaceNormalizer.java
                                MetadataExtractor.java
                            pdf/
                                PdfProcessor.java
                                DigitalPdfExtractor.java
                                ScannedPdfConverter.java
                            image/
                                ImageProcessor.java
                                ImageFormatHandler.java
                        search/
                            SearchService.java
                            SearchServiceImpl.java
                            indexing/
                                DocumentIndexer.java
                                ElasticsearchIndexer.java
                                IndexSchemaManager.java
                            query/
                                QueryBuilder.java
                                FuzzyQueryBuilder.java
                                PhraseQueryBuilder.java
                                SynonymExpander.java
                            detection/
                                KeywordDetectionService.java
                                PatternMatcher.java
                                ContextExtractor.java
                                ConfidenceCalculator.java
                        notification/
                            NotificationService.java
                            NotificationServiceImpl.java
                            email/
                                EmailService.java
                                EmailServiceImpl.java
                                EmailTemplateEngine.java
                                EmailDeliveryTracker.java
                            aggregation/
                                MatchAggregator.java
                                DigestBuilder.java
                            preferences/
                                PreferenceService.java
                                QuietHoursHandler.java
                        scheduler/
                            SchedulerService.java
                            SchedulerServiceImpl.java
                            job/
                                ScanJob.java
                                IngestionJob.java
                                CleanupJob.java
                            cron/
                                CronParser.java
                                CronValidator.java
                            orchestration/
                                ScanOrchestrator.java
                                JobTracker.java
                        api/
                            controller/
                                SourceController.java
                                SubscriptionController.java
                                DocumentController.java
                                MatchController.java
                                UserController.java
                                HealthController.java
                                AdminController.java
                            dto/
                                request/
                                    CreateSourceRequest.java
                                    UpdateSourceRequest.java
                                    CreateSubscriptionRequest.java
                                    SearchRequest.java
                                response/
                                    SourceResponse.java
                                    DocumentResponse.java
                                    MatchResponse.java
                                    HealthResponse.java
                                    PagedResponse.java
                            mapper/
                                SourceMapper.java
                                DocumentMapper.java
                                SubscriptionMapper.java
                                MatchMapper.java
                            validation/
                                RequestValidator.java
                                CronExpressionValidator.java
                            exception/
                                ApiExceptionHandler.java
                                ErrorResponse.java
                        security/
                            JwtTokenProvider.java
                            JwtAuthenticationFilter.java
                            UserDetailsServiceImpl.java
                            RateLimitingFilter.java
                            SecurityAuditLogger.java
                            encryption/
                                EncryptionService.java
                                AesEncryptionService.java
                            secrets/
                                SecretsManager.java
                                VaultSecretsManager.java
                        messaging/
                            producer/
                                MessageProducer.java
                                DocumentQueueProducer.java
                            consumer/
                                MessageConsumer.java
                                OcrJobConsumer.java
                                NotificationConsumer.java
                            dlq/
                                DeadLetterQueueHandler.java
                                FailedJobProcessor.java
                        resilience/
                            CircuitBreakerConfig.java
                            RetryPolicyConfig.java
                            FallbackHandler.java
                        monitoring/
                            MetricsCollector.java
                            HealthIndicatorConfig.java
                            custom/
                                OcrHealthIndicator.java
                                ElasticsearchHealthIndicator.java
                                QueueDepthHealthIndicator.java
                            tracing/
                                CorrelationIdFilter.java
                                DistributedTracingConfig.java
                        common/
                            exception/
                                BaseException.java
                                DocumentProcessingException.java
                                OcrException.java
                                SourceUnavailableException.java
                                NotificationDeliveryException.java
                            util/
                                DateTimeUtils.java
                                HashUtils.java
                                FileUtils.java
                                ValidationUtils.java
                            constants/
                                ApplicationConstants.java
                                ErrorCodes.java
            resources/
                application.yml
                application-dev.yml
                application-staging.yml
                application-prod.yml
                db/
                    migration/
                        V1__initial_schema.sql
                        V2__add_indexes.sql
                        V3__add_user_management.sql
                templates/
                    email/
                        match-notification.html
                        digest-notification.html
                        welcome.html
                        source-health-alert.html
                ocr/
                    tessdata/
                        eng.traineddata
                        deu.traineddata
                logback-spring.xml
                messages.properties
        test/
            java/
                com/
                    retailmonitor/
                        unit/
                            domain/
                                SourceServiceTest.java
                                DocumentServiceTest.java
                                SubscriptionServiceTest.java
                            ocr/
                                TesseractOcrEngineTest.java
                                ImagePreprocessorTest.java
                            search/
                                QueryBuilderTest.java
                                KeywordDetectionTest.java
                            notification/
                                EmailServiceTest.java
                                MatchAggregatorTest.java
                        integration/
                            IngestionIntegrationTest.java
                            OcrPipelineIntegrationTest.java
                            SearchIntegrationTest.java
                            NotificationIntegrationTest.java
                            ApiIntegrationTest.java
                        e2e/
                            FullWorkflowTest.java
                            ScheduledScanTest.java
            resources/
                application-test.yml
                test-data/
                    sample-digital.pdf
                    sample-scanned.pdf
                    sample-image.jpg
                    sample-webpage.html
    scripts/
        setup/
            init-db.sh
            init-elasticsearch.sh
            setup-dev-env.sh
        deployment/
            deploy.sh
            rollback.sh
            health-check.sh
        maintenance/
            backup-db.sh
            cleanup-old-data.sh
            reindex-elasticsearch.sh
    monitoring/
        grafana/
            dashboards/
                system-overview.json
                ocr-metrics.json
                notification-metrics.json
                business-metrics.json
            provisioning/
                dashboards.yml
                datasources.yml
        prometheus/
            prometheus.yml
            alert-rules.yml
    .env.example
    .gitignore
    pom.xml
    README.md
    CONTRIBUTING.md
    LICENSE
```

---

## Module Boundaries and Responsibilities

### 1. Ingestion Module (`com.retailmonitor.ingestion`)

**Responsibility:** Collect and import documents from various sources into the system.

**Boundaries:**
- Fetches documents from configured sources (HTTP, FTP, S3, file system)
- Validates document integrity and file types
- Manages temporary storage during processing
- Handles deduplication via content hashing
- Publishes ingestion events to message queue

**Dependencies:**
- Domain Module (Source, Document entities)
- Messaging Module (queue producer)
- Common Module (utilities, exceptions)

**Does NOT:**
- Process document content (OCR)
- Perform keyword matching
- Send notifications
- Manage user subscriptions

---

### 2. OCR Module (`com.retailmonitor.ocr`)

**Responsibility:** Extract text content from documents using optical character recognition.

**Boundaries:**
- Processes various document types (PDF, images)
- Applies image preprocessing for quality improvement
- Executes OCR with confidence scoring
- Post-processes extracted text for normalization
- Extracts document metadata (dates, prices)

**Dependencies:**
- Domain Module (Document, ExtractedContent entities)
- External OCR engines (Tesseract, Google Vision)
- Common Module (utilities)

**Does NOT:**
- Fetch documents from sources
- Perform keyword matching
- Index content in search engine
- Handle notifications

---

### 3. Search Module (`com.retailmonitor.search`)

**Responsibility:** Index processed content and detect keyword matches.

**Boundaries:**
- Manages Elasticsearch index schema
- Indexes extracted text with metadata
- Builds and executes search queries
- Performs fuzzy and synonym-based matching
- Calculates match confidence and extracts context

**Dependencies:**
- Domain Module (Subscription, MatchResult entities)
- Elasticsearch client
- Common Module (utilities)

**Does NOT:**
- Extract text from documents
- Manage source configurations
- Send notifications to users
- Handle user authentication

---

### 4. Notification Module (`com.retailmonitor.notification`)

**Responsibility:** Deliver alerts to users when keyword matches are found.

**Boundaries:**
- Aggregates matches by user/subscription
- Applies notification preferences (immediate/digest)
- Generates email content from templates
- Tracks delivery status and handles failures
- Respects quiet hours configuration

**Dependencies:**
- Domain Module (User, Subscription, MatchResult entities)
- Email service provider (SMTP)
- Template engine (Thymeleaf)

**Does NOT:**
- Detect keyword matches
- Process documents
- Manage source configurations
- Handle user authentication

---

### 5. Scheduler Module (`com.retailmonitor.scheduler`)

**Responsibility:** Orchestrate periodic scanning and maintenance jobs.

**Boundaries:**
- Manages cron-based job scheduling
- Triggers ingestion workflows
- Monitors source health status
- Tracks job execution history
- Handles cleanup and maintenance tasks

**Dependencies:**
- Domain Module (Source entities)
- Ingestion Module (triggers)
- Common Module (utilities)

**Does NOT:**
- Perform document fetching directly
- Process OCR
- Execute keyword matching
- Send user notifications

---

### 6. API Module (`com.retailmonitor.api`)

**Responsibility:** Expose REST endpoints for system configuration and monitoring.

**Boundaries:**
- Handles HTTP request/response lifecycle
- Validates and transforms input data
- Maps domain entities to DTOs
- Enforces rate limiting and authentication
- Provides OpenAPI documentation

**Dependencies:**
- Domain Module (all services)
- Security Module (authentication)
- Common Module (validation, exceptions)

**Does NOT:**
- Implement business logic directly
- Access database directly
- Handle message queue operations
- Perform background processing

---

### 7. Security Module (`com.retailmonitor.security`)

**Responsibility:** Manage authentication, authorization, and data protection.

**Boundaries:**
- JWT token generation and validation
- User authentication and session management
- Role-based access control enforcement
- Data encryption at rest
- Security audit logging

**Dependencies:**
- Domain Module (User entities)
- External secrets manager (Vault)
- Common Module (utilities)

**Does NOT:**
- Define business rules
- Process documents
- Handle notifications
- Manage scheduling

---

### 8. Messaging Module (`com.retailmonitor.messaging`)

**Responsibility:** Handle asynchronous communication between services.

**Boundaries:**
- Produces messages to queues (RabbitMQ)
- Consumes and processes queued jobs
- Manages dead letter queue for failures
- Ensures message delivery guarantees
- Handles backpressure and flow control

**Dependencies:**
- RabbitMQ client
- Domain services (job processing)
- Common Module (exceptions)

**Does NOT:**
- Implement business logic
- Manage data persistence directly
- Handle HTTP communications
- Perform security checks

---

### 9. Resilience Module (`com.retailmonitor.resilience`)

**Responsibility:** Implement fault tolerance patterns across the system.

**Boundaries:**
- Configures circuit breakers for external calls
- Implements retry policies with backoff
- Provides fallback mechanisms
- Handles transient failures gracefully
- Monitors failure rates

**Dependencies:**
- Resilience4j library
- Common Module (exceptions)

**Does NOT:**
- Implement business logic
- Store state persistently
- Handle specific domain operations

---

### 10. Monitoring Module (`com.retailmonitor.monitoring`)

**Responsibility:** Collect metrics and provide system observability.

**Boundaries:**
- Exposes application metrics (Micrometer)
- Implements custom health indicators
- Configures distributed tracing
- Manages correlation ID propagation
- Tracks performance metrics

**Dependencies:**
- Spring Boot Actuator
- Prometheus client
- Elastic APM agent

**Does NOT:**
- Store metrics long-term
- Implement alerting logic (done by Prometheus)
- Handle business operations

---

### 11. Domain Module (`com.retailmonitor.domain`)

**Responsibility:** Core business entities, repositories, and domain services.

**Boundaries:**
- Defines entity models and relationships
- Implements repository interfaces
- Contains domain service interfaces and implementations
- Enforces business invariants
- Manages entity lifecycle

**Dependencies:**
- Spring Data JPA
- Common Module (utilities)

**Does NOT:**
- Handle HTTP requests
- Manage infrastructure concerns
- Implement cross-cutting concerns

---

### 12. Common Module (`com.retailmonitor.common`)

**Responsibility:** Shared utilities and cross-cutting concerns.

**Boundaries:**
- Provides utility functions (date, hash, file operations)
- Defines base exception hierarchy
- Contains application constants
- Implements validation helpers
- Manages common patterns

**Dependencies:**
- None (base module)

**Does NOT:**
- Implement business logic
- Access external services
- Define domain entities

---

## Interface Contracts

### 1. Document Ingestion Contract

```java
/**
 * Contract for document collection from external sources
 */
public interface DocumentCollector {

    /**
     * Fetches documents from the configured source
     * @param source Configuration for the document source
     * @return List of collected document references
     * @throws SourceUnavailableException if source cannot be reached
     */
    List<CollectedDocument> collect(Source source) throws SourceUnavailableException;

    /**
     * Checks if this collector supports the given source type
     * @param sourceType Type of source to check
     * @return true if supported, false otherwise
     */
    boolean supports(SourceType sourceType);

    /**
     * Validates source accessibility
     * @param source Source to validate
     * @return HealthCheckResult with status and details
     */
    HealthCheckResult validateSource(Source source);
}

/**
 * Collected document data transfer object
 */
public record CollectedDocument(
    String originalPath,
    byte[] content,
    DocumentType type,
    String contentHash,
    Map<String, String> metadata,
    Instant fetchedAt
) {}
```

---

### 2. OCR Processing Contract

```java
/**
 * Contract for OCR engine implementations
 */
public interface OcrEngine {

    /**
     * Extracts text from an image
     * @param imageData Raw image bytes
     * @param options OCR processing options
     * @return Extracted text with confidence score
     * @throws OcrException if extraction fails
     */
    OcrResult extractText(byte[] imageData, OcrOptions options) throws OcrException;

    /**
     * Gets the name of this OCR engine
     * @return Engine identifier
     */
    String getEngineName();

    /**
     * Checks if the engine is available and healthy
     * @return true if operational
     */
    boolean isAvailable();
}

/**
 * OCR processing options
 */
public record OcrOptions(
    String language,
    boolean enablePreprocessing,
    int dpi,
    PageSegmentationMode segmentationMode
) {}

/**
 * OCR extraction result
 */
public record OcrResult(
    String extractedText,
    double confidenceScore,
    String languageDetected,
    Map<String, Object> metadata,
    Duration processingTime
) {}
```

---

### 3. Search and Indexing Contract

```java
/**
 * Contract for document indexing service
 */
public interface DocumentIndexer {

    /**
     * Indexes a document's extracted content
     * @param documentId Unique document identifier
     * @param content Extracted text content
     * @param metadata Document metadata
     * @return Indexing result with status
     */
    IndexingResult index(String documentId, ExtractedContent content, DocumentMetadata metadata);

    /**
     * Removes a document from the index
     * @param documentId Document to remove
     */
    void removeFromIndex(String documentId);

    /**
     * Refreshes the index to make recent changes searchable
     */
    void refreshIndex();
}

/**
 * Contract for keyword detection service
 */
public interface KeywordDetectionService {

    /**
     * Searches for keyword matches in indexed documents
     * @param subscription User's keyword subscription
     * @param searchScope Optional constraints on search
     * @return List of match results with context
     */
    List<DetectionResult> detectKeywords(KeywordSubscription subscription, SearchScope searchScope);
}

/**
 * Keyword detection result
 */
public record DetectionResult(
    String documentId,
    String matchedKeyword,
    String contextExcerpt,
    MatchLocation location,
    double confidenceScore,
    Instant detectedAt
) {}

/**
 * Match location in document
 */
public record MatchLocation(
    int pageNumber,
    int characterOffset,
    int lineNumber
) {}
```

---

### 4. Notification Service Contract

```java
/**
 * Contract for notification delivery service
 */
public interface NotificationService {

    /**
     * Sends notifications for detected matches
     * @param matches List of match results to notify
     * @param subscription User's subscription with preferences
     * @return Delivery result with status
     */
    NotificationDeliveryResult sendNotification(
        List<DetectionResult> matches,
        KeywordSubscription subscription
    );

    /**
     * Sends aggregated digest notification
     * @param userId User to notify
     * @param period Time period for digest
     * @return Delivery result
     */
    NotificationDeliveryResult sendDigest(String userId, DigestPeriod period);
}

/**
 * Notification delivery result
 */
public record NotificationDeliveryResult(
    String notificationId,
    DeliveryStatus status,
    Instant sentAt,
    String errorMessage
) {}

public enum DeliveryStatus {
    SENT, DELIVERED, FAILED, BOUNCED, PENDING
}

/**
 * Contract for email service
 */
public interface EmailService {

    /**
     * Sends an email using the configured provider
     * @param emailRequest Email details
     * @return Send result with message ID
     * @throws NotificationDeliveryException on failure
     */
    EmailSendResult send(EmailRequest emailRequest) throws NotificationDeliveryException;
}

/**
 * Email request details
 */
public record EmailRequest(
    String to,
    String subject,
    String htmlContent,
    String plainTextContent,
    Map<String, String> headers,
    List<Attachment> attachments
) {}
```

---

### 5. Scheduler Contract

```java
/**
 * Contract for scan scheduling service
 */
public interface SchedulerService {

    /**
     * Schedules a source for periodic scanning
     * @param source Source to schedule
     * @param cronExpression Cron schedule expression
     * @return Schedule ID
     */
    String scheduleSource(Source source, String cronExpression);

    /**
     * Cancels a scheduled scan
     * @param scheduleId Schedule to cancel
     */
    void cancelSchedule(String scheduleId);

    /**
     * Triggers an immediate scan for a source
     * @param sourceId Source to scan
     * @return Job ID for tracking
     */
    String triggerImmediateScan(String sourceId);

    /**
     * Gets the status of a scheduled job
     * @param jobId Job identifier
     * @return Current job status
     */
    JobStatus getJobStatus(String jobId);
}

/**
 * Scan job status
 */
public record JobStatus(
    String jobId,
    JobState state,
    Instant startedAt,
    Instant completedAt,
    int documentsProcessed,
    int errorsEncountered,
    String errorDetails
) {}

public enum JobState {
    PENDING, RUNNING, COMPLETED, FAILED, CANCELLED
}
```

---

### 6. Message Queue Contract

```java
/**
 * Contract for message production
 */
public interface MessageProducer<T> {

    /**
     * Publishes a message to the queue
     * @param message Message payload
     * @param routingKey Queue routing key
     */
    void publish(T message, String routingKey);

    /**
     * Publishes with confirmation callback
     * @param message Message payload
     * @param routingKey Queue routing key
     * @param confirmCallback Called on confirmation
     */
    void publishWithConfirmation(T message, String routingKey, Consumer<Boolean> confirmCallback);
}

/**
 * Contract for message consumption
 */
public interface MessageConsumer<T> {

    /**
     * Processes a received message
     * @param message Message payload
     * @param metadata Message metadata
     * @throws ProcessingException if processing fails
     */
    void consume(T message, MessageMetadata metadata) throws ProcessingException;

    /**
     * Gets the queue this consumer listens to
     * @return Queue name
     */
    String getQueueName();
}

/**
 * OCR job message
 */
public record OcrJobMessage(
    String jobId,
    String documentId,
    DocumentType documentType,
    String storagePath,
    OcrOptions options,
    int retryCount,
    Instant createdAt
) {}
```

---

### 7. Repository Contracts

```java
/**
 * Source repository contract
 */
public interface SourceRepository extends JpaRepository<Source, UUID> {

    List<Source> findByStatus(SourceStatus status);

    List<Source> findByStatusAndNextScanBefore(SourceStatus status, Instant time);

    Optional<Source> findByNameIgnoreCase(String name);

    @Query("UPDATE Source s SET s.lastScanAt = :timestamp WHERE s.id = :id")
    void updateLastScanTimestamp(UUID id, Instant timestamp);
}

/**
 * Document repository contract
 */
public interface DocumentRepository extends JpaRepository<Document, UUID> {

    List<Document> findBySourceIdAndProcessingStatus(UUID sourceId, ProcessingStatus status);

    Optional<Document> findByContentHash(String hash);

    @Query("SELECT d FROM Document d WHERE d.createdAt < :cutoff")
    List<Document> findDocumentsOlderThan(Instant cutoff);

    long countByProcessingStatus(ProcessingStatus status);
}

/**
 * Match result repository contract
 */
public interface MatchRepository extends JpaRepository<MatchResult, UUID> {

    List<MatchResult> findBySubscriptionIdAndNotificationStatusOrderByDetectedAtDesc(
        UUID subscriptionId,
        NotificationStatus status
    );

    @Query("SELECT m FROM MatchResult m WHERE m.detectedAt > :since AND m.subscription.user.id = :userId")
    List<MatchResult> findRecentMatchesForUser(UUID userId, Instant since);

    boolean existsBySubscriptionIdAndDocumentIdAndMatchedKeyword(
        UUID subscriptionId,
        UUID documentId,
        String keyword
    );
}
```

---

### 8. Health Check Contract

```java
/**
 * Custom health indicator contract
 */
public interface ServiceHealthIndicator extends HealthIndicator {

    /**
     * Performs detailed health check
     * @return Health status with details
     */
    @Override
    Health health();

    /**
     * Gets the service name being monitored
     * @return Service identifier
     */
    String getServiceName();
}

/**
 * OCR service health check
 */
public class OcrHealthIndicator implements ServiceHealthIndicator {

    @Override
    public Health health() {
        // Check OCR engine availability
        // Return Health.up() or Health.down() with details
    }

    @Override
    public String getServiceName() {
        return "ocr-service";
    }
}

/**
 * Elasticsearch health check
 */
public class ElasticsearchHealthIndicator implements ServiceHealthIndicator {

    @Override
    public Health health() {
        // Check cluster health, index status
        // Return Health.up() or Health.down() with details
    }

    @Override
    public String getServiceName() {
        return "elasticsearch";
    }
}
```

---

### 9. Security Contract

```java
/**
 * JWT token provider contract
 */
public interface JwtTokenProvider {

    /**
     * Generates a JWT token for a user
     * @param user Authenticated user
     * @return Signed JWT token
     */
    String generateToken(User user);

    /**
     * Validates a JWT token
     * @param token Token to validate
     * @return true if valid
     */
    boolean validateToken(String token);

    /**
     * Extracts user ID from token
     * @param token JWT token
     * @return User identifier
     */
    String getUserIdFromToken(String token);

    /**
     * Extracts roles from token
     * @param token JWT token
     * @return Set of user roles
     */
    Set<UserRole> getRolesFromToken(String token);
}

/**
 * Encryption service contract
 */
public interface EncryptionService {

    /**
     * Encrypts data using AES-256
     * @param plainData Data to encrypt
     * @return Encrypted bytes
     */
    byte[] encrypt(byte[] plainData);

    /**
     * Decrypts AES-256 encrypted data
     * @param encryptedData Data to decrypt
     * @return Decrypted bytes
     */
    byte[] decrypt(byte[] encryptedData);

    /**
     * Encrypts a string field
     * @param plainText Text to encrypt
     * @return Base64 encoded encrypted string
     */
    String encryptField(String plainText);

    /**
     * Decrypts a string field
     * @param encryptedText Base64 encoded encrypted string
     * @return Decrypted text
     */
    String decryptField(String encryptedText);
}
```

---

### 10. API Response Contracts

```java
/**
 * Standard API response wrapper
 */
public record ApiResponse<T>(
    boolean success,
    T data,
    String message,
    Instant timestamp,
    String correlationId
) {
    public static <T> ApiResponse<T> success(T data) {
        return new ApiResponse<>(true, data, null, Instant.now(), MDC.get("correlationId"));
    }

    public static <T> ApiResponse<T> error(String message) {
        return new ApiResponse<>(false, null, message, Instant.now(), MDC.get("correlationId"));
    }
}

/**
 * Paginated response wrapper
 */
public record PagedResponse<T>(
    List<T> content,
    int pageNumber,
    int pageSize,
    long totalElements,
    int totalPages,
    boolean isFirst,
    boolean isLast
) {}

/**
 * Error response structure
 */
public record ErrorResponse(
    int status,
    String error,
    String message,
    String path,
    Instant timestamp,
    String correlationId,
    Map<String, String> validationErrors
) {}
```

---

## Dependency Graph

```
Common Module (base)
       ↑
Domain Module ← Resilience Module
       ↑
  ┌────┴────┬────────┬──────────┬───────────┐
  ↓         ↓        ↓          ↓           ↓
Ingestion  OCR    Search  Notification  Scheduler
Module    Module  Module    Module       Module
  ↓         ↓        ↓          ↓           ↓
  └─────────┴────────┴──────────┴───────────┘
                     ↓
              Messaging Module
                     ↓
              Monitoring Module
                     ↓
                API Module ← Security Module
```

---

## Cross-Module Communication Patterns

1. **Synchronous (Direct Service Call):**
   - API → Domain Services
   - Domain Services → Repository Layer

2. **Asynchronous (Message Queue):**
   - Ingestion → OCR Processing
   - OCR Processing → Search Indexing
   - Search Detection → Notification Service

3. **Event-Driven:**
   - Source health status changes
   - Match detection events
   - Processing completion events

4. **Request-Response:**
   - API endpoints
   - Health check probes
   - External service calls (with circuit breaker)

---

## Implementation Notes

- All interfaces should be unit testable with mock implementations
- Use dependency injection for all service implementations
- Apply consistent error handling across module boundaries
- Implement circuit breakers for all external service calls
- Log all inter-module communications with correlation IDs
- Use DTOs for data transfer between modules (no entity leakage)
- Validate all inputs at module boundaries
- Monitor latency at each integration point
