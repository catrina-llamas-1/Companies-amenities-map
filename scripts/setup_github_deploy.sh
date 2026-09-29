#!/usr/bin/env bash
# One-time setup: lets this repo's GitHub Actions deploy to Firebase Hosting
# without a service-account key (Workload Identity Federation). Works when the
# organisation policy iam.disableServiceAccountKeyCreation is enforced.
#
# Run it in Google Cloud Shell (https://shell.cloud.google.com), signed in as an
# owner of the Firebase project:
#   git clone https://github.com/catrina-llamas-1/Companies-amenities-map.git
#   bash Companies-amenities-map/scripts/setup_github_deploy.sh
#
# At the end it prints two values to add as GitHub repository variables.
# Safe to run again: anything that already exists is reused.

set -euo pipefail

PROJECT_ID="${PROJECT_ID:-stony-plain-rd-companies-map}"
REPO="${REPO:-catrina-llamas-1/Companies-amenities-map}"
SA_NAME="github-deploy"
POOL="github"
PROVIDER="github-repo"
SA="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "Project: ${PROJECT_ID}"
echo "Repo:    ${REPO}"
gcloud config set project "${PROJECT_ID}" >/dev/null

echo "== Enabling APIs"
gcloud services enable iam.googleapis.com iamcredentials.googleapis.com sts.googleapis.com \
  firebasehosting.googleapis.com cloudresourcemanager.googleapis.com

echo "== Service account ${SA}"
if ! gcloud iam service-accounts describe "${SA}" >/dev/null 2>&1; then
  gcloud iam service-accounts create "${SA_NAME}" --display-name="GitHub Actions deploy"
fi

echo "== Granting deploy roles"
for role in roles/firebasehosting.admin roles/run.viewer \
            roles/serviceusage.apiKeysViewer roles/serviceusage.serviceUsageConsumer; do
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${SA}" --role="${role}" --condition=None >/dev/null
  echo "   ${role}"
done

echo "== Workload identity pool '${POOL}'"
if ! gcloud iam workload-identity-pools describe "${POOL}" --location=global >/dev/null 2>&1; then
  gcloud iam workload-identity-pools create "${POOL}" --location=global --display-name="GitHub Actions"
fi
POOL_NAME="$(gcloud iam workload-identity-pools describe "${POOL}" --location=global --format='value(name)')"

echo "== OIDC provider '${PROVIDER}' (only ${REPO} can use it)"
if ! gcloud iam workload-identity-pools providers describe "${PROVIDER}" \
      --location=global --workload-identity-pool="${POOL}" >/dev/null 2>&1; then
  gcloud iam workload-identity-pools providers create-oidc "${PROVIDER}" \
    --location=global --workload-identity-pool="${POOL}" \
    --display-name="GitHub repo" \
    --issuer-uri="https://token.actions.githubusercontent.com" \
    --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
    --attribute-condition="assertion.repository=='${REPO}'"
fi

echo "== Letting ${REPO} act as ${SA}"
gcloud iam service-accounts add-iam-policy-binding "${SA}" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/${POOL_NAME}/attribute.repository/${REPO}" >/dev/null

cat <<EOF

Done. Now add these two repository VARIABLES in GitHub
(repo -> Settings -> Secrets and variables -> Actions -> Variables tab -> New repository variable):

  Name:  GCP_WORKLOAD_IDENTITY_PROVIDER
  Value: ${POOL_NAME}/providers/${PROVIDER}

  Name:  GCP_SERVICE_ACCOUNT
  Value: ${SA}

EOF
