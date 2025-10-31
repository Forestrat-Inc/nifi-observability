## Kafka REST Proxy - Producer and Consumer Quickstart

This guide shows how to produce and consume messages using Kafka REST Proxy with simple curl commands.

- **REST Proxy base URL**: `http://34.228.114.139:9092`
- **Topic**: `test_topic`

### 1) Produce a JSON message (with key)

```bash
curl -X POST "http://34.228.114.139:9092/topics/test_topic" \
  -H "Content-Type: application/vnd.kafka.json.v2+json" \
  -d '{"records":[{"key":"my-key-2","value":{"msg":"with key 2"}}]}'
```

- **Content-Type**: `application/vnd.kafka.json.v2+json`
- Sends one record with key `my-key-2` and JSON value `{ "msg": "with key 2" }`.

If successful, you will get an offsets array with the assigned partition and offset.

### 2) Create a consumer instance

Create a consumer in consumer group `manispace-test-new` with instance name `c1`.

```bash
curl -X POST "http://34.228.114.139:9092/consumers/manispace-test-new" \
  -H "Content-Type: application/vnd.kafka.v2+json" \
  -d '{
    "name": "c1",
    "format": "json",
    "auto.offset.reset": "earliest",
    "enable.auto.commit": false
  }'
```

Notes:
- `format: json` expects JSON-encoded values when reading.
- `auto.offset.reset: earliest` reads from the beginning if no committed offset exists.
- `enable.auto.commit: false` means you manage commits manually (not shown here).

The response includes the base URI for the instance (e.g. `/consumers/manispace-test-new/instances/c1`).

### 3) Subscribe the consumer to the topic

```bash
curl -X POST "http://34.228.114.139:9092/consumers/manispace-test-new/instances/c1/subscription" \
  -H "Content-Type: application/vnd.kafka.v2+json" \
  -d '{"topics":["test_topic"]}'
```

### 4) Consume records

Fetch records from the subscribed topic(s).

```bash
curl -X GET "http://34.228.114.139:9092/consumers/manispace-test-new/instances/c1/records?timeout=2000&max_bytes=524288" \
  -H "Accept: application/vnd.kafka.json.v2+json"
```

Parameters:
- `timeout`: server-side wait time in ms (e.g., `2000`).
- `max_bytes`: maximum bytes to return in one response.

The response is a JSON array of records with `key`, `value`, `partition`, `offset`, and `timestamp`.

Repeat this request to continue consuming.

### 5) Delete the consumer instance (cleanup)

When done, delete the consumer to release server resources.

```bash
curl -X DELETE "http://34.228.114.139:9092/consumers/manispace-test-new/instances/c1"
```

### Common MIME types (Kafka REST Proxy)

- Produce JSON: `application/vnd.kafka.json.v2+json`
- Consume JSON: `application/vnd.kafka.json.v2+json`
- Control (create/subscribe/delete): `application/vnd.kafka.v2+json`

### Tips

- If you need to produce/consume Avro or binary, use the corresponding `application/vnd.kafka.*` media types.
- If `enable.auto.commit` is false, explicitly commit offsets via the commit API if you need durable progress.
- For repeated consumption, keep the consumer instance alive and call the `records` endpoint in a loop.


