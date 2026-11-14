# Deploy Card2Contact to Google Cloud Run (PowerShell).
# Usage: .\deploy.ps1 -Project <project-id>
# Requires: gcloud CLI, "gcloud auth login", billing enabled on the project.
param(
    [Parameter(Mandatory = $true)][string]$Project,
    [string]$Region = "europe-central2"
)
$ServiceAccount = "card2contact-run@$Project.iam.gserviceaccount.com"

# 1. Turn on the Google Cloud services the app needs (safe to repeat).
gcloud services enable aiplatform.googleapis.com run.googleapis.com `
    cloudbuild.googleapis.com artifactregistry.googleapis.com --project=$Project

# 2. Service account for the server with one permission: call Vertex AI.
#    This replaces an API key: Cloud Run gets short-lived tokens for this account automatically.
$existing = gcloud iam service-accounts list --project=$Project `
    --filter="email:$ServiceAccount" --format="value(email)"
if (-not $existing) {
    gcloud iam service-accounts create card2contact-run --display-name="Card2Contact Cloud Run" --project=$Project
}
gcloud projects add-iam-policy-binding $Project --member="serviceAccount:$ServiceAccount" `
    --role="roles/aiplatform.user" --condition=None --format="none"

# 3. Build the image from the Dockerfile in Cloud Build, store it in Artifact Registry
#    and start it on Cloud Run with a public URL. At most 2 instances to keep the cost tiny.
gcloud run deploy card2contact --source . --region=$Region --project=$Project `
    --service-account=$ServiceAccount --set-env-vars="GOOGLE_CLOUD_PROJECT=$Project" `
    --allow-unauthenticated --max-instances=2 --memory=512Mi --quiet
