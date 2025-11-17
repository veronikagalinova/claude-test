# Task: Data Storage and Indexing Infrastructure Implementation

**Module:** Data Layer (PostgreSQL + Elasticsearch + Redis)
**Priority:** Critical
**Phase:** 1-2 (Foundation through Core Features)
**Estimated Duration:** 4 weeks

---

## Overview

This task covers the implementation of the data persistence layer including PostgreSQL for relational data, Elasticsearch for full-text search capabilities, and Redis for caching. Proper data modeling, migration management, indexing strategy, and performance optimization are essential for system scalability.

---

## Implementation Details

### 1. PostgreSQL Database Schema Design

**Objective:** Create efficient, normalized schema for all domain entities.

**Implementation Approach:**
- Design normalized schema following 3NF principles
- Use UUID primary keys for distributed system compatibility
- Implement proper foreign key relationships with cascade rules
- Add database-level constraints (NOT NULL, UNIQUE, CHECK)
- Design indexes for common query patterns
- Use appropriate data types (JSONB for flexible metadata)
- Implement soft deletes for audit trail retention
- Support multi-tenancy if required
- Document schema with comments on tables and columns

**Core Tables:**
- sources: Source configuration and connection details
- documents: Ingested document metadata and status
- extracted_contents: OCR results linked to documents
- keyword_subscriptions: User keyword preferences
- match_results: Detected matches with context
- users: User accounts and authentication data
- processing_jobs: Job execution history
- notification_logs: Email delivery tracking

### 2. Database Migration Management

**Objective:** Version control database schema with reproducible migrations.

**Implementation Approach:**
- Use Flyway or Liquibase for migration management
- Create sequential version-numbered migration scripts
- Make migrations idempotent where possible
- Separate schema migrations from data migrations
- Test migrations on production-like data
- Support rollback scripts for each migration
- Track migration history in metadata table
- Enforce migration execution order
- Validate schema after migrations complete

**Migration Best Practices:**
- One migration per feature/change
- Never modify executed migrations
- Include both up and down scripts
- Test with realistic data volumes
- Document breaking changes
- Schedule data migrations during low-traffic periods

### 3. Database Connection Pooling

**Objective:** Manage database connections efficiently for high concurrency.

**Implementation Approach:**
- Configure HikariCP connection pool (Spring Boot default)
- Set appropriate pool size based on workload
- Configure connection validation queries
- Set connection timeout and idle timeout
- Monitor pool utilization metrics
- Implement connection leak detection
- Configure prepared statement caching
- Handle connection failures gracefully
- Support read replicas for query distribution

**Pool Configuration:**
- Maximum pool size: 2 * CPU cores + effective spindle count
- Minimum idle: Match maximum for consistency
- Connection timeout: 30 seconds
- Idle timeout: 10 minutes
- Max lifetime: 30 minutes (before forced refresh)
- Validation timeout: 5 seconds

### 4. Query Optimization and Indexing Strategy

**Objective:** Ensure database queries perform efficiently at scale.

**Implementation Approach:**
- Analyze query patterns and create appropriate indexes
- Use composite indexes for multi-column queries
- Implement partial indexes for filtered queries
- Use EXPLAIN ANALYZE to verify index usage
- Monitor slow query logs
- Implement query hints where necessary
- Use covering indexes for frequent queries
- Avoid over-indexing (balance write vs read)
- Regular index maintenance (REINDEX)

**Index Types:**
- B-tree: Default for most columns
- GiST/GIN: For JSONB and full-text search
- BRIN: For time-series data (processing dates)
- Hash: For equality comparisons only
- Partial: Index subset of rows (active sources only)

### 5. Data Partitioning Strategy

**Objective:** Manage large tables by partitioning for performance.

**Implementation Approach:**
- Partition match_results by date (monthly)
- Partition documents by source_id for isolation
- Use declarative partitioning (PostgreSQL 12+)
- Implement automatic partition creation
- Prune old partitions based on retention policy
- Ensure queries include partition key for efficiency
- Monitor partition sizes and balance
- Support partition-wise aggregation

**Partitioning Scheme:**
- match_results: Range partition by detection_date
- processing_jobs: Range partition by created_at
- notification_logs: Range partition by sent_at
- extracted_contents: Hash partition by document_id

### 6. Redis Caching Layer

**Objective:** Implement high-performance caching for frequently accessed data.

**Implementation Approach:**
- Cache source configurations with moderate TTL
- Store session data and rate limit counters
- Cache compiled search patterns
- Implement distributed locking with Redis
- Use appropriate data structures (Hash, Set, Sorted Set)
- Configure cache eviction policies (LRU)
- Monitor cache hit rates
- Implement cache stampede prevention
- Support cache invalidation on updates

**Cache Categories:**
- Session cache: User authentication tokens (TTL: session duration)
- Configuration cache: Source configs (TTL: 5 minutes)
- Query cache: Common search results (TTL: 1 hour)
- Rate limit counters: Request tracking (TTL: window size)
- Distributed locks: Job coordination (TTL: lock duration)

### 7. Elasticsearch Cluster Configuration

**Objective:** Set up search engine cluster for scalable full-text search.

**Implementation Approach:**
- Configure cluster with appropriate node count
- Set up master-eligible, data, and coordinating nodes
- Configure shard count based on data volume
- Set replica count for fault tolerance
- Tune JVM heap size (50% of available RAM, max 32GB)
- Configure index lifecycle management (ILM)
- Set up index templates for consistent mapping
- Monitor cluster health and performance
- Implement backup and restore procedures

**Cluster Architecture:**
- Master nodes: 3 dedicated (odd number for quorum)
- Data nodes: Scale based on data volume
- Coordinating nodes: Scale based on query load
- Shard strategy: 1 shard per 30-50 GB
- Replica strategy: 1 replica minimum for fault tolerance

### 8. Elasticsearch Index Lifecycle Management

**Objective:** Automate index maintenance for optimal performance and cost.

**Implementation Approach:**
- Create time-based index pattern (documents-YYYY-MM)
- Define lifecycle phases (hot, warm, cold, delete)
- Configure rollover criteria (size or document count)
- Set retention periods per phase
- Automate force merge in warm phase
- Move old indices to slower storage
- Delete indices past retention period
- Monitor ILM policy execution
- Alert on policy failures

**ILM Phases:**
- Hot: Actively indexing, high performance storage, 7 days
- Warm: No new data, searchable, merge to fewer segments, 30 days
- Cold: Rarely accessed, cheaper storage, frozen, 90 days
- Delete: Remove index after retention period, 365 days

### 9. Data Consistency and Transaction Management

**Objective:** Ensure data integrity across distributed components.

**Implementation Approach:**
- Use database transactions for atomic operations
- Implement optimistic locking for concurrent updates
- Handle transaction isolation levels appropriately
- Implement saga pattern for distributed transactions
- Use idempotency keys for retry safety
- Monitor transaction duration and deadlocks
- Implement eventual consistency where appropriate
- Track consistency metrics
- Provide reconciliation mechanisms

**Transaction Strategies:**
- ACID for critical operations (user creation, subscription changes)
- Eventual consistency for non-critical (search indexing)
- Saga pattern for cross-service (ingestion → OCR → indexing)
- Compensation transactions for rollback
- Dead letter handling for failed operations

### 10. Backup and Disaster Recovery

**Objective:** Protect data with comprehensive backup strategy.

**Implementation Approach:**
- Configure automated PostgreSQL backups (pg_dump, WAL archiving)
- Set up Elasticsearch snapshot repository
- Schedule regular backup jobs
- Test restore procedures periodically
- Implement point-in-time recovery capability
- Store backups in separate geographic location
- Encrypt backup files
- Monitor backup success and size
- Document recovery procedures

**Backup Schedule:**
- PostgreSQL: Daily full backup, continuous WAL archiving
- Elasticsearch: Daily snapshots to object storage
- Redis: RDB snapshots + AOF for persistence
- Retention: 7 daily, 4 weekly, 12 monthly backups
- Recovery Time Objective (RTO): < 4 hours
- Recovery Point Objective (RPO): < 1 hour

---

## Test Scenarios

### Unit Tests

1. **Entity Mapping Tests**
   - Entity fields map to database columns correctly
   - Relationships defined properly (OneToMany, ManyToOne)
   - Cascade rules work as expected
   - Soft delete marks but doesn't remove
   - Optimistic locking version increments

2. **Repository Query Tests**
   - Custom queries return correct results
   - Pagination parameters applied correctly
   - Sorting works across multiple fields
   - Filter conditions combine properly
   - Null handling in queries correct

3. **Cache Service Tests**
   - Cache put stores value correctly
   - Cache get retrieves stored value
   - TTL expiration works
   - Cache eviction clears properly
   - Distributed lock acquired and released

4. **Migration Script Tests**
   - Migration applies without errors
   - Data preserved during migration
   - Rollback restores previous state
   - Constraints enforced after migration
   - Indexes created correctly

### Integration Tests

1. **Database Operations**
   - CRUD operations complete successfully
   - Transactions commit and rollback properly
   - Connection pool handles concurrent access
   - Deadlock detection and resolution
   - Large batch operations complete

2. **Elasticsearch Integration**
   - Documents index successfully
   - Search queries return expected results
   - Index creation with mapping works
   - Bulk indexing handles errors
   - Cluster failover transparent to application

3. **Redis Caching Integration**
   - Cache improves response times
   - Cache invalidation works correctly
   - Distributed locks coordinate access
   - Connection pool stable under load
   - Failover to replica handles gracefully

4. **Cross-Component Consistency**
   - Document in PostgreSQL matches Elasticsearch
   - Cache reflects database state
   - Failed indexing logged and retryable
   - Reconciliation process corrects drift
   - Audit trail complete across stores

5. **Backup and Restore**
   - Backup completes within time window
   - Restore produces identical data
   - Point-in-time recovery accurate
   - Cross-datacenter replication works
   - Application handles restore gracefully

### Performance Tests

1. **Database Query Performance**
   - Complex queries complete < 100ms
   - Index usage verified with EXPLAIN
   - Connection pool doesn't bottleneck
   - Concurrent queries scale linearly
   - No table scans on production queries

2. **Elasticsearch Search Performance**
   - Full-text search < 50ms p95
   - Aggregation queries perform well
   - Indexing throughput meets requirements
   - Cluster handles peak load
   - No hot spots across shards

3. **Cache Hit Rate Analysis**
   - Cache hit rate > 80% for config data
   - Cache reduces database load significantly
   - No cache stampedes under load
   - Memory usage within bounds
   - Eviction policy optimal

4. **Scalability Testing**
   - Database handles 1M+ documents
   - Elasticsearch indexes scale horizontally
   - Read replicas distribute load
   - Partitioning improves query speed
   - No performance cliff at scale

---

## Potential Caveats, Pitfalls, and Edge Cases

### PostgreSQL Challenges

1. **Connection Pool Exhaustion**
   - All connections in use during peak load
   - Long-running transactions hold connections
   - Connection leaks from improper handling
   - Application hangs waiting for connection
   - **Mitigation:** Pool sizing, connection timeout, leak detection, monitoring

2. **Lock Contention and Deadlocks**
   - Multiple transactions updating same rows
   - Foreign key checks causing implicit locks
   - Index maintenance blocking operations
   - Deadlock detection kills transactions
   - **Mitigation:** Lock ordering, shorter transactions, retry logic, monitoring

3. **Bloated Tables and Indexes**
   - Deleted rows not vacuumed
   - Index bloat from frequent updates
   - Transaction ID wraparound risk
   - Query performance degrades over time
   - **Mitigation:** Autovacuum tuning, regular maintenance, monitoring bloat metrics

4. **Query Plan Regression**
   - Statistics become stale
   - Query planner chooses wrong plan
   - Table growth changes optimal strategy
   - Performance suddenly degrades
   - **Mitigation:** Regular ANALYZE, plan monitoring, hint usage, statistics targets

5. **Migration Failures**
   - Migration script has syntax error
   - Data migration times out
   - Constraint violation during migration
   - Migration partially applied
   - **Mitigation:** Test migrations, transaction wrapping, validation checks, rollback plans

### Elasticsearch Operational Issues

6. **Cluster Instability**
   - Master node election issues
   - Split brain scenario
   - Nodes leaving cluster unexpectedly
   - Yellow or red cluster status
   - **Mitigation:** Proper node count, network configuration, monitoring, quick recovery

7. **Shard Imbalance and Hot Spots**
   - Uneven data distribution across shards
   - Some nodes overloaded
   - Query routing inefficient
   - Storage fills on specific nodes
   - **Mitigation:** Rebalancing, shard allocation awareness, custom routing

8. **Index Mapping Conflicts**
   - Dynamic mapping creates wrong types
   - Field type cannot be changed
   - Template not applied to new index
   - Mapping explosion from too many fields
   - **Mitigation:** Strict mapping, template validation, field limits, schema governance

9. **Search Relevance Problems**
   - Results not matching user expectations
   - Scoring algorithm not optimal
   - Boosting configuration incorrect
   - Synonyms not applied properly
   - **Mitigation:** Relevance tuning, user feedback, A/B testing, analyzer verification

10. **Bulk Indexing Failures**
    - Some documents fail in bulk request
    - Entire batch rejected for one bad document
    - Retry logic causes duplicates
    - Throttling due to indexing pressure
    - **Mitigation:** Error handling per document, idempotency, backpressure monitoring

### Redis Caching Pitfalls

11. **Cache Invalidation Complexity**
    - Cache contains stale data
    - Invalidation missed some keys
    - Pattern-based invalidation too broad
    - Consistency issues between cache and source
    - **Mitigation:** Event-driven invalidation, versioned keys, TTL fallback

12. **Memory Pressure**
    - Redis memory limit exceeded
    - Eviction policy removes important data
    - Large values cause fragmentation
    - No memory left for operations
    - **Mitigation:** Memory monitoring, maxmemory policy, value size limits, sharding

13. **Cache Stampede**
    - Cache expires and all requests hit database
    - Thundering herd problem
    - Database overwhelmed
    - Slow recovery compounds problem
    - **Mitigation:** Staggered expiration, probabilistic early refresh, request coalescing

14. **Network Partition with Redis**
    - Application can't reach Redis
    - Inconsistent state across services
    - Distributed lock becomes invalid
    - Failover causes data loss
    - **Mitigation:** Circuit breaker, fallback to source, proper replication, sentinel/cluster mode

15. **Key Namespace Collisions**
    - Different features use same key names
    - Multi-tenancy key isolation broken
    - Development and production keys mixed
    - Accidental key overwrites
    - **Mitigation:** Key naming conventions, namespace prefixes, code review

### Data Consistency Challenges

16. **Dual Write Problems**
    - Write to PostgreSQL succeeds, Elasticsearch fails
    - Inconsistent state between stores
    - Retry causes duplicate in one store
    - No atomic cross-store transaction
    - **Mitigation:** Outbox pattern, eventual consistency, reconciliation jobs

17. **Eventual Consistency Delays**
    - Data visible in database but not searchable
    - User confusion from inconsistent views
    - Race conditions in read-after-write
    - Replication lag causes old data reads
    - **Mitigation:** Sync writes where critical, user expectations, read-your-writes consistency

18. **Transaction Isolation Issues**
    - Dirty reads in concurrent transactions
    - Phantom reads affect aggregations
    - Lost updates from race conditions
    - Long transactions block others
    - **Mitigation:** Appropriate isolation level, optimistic locking, short transactions

19. **Data Type Mismatches**
    - PostgreSQL and Elasticsearch types differ
    - JSON serialization loses precision
    - Date timezone handling inconsistent
    - Null vs empty value confusion
    - **Mitigation:** Explicit type mapping, serialization configuration, validation

### Performance and Scalability Issues

20. **N+1 Query Problem**
    - Lazy loading causes multiple queries
    - Each entity fetch triggers database call
    - List operations become extremely slow
    - Database connection pool saturated
    - **Mitigation:** Eager loading with join fetch, batch fetching, query optimization

21. **Index Over-Optimization**
    - Too many indexes slow writes
    - Index selection by planner wrong
    - Storage consumed by indexes
    - Maintenance overhead high
    - **Mitigation:** Index usage analysis, remove unused indexes, composite indexes

22. **Partition Management Overhead**
    - Creating partitions not automated
    - Queries not including partition key
    - Old partitions not pruned
    - Cross-partition queries slow
    - **Mitigation:** Automation scripts, query review, partition-aware queries, regular cleanup

23. **Backup Impact on Performance**
    - Backup causes I/O contention
    - Long-running transactions blocked
    - Replica lag during backup
    - Storage pressure from backup files
    - **Mitigation:** Schedule during low load, incremental backups, separate backup storage

### Operational and Maintenance Concerns

24. **Schema Migration Coordination**
    - Multiple application instances running different versions
    - Backward incompatible changes break old instances
    - Migration during deployment window
    - Rollback after migration difficult
    - **Mitigation:** Backward compatible migrations, blue-green deployment, feature flags

25. **Monitoring Blind Spots**
    - Query performance degradation not detected
    - Storage filling up silently
    - Replication lag not monitored
    - Cache effectiveness unknown
    - **Mitigation:** Comprehensive metrics, alerting rules, regular capacity reviews

26. **Disaster Recovery Failures**
    - Backup not tested for restore
    - Recovery procedure documentation outdated
    - Backup corruption not detected
    - RTO/RPO requirements not met
    - **Mitigation:** Regular restore tests, documented procedures, backup verification

---

## Dependencies

- Infrastructure: PostgreSQL 15+, Elasticsearch 8.x, Redis 7.x
- Libraries: Spring Data JPA, Spring Data Elasticsearch, Spring Data Redis
- Migration: Flyway or Liquibase
- Connection Pool: HikariCP
- Monitoring: Micrometer metrics exporters

## Success Criteria

- Database handles 1M+ documents without performance degradation
- Elasticsearch query latency < 100ms p95
- Cache hit rate > 80% for configuration data
- Zero data loss during failures (RPO = 0)
- Recovery time < 4 hours for full restore
- Migration execution < 10 minutes for schema changes
- Connection pool utilization < 80% under peak load
- Backup completion within 1-hour window
- Data consistency across stores > 99.9%
- No unplanned downtime from storage issues
