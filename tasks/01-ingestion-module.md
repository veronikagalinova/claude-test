# Task: Ingestion Module Implementation

**Module:** `com.retailmonitor.ingestion`
**Priority:** High
**Phase:** 1 (Foundation)
**Estimated Duration:** 2-3 weeks

---

## Overview

The Ingestion Module is responsible for collecting documents from various external sources (HTTP URLs, FTP servers, S3 buckets, local file systems) and preparing them for OCR processing. This is a critical entry point for all data entering the system.

---

## Implementation Details

### 1. Document Collector Framework

**Objective:** Create an extensible framework for collecting documents from multiple source types.

**Implementation Approach:**
- Design a strategy pattern with a base `DocumentCollector` interface
- Implement concrete collectors for each source type (HTTP, FTP, S3, FileSystem)
- Use a factory or registry pattern to select the appropriate collector based on source configuration
- Each collector must handle authentication, connection management, and error recovery independently
- Implement connection pooling for HTTP and FTP collectors to reuse connections
- Use streaming for large file downloads to avoid memory exhaustion

**Key Components:**
- Collector registry that maps source types to collector implementations
- Connection configuration manager for credentials and timeouts
- Download progress tracker for monitoring and logging
- Temporary file manager for staging downloaded documents

### 2. Document Validation Pipeline

**Objective:** Ensure only valid, safe documents enter the processing pipeline.

**Implementation Approach:**
- Validate file type using magic bytes (first N bytes of file), not file extensions
- Check file size against configurable maximum limits
- Verify document integrity (not corrupted or truncated)
- Scan for malicious content patterns (embedded scripts, macros)
- Validate character encoding for text-based sources
- Implement a chain-of-responsibility pattern for validation steps

**Validation Stages:**
- Size validation (reject oversized files immediately)
- Magic byte verification (confirm actual file type)
- Structural integrity check (valid PDF structure, valid image headers)
- Security scan (optional antivirus integration point)
- Metadata extraction and validation

### 3. Deduplication Service

**Objective:** Prevent reprocessing of identical documents.

**Implementation Approach:**
- Calculate SHA-256 hash of document content
- Store hashes in Redis cache with TTL for fast lookups
- Persist hashes in PostgreSQL for long-term deduplication
- Consider perceptual hashing for images (detect visually similar content)
- Implement bloom filter for preliminary fast checks before database lookup
- Handle hash collisions gracefully with full content comparison

**Deduplication Strategy:**
- First check Redis cache for recent duplicates
- If not found, query PostgreSQL hash index
- For images, consider fuzzy matching with perceptual hash
- Allow configurable deduplication window (e.g., skip if processed within 24 hours)

### 4. Storage Abstraction Layer

**Objective:** Provide unified interface for document storage across different backends.

**Implementation Approach:**
- Create abstract storage interface supporting local filesystem and cloud storage
- Implement local storage for development and small deployments
- Implement S3-compatible storage for production scalability
- Support automatic cleanup of temporary files after processing
- Implement storage quotas and monitoring
- Use content-addressable storage pattern (store by hash)

**Storage Operations:**
- Store with metadata (source, timestamp, processing status)
- Retrieve by document ID or content hash
- Delete with cascade to related extracted content
- List documents with filtering and pagination
- Archive old documents to cold storage tier

### 5. Message Queue Integration

**Objective:** Decouple ingestion from OCR processing via asynchronous messaging.

**Implementation Approach:**
- Publish ingestion completion events to RabbitMQ
- Include job metadata (document ID, type, storage path, priority)
- Implement message persistence for guaranteed delivery
- Add message TTL to prevent stale job processing
- Support priority queues for urgent document processing
- Implement dead letter queue for failed ingestion attempts

**Message Flow:**
- Create processing job record in database with PENDING status
- Publish job message to OCR queue
- Update job status to QUEUED
- Handle publish failures with local retry mechanism
- Log all message operations with correlation IDs

---

## Test Scenarios

### Unit Tests

1. **Collector Selection Tests**
   - Verify correct collector is selected for each source type
   - Test fallback behavior when collector is unavailable
   - Validate configuration validation for each collector type

2. **File Type Validation Tests**
   - Test magic byte detection for PDF, JPG, PNG, TIFF, WebP formats
   - Verify rejection of files with mismatched extension and content
   - Test handling of corrupted file headers
   - Validate maximum file size enforcement

3. **Hash Calculation Tests**
   - Verify consistent hash generation for identical content
   - Test hash calculation for various file sizes (1KB to 1GB)
   - Validate hash algorithm configuration
   - Test streaming hash calculation for large files

4. **Retry Logic Tests**
   - Test exponential backoff timing (1s, 2s, 4s delays)
   - Verify maximum retry count enforcement
   - Test retry behavior with different exception types
   - Validate state preservation between retries

5. **Storage Abstraction Tests**
   - Test file storage and retrieval consistency
   - Verify metadata preservation across storage operations
   - Test cleanup of temporary files
   - Validate storage quota enforcement

### Integration Tests

1. **HTTP Document Collection**
   - Test successful download from HTTP/HTTPS URLs
   - Verify handling of redirects (301, 302, 307, 308)
   - Test authentication (Basic Auth, Bearer Token, API Key)
   - Validate timeout handling for slow responses
   - Test resume capability for interrupted downloads

2. **FTP Document Collection**
   - Test connection to FTP and SFTP servers
   - Verify directory listing and file enumeration
   - Test binary mode transfer for documents
   - Validate passive vs active FTP mode selection
   - Test connection reuse and pooling

3. **S3 Document Collection**
   - Test bucket access with IAM credentials
   - Verify object listing with pagination
   - Test multipart download for large objects
   - Validate server-side encryption handling
   - Test cross-region bucket access

4. **End-to-End Ingestion Flow**
   - Test complete flow from source configuration to queue message
   - Verify database records are created correctly
   - Validate storage of downloaded documents
   - Test deduplication prevents reprocessing
   - Verify message queue receives correct job data

5. **Concurrent Ingestion Tests**
   - Test parallel downloads from multiple sources
   - Verify thread safety of shared resources
   - Test connection pool exhaustion handling
   - Validate rate limiting enforcement
   - Test resource cleanup under concurrent load

### Performance Tests

1. **Throughput Testing**
   - Measure documents ingested per minute under load
   - Test with varying document sizes (small, medium, large)
   - Benchmark different source types
   - Identify bottlenecks in the pipeline

2. **Memory Usage Testing**
   - Monitor heap usage during large file downloads
   - Test streaming efficiency for 1GB+ files
   - Verify no memory leaks in long-running processes
   - Test garbage collection behavior

3. **Network Resilience Testing**
   - Simulate network latency and packet loss
   - Test behavior under bandwidth constraints
   - Verify recovery from connection drops
   - Test DNS resolution failures

---

## Potential Caveats, Pitfalls, and Edge Cases

### Network and Connectivity Issues

1. **Intermittent Network Failures**
   - Sources may become temporarily unavailable during scans
   - DNS resolution can fail or return stale results
   - TLS handshake failures due to certificate issues
   - Network timeouts may vary significantly between environments
   - **Mitigation:** Implement robust retry with circuit breaker pattern

2. **Firewall and Proxy Complications**
   - Corporate firewalls may block certain ports or protocols
   - Proxy servers may modify or cache responses
   - Some sources may require specific IP whitelisting
   - SSL inspection may break certificate validation
   - **Mitigation:** Support comprehensive proxy configuration and custom trust stores

3. **Rate Limiting and Throttling**
   - External sources may impose request rate limits
   - Aggressive polling can result in IP bans
   - Some CDNs may require specific headers to avoid blocking
   - **Mitigation:** Implement per-source rate limiting with configurable delays

### Data Quality Challenges

4. **Corrupted or Partial Downloads**
   - Network interruptions can cause incomplete files
   - Source servers may send truncated responses
   - Compression issues can corrupt file content
   - **Mitigation:** Verify file integrity using checksums when available, implement resume capability

5. **Encoding and Character Set Issues**
   - Web pages may have incorrect charset declarations
   - FTP servers may not handle Unicode filenames properly
   - Different operating systems use different line endings
   - **Mitigation:** Implement robust charset detection and normalization

6. **Dynamic Content Changes**
   - Documents may be updated between listing and download
   - Websites may serve different content based on user agent
   - CDN caching may serve stale versions
   - **Mitigation:** Store document version information, implement change detection

### Security Vulnerabilities

7. **Malicious File Uploads**
   - PDF files can contain embedded JavaScript or malware
   - Images may have steganographic payloads
   - Zip bombs (highly compressed malicious archives)
   - Polyglot files that appear valid but contain exploits
   - **Mitigation:** Implement file type whitelisting, size limits, and optional antivirus scanning

8. **Server-Side Request Forgery (SSRF)**
   - User-provided URLs could point to internal network resources
   - Attackers may try to access cloud metadata endpoints
   - Private IP ranges should be blocked
   - **Mitigation:** Validate URLs against allowlists, block private IP ranges, use DNS pinning

9. **Credential Exposure**
   - Source credentials stored in database could be compromised
   - Credentials may be logged accidentally in error messages
   - Memory dumps could expose sensitive data
   - **Mitigation:** Encrypt credentials at rest, use secrets manager, sanitize logs

### Resource Management

10. **Disk Space Exhaustion**
    - Large documents can quickly fill temporary storage
    - Failed cleanup can leave orphaned files
    - Concurrent downloads may exceed available space
    - **Mitigation:** Implement storage quotas, automatic cleanup, and monitoring alerts

11. **Memory Pressure**
    - Loading entire large files into memory causes OOM errors
    - Too many concurrent downloads exhaust heap space
    - Buffer sizing affects both memory and performance
    - **Mitigation:** Use streaming APIs, limit concurrent operations, tune buffer sizes

12. **Connection Pool Exhaustion**
    - Too many concurrent requests drain connection pools
    - Long-running connections may not be returned to pool
    - Connection leaks from improper exception handling
    - **Mitigation:** Set appropriate pool sizes, implement connection timeouts, monitor pool metrics

### Data Consistency Issues

13. **Race Conditions in Deduplication**
    - Same document downloaded concurrently from different sources
    - Hash check and insert are not atomic
    - Cache and database may become inconsistent
    - **Mitigation:** Use distributed locks or optimistic locking with retry

14. **Source Configuration Changes During Scan**
    - Admin updates source config while scan is running
    - Source gets deleted mid-ingestion
    - Credentials change during long-running downloads
    - **Mitigation:** Snapshot configuration at scan start, validate references before operations

15. **Message Queue Failures**
    - RabbitMQ becomes unavailable after ingestion
    - Messages lost due to broker restart
    - Duplicate messages from retry logic
    - **Mitigation:** Use persistent messages, implement idempotency, handle duplicate processing

### Edge Cases

16. **Empty or Zero-Byte Files**
    - Source returns valid response but empty content
    - File exists but has no data
    - Some systems create placeholder files
    - **Mitigation:** Validate minimum file size, log warnings for empty files

17. **Extremely Large Documents**
    - PDFs with thousands of pages
    - High-resolution images (100MB+)
    - Web pages with infinite scroll content
    - **Mitigation:** Set reasonable limits, implement chunked processing, warn users

18. **Unusual File Formats**
    - Password-protected PDFs
    - Encrypted image files
    - Proprietary document formats
    - **Mitigation:** Detect and report unsupported formats, provide clear error messages

19. **Timestamp and Timezone Issues**
    - Source provides timestamps in unknown timezone
    - Last-modified dates may be unreliable
    - Clock skew between systems affects change detection
    - **Mitigation:** Normalize to UTC, handle missing timestamps gracefully, use content hashing

20. **Character Encoding in Filenames**
    - Non-ASCII characters in document names
    - Special characters that are filesystem-invalid
    - Maximum filename length exceeded
    - **Mitigation:** Sanitize filenames, use content-based naming (hashes), truncate safely

---

## Dependencies

- Domain Module (Source, Document entities)
- Common Module (utilities, exceptions)
- Messaging Module (RabbitMQ integration)
- External: Apache HttpClient, Commons Net (FTP), AWS SDK (S3)

## Success Criteria

- Successfully ingest documents from all supported source types
- Achieve 99%+ success rate for healthy sources
- Handle transient failures gracefully with retry logic
- Detect and reject 100% of invalid file types
- Prevent duplicate processing of identical documents
- Complete ingestion of 100 documents within 10 minutes
