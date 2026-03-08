#!/bin/bash

# Open Interest Data Upload Script
# Usage: bash import_oi_data.sh <username> <password> <filepath>

if [ "$#" -lt 3 ]; then
    echo "Usage: $0 <username> <password> <filepath>"
    exit 1
fi

USERNAME=$1
PASSWORD=$2
FILEPATH=$3
API_URL=${API_URL:-"http://localhost:8000"}

if [ ! -f "$FILEPATH" ]; then
    echo "Error: File not found at $FILEPATH"
    exit 1
fi

echo "--- Authenticating as $USERNAME ---"

# Step 1: Login to get token
# The API expects form data: username and password
TOKEN_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/auth/token" \
    -d "username=$USERNAME" \
    -d "password=$PASSWORD")

# Extract token using grep/sed (minimal dependencies)
TOKEN=$(echo $TOKEN_RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo "Authentication failed. Response:"
    echo "$TOKEN_RESPONSE"
    exit 1
fi

echo "Successfully authenticated."

echo "--- Uploading OI Matrix: $FILEPATH ---"

# Step 2: Upload file
# The API expects multipart form data with 'file' key
UPLOAD_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/data/open-interest/upload" \
    -H "Authorization: Bearer $TOKEN" \
    -F "file=@$FILEPATH")

echo "Upload Response:"
echo "$UPLOAD_RESPONSE"

# Check success (assuming success_response pattern)
if echo "$UPLOAD_RESPONSE" | grep -q '"status":"success"'; then
    echo "OI data imported successfully!"
else
    echo "Upload failed or returned an error."
    exit 1
fi
