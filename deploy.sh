### deploy.sh

#!/usr/bin/env bash
# Minimal deploy script: build and push images to Artifact Registry then deploy to Cloud Run
set -e
PROJECT_ID=${PROJECT_ID:-line-bot-2b383}
IMAGE=gcr.io/$PROJECT_ID/mtf-api

docker build -t $IMAGE ./services/api-gateway
docker push $IMAGE
# Example: gcloud run deploy mtf-api --image $IMAGE --region=asia-southeast1 --platform=managed
