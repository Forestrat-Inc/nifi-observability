#!/bin/bash
# Test provenance query with username/password

# Configuration
NIFI_URL="https://localhost:8443/nifi-api"
USERNAME="admin"
PASSWORD="shark4d12345"
PROCESSOR_ID="${1:-de4b7681-0199-1000-ffff-ffffcf4d6c3e}"
MAX_RESULTS="${2:-10}"

echo "=== Step 1: Get Access Token ==="
TOKEN=$(curl -k -s -X POST "${NIFI_URL}/access/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=${USERNAME}&password=${PASSWORD}")

if [ -z "$TOKEN" ]; then
    echo "❌ Failed to get access token"
    exit 1
fi

echo "✅ Token obtained (length: ${#TOKEN})"

echo -e "\n=== Step 2: Submit Provenance Query ==="
QUERY_RESPONSE=$(curl -k -s -X POST "${NIFI_URL}/provenance" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -d "{
    \"provenance\": {
      \"request\": {
        \"incrementalResults\": false,
        \"maxResults\": ${MAX_RESULTS},
        \"summarize\": true,
        \"searchTerms\": {
          \"ProcessorID\": {
            \"value\": \"${PROCESSOR_ID}\",
            \"inverse\": false
          }
        }
      }
    }
  }")

echo "$QUERY_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$QUERY_RESPONSE"

QUERY_ID=$(echo "$QUERY_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['provenance']['id'])" 2>/dev/null)

if [ -z "$QUERY_ID" ]; then
    echo "❌ Failed to get query ID"
    exit 1
fi

echo -e "\n✅ Query ID: ${QUERY_ID}"

echo -e "\n=== Step 3: Poll for Results ==="
MAX_POLLS=120
POLL_INTERVAL=1

for i in $(seq 1 $MAX_POLLS); do
    sleep $POLL_INTERVAL
    RESULT=$(curl -k -s -X GET "${NIFI_URL}/provenance/${QUERY_ID}" \
      -H "Authorization: Bearer ${TOKEN}")
    
    STATUS=$(echo "$RESULT" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['provenance']['status'])" 2>/dev/null)
    
    echo -n "Poll $i/$MAX_POLLS: Status = $STATUS"
    
    if [ "$STATUS" = "FINISHED" ]; then
        echo -e "\n✅ Query completed!"
        echo "$RESULT" | python3 -m json.tool
        break
    elif [ "$STATUS" = "FAILED" ]; then
        echo -e "\n❌ Query failed!"
        echo "$RESULT" | python3 -m json.tool
        exit 1
    else
        echo " (still running...)"
    fi
done

if [ "$STATUS" != "FINISHED" ]; then
    echo -e "\n⚠️  Query timed out after $MAX_POLLS polls"
fi

echo -e "\n=== Step 4: Clean Up Query ==="
curl -k -s -X DELETE "${NIFI_URL}/provenance/${QUERY_ID}" \
  -H "Authorization: Bearer ${TOKEN}" > /dev/null

if [ $? -eq 0 ]; then
    echo "✅ Query deleted"
else
    echo "⚠️  Failed to delete query"
fi

