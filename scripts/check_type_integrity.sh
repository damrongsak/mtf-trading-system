#!/bin/bash
# scripts/check_type_integrity.sh
# CI script to verify API schema consistency and frontend type generation.

set -e

# 1. Verify Backend Schema Consistency
echo "--- Verifying Backend APIResponse Consistency ---"
python3 scripts/verify_api_schemas.py

# 2. Verify OpenAPI Spec Validity via Frontend Code Generation
echo -e "\n--- Verifying OpenAPI Spec Validity (Frontend Type Generation) ---"
if [ -d "frontend" ]; then
    cd frontend
    # Load NVM if available (common in dev environments)
    export NVM_DIR="$HOME/.nvm"
    [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
    
    # Run the generation script
    # We use pnpm run gen:api which runs openapi-generator-cli
    pnpm run gen:api
    cd ..
else
    echo "⚠️ Frontend directory not found, skipping generation check."
fi

echo -e "\n✨ Type Integrity Check Passed Successfully!"
