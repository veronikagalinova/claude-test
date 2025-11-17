# Task: REST API Module Implementation

**Module:** `com.retailmonitor.api`
**Priority:** High
**Phase:** 2 (Core Features)
**Estimated Duration:** 3 weeks

---

## Overview

The API Module exposes REST endpoints for system configuration, monitoring, and management. It provides the interface for administrators to configure sources, manage subscriptions, query results, and monitor system health. The API follows REST best practices with comprehensive documentation.

---

## Implementation Details

### 1. REST Controller Architecture

**Objective:** Create well-structured, maintainable API controllers.

**Implementation Approach:**
- Organize controllers by domain entity (Source, Subscription, Document, Match)
- Use Spring Web MVC with annotation-based routing
- Implement consistent URL patterns following REST conventions
- Separate controller logic from business logic (thin controllers)
- Use constructor injection for dependencies
- Apply cross-cutting concerns via interceptors
- Version API from the start (v1 prefix)
- Document every endpoint with OpenAPI annotations

**Controller Organization:**
- SourceController: CRUD operations for source configurations
- SubscriptionController: Keyword subscription management
- DocumentController: Document status and results queries
- MatchController: Match result retrieval and analysis
- UserController: User management and preferences
- HealthController: System health and status endpoints
- AdminController: Administrative operations and monitoring

### 2. Request/Response DTO Layer

**Objective:** Decouple API contracts from internal domain models.

**Implementation Approach:**
- Create separate DTOs for requests and responses
- Use Java records for immutable DTOs (Java 17+)
- Implement mapper layer to convert between DTOs and entities
- Apply validation annotations on request DTOs
- Include only necessary fields in responses (no entity leakage)
- Support field filtering (allow clients to request specific fields)
- Version DTOs alongside API version
- Document DTO fields with clear descriptions

**DTO Categories:**
- CreateSourceRequest: Fields needed to create new source
- UpdateSourceRequest: Partial update with optional fields
- SourceResponse: Public representation of source entity
- PagedResponse: Generic wrapper for paginated results
- ErrorResponse: Standardized error format
- HealthResponse: System health status structure

### 3. Input Validation Framework

**Objective:** Ensure all API inputs are validated before processing.

**Implementation Approach:**
- Use Bean Validation (JSR-380) annotations
- Implement custom validators for domain-specific rules
- Validate cron expressions with custom validator
- Validate URL formats and accessibility
- Apply size limits to string fields
- Validate enum values against allowed options
- Implement cross-field validation (field A required if field B present)
- Return detailed validation error messages

**Validation Rules:**
- Required fields: @NotNull, @NotBlank, @NotEmpty
- Size constraints: @Size, @Min, @Max
- Format validation: @Email, @URL, @Pattern
- Custom validators: @ValidCronExpression, @ValidSourceType
- Group validation: Different rules for create vs update
- Nested object validation: @Valid annotation propagation

### 4. Exception Handling and Error Responses

**Objective:** Provide consistent, informative error responses across all endpoints.

**Implementation Approach:**
- Implement global exception handler with @ControllerAdvice
- Map domain exceptions to appropriate HTTP status codes
- Create standardized error response structure
- Include correlation ID for error tracking
- Provide developer-friendly error messages (without security leaks)
- Support multiple error formats (JSON, problem details RFC 7807)
- Log exceptions with full context for debugging
- Handle framework exceptions (validation, serialization)

**Error Response Structure:**
- HTTP status code (4xx for client, 5xx for server errors)
- Error code (application-specific identifier)
- Human-readable message
- Timestamp of error occurrence
- Path that caused error
- Correlation ID for tracing
- Validation errors array (for 400 responses)

### 5. Pagination and Filtering

**Objective:** Support efficient querying of large result sets.

**Implementation Approach:**
- Implement cursor-based and offset-based pagination
- Support configurable page size with maximum limit
- Return pagination metadata (total count, page info, links)
- Implement sorting by multiple fields
- Support filtering by various criteria
- Use query parameters for filter specification
- Cache count queries for performance
- Implement HATEOAS links for navigation

**Pagination Features:**
- Page number and size parameters
- Total elements and total pages in response
- First, last, next, previous indicators
- Self-describing links in response
- Maximum page size enforcement (prevent abuse)
- Default page size when not specified

### 6. Rate Limiting and Throttling

**Objective:** Protect API from abuse and ensure fair resource allocation.

**Implementation Approach:**
- Implement per-client rate limiting
- Use token bucket algorithm for smooth limiting
- Apply different limits per endpoint type
- Return rate limit headers (X-RateLimit-*)
- Queue or reject requests exceeding limits
- Support burst capacity for legitimate traffic
- Configure limits via external configuration
- Monitor and alert on rate limit violations

**Rate Limit Configuration:**
- Per-user limits: Requests per minute/hour
- Per-IP limits: Prevent anonymous abuse
- Endpoint-specific limits: Expensive operations more restricted
- Global limits: Overall system protection
- Headers: X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset

### 7. API Documentation with OpenAPI

**Objective:** Generate comprehensive, interactive API documentation.

**Implementation Approach:**
- Use Springdoc OpenAPI for automatic documentation generation
- Annotate controllers with @Operation, @ApiResponse
- Document request/response schemas with examples
- Describe all possible error responses
- Group endpoints by functionality (tags)
- Include authentication requirements
- Provide example requests and responses
- Support documentation export (JSON/YAML)

**Documentation Features:**
- Interactive API explorer (Swagger UI)
- Request/response schema definitions
- Authentication mechanism description
- Error response catalog
- Endpoint grouping by domain
- Change log for API versions
- SDK generation support

### 8. Content Negotiation

**Objective:** Support multiple response formats based on client preferences.

**Implementation Approach:**
- Default to JSON (application/json)
- Support Accept header for format selection
- Implement XML support if required
- Handle unsupported media types gracefully
- Apply consistent serialization configuration
- Configure date/time format standards (ISO 8601)
- Handle null field serialization policy
- Support compression (gzip) for large responses

**Serialization Configuration:**
- Date format: ISO 8601 (2025-11-17T10:30:00Z)
- Null handling: Exclude nulls or include explicitly
- Enum serialization: String representation
- BigDecimal precision: Configure for monetary values
- Collection handling: Consistent empty collection behavior
- Error message localization support

---

## Test Scenarios

### Unit Tests

1. **Controller Method Tests**
   - Correct HTTP method mapping (GET, POST, PUT, DELETE)
   - Path variable extraction works correctly
   - Query parameter binding functions properly
   - Request body deserialization accurate
   - Response serialization correct
   - Status codes returned appropriately

2. **DTO Validation Tests**
   - Required fields trigger validation error
   - Size constraints enforced correctly
   - Pattern validation rejects invalid formats
   - Custom validators execute properly
   - Validation groups apply correctly
   - Error messages are descriptive

3. **Mapper Tests**
   - Entity to DTO conversion accurate
   - DTO to entity conversion correct
   - Null handling in mappings
   - Nested object mapping works
   - Collection mapping preserves order
   - Partial updates map correctly

4. **Exception Handler Tests**
   - Domain exceptions map to correct status codes
   - Validation exceptions return 400 with details
   - Not found exceptions return 404
   - Unauthorized exceptions return 401
   - Server errors return 500 with safe message
   - Correlation ID included in all errors

5. **Pagination Tests**
   - Page calculation correct
   - Boundary conditions handled (first, last page)
   - Total count accurate
   - Empty result set handled
   - Maximum page size enforced
   - Sort parameters applied correctly

### Integration Tests

1. **Full Request Lifecycle**
   - Request received by controller
   - Validation executed successfully
   - Service layer invoked correctly
   - Database operations complete
   - Response returned with correct data
   - Headers set appropriately

2. **Authentication and Authorization**
   - Valid token grants access
   - Invalid token rejected with 401
   - Insufficient permissions return 403
   - Token expiration handled correctly
   - Refresh token flow works

3. **CRUD Operations**
   - Create resource returns 201 with location header
   - Read resource returns complete data
   - Update resource persists changes
   - Delete resource removes correctly
   - Concurrent modifications handled

4. **Rate Limiting Integration**
   - Rate limit headers returned correctly
   - Exceeding limit returns 429
   - Rate limit resets after window
   - Different limits for different endpoints
   - Client identification works correctly

5. **Error Scenarios**
   - Invalid input returns detailed validation errors
   - Resource not found returns 404
   - Conflict (duplicate) returns 409
   - Server error returns safe 500 response
   - Timeout returns 504 Gateway Timeout

### Performance Tests

1. **Response Time Under Load**
   - Simple GET requests < 50ms p95
   - Complex queries < 200ms p95
   - Create operations < 100ms p95
   - Paginated results performant
   - No degradation with concurrent requests

2. **Throughput Testing**
   - Handle 100 requests/second sustained
   - Scale with additional instances
   - Connection pooling efficient
   - No resource leaks under load
   - Graceful degradation at limits

3. **Large Payload Handling**
   - Large response serialization efficient
   - Request body size limits enforced
   - Streaming for very large responses
   - Memory usage bounded
   - Compression reduces bandwidth

---

## Potential Caveats, Pitfalls, and Edge Cases

### API Design Issues

1. **Inconsistent Response Structures**
   - Different endpoints return different formats
   - Error responses vary in structure
   - Null vs empty collection confusion
   - Date format inconsistency
   - **Mitigation:** Establish and enforce standards, use response wrappers

2. **Breaking Changes in API Evolution**
   - Field removals break clients
   - Type changes cause deserialization failures
   - URL restructuring invalidates client code
   - Behavior changes surprise consumers
   - **Mitigation:** API versioning, deprecation warnings, backward compatibility

3. **Over-fetching and Under-fetching**
   - Responses include unnecessary data
   - Multiple requests needed for complete information
   - N+1 query problems at API level
   - Inefficient for mobile clients
   - **Mitigation:** Field selection, GraphQL consideration, compound endpoints

4. **Pagination Challenges**
   - Offset pagination inconsistent when data changes
   - Total count expensive for large datasets
   - Cursor-based pagination complex to implement
   - Deep pagination performance issues
   - **Mitigation:** Use cursor pagination, cache counts, limit maximum depth

### Input Validation Vulnerabilities

5. **Injection Attacks**
   - SQL injection through unsanitized input
   - NoSQL injection in search queries
   - Command injection in file paths
   - LDAP injection in user queries
   - **Mitigation:** Parameterized queries, input sanitization, whitelisting

6. **Cross-Site Scripting (XSS)**
   - Malicious scripts in input fields
   - Reflected XSS in error messages
   - Stored XSS in database content
   - **Mitigation:** Output encoding, Content Security Policy, input sanitization

7. **Mass Assignment Vulnerabilities**
   - Client sends unexpected fields
   - Internal fields overwritten (role, permissions)
   - Hidden fields populated maliciously
   - **Mitigation:** Explicit DTO fields, whitelist allowed properties, ignore unknown

8. **Denial of Service via Input**
   - Extremely large request bodies
   - Complex regex causing ReDoS
   - Deeply nested JSON objects
   - Huge arrays in requests
   - **Mitigation:** Size limits, depth limits, timeout on parsing, rate limiting

### Authentication and Authorization Gaps

9. **Token Management Issues**
   - JWT tokens not properly validated
   - Token expiration not enforced
   - Token revocation not implemented
   - Sensitive data in token payload
   - **Mitigation:** Proper JWT libraries, token blacklisting, minimize token content

10. **Authorization Bypass**
    - Horizontal privilege escalation (access other user's data)
    - Vertical privilege escalation (gain admin access)
    - Missing authorization checks on endpoints
    - IDOR (Insecure Direct Object References)
    - **Mitigation:** Consistent authorization middleware, ownership checks, audit logging

11. **Session Management Problems**
    - Sessions not properly invalidated
    - Session fixation vulnerabilities
    - Concurrent session limits not enforced
    - Session timeout too long
    - **Mitigation:** Proper session lifecycle, secure session configuration, monitoring

### Performance and Scalability

12. **N+1 Query Problems**
    - Each API call triggers multiple database queries
    - Nested object loading causes query explosion
    - List endpoints particularly affected
    - Performance degrades with data growth
    - **Mitigation:** Eager loading strategies, query optimization, caching

13. **Memory Pressure from Large Responses**
    - Entire result set loaded into memory
    - Serialization of large objects
    - Response buffering consumes memory
    - Concurrent large requests exhaust heap
    - **Mitigation:** Streaming responses, pagination enforcement, memory monitoring

14. **Connection Pool Starvation**
    - Long-running requests hold connections
    - Peak traffic exhausts pool
    - Database connections not released
    - HTTP client connections not managed
    - **Mitigation:** Connection timeouts, pool sizing, connection release policies

15. **Cache Invalidation Complexity**
    - Stale data served from cache
    - Cache invalidation logic incorrect
    - Distributed cache consistency issues
    - Cache stampede on expiration
    - **Mitigation:** TTL-based caching, invalidation events, cache warming

### Error Handling Edge Cases

16. **Sensitive Information Leakage**
    - Stack traces exposed in errors
    - Database schema revealed in error messages
    - Internal service names leaked
    - File paths exposed
    - **Mitigation:** Generic error messages externally, detailed logs internally

17. **Inconsistent Error Responses**
    - Framework errors not caught
    - Serialization errors not handled
    - Validation errors lack detail
    - Third-party library exceptions not mapped
    - **Mitigation:** Comprehensive exception handler, test error scenarios

18. **Silent Failures**
    - Operations fail without proper error indication
    - Partial success not communicated
    - Error logged but not returned
    - Status code doesn't match reality
    - **Mitigation:** Explicit error handling, audit all code paths, comprehensive testing

### Documentation and Usability

19. **Documentation Drift**
    - API behavior changes but docs don't
    - Examples become outdated
    - Missing error scenarios
    - Undocumented endpoints
    - **Mitigation:** Generated documentation, automated testing against docs, version control

20. **Poor API Ergonomics**
    - Unintuitive endpoint naming
    - Inconsistent parameter conventions
    - Confusing response structures
    - Missing helpful error messages
    - **Mitigation:** API design review, developer feedback, usability testing

21. **Lack of Client SDK Support**
    - No official clients available
    - OpenAPI spec incomplete
    - Generated clients have issues
    - Authentication flow unclear
    - **Mitigation:** Complete OpenAPI spec, test generated clients, provide examples

### Operational Concerns

22. **Missing Observability**
    - Request tracing not implemented
    - Performance metrics not collected
    - Error rates not monitored
    - Usage patterns unknown
    - **Mitigation:** Request correlation, comprehensive metrics, dashboards

23. **Configuration Management**
    - Hard-coded values in code
    - Environment-specific config mixed
    - Secrets in configuration files
    - Configuration drift between environments
    - **Mitigation:** External configuration, secrets management, configuration validation

24. **Deployment Challenges**
    - Breaking changes during deployment
    - Old clients fail with new API
    - Migration path unclear
    - Rollback difficult
    - **Mitigation:** Blue-green deployment, feature flags, backward compatibility period

---

## Dependencies

- Domain Module (all services)
- Security Module (authentication and authorization)
- Common Module (utilities, exceptions)
- External: Spring Web, Springdoc OpenAPI, Jackson
- Monitoring Module (request metrics)

## Success Criteria

- 100% endpoint documentation coverage
- Response time p95 < 200ms for all endpoints
- Zero security vulnerabilities (OWASP Top 10)
- API passes contract testing
- Rate limiting prevents abuse
- Validation catches all invalid inputs
- Error responses are consistent and informative
- Support 1000 concurrent users
- OpenAPI spec generates valid clients
- Zero breaking changes within major version
