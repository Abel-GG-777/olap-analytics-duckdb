#!/usr/bin/env bash
# Execute once from Google Cloud Shell with an authorized project administrator.
set -euo pipefail
: "${PROJECT_ID:?Export PROJECT_ID with your billed Google Cloud project ID}"
REGION="${REGION:-us-central1}"
REPO="Abel-GG-777/olap-analytics-duckdb"
gcloud config set project "$PROJECT_ID"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com iam.googleapis.com iamcredentials.googleapis.com sts.googleapis.com
NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
OWNER_ID=$(curl -fsSL "https://api.github.com/repos/$REPO" | python3 -c 'import sys,json; print(json.load(sys.stdin)["owner"]["id"])')
for ACCOUNT in olap-deployer olap-builder olap-runtime; do
  if ! gcloud iam service-accounts describe "$ACCOUNT@$PROJECT_ID.iam.gserviceaccount.com" >/dev/null 2>&1; then
    gcloud iam service-accounts create "$ACCOUNT"
  fi
done
DEPLOY="olap-deployer@$PROJECT_ID.iam.gserviceaccount.com"
BUILD="olap-builder@$PROJECT_ID.iam.gserviceaccount.com"
RUNTIME="olap-runtime@$PROJECT_ID.iam.gserviceaccount.com"
# run.admin is needed to make this demonstration service publicly invokable.
for ROLE in roles/run.admin roles/run.sourceDeveloper roles/serviceusage.serviceUsageConsumer; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$DEPLOY" --role="$ROLE" --condition=None --quiet
done
gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$BUILD" --role=roles/run.builder --condition=None --quiet
for SA in "$BUILD" "$RUNTIME"; do
  gcloud iam service-accounts add-iam-policy-binding "$SA" --member="serviceAccount:$DEPLOY" --role=roles/iam.serviceAccountUser --quiet
done
if ! gcloud iam workload-identity-pools describe github-olap --location=global >/dev/null 2>&1; then
  gcloud iam workload-identity-pools create github-olap --location=global --display-name="GitHub OLAP"
fi
if ! gcloud iam workload-identity-pools providers describe github --workload-identity-pool=github-olap --location=global >/dev/null 2>&1; then
  gcloud iam workload-identity-pools providers create-oidc github --location=global \
    --workload-identity-pool=github-olap --issuer-uri=https://token.actions.githubusercontent.com \
    --attribute-mapping='google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.repository_owner_id=assertion.repository_owner_id' \
    --attribute-condition="assertion.repository_owner_id == '$OWNER_ID' && assertion.repository == '$REPO' && assertion.ref == 'refs/heads/main'"
fi
gcloud iam service-accounts add-iam-policy-binding "$DEPLOY" \
  --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/projects/$NUMBER/locations/global/workloadIdentityPools/github-olap/attribute.repository/$REPO" --quiet
printf '\nRepository variables (Settings > Secrets and variables > Actions > Variables):\n'
printf 'GCP_PROJECT_ID=%s\nGCP_REGION=%s\nGCP_WIF_PROVIDER=projects/%s/locations/global/workloadIdentityPools/github-olap/providers/github\nGCP_DEPLOY_SERVICE_ACCOUNT=%s\nGCP_BUILD_SERVICE_ACCOUNT=%s\nGCP_RUNTIME_SERVICE_ACCOUNT=%s\n' "$PROJECT_ID" "$REGION" "$NUMBER" "$DEPLOY" "$BUILD" "$RUNTIME"
