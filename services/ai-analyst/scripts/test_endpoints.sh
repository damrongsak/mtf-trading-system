# Function to make request and print details
make_request() {
    local method=$1
    local url=$2
    local data=$3

    echo "➡️  $method $url"
    if [ -n "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$url" -H "Content-Type: application/json" -d "$data")
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$url")
    fi

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    echo "⬅️  Status: $http_code"
    if [ "$http_code" -eq 200 ]; then
        echo "$body" | python3 -m json.tool
    else
        echo "❌ Error Body: $body"
    fi
    echo ""
}

# 1. Health Check
echo "1. Checking Health..."
make_request "GET" "$API_URL/health"

# 2. List Agents
echo "2. Listing Agents..."
make_request "GET" "$API_URL/api/v1/ai/agents"

# 3. Chat Session
echo "3. Testing Chat (Strategy Advisor - CoT)..."
make_request "POST" "$API_URL/api/v1/ai/chat/sessions/message" \
    '{
        "message": "What is a delta neutral strategy?",
        "user_id": "curl_user_test",
        "context_code": null
    }'
