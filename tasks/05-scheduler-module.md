# Task: Scheduler and Job Orchestration Module Implementation

**Module:** `com.retailmonitor.scheduler`
**Priority:** High
**Phase:** 2 (Core Features)
**Estimated Duration:** 2 weeks

---

## Overview

The Scheduler Module orchestrates periodic document scans, manages job execution, monitors source health, and coordinates maintenance tasks. It uses cron-based scheduling to trigger automated workflows and provides visibility into job execution status.

---

## Implementation Details

### 1. Cron-Based Job Scheduler

**Objective:** Enable flexible scheduling of scans using cron expressions.

**Implementation Approach:**
- Integrate Spring Scheduler or Quartz Scheduler for robust scheduling
- Parse and validate cron expressions for each source
- Support standard cron syntax (minute, hour, day, month, weekday)
- Handle timezone-aware scheduling
- Implement job persistence for recovery after restarts
- Support one-time and recurring schedules
- Enable dynamic schedule modification without restart
- Track next execution time for each scheduled job

**Cron Expression Support:**
- Standard 5-6 field cron syntax
- Special keywords (@daily, @weekly, @monthly)
- Range expressions (1-5, MON-FRI)
- Step values (*/15 for every 15 minutes)
- List values (1,15,30)
- Timezone specification per schedule

### 2. Scan Job Orchestration

**Objective:** Coordinate the complete scan workflow from trigger to completion.

**Implementation Approach:**
- Create orchestrator that manages scan lifecycle
- Load all sources scheduled for current execution window
- Validate source accessibility before starting scan
- Trigger ingestion module for each active source
- Track progress of document collection and processing
- Handle parallel execution of multiple source scans
- Implement job dependencies (scan A must complete before B)
- Generate comprehensive scan reports
- Update source last-scan timestamps atomically

**Scan Workflow:**
1. Scheduler triggers scan job at configured time
2. Load active source configurations from database
3. Filter sources due for scanning
4. Validate each source is healthy and accessible
5. Create job execution record with PENDING status
6. Dispatch ingestion tasks for each source
7. Monitor task completion and aggregate results
8. Update job status and source metadata
9. Trigger notifications for scan completion

### 3. Source Health Monitoring

**Objective:** Track source availability and automatically manage unhealthy sources.

**Implementation Approach:**
- Perform connectivity checks before each scan
- Track consecutive failure counts per source
- Implement health status state machine (ACTIVE → DEGRADED → UNHEALTHY)
- Auto-pause sources after configurable failure threshold
- Alert administrators when sources become unhealthy
- Provide manual recovery mechanism for paused sources
- Log health check results for trend analysis
- Support different health check strategies per source type

**Health Status Transitions:**
- ACTIVE: Source functioning normally
- DEGRADED: Recent failures but still operational (1-2 failures)
- UNHEALTHY: Multiple consecutive failures (3+ failures)
- PAUSED: Manually or automatically disabled
- Recovery: Manual intervention or automatic retry after cooldown

### 4. Job Tracking and Persistence

**Objective:** Maintain complete history of job executions for auditing and debugging.

**Implementation Approach:**
- Persist job metadata in PostgreSQL
- Store job type, start time, end time, status, and results
- Track documents processed, errors encountered, matches found
- Implement job log storage (separate from application logs)
- Support job result queries and filtering
- Calculate job performance metrics
- Archive old job records based on retention policy
- Enable job result export for reporting

**Job Record Fields:**
- Job ID (unique identifier)
- Job type (scan, cleanup, health check)
- Source ID (for source-specific jobs)
- Start timestamp and end timestamp
- Status (PENDING, RUNNING, COMPLETED, FAILED, CANCELLED)
- Documents processed count
- Errors encountered with details
- Execution duration
- Trigger type (scheduled, manual, retry)

### 5. Maintenance Task Scheduling

**Objective:** Automate system maintenance operations.

**Implementation Approach:**
- Schedule cleanup jobs for old documents and results
- Implement index optimization tasks (Elasticsearch maintenance)
- Schedule database vacuum and statistics updates
- Automate log rotation and archival
- Schedule health metric aggregation
- Implement backup job coordination
- Support maintenance windows (avoid during peak usage)
- Track maintenance job completion and effectiveness

**Maintenance Jobs:**
- Daily: Clean temporary files, aggregate metrics
- Weekly: Optimize search indexes, vacuum database tables
- Monthly: Archive old data, rotate logs, full health check
- On-demand: Reprocess failed documents, rebuild indexes

### 6. Retry and Recovery Mechanisms

**Objective:** Automatically recover from transient failures.

**Implementation Approach:**
- Implement automatic retry for failed scan jobs
- Configure maximum retry attempts per job type
- Use exponential backoff between retries
- Track retry history for pattern analysis
- Support partial retry (retry only failed sources)
- Implement dead letter queue for permanently failed jobs
- Alert on repeated failures for same source
- Provide manual retry trigger through admin interface

**Retry Policy:**
- First retry: 5 minutes after failure
- Second retry: 15 minutes after first retry
- Third retry: 1 hour after second retry
- Maximum retries: Configurable (default 3)
- Permanent failure: Move to dead letter queue

### 7. Concurrency and Resource Management

**Objective:** Control resource usage and prevent system overload.

**Implementation Approach:**
- Limit concurrent scan jobs (prevent resource exhaustion)
- Implement job queue with priority levels
- Support job locking to prevent duplicate execution
- Monitor system resources before starting new jobs
- Throttle job execution based on current load
- Implement circuit breaker for downstream services
- Track resource usage per job for capacity planning
- Support job preemption for high-priority tasks

**Concurrency Controls:**
- Maximum concurrent scans: Configurable (default 5)
- Job queue size: Bounded with overflow handling
- Resource thresholds: CPU, memory, disk triggers
- Priority levels: Critical, high, normal, low
- Locking mechanism: Distributed lock for cluster deployment

---

## Test Scenarios

### Unit Tests

1. **Cron Expression Parsing Tests**
   - Parse valid standard cron expression
   - Parse expressions with special keywords
   - Validate invalid expressions rejected
   - Calculate next execution time correctly
   - Handle timezone conversions properly
   - Test edge cases (end of month, leap year)

2. **Job State Machine Tests**
   - Transition from PENDING to RUNNING correctly
   - Handle RUNNING to COMPLETED transition
   - Process RUNNING to FAILED transition
   - Prevent invalid state transitions
   - Track state change timestamps

3. **Health Status Calculation Tests**
   - Increment failure count on failed check
   - Reset failure count on success
   - Transition to DEGRADED at threshold
   - Transition to UNHEALTHY at higher threshold
   - Remain ACTIVE with occasional failures

4. **Retry Logic Tests**
   - Calculate correct backoff intervals
   - Enforce maximum retry count
   - Track retry attempt history
   - Respect retry policy configuration
   - Handle permanent failure correctly

5. **Concurrency Control Tests**
   - Enforce maximum concurrent job limit
   - Queue jobs when limit reached
   - Priority ordering in queue
   - Job locking prevents duplicates
   - Release locks on completion

### Integration Tests

1. **Scheduler Framework Integration**
   - Job scheduled at correct time
   - Job executes within tolerance window
   - Schedule modifications applied dynamically
   - Jobs survive application restart
   - Multiple jobs execute without interference

2. **Database Job Persistence**
   - Job records created correctly
   - Status updates persisted immediately
   - Query historical jobs accurately
   - Handle concurrent updates safely
   - Archive old records properly

3. **Distributed Locking Tests**
   - Single instance acquires lock
   - Lock released on completion
   - Lock released on failure
   - Timeout handling for stale locks
   - Multiple instances respect locks

4. **End-to-End Scan Orchestration**
   - Schedule triggers scan job
   - Sources loaded correctly
   - Ingestion tasks dispatched
   - Results aggregated accurately
   - Final status reflects reality

5. **Failure Recovery Tests**
   - Job restarts after application crash
   - Incomplete jobs identified on startup
   - Recovery logic executes properly
   - Data consistency maintained
   - No duplicate processing

### Performance Tests

1. **High Frequency Scheduling**
   - Handle minute-level scheduling precision
   - Multiple jobs triggering simultaneously
   - No job execution drift over time
   - Memory stable with many scheduled jobs

2. **Large Scale Job Management**
   - Track thousands of job records
   - Query performance remains acceptable
   - Archive process doesn't block operations
   - Historical analysis remains fast

3. **Concurrent Execution Stress**
   - Maximum concurrent jobs running
   - Resource usage within bounds
   - No deadlocks or race conditions
   - Graceful degradation under load

---

## Potential Caveats, Pitfalls, and Edge Cases

### Scheduling Complexities

1. **Timezone and Daylight Saving Time**
   - Cron expression assumes specific timezone
   - DST transitions cause schedule ambiguity
   - Jobs scheduled at 2 AM might not run during DST change
   - International sources in different timezones
   - **Mitigation:** Use UTC internally, handle DST explicitly, document timezone behavior

2. **Clock Drift and Synchronization**
   - Server clock drifts from actual time
   - NTP corrections cause time jumps
   - Cluster nodes have different times
   - Scheduled jobs fire at wrong time
   - **Mitigation:** NTP synchronization, clock drift monitoring, tolerance windows

3. **Schedule Overlap and Collision**
   - Multiple sources scheduled at same time
   - Previous scan still running when next triggers
   - Resource contention from overlapping jobs
   - Queue backs up from simultaneous triggers
   - **Mitigation:** Stagger schedules, skip-if-running policy, load balancing

4. **Cron Expression Complexity**
   - Users create overly complex expressions
   - Expression doesn't match intended schedule
   - Edge cases in month/weekday combinations
   - Ambiguous interpretations of syntax
   - **Mitigation:** Expression validator, preview next N executions, clear documentation

### Job Execution Failures

5. **Partial Scan Failures**
   - Some sources succeed while others fail
   - Network issues affect subset of sources
   - Individual document failures in batch
   - Inconsistent state after partial completion
   - **Mitigation:** Independent source processing, partial success handling, clear status reporting

6. **Job Stuck in Running State**
   - Processing hangs without timeout
   - Network call never returns
   - Memory leak causes gradual slowdown
   - Database connection lost mid-processing
   - **Mitigation:** Job timeouts, watchdog threads, heartbeat monitoring, automatic cancellation

7. **Cascade Failures**
   - One failed source triggers cascade of failures
   - Database overload from error logging
   - Queue saturation from retry attempts
   - Alert system overwhelmed
   - **Mitigation:** Circuit breakers, rate-limited retries, alert aggregation, backoff strategies

8. **Data Corruption During Job**
   - Job writes partial results before failure
   - Transaction not properly rolled back
   - Inconsistent state across services
   - Duplicate processing from retry
   - **Mitigation:** Transactional boundaries, idempotent operations, consistency checks

### Resource Management Issues

9. **Memory Exhaustion**
   - Too many concurrent jobs consume all memory
   - Job results accumulate without cleanup
   - Memory leaks in job execution code
   - Large job history queries cause OOM
   - **Mitigation:** Memory limits per job, aggressive garbage collection, pagination

10. **Thread Pool Exhaustion**
    - All scheduler threads busy with stuck jobs
    - New jobs can't be scheduled
    - Deadlock between job threads
    - Thread starvation for critical jobs
    - **Mitigation:** Thread pool sizing, job timeouts, thread dump monitoring, priority pools

11. **Database Connection Exhaustion**
    - Jobs hold connections too long
    - Connection pool depleted
    - Queries time out waiting for connections
    - Long-running transactions block others
    - **Mitigation:** Connection timeout configuration, pool monitoring, connection release policies

12. **Disk Space Issues**
    - Job logs fill up disk
    - Temporary files not cleaned up
    - Job result storage grows unbounded
    - Database transaction logs expand
    - **Mitigation:** Log rotation, temp file cleanup, archival policies, disk monitoring

### Coordination Challenges

13. **Distributed Scheduler Problems**
    - Multiple instances try to run same job
    - Split-brain in cluster causes duplication
    - Lock service becomes unavailable
    - Leader election takes too long
    - **Mitigation:** Robust distributed locking, leader election algorithms, lock service redundancy

14. **Configuration Changes During Execution**
    - Source configuration updated while scanning
    - Schedule modified during job execution
    - Source deleted while job running
    - Priority changed after job queued
    - **Mitigation:** Configuration snapshots, handle deletions gracefully, re-evaluation points

15. **Service Dependencies**
    - Ingestion service unavailable
    - Message queue down
    - Database unreachable
    - External health check services fail
    - **Mitigation:** Dependency health checks, circuit breakers, graceful degradation

16. **Job Priority Conflicts**
    - High-priority job can't preempt running job
    - Priority inversion scenarios
    - Resource starvation for low-priority jobs
    - Priority escalation logic bugs
    - **Mitigation:** Preemption support, anti-starvation mechanisms, priority inheritance

### Monitoring and Visibility Gaps

17. **Silent Job Failures**
    - Job fails without proper logging
    - Error swallowed in generic catch
    - Status not updated before crash
    - No alert generated for failure
    - **Mitigation:** Comprehensive error handling, finally blocks for status updates, external monitoring

18. **Metric Inconsistencies**
    - Job duration calculated incorrectly
    - Document counts don't match reality
    - Success rate skewed by retries
    - Health metrics lag behind actual state
    - **Mitigation:** Accurate instrumentation, metric validation, real-time aggregation

19. **Historical Analysis Limitations**
    - Old job records purged too aggressively
    - Aggregated metrics lose detail
    - Pattern detection not possible without history
    - Capacity planning lacks historical data
    - **Mitigation:** Balanced retention policies, metric pre-aggregation, cold storage archives

20. **Alert Fatigue**
    - Too many alerts for minor issues
    - Critical alerts lost in noise
    - Repetitive alerts for same problem
    - Alert storms during incidents
    - **Mitigation:** Alert severity tuning, alert deduplication, intelligent grouping, escalation policies

### Edge Cases

21. **First Time Source Scan**
    - No previous scan baseline exists
    - All documents appear as new
    - Could trigger massive processing load
    - No deduplication history available
    - **Mitigation:** Incremental first scan, limit initial batch size, special handling for new sources

22. **Source with No New Content**
    - Scan completes but nothing to process
    - Resource spent on empty checks
    - Job appears successful but useless
    - Users expect something to happen
    - **Mitigation:** Record no-change scans, optimize empty checks, report accurately

23. **Very Long Running Jobs**
    - Processing takes longer than schedule interval
    - Next execution overlaps current
    - Resource held for extended period
    - Timeouts kill valid long operations
    - **Mitigation:** Dynamic timeout adjustment, skip-if-running, resource reservation

24. **Scheduler Restart During Execution**
    - Application restarts while jobs running
    - Job state inconsistent after restart
    - Orphaned locks from previous instance
    - Duplicate job execution on recovery
    - **Mitigation:** Persistent job state, graceful shutdown, lock cleanup on startup

25. **Mass Source Configuration Import**
    - Bulk import of many new sources
    - All scheduled at similar times
    - System overwhelmed at trigger time
    - No gradual ramp-up
    - **Mitigation:** Import validation, automatic schedule distribution, soft launch periods

---

## Dependencies

- Domain Module (Source entities)
- Common Module (utilities, exceptions)
- External: Spring Scheduler or Quartz
- Ingestion Module (triggered by scheduler)
- Messaging Module (job events)
- Monitoring Module (job metrics)

## Success Criteria

- Jobs execute within 1 minute of scheduled time
- Zero missed scheduled executions
- Support 1000+ scheduled sources
- Job history retained for 30+ days
- Health monitoring accuracy > 99%
- Automatic recovery from transient failures
- No duplicate job executions in cluster
- Resource usage predictable and bounded
- Clear visibility into all job states
- Maintenance jobs complete without impacting production
