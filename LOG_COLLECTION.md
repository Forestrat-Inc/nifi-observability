# Log Collection Guide

This guide explains how to collect and view logs for NiFi processors using the NiFi Observability application.

## Overview

The log collection feature allows you to query and display logs from Grafana Loki for specific NiFi processors. Logs are filtered by processor ID and can be viewed for configurable time ranges. The system automatically handles timezone conversions, calculating time ranges based on your local system time while displaying results in your local timezone.

## Prerequisites

### Backend Configuration

The log collection feature requires Grafana/Loki credentials configured in your backend `.env` file:

```env
# Grafana/Loki Configuration
GRAFANA_URL=https://forestrat.grafana.net
GRAFANA_API_KEY=your_api_key_here
# OR use username/password:
# GRAFANA_USERNAME=your_username
# GRAFANA_PASSWORD=your_password

# Optional: Specify Loki datasource UID (auto-discovered if not set)
# LOKI_DATASOURCE_UID=grafanacloud-logs
```

### Log Format

The system expects logs in the following format from Grafana Loki:

```
{
  "body": "Log message content",
  "attributes": {
    "processor_id": "processor-uuid",
    "level": "INFO|WARN|ERROR|DEBUG",
    "logger": "org.apache.nifi.processor",
    "thread": "Timer-Driven Process Thread-2",
    "timestamp": "2025-10-31 10:33:55,868"
  },
  "resources": {
    "service.name": "nifi-local-instance",
    "service.version": "2.6.0"
  }
}
```

Logs must be labeled with `service_name="nifi-local-instance"` in Loki, and the processor ID must be available in the `attributes.processor_id` field after JSON parsing.

## Usage

### Via Web UI

1. **Navigate to Processor Page**: 
   - Go to the provenance page for a processor (e.g., `http://localhost:3000/provenance/{processor_id}`)
   - You can also search for a processor by ID from the dashboard

2. **View Logs**:
   - Click the "View Logs" button in the provenance page header
   - Logs will be fetched for the default time range (last 6 hours)

3. **Adjust Time Range**:
   - Use the time range selector dropdown to choose:
     - Last 1 hour
     - Last 3 hours
     - Last 6 hours (default)
     - Last 12 hours
     - Last 24 hours
     - Last 48 hours
   - The time range is calculated from your current local time

4. **Refresh Logs**:
   - Click the "Refresh" button to reload logs with the current time range
   - Changing the time range automatically refreshes the logs

5. **View Log Details**:
   - Each log entry displays:
     - Timestamp (in your local timezone)
     - Log level (INFO, WARN, ERROR, DEBUG) with color coding
     - Full log message body
     - Parsed attributes (processor ID, logger, thread, etc.)
     - Stream labels from Loki

### Via API

#### Endpoint

**GET** `/api/processors/{processor_id}/logs`

#### Query Parameters

- `processor_id` (path parameter): The NiFi processor UUID
- `limit` (optional): Maximum number of log entries to return (default: 100)
- `hours` (optional): Number of hours to look back (default: 6) - used if `start_time`/`end_time` not provided
- `start_time` (optional): Start time in ISO 8601 format (UTC) - e.g., `2025-10-31T16:29:00.000Z`
- `end_time` (optional): End time in ISO 8601 format (UTC) - e.g., `2025-10-31T17:29:00.000Z`

**Note**: If both `start_time` and `end_time` are provided, they override the `hours` parameter. Otherwise, the time range is calculated as `hours` back from the current UTC time.

#### Examples

**Example 1: Get logs for last 6 hours (default)**
```bash
curl "http://localhost:8000/api/processors/316a1e0e-019a-1000-212e-e85fe4b80549/logs?limit=100"
```

**Example 2: Get logs for last 1 hour**
```bash
curl "http://localhost:8000/api/processors/316a1e0e-019a-1000-212e-e85fe4b80549/logs?hours=1&limit=50"
```

**Example 3: Get logs for specific time range**
```bash
curl "http://localhost:8000/api/processors/316a1e0e-019a-1000-212e-e85fe4b80549/logs?start_time=2025-10-31T16:29:00.000Z&end_time=2025-10-31T17:29:00.000Z&limit=100"
```

**Example 4: Get logs for last 24 hours with limit**
```bash
curl "http://localhost:8000/api/processors/316a1e0e-019a-1000-212e-e85fe4b80549/logs?hours=24&limit=200"
```

#### Response Format

```json
{
  "processor_id": "316a1e0e-019a-1000-212e-e85fe4b80549",
  "total_logs": 42,
  "query_time": "2025-10-31T17:32:47.263756",
  "time_range": {
    "start": "2025-10-31T11:32:47.263756",
    "end": "2025-10-31T17:32:47.263756"
  },
  "logs": [
    {
      "timestamp": "2025-10-31T17:29:12.000000",
      "body": "ExecuteStreamCommand[id=303e3bd8-019a-1000-9cff-67c3ec2ea6e2] Transferring StandardFlowFileRecord[uuid=...]",
      "attributes": {
        "processor_id": "303e3bd8-019a-1000-9cff-67c3ec2ea6e2",
        "level": "INFO",
        "logger": "o.a.n.p.standard.ExecuteStreamCommand",
        "thread": "Timer-Driven Process Thread-2",
        "timestamp": "2025-10-31 10:33:55,868"
      },
      "resources": {
        "service.name": "nifi-local-instance",
        "service.version": "2.6.0"
      },
      "stream_labels": {
        "service_name": "nifi-local-instance"
      }
    }
  ]
}
```

#### Response Fields

- `processor_id`: The processor UUID that was queried
- `total_logs`: Number of log entries returned
- `query_time`: ISO 8601 timestamp (UTC) when the query was executed
- `time_range`: Object containing:
  - `start`: ISO 8601 timestamp (UTC) for the start of the time range
  - `end`: ISO 8601 timestamp (UTC) for the end of the time range
- `logs`: Array of log entries, each containing:
  - `timestamp`: ISO 8601 timestamp (UTC) of the log entry
  - `body`: The log message body
  - `attributes`: Parsed JSON attributes from the log
  - `resources`: Resource information (service name, version)
  - `stream_labels`: Loki stream labels

## Timezone Handling

The system handles timezones automatically:

1. **Frontend Calculation**: 
   - Time ranges (e.g., "last 6 hours") are calculated from your local system time
   - Example: If it's 1:29 PM EST, "last 1 hour" means 12:29 PM EST to 1:29 PM EST

2. **API Communication**: 
   - Local times are converted to UTC ISO 8601 format for API calls
   - Example: 12:29 PM EST becomes `2025-10-31T16:29:00.000Z` (UTC)

3. **Display**: 
   - Times are displayed in your local timezone with timezone abbreviation
   - Example: `10/31/2025, 12:29:12 PM EST`

4. **Backend Queries**: 
   - All queries to Loki use UTC timestamps (required by Loki API)
   - The backend converts and logs times in both UTC and EDT for debugging

## LogQL Query

The system generates the following LogQL query to filter logs:

```logql
{service_name="nifi-local-instance"} | json | attributes_processor_id="processor-uuid"
```

This query:
1. Filters logs by the `service_name` label
2. Parses JSON from log lines
3. Filters by `attributes_processor_id` matching the processor UUID

## Error Handling

### Common Errors

**401 Unauthorized**
- **Cause**: Invalid or expired Grafana API key
- **Solution**: Check your `GRAFANA_API_KEY` in `.env` and ensure it has proper permissions

**403 Forbidden**
- **Cause**: API key lacks necessary permissions
- **Solution**: Ensure the API key has "Datasource Query" permissions in Grafana

**404 Not Found**
- **Cause**: Loki datasource not found or invalid UID
- **Solution**: Check that the Loki datasource exists in Grafana, or let the system auto-discover it

**No Logs Returned**
- **Possible Causes**:
  - No logs exist for the processor in the time range
  - Processor ID doesn't match exactly (check for typos)
  - Time range is outside when logs were generated
  - Log format doesn't match expected structure
- **Solution**: 
  - Verify the processor ID is correct
  - Expand the time range
  - Check in Grafana directly if logs exist for this processor

## Troubleshooting

### Verify Configuration

1. **Check Environment Variables**:
   ```bash
   # In backend directory
   cat .env | grep GRAFANA
   ```

2. **Test API Key**:
   ```bash
   curl -H "Authorization: Bearer YOUR_API_KEY" \
        "https://forestrat.grafana.net/api/datasources"
   ```

3. **Check Backend Logs**:
   - Backend logs show the LogQL query and time ranges
   - Look for lines like:
     ```
     LogQL Query: {service_name="nifi-local-instance"} | json | attributes_processor_id="..."
     Query time range - Start (UTC): ..., End (UTC): ...
     ```

### Verify Log Format

Check in Grafana that your logs match the expected format:
1. Go to Grafana Explore
2. Query: `{service_name="nifi-local-instance"}`
3. Ensure logs have JSON structure with `attributes.processor_id` field

### Debug Timezone Issues

The backend logs include time ranges in both UTC and EDT:
```
Start Time - UTC: 2025-10-31T16:29:28.580373, EDT: 2025-10-31 12:29:28 PM UTC-04:00
End Time - UTC: 2025-10-31T17:29:28.580373, EDT: 2025-10-31 01:29:28 PM UTC-04:00
```

Compare these with what you see in Grafana to verify the query is targeting the correct time range.

## Best Practices

1. **Time Range Selection**: Start with shorter time ranges (1-6 hours) to avoid large result sets
2. **Limit Results**: Use appropriate `limit` values based on your needs (default: 100)
3. **Processor ID Verification**: Double-check processor IDs before querying
4. **Error Monitoring**: Monitor backend logs for authentication or query errors
5. **Performance**: Large time ranges (48+ hours) may take longer to query

## Integration with Provenance

The log collection feature integrates seamlessly with the provenance view:
- View logs alongside provenance events for the same processor
- Compare log timestamps with provenance event timestamps
- Debug processor behavior by correlating logs with provenance events

## API Reference Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/processors/{processor_id}/logs` | Get logs for a processor |
| GET | `/api/processors/{processor_id}` | Find processor by ID (navigate to provenance page) |

## Related Documentation

- [PROVENANCE_FLOW.md](./PROVENANCE_FLOW.md) - Guide for working with provenance events
- [README.md](./README.md) - General project documentation

