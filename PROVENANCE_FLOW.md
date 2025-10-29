# Provenance Flow Guide

This guide explains how to work with NiFi Provenance events in the NiFi Observability application.

## Overview

Provenance events track the complete lineage of FlowFiles as they move through your NiFi flow. Each event represents a specific action taken on a FlowFile, such as:
- **CREATE**: FlowFile was created
- **RECEIVE**: FlowFile was received from an external source
- **FETCH**: FlowFile was fetched from a remote location
- **SEND**: FlowFile was sent to a remote destination
- **CLONE**: FlowFile was cloned
- **ATTRIBUTES_MODIFIED**: FlowFile attributes were modified
- **CONTENT_MODIFIED**: FlowFile content was modified
- **DROP**: FlowFile was dropped

## API Endpoints

### 1. Get Provenance Events for a Processor

Retrieve the latest provenance events for a specific processor.

**Endpoint:** `GET /api/provenance/{processor_id}`

**Query Parameters:**
- `max_results` (optional): Maximum number of events to return (default: 100, max: 1000)
- `start_date` (optional): Start date for filtering in ISO 8601 format
- `end_date` (optional): End date for filtering in ISO 8601 format

**Example:**
```bash
curl "http://localhost:8000/api/provenance/2ce4d9a2-019a-1000-b9a7-2a2fd2ebdb1e?max_results=50"
```

**Response:**
```json
{
  "processor_id": "2ce4d9a2-019a-1000-b9a7-2a2fd2ebdb1e",
  "total_events": 42,
  "events": [
    {
      "id": "211",
      "event_id": 211,
      "event_time": "10/29/2025 16:32:35.421 EDT",
      "event_type": "ATTRIBUTES_MODIFIED",
      "flowfile_uuid": "8c953604-7ec3-4435-9c83-47d4f1843435",
      "component_id": "2ce4d9a2-019a-1000-b9a7-2a2fd2ebdb1e",
      "component_type": "UpdateAttribute",
      "component_name": "UpdateAttribute",
      ...
    }
  ],
  "query_time": "2025-10-29T18:34:03.763000"
}
```

### 2. Query Provenance Events (POST)

Query provenance events using a request body for more complex queries.

**Endpoint:** `POST /api/provenance`

**Request Body:**
```json
{
  "processor_id": "2ce4d9a2-019a-1000-b9a7-2a2fd2ebdb1e",
  "max_results": 100,
  "start_date": "2025-10-28T00:00:00Z",
  "end_date": "2025-10-29T23:59:59Z"
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/api/provenance" \
  -H "Content-Type: application/json" \
  -d '{
    "processor_id": "2ce4d9a2-019a-1000-b9a7-2a2fd2ebdb1e",
    "max_results": 50
  }'
```

### 3. Get Provenance Event Details

Retrieve detailed information for a specific provenance event.

**Endpoint:** `GET /api/provenance-events/{event_id}`

**Example:**
```bash
curl "http://localhost:8000/api/provenance-events/215"
```

**Response:**
Returns full event details including all attributes, identifiers, transit URIs, and content claim information.

### 4. Get Provenance Event Content

Retrieve the input or output content for a specific provenance event.

**Endpoint:** `GET /api/provenance-events/{event_id}/content/{content_type}`

**Parameters:**
- `event_id`: The provenance event ID
- `content_type`: Either `"input"` or `"output"`

**Example:**
```bash
# Get input content
curl "http://localhost:8000/api/provenance-events/215/content/input"

# Get output content
curl "http://localhost:8000/api/provenance-events/215/content/output"
```

**Response:**
```json
{
  "event_id": "215",
  "content_type": "input",
  "data": "content data here...",
  "is_text": true,
  "size": 1234
}
```

For binary content, the data is base64-encoded and `is_text` will be `false`.

## Frontend Usage

### Accessing Provenance Events

1. **Navigate to a Processor:**
   - Open the Dashboard
   - Expand the process group hierarchy
   - Click on a processor with the gear icon (⚙️)
   - Click the "View Provenance" link

2. **View Provenance Events:**
   - The Provenance Page displays all events for the processor
   - Events are sorted by time (most recent first)
   - Each event shows:
     - Event Type (with color coding)
     - Event Time
     - FlowFile UUID
     - Component Name
     - Relationship (if applicable)
     - Transit URI (if applicable)
     - Content Size

3. **View Event Details:**
   - Click the "View Details" button on any event
   - Shows complete event information including:
     - All attributes (previous and updated)
     - Identifiers
     - Content claim information
     - Transit URIs
     - Details and relationships

4. **View Event Content:**
   - Click "View Input Content" to see the input data
   - Click "View Output Content" to see the output data
   - Content is displayed in a formatted code block
   - Binary content is shown as base64-encoded data

## How It Works

### Backend Process

1. **Query Submission:**
   - When you request provenance events, the backend submits a query to NiFi
   - The query uses `summarize: true` for fast results when available
   - NiFi returns a query ID and may return results immediately

2. **Polling (if needed):**
   - If results aren't immediately available, the backend polls NiFi
   - Polling continues until the query status is "FINISHED" or "FAILED"
   - Maximum polling time: 2 minutes (120 polls at 1-second intervals)

3. **Event Parsing:**
   - Events are parsed using Pydantic models
   - Supports both camelCase (from NiFi) and snake_case (for API)
   - Invalid events are logged as warnings but don't stop processing

4. **Cleanup:**
   - **IMPORTANT:** The backend automatically deletes the provenance query after processing
   - This happens in all scenarios:
     - When results are immediately available
     - After successful polling
     - On query failure
     - On timeout
     - On any error
   - This prevents orphaned queries in NiFi and ensures resource cleanup

### Event Types

Common event types you'll encounter:

| Event Type | Description |
|------------|-------------|
| `CREATE` | FlowFile was created |
| `RECEIVE` | FlowFile was received |
| `FETCH` | FlowFile was fetched |
| `SEND` | FlowFile was sent |
| `CLONE` | FlowFile was cloned |
| `ATTRIBUTES_MODIFIED` | FlowFile attributes changed |
| `CONTENT_MODIFIED` | FlowFile content changed |
| `DROP` | FlowFile was dropped |
| `REPLAY` | FlowFile was replayed |

## Best Practices

1. **Limit Results:**
   - Use `max_results` to limit the number of events returned
   - Default is 100, maximum is 1000
   - For large processors, start with a smaller limit

2. **Use Date Filters:**
   - Specify `start_date` and `end_date` to narrow results
   - Reduces query time and result size
   - Use ISO 8601 format: `YYYY-MM-DDTHH:MM:SSZ`

3. **Monitor Query Performance:**
   - Check backend logs for query timing
   - Large queries may take longer
   - Immediate results are faster than polling

4. **Content Retrieval:**
   - Only fetch content when needed (it can be large)
   - Input/output content may not be available for all events
   - Some events track metadata only, not content

## Troubleshooting

### No Events Returned

- Verify the processor ID is correct
- Check that the processor has processed FlowFiles
- Ensure NiFi Provenance Repository is configured
- Check backend logs for errors

### Query Timeout

- Reduce `max_results` or add date filters
- Check NiFi Provenance Repository health
- Verify network connectivity to NiFi

### Content Not Available

- Content may have been archived or purged
- Some event types don't store content (e.g., DROP events)
- Content Repository may be full or not configured

### Event Details Missing

- Some events may not have all fields populated
- Check that FlowFiles were successfully processed
- Verify NiFi Provenance Repository configuration

## API Documentation

For detailed API documentation, visit:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## Related Documentation

- [Quick Start Guide](QUICKSTART.md) - Getting started with the application
- [Testing Guide](TESTING.md) - How to test provenance functionality
- [Architecture Documentation](ARCHITECTURE.md) - System architecture overview

## Example Workflows

### Tracking a FlowFile Through the Flow

1. Start with a CREATE or RECEIVE event
2. Follow the FlowFile UUID through subsequent events
3. Use the event details to see attribute changes
4. Check transit URIs for external interactions
5. Find the final SEND or DROP event

### Debugging a Failed FlowFile

1. Find the DROP event for the FlowFile UUID
2. Look at the event details for error information
3. Check the "Details" field for failure reasons
4. Review previous events to see where issues occurred
5. View input/output content to verify data correctness

### Monitoring Processor Activity

1. Query events for a specific processor
2. Filter by date range for recent activity
3. Count events by type to understand processor behavior
4. Check event times to identify processing patterns
5. Review content sizes to monitor data volumes

