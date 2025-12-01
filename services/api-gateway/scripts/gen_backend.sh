#!/bin/bash

# Navigate to the service root directory
cd "$(dirname "$0")"/..

# Check for venv and use it if available
if [ -f "venv/bin/datamodel-codegen" ]; then
    CMD="venv/bin/datamodel-codegen"
else
    CMD="datamodel-codegen"
fi

echo "Generating Pydantic models from OpenAPI spec using $CMD..."

# Ensure the output directory exists
mkdir -p app/schemas

# Generate models
$CMD \
  --input ../../specs/02_api_spec.yaml \
  --output app/schemas/generated.py \
  --input-file-type openapi \
  --output-model-type pydantic_v2.BaseModel \
  --use-schema-description \
  --field-constraints \
  --snake-case-field \
  --allow-population-by-field-name

if [ $? -eq 0 ]; then
  echo "✅ Successfully generated Pydantic models in app/schemas/generated.py"
else
  echo "❌ Failed to generate models"
  exit 1
fi