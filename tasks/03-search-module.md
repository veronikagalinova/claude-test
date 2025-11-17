# Task: Search and Keyword Detection Module Implementation

**Module:** `com.retailmonitor.search`
**Priority:** High
**Phase:** 2-3 (Core Features through Enhancement)
**Estimated Duration:** 3-4 weeks

---

## Overview

The Search Module is responsible for indexing extracted text content and detecting keyword matches based on user subscriptions. It leverages Elasticsearch for full-text search capabilities including fuzzy matching, synonym expansion, and relevance scoring.

---

## Implementation Details

### 1. Elasticsearch Index Schema Design

**Objective:** Create an optimized index structure for retail document search.

**Implementation Approach:**
- Design document index with appropriate field mappings
- Use keyword type for exact match fields (document ID, source ID, category)
- Use text type with custom analyzer for searchable content
- Implement nested objects for metadata (dates, prices, store information)
- Configure index settings for optimal performance (shards, replicas)
- Design index lifecycle management policies
- Support versioning for schema migrations

**Index Fields:**
- document_id: keyword (exact match identifier)
- source_id: keyword (filtering by source)
- content: text (main searchable field with custom analysis)
- content_normalized: text (lowercase, stemmed version)
- page_contents: nested array (per-page text with page numbers)
- extracted_metadata: object (prices, dates, product codes)
- source_category: keyword (filtering by retail category)
- processed_date: date (temporal filtering)
- ocr_confidence: float (quality filtering)
- language: keyword (language-specific search)

### 2. Custom Text Analyzer Configuration

**Objective:** Optimize text analysis for retail terminology and OCR-corrected text.

**Implementation Approach:**
- Create custom analyzer chain with specific tokenizers and filters
- Use standard tokenizer for word boundary detection
- Apply lowercase filter for case-insensitive matching
- Implement stop words filter (remove common words)
- Add stemming filter for linguistic variations
- Configure edge n-gram tokenizer for prefix matching
- Create synonym filter for retail terminology
- Support character folding for diacritics

**Analyzer Components:**
- Tokenizer: Standard with maximum token length limit
- Character filters: HTML strip, mapping filter for special characters
- Token filters: Lowercase, stop words, stemmer, synonym, word delimiter
- Custom filters: OCR error correction patterns, retail terminology

### 3. Document Indexing Service

**Objective:** Efficiently index processed documents into Elasticsearch.

**Implementation Approach:**
- Implement batch indexing for bulk operations
- Use asynchronous indexing to avoid blocking OCR pipeline
- Handle index refresh timing (balance freshness vs performance)
- Implement retry logic for transient Elasticsearch failures
- Track indexing success and failure metrics
- Support partial document updates
- Implement index aliasing for zero-downtime schema updates

**Indexing Process:**
1. Receive extracted content from OCR module
2. Transform content into Elasticsearch document format
3. Enrich with metadata (source info, timestamps, categories)
4. Submit to bulk indexing queue
5. Flush queue periodically or when threshold reached
6. Update document status in PostgreSQL
7. Trigger keyword detection after successful indexing

### 4. Query Builder Framework

**Objective:** Construct sophisticated search queries from user keyword subscriptions.

**Implementation Approach:**
- Build query DSL programmatically using Elasticsearch client
- Support exact phrase matching with quoted strings
- Implement fuzzy matching with configurable edit distance
- Add wildcard and prefix matching capabilities
- Support boolean operators (AND, OR, NOT)
- Implement field boosting for relevance tuning
- Create filters for source, date range, and category
- Support minimum match percentage for multiple keywords

**Query Types:**
- Match query: Standard full-text search with analysis
- Phrase query: Exact phrase in specific order
- Fuzzy query: Allow character variations (OCR errors)
- Bool query: Combine multiple conditions
- Range query: Date and numeric filtering
- Term query: Exact value matching (categories, IDs)

### 5. Fuzzy Matching for OCR Error Tolerance

**Objective:** Find matches despite OCR recognition errors.

**Implementation Approach:**
- Configure Levenshtein distance threshold (typically 1-2 edits)
- Implement automatic fuzziness based on word length
- Short words (3-4 chars): exact match only
- Medium words (5-7 chars): 1 edit allowed
- Long words (8+ chars): 2 edits allowed
- Consider phonetic matching for similar sounding words
- Weight exact matches higher than fuzzy matches
- Log fuzzy matches for OCR quality analysis

**Fuzziness Strategy:**
- "AUTO" setting in Elasticsearch adapts to word length
- Prefix matching combined with fuzzy for better results
- Exclude common OCR confusions from fuzziness (rn/m already handled)
- Balance between recall (finding matches) and precision (avoiding false positives)

### 6. Synonym Expansion System

**Objective:** Match semantically equivalent terms automatically.

**Implementation Approach:**
- Create synonym dictionaries for retail domain
- Support bidirectional synonyms (diapers ↔ nappies)
- Implement unidirectional synonyms (TV → television)
- Handle brand name variations and abbreviations
- Support multi-word synonyms (2-for-1 → buy one get one free)
- Allow user-defined synonym additions
- Update synonyms without full reindex (synonym filter reload)

**Synonym Categories:**
- Product categories (soft drink, soda, pop)
- Retail terms (discount, sale, savings)
- Brand variations (Coke, Coca-Cola)
- Regional terminology (shopping cart, trolley)
- Abbreviations (BOGO, B1G1)

### 7. Context Window Extraction

**Objective:** Provide meaningful text surrounding keyword matches.

**Implementation Approach:**
- Extract configurable number of characters around match
- Respect word boundaries (don't cut words)
- Preserve sentence structure when possible
- Highlight matched keywords in context
- Handle multiple matches in same document
- Extract from specific page where match occurred
- Provide position information (page number, character offset)

**Context Configuration:**
- Default window size: 200 characters before and after
- Maximum context per match: 500 characters total
- Multiple matches in proximity: merge contexts
- Preserve formatting hints (paragraph breaks, lists)

### 8. Match Deduplication and Aggregation

**Objective:** Prevent alerting users multiple times for same content.

**Implementation Approach:**
- Track previously notified matches per subscription
- Consider document version/hash in deduplication
- Implement time-based deduplication window
- Aggregate multiple keyword matches in same document
- Score matches by relevance and confidence
- Prioritize high-confidence, exact matches
- Batch results for efficient notification

**Deduplication Rules:**
- Same document + same keyword + same subscription = duplicate
- New version of document (different hash) = new match
- Same keyword in different page location = single notification
- Configurable deduplication window (default 24 hours)

---

## Test Scenarios

### Unit Tests

1. **Query Builder Tests**
   - Build correct match query for single keyword
   - Construct phrase query with proper escaping
   - Create fuzzy query with appropriate edit distance
   - Build boolean query with AND/OR/NOT conditions
   - Apply date range filters correctly
   - Validate query serialization to JSON DSL

2. **Synonym Expansion Tests**
   - Verify bidirectional synonym matching
   - Test unidirectional synonym behavior
   - Validate multi-word synonym handling
   - Test synonym case sensitivity
   - Verify synonym file parsing

3. **Context Extraction Tests**
   - Extract correct character window around match
   - Respect word boundaries in extraction
   - Handle matches at document start/end
   - Merge overlapping contexts properly
   - Preserve keyword highlighting markers

4. **Deduplication Logic Tests**
   - Detect duplicate matches correctly
   - Allow new versions to be reported
   - Test time window expiration
   - Validate aggregation of multiple matches
   - Test subscription-specific deduplication

5. **Confidence Scoring Tests**
   - Calculate match confidence accurately
   - Weight exact matches higher than fuzzy
   - Factor in OCR confidence score
   - Test relevance score calculation

### Integration Tests

1. **Elasticsearch Connection Tests**
   - Connect to Elasticsearch cluster successfully
   - Handle connection timeouts gracefully
   - Reconnect after cluster restart
   - Validate cluster health check
   - Test index creation and mapping

2. **Document Indexing Tests**
   - Index single document successfully
   - Batch index multiple documents
   - Update existing document
   - Delete document from index
   - Verify document is searchable after indexing

3. **Search Execution Tests**
   - Execute simple keyword search
   - Test fuzzy matching finds OCR errors
   - Verify synonym expansion works
   - Test phrase matching accuracy
   - Validate filtering by source and date

4. **Full Detection Workflow Tests**
   - Index document and detect keyword match
   - Verify match includes correct context
   - Test notification queuing after detection
   - Validate deduplication prevents re-alerts
   - Measure end-to-end detection latency

5. **Performance Under Load Tests**
   - Index 1000 documents in batch
   - Search with 100 concurrent subscriptions
   - Measure query latency at scale
   - Test index refresh impact on search
   - Monitor resource usage during bulk operations

### Search Accuracy Tests

1. **Exact Match Accuracy**
   - Find exact keyword in document
   - Handle case variations correctly
   - Match keywords with punctuation
   - Find keywords at word boundaries only
   - Reject partial word matches

2. **Fuzzy Match Quality**
   - Find "diapers" when OCR produces "d1apers"
   - Match "discount" despite "disount" OCR error
   - Avoid false positives with excessive fuzziness
   - Test with various edit distances
   - Validate scoring prefers exact matches

3. **Phrase Match Precision**
   - Match "buy one get one" as exact phrase
   - Reject when words are out of order
   - Handle phrases with common words
   - Test phrase with OCR spacing errors
   - Validate phrase boundary detection

4. **Filter Accuracy**
   - Filter by source returns only matching documents
   - Date range filtering works correctly
   - Category filtering is precise
   - Combined filters work as expected
   - Negative filters exclude correctly

---

## Potential Caveats, Pitfalls, and Edge Cases

### Elasticsearch Operational Issues

1. **Cluster Health and Availability**
   - Cluster may be in yellow or red state (missing replicas)
   - Split-brain scenarios with multiple masters
   - Node failures during indexing operations
   - Network partitions causing cluster instability
   - **Mitigation:** Health monitoring, circuit breakers, graceful degradation

2. **Index Performance Degradation**
   - Index grows too large affecting query performance
   - Too many small segments from frequent updates
   - Mapping explosion from dynamic field creation
   - Query complexity increases response time exponentially
   - **Mitigation:** Index lifecycle management, force merge scheduling, mapping constraints

3. **Resource Exhaustion**
   - Heap memory pressure from large result sets
   - Circuit breaker trips on memory-intensive queries
   - Thread pool rejection due to queue saturation
   - Disk space exhaustion stops indexing
   - **Mitigation:** Resource monitoring, query size limits, proactive scaling

4. **Data Consistency Issues**
   - Near real-time search means delayed visibility
   - Documents indexed but not immediately searchable
   - Index refresh conflicts with bulk operations
   - Replica lag causing inconsistent results
   - **Mitigation:** Understand refresh intervals, wait for refresh when needed

### Search Quality Challenges

5. **False Positive Matches**
   - Fuzzy matching returns unintended results
   - Synonym expansion too broad
   - Common words match inappropriately
   - OCR errors create accidental matches
   - **Mitigation:** Precision tuning, exclusion patterns, minimum confidence thresholds

6. **False Negative Misses**
   - Keyword not found due to OCR errors beyond fuzziness
   - Synonyms not configured for specific terms
   - Analyzer removes important words as stop words
   - Stemming produces unexpected base forms
   - **Mitigation:** Comprehensive synonym lists, analyzer testing, OCR quality monitoring

7. **Relevance Scoring Problems**
   - Low-quality matches scored higher than good matches
   - Document frequency skews scoring unexpectedly
   - Field boosting creates imbalanced results
   - BM25 algorithm assumptions don't fit retail content
   - **Mitigation:** Custom scoring functions, relevance testing, score normalization

8. **Context Extraction Issues**
   - Context window cuts off important information
   - Multiple matches create overwhelming context
   - Page boundaries not respected properly
   - Formatting lost in context extraction
   - **Mitigation:** Intelligent boundary detection, configurable window sizes

### Scalability Concerns

9. **High Subscription Volume**
   - Thousands of active keyword subscriptions
   - Each new document triggers many searches
   - Query execution time grows linearly
   - Database load from subscription lookups
   - **Mitigation:** Batch query execution, subscription caching, query optimization

10. **Large Document Corpus**
    - Millions of indexed documents over time
    - Query performance degrades with index size
    - Storage costs increase significantly
    - Backup and recovery time extends
    - **Mitigation:** Time-based indexes, archival policies, index optimization

11. **Complex Query Patterns**
    - Users create overly broad searches
    - Regex patterns cause exponential matching
    - Deeply nested boolean queries
    - Too many expansion terms from synonyms
    - **Mitigation:** Query complexity limits, pattern restrictions, expansion caps

12. **Burst Traffic Patterns**
    - Scheduled scans create indexing spikes
    - Many subscriptions trigger simultaneously
    - Detection results overwhelm notification queue
    - **Mitigation:** Rate limiting, queue buffers, horizontal scaling

### Data Quality Edge Cases

13. **Empty or Minimal Content**
    - Documents with very little text
    - Pages with only numbers or codes
    - Mostly images with sparse text
    - Blank pages between content
    - **Mitigation:** Minimum content thresholds, sparse document handling

14. **Extremely Long Documents**
    - Documents with thousands of pages
    - Text content exceeds field size limits
    - Query highlighting on huge text fields
    - Context extraction performance degrades
    - **Mitigation:** Content chunking, field size limits, pagination

15. **Special Character Handling**
    - Keywords contain special regex characters
    - Currency symbols not indexed properly
    - Emojis and Unicode symbols in modern ads
    - HTML entities not decoded
    - **Mitigation:** Character escaping, encoding normalization, comprehensive testing

16. **Duplicate Content Across Sources**
    - Same brochure from multiple retailers
    - Slightly different versions of same content
    - National vs regional variations
    - **Mitigation:** Cross-source deduplication, version tracking

### Configuration and Maintenance

17. **Synonym Dictionary Management**
    - Synonyms become stale or incorrect
    - Regional variations not covered
    - New products and terms emerge
    - Conflicting synonym definitions
    - **Mitigation:** Regular review cycles, user feedback integration, version control

18. **Analyzer Configuration Drift**
    - Analyzer behavior changes between Elasticsearch versions
    - Custom filters may have bugs
    - Stop words list needs updating
    - Stemmer produces unexpected results
    - **Mitigation:** Comprehensive testing, version pinning, configuration documentation

19. **Index Schema Evolution**
    - Need to add new fields to schema
    - Changing field types requires reindex
    - Backward compatibility concerns
    - Migration downtime requirements
    - **Mitigation:** Schema versioning, alias switching, reindex strategies

20. **Multi-tenancy Complications**
    - Different users need different synonym sets
    - Subscription-specific analyzers not feasible
    - Privacy concerns with shared indexes
    - **Mitigation:** Query-time synonyms, user-specific filters, proper access controls

### Error Handling Complexities

21. **Partial Search Failures**
    - Some shards fail during query
    - Timeout on specific query conditions
    - Circuit breaker trips mid-search
    - **Mitigation:** Graceful partial results, retry logic, failure logging

22. **Indexing Failures**
    - Document too large to index
    - Invalid field values reject indexing
    - Bulk request partially fails
    - **Mitigation:** Validation before indexing, error isolation, retry queues

23. **Result Set Issues**
    - Query returns more results than expected
    - Pagination cursor expires or becomes invalid
    - Scoring inconsistencies between pages
    - **Mitigation:** Result limits, scroll context management, consistent scoring

---

## Dependencies

- Domain Module (Subscription, MatchResult entities)
- Common Module (utilities, exceptions)
- Elasticsearch client library (High-level REST client or new Java client)
- Messaging Module (publish detection events)

## Success Criteria

- Index documents within 5 seconds of OCR completion
- Query latency < 100ms for 95th percentile
- Keyword detection accuracy > 95% (precision)
- Keyword recall > 90% (finding actual matches)
- Support 10,000+ concurrent subscriptions
- Zero data loss during indexing failures
- Fuzzy matching catches 80%+ of OCR errors
- Synonym coverage for common retail terms
