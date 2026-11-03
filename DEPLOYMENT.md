# Deployment: Cloudflare Workers (frontend) + Google Cloud Run (backend)

```
Browser ──► Cloudflare Worker (TanStack Start SSR + static assets)
   │
   └──────► Cloud Run service "deepfake-shield-api" (FastAPI + PyTorch CPU, 1 instance max)
```

The browser calls the API directly (CORS); the Worker also calls it during server-side rendering.

## Why the backend is configured this way

| Setting | Value | Reason |
| --- | --- | --- |
| `SYNC_ANALYSIS` | `true` | Cloud Run (request-based billing) throttles CPU once a response is sent, so a background task would crawl. The POST returns after the analysis finished (about 1.2 s per test video locally). |
| `--max-instances` | `1` | Records live in process memory. A second instance would not know analyses started on the first. It also caps cost. |
| uvicorn `--workers` | `1` | Same reason, inside the instance. |
| `--cpu` / `--memory` | `2` / `2Gi` | Measured peak 783 MiB over 31 analyses (see below). Headroom covers `/tmp`, which is held **in memory** on Cloud Run. |
| `--concurrency` | `8` | While one analysis runs, health checks, polling and frame images are still served. A second upload gets `503 Busy` instead of queueing. |
| `--timeout` | `300` | A 32 MB upload on a slow connection plus analysis. |
| Upload cap | 32,000,000 bytes | Cloud Run rejects HTTP/1 request bodies over 32 MiB (33,554,432 bytes) before they reach the app ([quotas](https://docs.cloud.google.com/run/quotas)). The 1.5 MB gap holds the multipart envelope. The frontend checks the size first, because Cloud Run's own 413 has no CORS headers and would look like a network error. |

### Hardening in the image

| Control | Env var (image default) | Behaviour |
| --- | --- | --- |
| Rate limit | `RATE_LIMIT_PER_HOUR=20` | Accepted analyses per client IP per hour. Excess requests get `429` + `Retry-After`. The IP is the **last** `X-Forwarded-For` hop (`TRUST_X_FORWARDED_FOR=true`), so a spoofed first hop doesn't help. |
| Busy response | `MAX_CONCURRENT_ANALYSES=1` | A second concurrent upload gets `503` + `Retry-After: 15`. It is rejected before the file is written. |
| Private history | `PROTECT_LIST=true`, `ADMIN_TOKEN` | `GET /api/v1/analyze` needs `Authorization: Bearer $ADMIN_TOKEN`. Without a token it is closed. The Investigations page then shows only analyses submitted from that browser (stored in `localStorage`). |
| Retention | `RETENTION_SECONDS=3600`, `MAX_RECORDS=200` | Finished records and their frame/heatmap JPEGs are deleted after 1 hour, or beyond the newest 200. Uploads are deleted as soon as the analysis ends. |
| CORS | `ALLOWED_ORIGINS` | Comma-separated list of origins, e.g. the `workers.dev` URL. |
| Privacy notice | (frontend) | The Analyze page states what is uploaded, what is kept and for how long (read from `/health`), and asks for consent of people shown. |
| Wake-up message | (frontend) | If `/health` has not answered after 1.5 s, the Analyze page shows "Waking up the server…" and retries for about a minute. |

### Measured locally (`docker run --cpus=2 --memory=2g`, Apple M4, arm64 image)

| | Value |
| --- | --- |
| Image size | 1.64 GB (CPU-only torch 2.14.1, Python 3.14) |
| Process start to `/health` OK | ~2 s (Cloud Run adds image pull and instance start; not measured yet) |
| Idle memory | 328 MiB |
| Peak memory, 1 analysis | 641 MiB |
| Peak memory, 31 consecutive analyses | 783 MiB (steady state ~490 MiB, no growth) |
| Request time per test video (upload + analysis, sync) | 0.7–1.5 s |

Before the Grad-CAM change on this branch, the peak was 1,969 MiB (see "Grad-CAM memory" at the end).

---

## 0. Prerequisites (once)

```bash
# Google Cloud SDK: https://cloud.google.com/sdk/docs/install
gcloud auth login
gcloud components update

# Cloudflare: wrangler runs through npx (pinned below); log in once
cd frontend && npx --yes wrangler@4.156.2 login && cd ..
```

Set these in your shell (all commands below use them):

```bash
export PROJECT_ID="deepfake-shield-XXXX"       # your GCP project id
export REGION="us-central1"                    # or asia-south1 (Mumbai) for lower latency in India
export SERVICE="deepfake-shield-api"
export REPO="deepfake-shield"
export TAG="$(git rev-parse --short HEAD)"
export IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO/api:$TAG"
```

## 1. Project, APIs and the image registry (once)

```bash
gcloud projects create "$PROJECT_ID"            # skip if it exists
gcloud config set project "$PROJECT_ID"
gcloud billing accounts list                    # note the ACCOUNT_ID
export BILLING_ACCOUNT="XXXXXX-XXXXXX-XXXXXX"
gcloud billing projects link "$PROJECT_ID" --billing-account="$BILLING_ACCOUNT"

gcloud services enable run.googleapis.com artifactregistry.googleapis.com \
  cloudbuild.googleapis.com secretmanager.googleapis.com billingbudgets.googleapis.com

gcloud artifacts repositories create "$REPO" \
  --repository-format=docker --location="$REGION" \
  --description="DeepFake Shield images"
```

## 2. Budget alert (once)

```bash
gcloud billing budgets create \
  --billing-account="$BILLING_ACCOUNT" \
  --display-name="deepfake-shield monthly" \
  --budget-amount=5USD \
  --filter-projects="projects/$PROJECT_ID" \
  --threshold-rule=percent=0.5 \
  --threshold-rule=percent=0.9 \
  --threshold-rule=percent=1.0 \
  --threshold-rule=percent=1.0,basis=forecasted-spend

gcloud billing budgets list --billing-account="$BILLING_ACCOUNT"
```

Alerts are emailed to the billing account's admins. **A budget only alerts; it does not stop spending.** The hard limits are `--max-instances=1`, scale to zero and the rate limit. Even in the worst case (one instance busy 24/7), the bill is bounded by a single 2 vCPU / 2 GiB instance-month, minus the free tier. Check current rates on [Cloud Run pricing](https://cloud.google.com/run/pricing).

## 3. Admin token for the history endpoint (once)

```bash
openssl rand -hex 24 | tr -d '\n' | gcloud secrets create deepfake-admin-token --data-file=-

PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
gcloud secrets add-iam-policy-binding deepfake-admin-token \
  --member="serviceAccount:$PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

Read it later with `gcloud secrets versions access latest --secret=deepfake-admin-token`.

## 4. Build and push the backend image

Cloud Build builds on linux/amd64 (what Cloud Run runs), so no local cross-build is needed. Run from the **repository root**. `.gcloudignore` uploads only the 18 files the image needs (~25 MB), not the datasets.

```bash
gcloud meta list-files-for-upload             # optional: check what gets uploaded
gcloud builds submit --config cloudbuild.yaml --substitutions=_IMAGE="$IMAGE" .
```

## 5. Deploy the backend

First deploy, before the frontend URL is known. Origins are added in step 7.

```bash
gcloud run deploy "$SERVICE" \
  --image="$IMAGE" \
  --region="$REGION" \
  --platform=managed \
  --allow-unauthenticated \
  --port=8080 \
  --cpu=2 \
  --memory=2Gi \
  --min-instances=0 \
  --max-instances=1 \
  --concurrency=8 \
  --timeout=300 \
  --cpu-boost \
  --set-env-vars="^@^SYNC_ANALYSIS=true@PROTECT_LIST=true@TRUST_X_FORWARDED_FOR=true@RATE_LIMIT_PER_HOUR=20@ALLOWED_ORIGINS=http://localhost:5173" \
  --set-secrets="ADMIN_TOKEN=deepfake-admin-token:latest"

export API_URL="$(gcloud run services describe "$SERVICE" --region="$REGION" --format='value(status.url)')"
echo "$API_URL"
curl -s "$API_URL/health"
```

`^@^` changes gcloud's list separator from `,` to `@`, so `ALLOWED_ORIGINS` can hold commas.

## 6. Build and deploy the frontend to Cloudflare

Vite bakes `VITE_*` values into the bundle at build time. Put them in `frontend/.env.production.local`. It is gitignored and wins over `.env.local`, which points at localhost.

```bash
cd frontend
cat > .env.production.local <<EOF
VITE_API_BASE_URL=$API_URL
VITE_USE_MOCK_DATA=false
EOF

npm ci
npm run cf:deploy     # vite build -> delete ._* files -> wrangler deploy
cd ..
```

Wrangler prints the Worker URL, e.g. `https://gokulm8-deep-fake-shield-frontend.<your-subdomain>.workers.dev`. The Worker name comes from the nitro Cloudflare preset (`.output/server/wrangler.json`).

> **exFAT drive note:** macOS writes `._*` AppleDouble files on the SanDisk drive. Wrangler uploads every `*.mjs`, including `._*.mjs`, and fails. `cf:deploy` and `cf:dev` delete them from `.output` first. For a local `docker build`, stream a clean context instead (see "Local container test").

## 7. Allow the frontend origin on the backend

```bash
export FRONTEND_URL="https://gokulm8-deep-fake-shield-frontend.<your-subdomain>.workers.dev"

gcloud run services update "$SERVICE" --region="$REGION" \
  --update-env-vars="^@^ALLOWED_ORIGINS=$FRONTEND_URL"
```

For a custom domain later, list both: `ALLOWED_ORIGINS=https://a.workers.dev,https://shield.example.com` (inside the `^@^` form).

## 8. Smoke test

```bash
# Health, limits and model
curl -s "$API_URL/health"

# CORS preflight from the frontend origin -> must echo the origin
curl -s -o /dev/null -D - -X OPTIONS "$API_URL/api/v1/analyze" \
  -H "Origin: $FRONTEND_URL" -H "Access-Control-Request-Method: POST" | grep -i access-control-allow-origin

# History is private
curl -s -o /dev/null -w "%{http_code}\n" "$API_URL/api/v1/analyze"                       # 401
curl -s -o /dev/null -w "%{http_code}\n" "$API_URL/api/v1/analyze" \
  -H "Authorization: Bearer $(gcloud secrets versions access latest --secret=deepfake-admin-token)"  # 200

# A real analysis (sync: returns status "completed")
curl -s -F "file=@datasets/raw/test/00272.mp4;type=video/mp4" "$API_URL/api/v1/analyze"
```

Then open `$FRONTEND_URL/analyze` and upload a video. After 15 or more idle minutes, the first visit should show "Waking up the server…".

## Redeploying

```bash
export TAG="$(git rev-parse --short HEAD)"
export IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO/api:$TAG"
gcloud builds submit --config cloudbuild.yaml --substitutions=_IMAGE="$IMAGE" .
gcloud run deploy "$SERVICE" --image="$IMAGE" --region="$REGION"   # keeps all other settings

cd frontend && npm run cf:deploy && cd ..                          # frontend changes
```

## Operations

```bash
gcloud run services logs read "$SERVICE" --region="$REGION" --limit=100
gcloud run services describe "$SERVICE" --region="$REGION"
gcloud run revisions list --service="$SERVICE" --region="$REGION"
gcloud run services update-traffic "$SERVICE" --region="$REGION" --to-revisions=REVISION=100   # roll back

cd frontend && npx --yes wrangler@4.156.2 --cwd .output tail     # Worker logs
```

**Tear down:** `gcloud run services delete "$SERVICE" --region="$REGION"`, `gcloud artifacts repositories delete "$REPO" --location="$REGION"`, and `npx wrangler@4.156.2 delete --name gokulm8-deep-fake-shield-frontend`.

## Known behaviour of this setup

- **Results vanish when the instance stops.** With `--min-instances=0`, Cloud Run stops an idle instance after roughly 15 minutes. All records and frame images go with it, and the Investigations page then shows nothing. `--min-instances=1` keeps them for the full retention hour, but an idle instance is billed around the clock.
- **Cold start.** The first request after idling waits for the 1.6 GB image to start and the model to load. The frontend shows the wake-up message meanwhile. `--cpu-boost` shortens it.
- **Shared limits.** The rate limit is per IP. Visitors behind one NAT (a campus network) share 20 analyses per hour. Raise `RATE_LIMIT_PER_HOUR` with `gcloud run services update --update-env-vars`.
- **Analysis links are bearer links.** Anyone with an analysis ID can open it until it expires. IDs carry 32 random bits.

## Local container test

```bash
# From the repository root. tar strips the exFAT ._* files that make `docker build .` fail.
COPYFILE_DISABLE=1 tar --no-xattrs --exclude='._*' --exclude='__pycache__' -cf - \
  backend/Dockerfile backend/requirements-deploy.txt backend/app \
  ml/data/video_dataset.py ml/models/efficientnet_baseline.py ml/models/video_heads.py \
  models/deepfake_shield_video_v1.pt models/deepfake_shield_meanpool_mlp_v1.pt models/deepfake_shield_temporal_v1.pt \
  | docker build -f backend/Dockerfile -t deepfake-shield-api:local -

docker run --rm --cpus=2 --memory=2g -p 8080:8080 \
  -e ALLOWED_ORIGINS=http://localhost:4173 -e ADMIN_TOKEN=dev deepfake-shield-api:local

# Peak memory of the running container (cgroup v2)
docker exec <container> sh -c 'echo $(( $(cat /sys/fs/cgroup/memory.peak) / 1048576 )) MiB'
```

Frontend against it: build with `VITE_API_BASE_URL=http://127.0.0.1:8080 VITE_USE_MOCK_DATA=false npm run build`, then `npm run cf:dev` (Workers runtime on http://localhost:4173). `vite preview` does not work with the Cloudflare preset.

## Grad-CAM memory

Grad-CAM used to backpropagate through the whole EfficientNet-B0 with trainable weights, so autograd kept every activation for 16 frames. That came to 1.97 GiB peak in a 2 GiB container. The served model's weights are now frozen (`requires_grad_(False)`), and the graph starts at the last feature block's output, which is all Grad-CAM needs. Outputs are unchanged within float32 rounding: frame scores within 1.1e-6, head score within 1.2e-7, Grad-CAM maps within 3.3e-5 on three test videos. Peak memory fell to 783 MiB and per-video time from 2–4.7 s to ~1.2 s.
